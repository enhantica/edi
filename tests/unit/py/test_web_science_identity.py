"""Independent identity/role escapes; no product imports or generated numeric pins."""

import copy
import hashlib
import json

import pytest

from tests.fixtures.project_save.reference import declared_rule
from tests.fixtures.web_parallel import science_identity as bridge
from tests.fixtures.web_parallel.numeric import compare_scientific


def reference():
    # Literal declared storage identities, not an output of a writer or fit.
    return {
        'structures/sample.edi': [
            ['_cell.length_a', '1.234(.01)'],
            ['_space_group.it_number', '1'],
            ['_atom_site.id', '_atom_site.fract_x', 'A', '0.25'],
            ['_atom_site.id', '_atom_site.fract_x', 'B', '0.75'],
        ],
        'experiments/bank.edi': [
            ['_peak.type', 'cwl-tch-pseudo-voigt'],
            ['_background.id', '_background.position', '_background.intensity', '1', '0', '4()'],
            ['_linked_structure.structure_id', '_linked_structure.scale', 'sample', '2()'],
            ['_instrument.calib_twotheta_offset', '0.3()'],
            ['_data.two_theta', '_data.id', '_data.intensity_meas', '10', '1', '100'],
            ['_data.two_theta', '_data.id', '_data.intensity_meas', '11', '2', '110'],
        ],
        'analysis/analysis.edi': [
            ['_fit_result.iterations', '2'],
            ['_fit_result_bank.experiment_id', '_fit_result_bank.chi_square', 'bank', '1.2'],
            [
                '_fit_result_phase.experiment_id',
                '_fit_result_phase.structure_id',
                '_fit_result_phase.bragg_r_factor',
                'bank',
                'sample',
                '0.1',
            ],
        ],
    }


BLOCKS = {
    'structures/sample.edi': 'sample',
    'experiments/bank.edi': 'bank',
    'analysis/analysis.edi': 'analysis',
}


def align(actual, frozen):
    return bridge.align_to_frozen(actual, frozen, actual_blocks=BLOCKS, frozen_blocks=BLOCKS)


def test_category_order_only_aligns_without_changing_old_coordinates_or_bytes():
    frozen = reference()
    before = json.dumps(frozen)
    actual = copy.deepcopy(frozen)
    actual['structures/sample.edi'] = [
        *actual['structures/sample.edi'][2:],
        actual['structures/sample.edi'][1],
        actual['structures/sample.edi'][0],
    ]
    actual['analysis/analysis.edi'].reverse()  # Distinct categories, one record each.
    assert actual != frozen, (
        'Required: category order only aligns without changing old coordinates or bytes.'
    )
    aligned = align(actual, frozen)
    assert aligned == frozen, (
        'Required: category order only aligns without changing old coordinates or bytes.'
    )
    assert compare_scientific(aligned, frozen), (
        'Required: category order only aligns without changing old coordinates or bytes.'
    )
    assert json.dumps(frozen) == before, (
        'Required: category order only aligns without changing old coordinates or bytes.'
    )
    # An actual measurement corruption still reaches the unchanged comparator.
    actual['experiments/bank.edi'][-1][-1] = '111'
    with pytest.raises(ValueError, match='operand'):
        compare_scientific(align(actual, frozen), frozen)


@pytest.mark.parametrize(
    'mutation',
    [
        'missing-bank',
        'renamed-bank',
        'missing-row',
        'duplicate-row',
        'renamed-site',
        'duplicate-column',
        'missing-column',
        'renamed-column',
        'data-order',
        'duplicate-data-id',
        'unknown-bank',
        'unknown-link',
    ],
)
def test_identity_mutations_refuse_after_the_genuine_positive(mutation):
    frozen = reference()
    assert align(frozen, frozen) == frozen, (
        'Required: identity mutations refuse after the genuine positive.'
    )
    actual = copy.deepcopy(frozen)
    experiment = actual['experiments/bank.edi']
    structure = actual['structures/sample.edi']
    if mutation == 'missing-bank':
        del actual['experiments/bank.edi']
    elif mutation == 'renamed-bank':
        actual['experiments/other.edi'] = actual.pop('experiments/bank.edi')
    elif mutation == 'missing-row':
        structure.pop()
    elif mutation == 'duplicate-row':
        structure.append(list(structure[-1]))
    elif mutation == 'renamed-site':
        structure[-1][2] = 'C'
    elif mutation == 'duplicate-column':
        structure[-1][1] = structure[-1][0]
    elif mutation == 'missing-column':
        structure[-1] = [structure[-1][0], structure[-1][2]]
    elif mutation == 'renamed-column':
        structure[-1][1] = '_atom_site.fract_y'
    elif mutation == 'data-order':
        experiment[-2:] = reversed(experiment[-2:])
    elif mutation == 'duplicate-data-id':
        experiment[-1][-2] = experiment[-2][-2]
    elif mutation == 'unknown-bank':
        actual['analysis/analysis.edi'][1][2] = 'other'
    else:
        experiment[2][2] = 'other'
    with pytest.raises(ValueError, match='identity'):
        align(actual, frozen)


