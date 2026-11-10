"""Unit 9: BP5014 FullProf correctness references, never product regression pins."""

import hashlib
import importlib

import gemmi
import numpy as np
import pytest

from tests.fixtures.cosio_heidi_2008.generate import rows
from tests.fixtures.cosio_heidi_2008.reference import HERE, REFERENCE, project_files

TEMPERATURES = tuple(REFERENCE['cases'])

# The independent printed inputs already miss these two external values.
# Nominal closed-form parity still covers every row, including these two.
FULLPROF_SOURCE_EXCLUSIONS = {
    ('2.5K', 4, 0, 1): '816.25',
    ('2.5K', -10, 4, 7): '0.08',
}


def source_comparison_mask(temperature, record):
    return np.array([
        (temperature, *row[:3]) not in FULLPROF_SOURCE_EXCLUSIONS for row in record['rows']
    ])


def source_discrepancies(temperature, record, actual):
    expected = np.array([row[3] for row in record['rows']])
    return np.flatnonzero(
        ~np.isfinite(actual)
        | (
            source_comparison_mask(temperature, record)
            & (np.abs(actual - expected) > record['tolerance'])
        )
    )


def assert_calculated_reference(temperature, record, actual):
    bad = source_discrepancies(temperature, record, actual)
    assert not len(bad), (
        'Every eligible calculated F² matches external FullProf within the unchanged '
        'published-input three-s.u. and output-rounding tolerance; only the two '
        'documented 2.5 K source discrepancies are excluded, and no nonfinite value is allowed'
    )
    np.testing.assert_allclose(
        actual,
        record['independent_f2'],
        rtol=2e-7,
        atol=2e-7,
        err_msg=(
            'Exact printed input at every reflection, including the two external-source '
            'exclusions, matches the independent Pnma axial-vector, Brown Co2+ '
            'and anisotropic Larson closed form'
        ),
    )


def engine():
    return importlib.import_module('edi')


def test_published_inputs_remain_byte_identical():
    actual = {
        name: hashlib.sha256((HERE / 'published' / name).read_bytes()).hexdigest()
        for name in REFERENCE['hashes']
    }
    assert actual == REFERENCE['hashes'], (
        'Unit 9: BP5014 originals remain unchanged, including the erroneous low-temperature sigma'
    )


@pytest.mark.parametrize('temperature', TEMPERATURES)
def test_published_cif_reflection_reader_keeps_exact_rows(temperature):
    path = HERE / 'published' / f'bp5014-{temperature}.hkl'
    experiment = engine().ExperimentFactory.from_data_path(
        name='published',
        data_path=str(path),
        sample_form='single crystal',
        radiation_probe='neutron',
        scattering_type='bragg',
        beam_mode='constant wavelength',
    )
    data = experiment.refln
    actual = list(
        zip(
            data.index_h,
            data.index_k,
            data.index_l,
            data.intensity_meas,
            data.intensity_meas_su,
            strict=True,
        )
    )
    expected = [tuple(row[:3] + row[4:6]) for row in rows(path)]
    assert actual == expected, (
        'Unit 9: the CIF reflection loop preserves every signed h k l, meas'
        'ured F², sigma and row order; source sigma is not silently repaire'
        'd'
    )


@pytest.mark.parametrize('temperature', TEMPERATURES)
def test_independent_physics_is_consistent_with_printed_source(temperature):
    record = REFERENCE['cases'][temperature]
    expected = np.array([row[3] for row in record['rows']])
    residual = np.abs(np.array(record['independent_f2']) - expected)
    bad = source_discrepancies(temperature, record, np.array(record['independent_f2']))
    detail = [(record['rows'][i][:4], float(residual[i]), record['tolerance'][i]) for i in bad]
    assert not len(bad), (
        'Published FullProf F²calc and printed CIF/Table 4 inputs agree within the unchanged '
        'three-s.u. envelope outside the two documented source exclusions; discrepancies='
    ) + str(detail)


@pytest.mark.parametrize('temperature', TEMPERATURES)
def test_each_calculated_f2_matches_fullprof_with_published_input_tolerance(tmp_path, temperature):
    record = REFERENCE['cases'][temperature]
    project = engine().Project.load(project_files(tmp_path / 'input', temperature))
    project.analysis.calculate()
    data = project.experiments[0].refln
    assert list(zip(data.index_h, data.index_k, data.index_l, strict=True)) == [
        tuple(row[:3]) for row in record['rows']
    ], (
        'Unit 9: FullProf comparisons include every published reflection wi'
        'thout merging or filtering'
    )
    actual = np.array(data.intensity_calc)
    assert_calculated_reference(temperature, record, actual)


