"""Admission/schema controls do not regenerate any CLI or scientific witness."""

import pytest

from tests.fixtures.e05_t1 import declarations, stop_projects


def experiment(project, text, name='bank'):
    folder = project / 'experiments'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / (name + '.edi')).write_text('data_' + name + '\n' + text)


@pytest.mark.parametrize(
    'text',
    [
        'loop_\n_data.two_theta\n_data.intensity_meas\n20 0\n',
        'loop_\n_refln.index_h\n_refln.index_k\n_refln.index_l\n_refln.intensity_meas\n0 0 1 0\n',
    ],
    ids=['powder', 'reflections'],
)
def test_measured_declarations_admit_both_families_even_with_simulation_in_the_id(tmp_path, text):
    project = tmp_path / 'measured_simulation'
    experiment(project, text)
    assert declarations.has_measured_data(project), (
        'Actual measured columns, including zeros, own admission'
    )


@pytest.mark.parametrize(
    'text',
    [
        (
            '_data_range.two_theta_min 10\n'
            '_data_range.two_theta_max 90\n_data_range.two_theta_step 1\n'
        ),
        'loop_\n_data.two_theta\n_data.intensity_calc\n20 1\n',
        'loop_\n_refln.index_h\n_refln.intensity_calc\n1 1\n',
        '_note.text "_data.intensity_meas"\n# _refln.intensity_meas\n',
        '_note.text\n;\n_data.intensity_meas\n;\n',
    ],
    ids=['range', 'calculated-powder', 'calculated-reflections', 'quoted-comment', 'multiline'],
)
def test_range_calculated_and_quoted_tag_text_are_not_measured_data(tmp_path, text):
    experiment(tmp_path, text)
    assert not declarations.has_measured_data(tmp_path), (
        'Neither ranges nor calculated-only/tag-like text admits'
    )


def test_any_actual_experiment_may_supply_the_measurement(tmp_path):
    experiment(tmp_path, '_data_range.two_theta_min 10\n', 'a_range_only')
    assert not declarations.has_measured_data(tmp_path), 'The initial range-only control is armed'
    experiment(tmp_path, '_refln.intensity_meas 0\n', 'z_measured')
    banks = sorted((tmp_path / 'experiments').glob('*.edi'))
    assert [bank.name for bank in banks] == ['a_range_only.edi', 'z_measured.edi'], (
        'The range-only bank is actually visited before the independently measured later bank'
    )
    assert banks[0].read_text() == 'data_a_range_only\n_data_range.two_theta_min 10\n', (
        'The actual first bank contains a range declaration and no measured column'
    )
    assert banks[1].read_text() == 'data_z_measured\n_refln.intensity_meas 0\n', (
        'The actual later bank supplies the declared measured reflection, including literal zero'
    )
    assert declarations.has_measured_data(tmp_path), (
        'A later bank with measured reflections admits the project'
    )


@pytest.mark.parametrize('version', ['2', '3', '4'])
@pytest.mark.parametrize('before', [False, True])
def test_body_replacement_retains_the_actual_schema_independent_of_order(version, before):
    schema = '_edi.schema_version ' + version + '\n'
    text = 'data_bank\n' + (schema if before else '') + '_background.type polynomial\n'
    text += '' if before else schema
    prefix = stop_projects.background_prefix(text)
    assert prefix.count('_edi.schema_version') == 1, (
        'Body replacement retains one actual declaration'
    )
    assert schema in prefix, 'The actual supported version survives, rather than an older default'
    assert '_background.type' not in prefix, 'Only the intended old background body is replaced'


@pytest.mark.parametrize(
    'schema', ['', '_edi.schema_version 1\n', '_edi.schema_version 3\n_edi.schema_version 4\n']
)
def test_body_replacement_cannot_invent_missing_unknown_or_duplicate_schema(schema):
    assert '_edi.schema_version 3\n' in stop_projects.background_prefix(
        'data_bank\n_background.type polynomial\n_edi.schema_version 3\n'
    ), 'The supported normal-writer control is armed before each schema adversary'
    with pytest.raises((ValueError, RuntimeError), match='schema_version'):
        stop_projects.background_prefix('data_bank\n_background.type polynomial\n' + schema)