def test_site_row_order_is_not_normalized():
    frozen = reference()
    assert align(frozen, frozen) == frozen, 'Required: site row order is not normalized.'
    actual = copy.deepcopy(frozen)
    actual['structures/sample.edi'][-2:] = reversed(actual['structures/sample.edi'][-2:])
    with pytest.raises(ValueError, match='inventory or order'):
        align(actual, frozen)


def test_actual_block_name_is_mandatory_and_cannot_be_inferred_from_the_path():
    frozen = reference()
    with pytest.raises(ValueError, match='document/block'):
        bridge.align_to_frozen(frozen, frozen, actual_blocks={}, frozen_blocks=BLOCKS)
    changed = {**BLOCKS, 'experiments/bank.edi': 'other'}
    with pytest.raises(ValueError, match='identity'):
        bridge.align_to_frozen(frozen, frozen, actual_blocks=changed, frozen_blocks=BLOCKS)


def test_coherent_renamed_bank_still_cannot_retarget_the_independent_reference():
    frozen = reference()
    assert align(frozen, frozen) == frozen, (
        'Required: coherent renamed bank still cannot retarget the independent reference.'
    )
    actual = copy.deepcopy(frozen)
    actual['analysis/analysis.edi'][1][2] = 'renamed'
    actual['analysis/analysis.edi'][2][3] = 'renamed'
    blocks = {**BLOCKS, 'experiments/bank.edi': 'renamed'}
    # The changed source is internally coherent; refusal must reach correspondence.
    assert bridge.semantic_index(actual, blocks), (
        'Required: coherent renamed bank still cannot retarget the independent reference.'
    )
    with pytest.raises(ValueError, match='inventory or order'):
        bridge.align_to_frozen(actual, frozen, actual_blocks=blocks, frozen_blocks=BLOCKS)


def test_column_identity_is_semantic_but_old_tag_coordinates_are_unchanged():
    frozen = reference()
    actual = copy.deepcopy(frozen)
    actual['structures/sample.edi'][2] = ['_atom_site.fract_x', '_atom_site.id', '0.25', 'A']
    assert align(actual, frozen) == frozen, (
        'Required: column identity is semantic but old tag coordinates are unchanged.'
    )


@pytest.mark.parametrize(
    ('rule', 'token', 'literal'),
    [
        (None, '0.1234(.0196)', '0.123(20)'),
        ('iucr_99', '0.1234(.0196)', '0.123(20)'),
        ('iucr_19', '0.1234(.0196)', '0.12(2)'),
        ('iucr_99', '-0.1234(.0196)', '-0.123(20)'),
        ('iucr_19', '-0.1234(.0196)', '-0.12(2)'),
        (None, '2.125()', '2.125()'),
        (None, '2.125(0)', '2.125(0)'),
        (None, '2.125', '2.125'),
    ],
)
def test_first_decimal_reference_projects_declared_rule_and_parameter_role(rule, token, literal):
    assert bridge.projected_parameter(token, rule) == literal, (
        'Required: first decimal reference projects declared rule and parameter role.'
    )


def test_wrong_rule_and_absent_zero_free_mutations_remain_distinguishable():
    expected = bridge.projected_parameter('0.1234(.0196)', 'iucr_99')
    assert expected == '0.123(20)', (
        'Required: wrong rule and absent zero free mutations remain distinguishable.'
    )
    assert bridge.projected_parameter('0.1234(.0196)', 'iucr_19') != expected, (
        'Required: wrong rule and absent zero free mutations remain distinguishable.'
    )
    roles = [bridge.projected_parameter(token, None) for token in ('2.125', '2.125()', '2.125(0)')]
    assert len(set(roles)) == 3, (
        'Required: wrong rule and absent zero free mutations remain distinguishable.'
    )
    for rule in ('', '99', 'unknown'):
        with pytest.raises(ValueError, match='declared IUCr rule'):
            bridge.projected_parameter('0.1234(.0196)', rule)


def test_actual_project_declaration_drives_the_first_decimal_projection(tmp_path):
    project = tmp_path / 'project.edi'
    project.write_text('_edi.schema_version 3\n')
    assert declared_rule(tmp_path) == 'iucr_99', (
        'Required: actual project declaration drives the first decimal projection.'
    )
    assert bridge.projected_parameter('0.1234(.0196)', declared_rule(tmp_path)) == '0.123(20)', (
        'Required: actual project declaration drives the first decimal projection.'
    )
    project.write_text('_edi.schema_version 3\n_su_format.rule iucr_19\n')
    assert declared_rule(tmp_path) == 'iucr_19', (
        'Required: actual project declaration drives the first decimal projection.'
    )
    assert bridge.projected_parameter('0.1234(.0196)', declared_rule(tmp_path)) == '0.12(2)', (
        'Required: actual project declaration drives the first decimal projection.'
    )