def test_magnetic_only_reflections_appear_without_nuclear_interference(tmp_path):
    engine_module = engine()
    record = REFERENCE['cases']['2.5K']
    with_moments = engine_module.Project.load(project_files(tmp_path / 'magnetic', '2.5K'))
    without_moments = engine_module.Project.load(
        project_files(tmp_path / 'nuclear', '2.5K', magnetic=False)
    )
    with_moments.analysis.calculate()
    without_moments.analysis.calculate()
    on = np.array(with_moments.experiments[0].refln.intensity_calc)
    off = np.array(without_moments.experiments[0].refln.intensity_calc)
    indices = [i for i, row in enumerate(record['rows']) if row[:3] in record['magnetic_only']]
    assert [1, 0, 0] in record['magnetic_only'], (
        'The independent Pnma extinction set includes the magnetic-only (100) witness'
    )
    assert len(indices) > 1, (
        'Unit 9: the independent Pnma extinction set includes (100) and add'
        'itional magnetic-only witnesses'
    )
    assert bool(np.max(np.abs(off[indices])) < 1e-12 and np.max(on[indices]) > 100), (
        'Unit 9: forbidden nuclear reflections vanish before moments and ga'
        'in magnetic intensity after moments'
    )
    i100 = next(i for i, row in enumerate(record['rows']) if row[:3] == [1, 0, 0])
    assert abs(on[i100] - record['rows'][i100][3]) <= record['tolerance'][i100], (
        'Unit 9: magnetic-only (100) agrees with published FullProf, with n'
        'o nuclear-magnetic interference term'
    )


def test_fullprof_source_exclusions_are_only_the_two_documented_rows():
    excluded = {
        (temperature, *row[:3])
        for temperature, record in REFERENCE['cases'].items()
        for row, eligible in zip(
            record['rows'], source_comparison_mask(temperature, record), strict=True
        )
        if not eligible
    }
    assert excluded == {('2.5K', 4, 0, 1), ('2.5K', -10, 4, 7)}, (
        'Only the two signed 2.5 K published-input discrepancies are excluded from external parity'
    )
    record = REFERENCE['cases']['2.5K']
    table = (
        gemmi.cif
        .read_file(str(HERE / 'published/bp5014-2.5K.hkl'))
        .sole_block()
        .find(['_refln_index_h', '_refln_index_k', '_refln_index_l', '_refln_F_squared_calc'])
    )
    printed = {tuple(int(value) for value in list(row)[:3]): row[3] for row in table}
    for key, token in FULLPROF_SOURCE_EXCLUSIONS.items():
        hkl = key[1:]
        indices = [i for i, row in enumerate(record['rows']) if tuple(row[:3]) == hkl]
        assert len(indices) == 1, 'Every documented exclusion identifies exactly one source row'
        assert printed[hkl] == token, (
            'Each documented exclusion occurs once and retains its exact published FullProf token'
        )
        i = indices[0]
        assert abs(record['independent_f2'][i] - record['rows'][i][3]) > record['tolerance'][i], (
            'The documented source discrepancy exists independently of either product calculation'
        )
    assert all(
        eligible
        for row, eligible in zip(
            record['rows'], source_comparison_mask('2.5K', record), strict=True
        )
        if row[:3] in record['magnetic_only']
    ), 'Every published magnetic-only reflection remains eligible for external FullProf parity'
    weak = next(i for i, row in enumerate(record['rows']) if row[:3] == [-10, 4, 7])
    assert printed[-10, 4, 7] == '0.08', (
        'The weak external reference retains its two-decimal token'
    )
    assert record['independent_f2'][weak] < 0.08 - 0.005, (
        'The published weak value has two decimal places; ordinary output rounding does not '
        'explain its nominal printed-input mismatch'
    )


@pytest.mark.parametrize(
    ('temperature', 'magnetic_only'),
    [('300K', False), ('55K', False), ('2.5K', False), ('2.5K', True)],
)
def test_fullprof_comparison_refuses_a_changed_other_reflection(temperature, magnetic_only):
    record = REFERENCE['cases'][temperature]
    mask = source_comparison_mask(temperature, record)
    i = next(
        i
        for i, row in enumerate(record['rows'])
        if mask[i] and (row[:3] in record['magnetic_only']) == magnetic_only
    )
    actual = np.array([row[3] for row in record['rows']])
    assert not len(source_discrepancies(temperature, record, actual)), (
        'The external FullProf columns satisfy the comparison before the escape exercise'
    )
    actual[i] += 1.01 * record['tolerance'][i]
    assert list(source_discrepancies(temperature, record, actual)) == [i], (
        'A changed nonexcluded nuclear, mixed or magnetic-only reflection '
        'still fails its original tolerance'
    )
    with pytest.raises(AssertionError, match='eligible calculated F² matches external FullProf'):
        assert_calculated_reference(temperature, record, actual)


@pytest.mark.parametrize('hkl', [(4, 0, 1), (-10, 4, 7)])
def test_external_source_exclusions_still_require_nominal_closed_form(hkl):
    record = REFERENCE['cases']['2.5K']
    actual = np.array(record['independent_f2'])
    assert_calculated_reference('2.5K', record, actual)
    i = next(i for i, row in enumerate(record['rows']) if tuple(row[:3]) == hkl)
    actual[i] += record['tolerance'][i]
    assert not len(source_discrepancies('2.5K', record, actual)), (
        'The escape exercise changes exactly a documented external-source exclusion'
    )
    with pytest.raises(AssertionError, match='including the two external-source exclusions'):
        assert_calculated_reference('2.5K', record, actual)
    actual[i] = np.nan
    with pytest.raises(AssertionError, match='no nonfinite value is allowed'):
        assert_calculated_reference('2.5K', record, actual)