@pytest.mark.parametrize('body_first', [False, True])
def test_body_replacement_preserves_complete_actual_profile_calibration_and_relations(body_first):
    retained = (
        '_edi.schema_version 3\n'
        '_experiment_type.beam_mode "constant wavelength"\n'
        '_peak.type cwl-tch-pseudo-voigt\n'
        '_peak.broad_gauss_u 0.1\n_peak.broad_gauss_v -0.1\n_peak.broad_gauss_w 0.1\n'
        '_peak.broad_lorentz_x 0.\n_peak.broad_lorentz_y 0.001\n'
        '_instrument.setup_wavelength 1.494\n_instrument.calib_twotheta_offset 0.6\n'
        'loop_\n_preferred_orientation.structure_id\n_preferred_orientation.march_random_fract\n'
        'lbco 0.\n'
        'loop_\n_linked_structure.structure_id\n_linked_structure.scale\nlbco 10.0\n'
        '_instrument.name "literal _data.intensity_meas"\n'
    )
    replaced = (
        '_background.type line-segment\n'
        'loop_\n_background.id\n_background.position\n_background.intensity\nold 35 0\n'
        'loop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n40 -1 1\n'
    )
    source = 'data_bank\n' + (replaced + retained if body_first else retained + replaced)
    assert stop_projects.background_prefix(source) == 'data_bank\n' + retained, (
        'Only the actual background/measured categories are replaced; every saved typed profile, '
        'calibration and relation token survives verbatim on either side of them'
    )


def test_body_replacement_refuses_to_discard_nonowned_columns_in_a_shared_loop():
    valid = 'data_bank\n_edi.schema_version 3\n_background.type line-segment\n'
    assert stop_projects.background_prefix(valid) == 'data_bank\n_edi.schema_version 3\n', (
        'The normal independent-category source is valid before the mixed-category adversary'
    )
    with pytest.raises(ValueError, match='mixing owned and retained'):
        stop_projects.background_prefix(
            valid + 'loop_\n_data.two_theta\n_peak.broad_gauss_u\n40 0.1\n'
        )


@pytest.mark.parametrize('boundary', ['retained-owned-pair', 'owned-retained-pair', 'loop-tail'])
def test_body_replacement_refuses_ambiguous_physical_item_boundaries(boundary):
    retained = '_edi.schema_version 3\n_peak.type cwl-tch-pseudo-voigt\n'
    background = '_background.type line-segment\n'
    measured = 'loop_\n_data.two_theta\n_data.intensity_meas\n40 -1\n'
    instrument = '_instrument.setup_wavelength 1.494\n'
    source = 'data_bank\n' + retained + background + measured + instrument
    assert stop_projects.background_prefix(source) == 'data_bank\n' + retained + instrument, (
        'The exact normal separate-line tokens are retained before each boundary adversary'
    )
    if boundary == 'retained-owned-pair':
        source = source.replace(
            'cwl-tch-pseudo-voigt\n_background', 'cwl-tch-pseudo-voigt _background'
        )
    elif boundary == 'owned-retained-pair':
        source = source.replace(
            '_background.type line-segment\nloop_',
            '_background.type line-segment _instrument.name HRPT\nloop_',
        )
    else:
        source = source.replace('40 -1\n_instrument', '40 -1 _instrument')
    with pytest.raises(ValueError, match='canonical physical item starts'):
        stop_projects.background_prefix(source)


def test_body_replacement_retains_canonical_comments_quoted_and_multiline_values():
    retained = (
        '_edi.schema_version 3\n'
        '# literal _background.type line-segment and loop_ are comments\n'
        '_peak.type "cwl-tch-pseudo-voigt"\n'
        '_instrument.name\n;\nHRPT with literal _data.intensity_meas\n;\n'
    )
    source = 'data_bank\n' + retained + '_background.type line-segment\n'
    assert stop_projects.background_prefix(source) == 'data_bank\n' + retained, (
        'Validated line boundaries preserve complete raw quoted/comment/multiline tokens '
        'without confusing their contents with a replaceable category'
    )


@pytest.mark.parametrize('separator', ['\u0085', '\u2028', '\u2029'])
@pytest.mark.parametrize('new_line', ['\n', '\r\n'], ids=['lf', 'crlf'])
@pytest.mark.parametrize('location', ['comment', 'semicolon'])
def test_body_replacement_preserves_non_lf_data_in_parser_line_coordinates(
    separator, new_line, location
):
    def source_with(fragment):
        value = (
            '# retained comment' + fragment + '_background.type\n'
            if location == 'comment'
            else '_instrument.name\n;\nHRPT' + fragment + '_background.type\n;\n'
        )
        retained = '_edi.schema_version 3\n' + value
        source = 'data_bank\n' + retained + '_background.type line-segment\n'
        expected = 'data_bank\n' + retained
        return source.replace('\n', new_line), expected.replace('\n', new_line)

    canonical, expected = source_with(' ')
    assert stop_projects.background_prefix(canonical) == expected, (
        'The same canonical writer layout is admitted before the non-LF comment/value contrast'
    )
    source, expected = source_with(separator)
    assert stop_projects.background_prefix(source) == expected, (
        'Unicode data containing a tag-like fragment preserves every comment/semicolon byte; '
        'only parser LF coordinates locate the actual owned declaration'
    )
