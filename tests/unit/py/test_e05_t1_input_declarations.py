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