def test_conditioning_frame_and_mixed_provenance_are_not_rebased():
    scientific = {
        'structures/sample.edi': [['_cell.length_a', '1.234(.01)'], ['_cell.length_b', '2']]
    }
    blocks = {'structures/sample.edi': 'sample'}
    conditioning = {
        'scientific_sha256': hashlib.sha256(
            json.dumps(scientific, sort_keys=True).encode()
        ).hexdigest(),
        'labels': ['cell_length_a'],
        'n_data': 4,
        'scaled_normal': [[1.0]],
        'scaled_inverse_normal': [[1.0]],
        'bindings': [['structures/sample.edi', 0, 1, 0]],
    }
    before = json.dumps([scientific, conditioning])
    mapping = bridge.conditioning_semantics(scientific, conditioning, blocks)
    coordinate = ('structures/sample.edi', 0, 1)
    assert mapping[coordinate] == (
        bridge.Cell('structures/sample.edi', 'sample', '_cell', (), '_cell.length_a'),
        0,
        'cell_length_a',
    ), 'Required: conditioning frame and mixed provenance are not rebased.'
    assert json.dumps([scientific, conditioning]) == before, (
        'Required: conditioning frame and mixed provenance are not rebased.'
    )
    changed = copy.deepcopy(scientific)
    changed['structures/sample.edi'][0][1] = '1.235(.01)'
    with pytest.raises(ValueError, match='exact scientific reference'):
        bridge.conditioning_semantics(changed, conditioning, blocks)
    fixture = {
        'scientific': scientific,
        'native_precision_bindings': [
            ['structures/sample.edi', 0, 1, 0, '1.23(1)', '1.234(.01)'],
        ],
    }
    assert bridge.frozen_domains(fixture, blocks)[coordinate] == 'native-raw-parameter', (
        'Required: conditioning frame and mixed provenance are not rebased.'
    )
    assert (
        bridge.frozen_domains(fixture, blocks)['structures/sample.edi', 1, 1]
        == 'historical-written'
    ), 'Required: conditioning frame and mixed provenance are not rebased.'
    fixture['native_precision_bindings'][0][-1] = '1.235(.01)'
    with pytest.raises(ValueError, match='frozen token'):
        bridge.frozen_domains(fixture, blocks)


def raw_capture():
    # Distinct storage labels deliberately have EQUAL values and uncertainties.
    return {
        'labels': ['bank.scale', 'bank.calib_twotheta_offset'],
        'values': [2.0, 2.0],
        'covariance': [0.25, 0.0, 0.0, 0.25],
    }


def test_omitted_raw_scale_and_calibration_bind_storage_not_equal_numbers():
    raw = raw_capture()
    banks = {'experiments/bank.edi': ('bank', ('sample',))}
    before = json.dumps(raw)
    bound = bridge.omitted_raw_parameters(raw, banks)
    assert bound['bank.scale'].key == bridge.Cell(
        'experiments/bank.edi',
        'bank',
        '_linked_structure',
        (('_linked_structure.structure_id', 'sample'),),
        '_linked_structure.scale',
    ), 'Required: omitted raw scale and calibration bind storage not equal numbers.'
    assert bound['bank.calib_twotheta_offset'].key == bridge.Cell(
        'experiments/bank.edi',
        'bank',
        '_instrument',
        (),
        '_instrument.calib_twotheta_offset',
    ), 'Required: omitted raw scale and calibration bind storage not equal numbers.'
    assert bound['bank.scale'].column == 0, (
        'Required: omitted raw scale and calibration bind storage not equal numbers.'
    )
    assert bound['bank.calib_twotheta_offset'].column == 1, (
        'Required: omitted raw scale and calibration bind storage not equal numbers.'
    )
    assert bound['bank.scale'].value == bound['bank.calib_twotheta_offset'].value == 2, (
        'Required: omitted raw scale and calibration bind storage not equal numbers.'
    )
    assert bound['bank.scale'].uncertainty == 0.5, (
        'Required: omitted raw scale and calibration bind storage not equal numbers.'
    )
    assert json.dumps(raw) == before, (
        'Required: omitted raw scale and calibration bind storage not equal numbers.'
    )


@pytest.mark.parametrize(
    'mutation',
    ['wrong-bank', 'ambiguous-link', 'missing-values', 'duplicate-label', 'unknown-calibration'],
)
def test_omitted_parameter_storage_escapes_refuse_after_positive(mutation):
    raw = raw_capture()
    banks = {'experiments/bank.edi': ('bank', ('sample',))}
    assert bridge.omitted_raw_parameters(raw, banks), (
        'Required: omitted parameter storage escapes refuse after positive.'
    )
    if mutation == 'wrong-bank':
        banks = {'experiments/bank.edi': ('other', ('sample',))}
    elif mutation == 'ambiguous-link':
        banks = {'experiments/bank.edi': ('bank', ('sample', 'second'))}
    elif mutation == 'missing-values':
        raw['values'].pop()
    elif mutation == 'duplicate-label':
        raw['labels'][1] = raw['labels'][0]
    else:
        raw['labels'][1] = 'bank.calib_unknown'
    with pytest.raises(ValueError, match='raw'):
        bridge.omitted_raw_parameters(raw, banks)
