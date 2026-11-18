"""Admission, merging and reporting against independent reflection arithmetic."""

import copy
import hashlib
import importlib
import json
import os
import re
import subprocess
from pathlib import Path

import numpy as np
import pytest

from tests.fixtures.fitting_correctness.admission import (
    MERGE_ROWS,
    column,
    exclusion,
    merged,
    region,
    scalar,
    stage,
)
from tests.fixtures.fitting_correctness.contracts import (
    DECLARATIONS,
    INDEX_ROWS,
    RICH_ROWS,
    partition,
    rich_reference,
)
from tests.fixtures.fitting_correctness.contracts import (
    summary as reference_summary,
)
from tests.fixtures.native_process import native_executable
from tests.fixtures.single_crystal_edges.observe import observe

ENGINE = 'edi'
BASIS = 1.03**2


def saved(root, destination):
    project = importlib.import_module(ENGINE).Project.load(root)
    project.analysis.calculate()
    project.save_as(destination)
    return (destination / 'experiments/bank.edi').read_text()


@pytest.fixture(scope='module')
def native():
    root = Path(__file__).resolve().parents[3]
    selected = os.environ.get('SINGLE_CRYSTAL_EMPTY_OBSERVER')
    if selected:
        executable = Path(selected)
    elif ENGINE == 'crysta':
        executable = (
            root / 'build/crysta'
        ).resolve().parent / 'tests/fixtures/single_crystal_edges/single_crystal_edge_probe'
    else:
        directory = Path(importlib.import_module(ENGINE)._edi.__file__).resolve().parents[2]
        executable = directory / 'single_crystal_edges/single_crystal_edge_probe'
    if not selected:
        executable = native_executable(executable)
    assert executable.is_file(), (
        'The admission gates require the prepared actual native-model observer'
    )
    identity = subprocess.check_output(
        [str(executable), '--identity'], text=True, timeout=10
    ).strip()
    expected = hashlib.sha256(
        (root / 'tests/fixtures/single_crystal_edges/probe.cpp').read_bytes()
    ).hexdigest()
    assert identity == expected, (
        'The prepared observer must match the complete committed fixture source'
    )
    return executable


@pytest.mark.parametrize(
    ('axis', 'start', 'end', 'kept'),
    [
        ('d_spacing', 3, 6, [2, 3]),
        ('d_spacing', 6, 3, [2, 3]),
        ('sin_theta_over_lambda', 1 / 12, 1 / 6, [2, 3]),
        ('sin_theta_over_lambda', 1 / 6, 1 / 12, [2, 3]),
    ],
)
def test_range_closed_endpoints_and_reversed_bounds_reach_fit(
    native, tmp_path, axis, start, end, kept
):
    rows = [(1, 0, 0, 1000, 1), (2, 0, 0, 200, 2), (2, 1, 1, 14, 2), (2, 2, 0, -2, 3)]
    root = stage(tmp_path / 'input', rows=rows, declarations=region(axis, start, end))
    result = observe(native, root, 'admission')
    assert result['ok'], (
        'Single-crystal ranges must be admitted on either declared reciprocal-space axis'
    )
    require_fit(result, [rows[index] for index in kept])
    text = (tmp_path / 'input-saved/experiments/bank.edi').read_text()
    assert column(text, '_refln.include_status') == ['x', 'x', 'o', '<'], (
        'Closed range endpoints must exclude both boundaries while '
        'retaining a signed weak measurement'
    )


def require_saved_factor(text, tag, expected):
    assert scalar(text, tag) == pytest.approx(float(f'{expected:.6g}'), rel=1e-12, abs=1e-15), (
        'Saved computed factors retain the independent value '
        'at ADR-0092 six-significant-digit precision'
    )


def require_fit(result, rows, basis=BASIS):
    values = np.array([row[3] for row in rows], dtype=float)
    sigma = np.array([row[4] for row in rows], dtype=float)
    predictor = np.broadcast_to(basis, values.shape)
    scale = np.dot(values * sigma**-2, predictor) / np.dot(predictor * sigma**-2, predictor)
    links = result['after:link']
    assert len(links) == 1, 'The scale-only fit must retain its one declared phase link'
    assert float(links[0][3]) == pytest.approx(scale, rel=3e-5), (
        'The actual native fit must minimize the independently admitted weighted observations'
    )
    chi2 = np.sum(((values - scale * predictor) / sigma) ** 2) / (len(rows) - 1)
    assert float(result['chi2'][0][0]) == pytest.approx(chi2, rel=5e-5, abs=1e-6), (
        'The actual fit objective and degrees of freedom must use the reduced reflection list'
    )


@pytest.mark.parametrize('mode', ['none', 'point_group', 'laue_class'])
@pytest.mark.parametrize('group', ['P 2 2 2', 'P m m m'])
def test_reduced_index_omit_removes_repeats_and_equivalents(native, tmp_path, mode, group):
    groups, excluded = partition(
        INDEX_ROWS, mode, centrosymmetric=group == 'P m m m', omit=(1, 2, 3)
    )
    root = stage(
        tmp_path / 'input',
        rows=INDEX_ROWS,
        group=group,
        declarations=f'_reflns.merge {mode}\n' + exclusion(1, 2, 3),
    )
    result = observe(native, root, 'admission')
    assert result['ok'], 'SHELXL OMIT must match reduced indices in the selected merge mode'
    reduced, _, _ = merged(INDEX_ROWS, groups)
    require_fit(result, [(0, 0, 0, mean, su) for mean, su in reduced])
    text = (tmp_path / 'input-saved/experiments/bank.edi').read_text()
    require_omissions(column(text, '_refln.include_status'), excluded)
    assert scalar(text, '_reflns.number_excluded') == len(excluded), (
        'Reduced-index OMIT counts every repeated or equivalent input once'
    )


def require_omissions(statuses, excluded):
    assert [i for i, status in enumerate(statuses) if status == 'x'] == excluded, (
        'OMIT uses the complete reduced h k l tuple, preserving neighboring indices'
    )


@pytest.mark.parametrize('mode', ['none', 'point_group', 'laue_class'])
@pytest.mark.parametrize('group', ['P 2 2 2', 'P m m m'])
def test_merge_modes_weighted_sigma_and_published_r_factors(native, tmp_path, mode, group):
    groups, _ = partition(INDEX_ROWS, mode, centrosymmetric=group == 'P m m m')
    root = stage(
        tmp_path / 'input',
        rows=INDEX_ROWS,
        group=group,
        declarations=f'_reflns.merge {mode}\n_reflns.absences include\n',
    )
    result = observe(native, root, 'admission')
    assert result['ok'], 'Nontrivial point-group and Laue partitions must reach the actual fit'
    reduced, r_int, r_sigma = merged(INDEX_ROWS, groups)
    require_fit(result, [(0, 0, 0, mean, su) for mean, su in reduced])
    text = (tmp_path / 'input-saved/experiments/bank.edi').read_text()
    assert scalar(text, '_reflns.number_measured') == len(INDEX_ROWS), (
        'The saved measured count includes every original observation before merging'
    )
    assert scalar(text, '_reflns.number_total') == len(groups), (
        '222 merges proper rotational equivalents while retaining its Friedel orbit'
    )
    assert scalar(text, '_refine_ls.number_reflns') == len(groups), (
        'The residual uses every admitted unique observation before a cutoff is declared'
    )
    require_saved_factor(text, '_reflns.R_sigma', r_sigma)
    if mode == 'none' or r_int is None:
        assert '_reflns.R_int ' not in text, 'Unmerged repeats do not define a merged Rint'
    else:
        require_saved_factor(text, '_reflns.R_int', r_int)


def test_merging_precedes_fit_cutoff(native, tmp_path):
    rows = [
        (1, 0, 0, 1, 1),
        (-1, 0, 0, 5, 1),
        (0, 1, 0, 20, 1),
        (0, -1, 0, 21, 1),
        (0, 0, 1, 30, 1),
    ]
    root = stage(
        tmp_path / 'input', rows=rows, declarations='_reflns.merge laue_class\n', cutoff=2
    )
    result = observe(native, root, 'admission')
    assert result['ok'], 'The post-merge cutoff must admit the merged weak/strong pair'
    reduced, _, _ = merged(rows, [[0, 1], [2, 3], [4]])
    used = [(0, 0, 0, mean, sigma) for mean, sigma in reduced if mean > 2 * sigma]
    require_fit(result, used)

    text = (tmp_path / 'input-saved/experiments/bank.edi').read_text()
    assert scalar(text, '_reflns.number_total') == 3, (
        'The unique count is reported before the merged-observation cutoff'
    )
    assert scalar(text, '_refine_ls.number_reflns') == len(used), (
        'The used count is reported after the merged-observation cutoff'
    )
    expected_sigma = sum(row[4] for row in used) / sum(row[3] for row in used)
    require_saved_factor(text, '_reflns.R_sigma', expected_sigma)


@pytest.mark.parametrize(
    ('group', 'rows', 'absent'),
    [
        (
            'I m -3 m',
            [(1, 0, 0, 100, 1), (2, 0, 0, 10, 1), (2, 1, 1, 14, 2), (2, 2, 0, -2, 3)],
            [0],
        ),
        (
            'P 21/c',
            [(0, 1, 0, 100, 1), (1, 0, 1, 90, 2), (0, 2, 0, 10, 1), (1, 0, 2, -2, 3)],
            [0, 1],
        ),
    ],
)
@pytest.mark.parametrize('policy', ['include', 'exclude'])
def test_international_tables_absences_and_warning(tmp_path, group, rows, absent, policy):
    root = stage(
        tmp_path / 'input', rows=rows, group=group, declarations=f'_reflns.absences {policy}\n'
    )
    text = saved(root, tmp_path / 'saved')
    assert scalar(text, '_reflns.number_measured') == len(rows), (
        'The saved measured count includes systematically absent observations under either policy'
    )
    assert scalar(text, '_reflns.number_absent') == len(absent), (
        'Integral centring, serial screw and zonal glide absences must '
        'follow International Tables rules'
    )
    assert scalar(text, '_refine_ls.number_reflns') == len(rows) - (
        len(absent) if policy == 'exclude' else 0
    ), (
        'Systematic absences must be removed before residual admission '
        'while weak allowed rows remain'
    )
    statuses = column(text, '_refln.include_status')
    assert all((statuses[index] == '-') == (policy == 'exclude') for index in absent), (
        'The exported row status must distinguish systematic absences from user omissions'
    )


@pytest.mark.parametrize(
    ('axis', 'start', 'end'), [('d_spacing', 3, 6), ('sin_theta_over_lambda', 1 / 12, 1 / 6)]
)
def test_range_and_hkl_save_reload_preserve_declared_rows(tmp_path, axis, start, end):
    root = stage(tmp_path / 'input', declarations=exclusion(9, 8, 7) + region(axis, start, end))
    first = saved(root, tmp_path / 'first')
    second = saved(tmp_path / 'first', tmp_path / 'second')
    for tag in (
        '_excluded_reflection.index_h',
        '_excluded_reflection.index_k',
        '_excluded_reflection.index_l',
        '_excluded_region.axis',
        '_excluded_region.start',
        '_excluded_region.end',
    ):
        assert column(first, tag) == column(second, tag), (
            'Exclusion rows, range axis and given bounds must survive the '
            'second save byte for byte'
        )
    assert column(first, '_excluded_region.axis') == [axis], (
        'Saving must retain the explicit range axis'
    )
    for tag, expected in (
        ('_excluded_reflection.index_k', '8'),
        ('_excluded_reflection.index_l', '7'),
    ):
        assert column(first, tag) == [expected], (
            'The first save must retain every originally declared signed hkl index'
        )
    for tag, expected in (('_excluded_region.start', start), ('_excluded_region.end', end)):
        assert float(column(first, tag)[0]).hex() == float(expected).hex(), (
            'The first save must preserve each originally declared range endpoint exactly'
        )
    assert list(map(float, column(first, '_refln.intensity_meas'))) == [
        row[3] for row in MERGE_ROWS
    ], 'Saving exclusions must retain all signed observations in their original order'
    assert column(first, '_excluded_reflection.index_h') == ['9'], (
        'An unmatched hkl omission must persist without excluding another row'
    )


@pytest.mark.parametrize('mode', ['point_group', 'laue_class'])
def test_tof_merging_is_refused_by_name(tmp_path, mode):
    root = stage(tmp_path / 'input', tof=True, declarations=f'_reflns.merge {mode}\n')
    with pytest.raises((RuntimeError, ValueError), match=r'(?i)merge'):
        importlib.import_module(ENGINE).Project.load(root)


@pytest.mark.parametrize('kind', ['tbti', 'taurine'])
def test_measured_list_rint_adapter(tmp_path, kind):
    reference = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / 'fixtures/fitting_correctness/merge_reference.json'
        ).read_text()
    )['cases'][kind]
    # The original taurine measurements are a CW grouping input here.
    rows = [row[:5] for row in reference['input_rows']]
    group = 'F d -3 m' if kind == 'tbti' else 'P 21/c'
    root = stage(
        tmp_path / 'input',
        rows=rows,
        group=group,
        declarations='_reflns.merge laue_class\n_reflns.absences include\n',
    )
    experiment = root / 'experiments/bank.edi'
    experiment.write_text(
        experiment.read_text().replace(
            '_instrument.setup_wavelength 0.8', '_instrument.setup_wavelength 0.05'
        )
    )
    text = saved(root, tmp_path / 'saved')
    expected = reference['laue_include_absences']
    assert scalar(text, '_reflns.number_total') == len(expected['rows']), (
        'Real measured-list adapters must group equivalents by their '
        'independently enumerated point rotations'
    )
    if expected['r_int'] is not None:
        require_saved_factor(text, '_reflns.R_int', float(expected['r_int']))
    require_saved_factor(text, '_reflns.R_sigma', float(expected['r_sigma_weighted']))


@pytest.mark.parametrize(
    ('declaration', 'word'),
    [
        ('_reflns.merge unknown\n', 'merge'),
        ('_reflns.absences unknown\n', 'absences'),
        (
            'loop_\n_excluded_region.id\n_excluded_region.start\n_excluded_region.end\n1 3 6\n',
            'axis',
        ),
        (region('two_theta', 3, 6), 'axis'),
    ],
)
def test_invalid_admission_configuration_is_refused_at_load(tmp_path, declaration, word):
    root = stage(tmp_path / 'input', declarations=declaration)
    with pytest.raises((RuntimeError, ValueError), match=word):
        importlib.import_module(ENGINE).Project.load(root)


def test_legacy_no_settings_preserves_saved_scale_and_raw_observations(tmp_path):
    root = stage(tmp_path / 'input')
    project = importlib.import_module(ENGINE).Project.load(root)
    assert project.experiments[0].linked_structure.scale.value.hex() == (2.3).hex(), (
        'Opening a saved project never automatically changes its declared phase scale'
    )
    project.save_as(tmp_path / 'saved')
    assert list(project.experiments[0].refln.intensity_meas) == [row[3] for row in MERGE_ROWS], (
        'A legacy project with no merge or absence setting retains all raw signed observations'
    )
    text = (tmp_path / 'saved/experiments/bank.edi').read_text()
    assert '_reflns.merge laue_class' not in text, (
        'Saving a legacy project must not silently opt it into new merge or absence defaults'
    )
    assert '_reflns.absences exclude' not in text, (
        'Saving a legacy project must preserve its absence-admission default'
    )


def require_absence_notice(notes, count, mean):
    notices = [line for line in notes.splitlines() if 'systematic absences' in line.lower()]
    if count == 0 or mean <= 3:
        assert not notices, (
            'No absence warning is emitted at or below mean I/sigma three, or without absences'
        )
        return
    assert len(notices) == 1, 'Strong absences produce exactly one diagnostic under either policy'
    numbers = [float(value) for value in re.findall(r'(?<![A-Za-z])\d+(?:\.\d+)?', notices[0])]
    assert numbers == pytest.approx([count, mean]), (
        'The absence warning reports its actual absent count and mean I/sigma'
    )


@pytest.mark.parametrize('policy', ['include', 'exclude'])
@pytest.mark.parametrize('mean', [None, 2, 3, 6], ids=['none', 'below', 'boundary', 'above'])
def test_absence_diagnostic_reports_independent_count_and_mean(native, tmp_path, policy, mean):
    rows = [(2, 0, 0, 10, 1), (2, 1, 1, 14, 2), (2, 2, 0, 18, 3)]
    if mean is not None:
        rows += [(1, 0, 0, 2 * mean, 2), (1, 1, 1, 3 * mean, 3)]
    root = stage(
        tmp_path / 'input',
        rows=rows,
        group='I m -3 m',
        declarations=f'_reflns.absences {policy}\n',
    )
    result = observe(native, root, 'admission')
    assert result['ok'], 'Absence diagnostics remain observable under both admission policies'
    require_absence_notice(result['notes'], 0 if mean is None else 2, mean or 0)


def test_exclusion_precedes_absence_and_is_not_counted_twice(tmp_path):
    rows = [(1, 0, 0, 100, 1), (2, 0, 0, 10, 1), (2, 1, 1, 14, 2), (2, 2, 0, -2, 3)]
    root = stage(
        tmp_path / 'input',
        rows=rows,
        group='I m -3 m',
        declarations=exclusion(1, 0, 0) + region('d_spacing', 6, 6) + '_reflns.absences exclude\n',
    )
    text = saved(root, tmp_path / 'saved')
    assert column(text, '_refln.include_status')[0] == 'x', (
        'A user-omitted row must retain user exclusion as its first reason '
        'even when absent and inside a range'
    )
    assert scalar(text, '_reflns.number_excluded') == 1, (
        'Overlapping hkl and range exclusions must count the same measured row once'
    )


def test_tof_none_keeps_each_observation_wavelength(tmp_path):
    rows = [(1, 0, 0, 10, 1, 0.6), (-1, 0, 0, 20, 2, 1.1)]
    root = stage(tmp_path / 'input', rows=rows, tof=True, declarations='_reflns.merge none\n')
    text = saved(root, tmp_path / 'saved')
    assert list(map(float, column(text, '_refln.wavelength'))) == [0.6, 1.1], (
        'Nonmerged TOF observations must retain their own nontrivial wavelengths'
    )


def assistant_summaries(context):
    # Scope by the actual dataset identity, never collect a factor from another experiment.
    datasets = context.get('datasets', [])
    result = {}
    for dataset in datasets:
        name = dataset.get('id')
        result[name] = {}

        def walk(value, name=name):
            if isinstance(value, dict):
                for key, item in value.items():
                    normalized = key.lower().replace('_', '').replace('-', '')
                    aliases = {
                        'rint': 'rint',
                        'avrequivalents': 'rint',
                        'rsigma': 'rsigma',
                        'measured': 'measured',
                        'unique': 'unique',
                        'used': 'used',
                        'excluded': 'excluded',
                        'absent': 'absent',
                        'mergemode': 'mode',
                        'merge': 'mode',
                        'mode': 'mode',
                    }
                    if normalized in aliases:
                        result[name][aliases[normalized]] = item
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(dataset)
    return result


def test_assistant_inspect_project_carries_the_same_merge_statistics(native, tmp_path):
    root = stage(
        tmp_path / 'input', rows=RICH_ROWS, group='I 2 2 2', declarations=DECLARATIONS, cutoff=2
    )
    other = (root / 'experiments/bank.edi').read_text().replace('data_bank', 'data_other')
    other = other.replace(DECLARATIONS, '_reflns.merge point_group\n_reflns.absences include\n')
    (root / 'experiments/other.edi').write_text(other)
    analysis = root / 'analysis/analysis.edi'
    analysis.write_text(analysis.read_text() + '\n_fitting_mode.type joint\n')
    result = observe(native, root, 'admission')
    assert result['ok'], 'Two distinct experiments expose their own actual assistant summaries'
    context = json.loads(bytes.fromhex(result['inspect'][0][0]).decode())
    expected = json.loads(
        (
            Path(__file__).parents[2] / 'fixtures/fitting_correctness/admission_reference.json'
        ).read_text()
    )
    actual = assistant_summaries(context)
    for name in ('bank', 'other'):
        assert name in actual, (
            'inspect_project associates reflection statistics with the dataset identity'
        )
        require_summary(actual[name], expected[name])


def test_assistant_summary_escape_rejects_swapped_experiments():
    expected = json.loads(
        (
            Path(__file__).parents[2] / 'fixtures/fitting_correctness/admission_reference.json'
        ).read_text()
    )
    context = {
        'datasets': [
            {'id': name, 'reflection_summary': summary}
            for name, summary in expected.items()
            if name in {'bank', 'other'}
        ]
    }
    actual = assistant_summaries(context)
    for name in ('bank', 'other'):
        require_summary(actual[name], expected[name])
    with pytest.raises(AssertionError, match='experiment'):
        require_summary(actual['other'], expected['bank'])


def test_no_automatic_outlier_rejection_during_merging(native, tmp_path):
    rows = [*MERGE_ROWS, (1, 0, 0, 10000, 1)]
    root = stage(tmp_path / 'input', rows=rows, declarations='_reflns.merge laue_class\n')
    result = observe(native, root, 'admission')
    assert result['ok'], 'Default merging must retain even a strongly inconsistent equivalent'
    reduced, _, _ = merged(rows, [[0, 1, 6], [2, 3], [4, 5]])
    require_fit(result, [(0, 0, 0, mean, sigma) for mean, sigma in reduced])


@pytest.mark.parametrize('sigma', [0, -1])
def test_merging_never_hides_invalid_measurement_uncertainty(native, tmp_path, sigma):
    rows = [*MERGE_ROWS]
    rows[0] = (1, 0, 0, 10, sigma)
    root = stage(tmp_path / 'input', rows=rows, declarations='_reflns.merge laue_class\n')
    result = observe(native, root, 'admission')
    assert not result['ok'], (
        'A nonpositive measurement uncertainty must be refused before merging or weighting'
    )
    assert re.search(r'(?i)sigma|uncert|s.u.|positive', result['error']), (
        'The invalid uncertainty refusal must identify the scientific input problem'
    )


def require_summary(actual, expected):
    for key in ('measured', 'unique', 'used', 'excluded', 'absent', 'mode', 'rint', 'rsigma'):
        assert key in actual, (
            'Every reflection summary field must be present in its experiment block'
        )
        if key in {'rint', 'rsigma'} and expected[key] is not None:
            assert actual[key] == pytest.approx(expected[key], rel=1e-6), (
                'Each experiment reports its own independently computed agreement factor'
            )
        else:
            assert actual[key] == expected[key], (
                'Each experiment reports its own counts, merge mode and undefined state'
            )


def test_combined_admission_reaches_fit_and_used_statistics(native, tmp_path):
    root = stage(
        tmp_path / 'input', rows=RICH_ROWS, group='I 2 2 2', declarations=DECLARATIONS, cutoff=2
    )
    result = observe(native, root, 'admission')
    assert result['ok'], (
        'The actual residual composes reduced OMIT, ranges, absences, merging and cutoff'
    )
    expected = rich_reference()
    require_fit(
        result,
        [(0, 0, 0, mean, su) for mean, su in expected['reduced'] if mean > 2 * su],
        basis=4 * BASIS,
    )
    text = (tmp_path / 'input-saved/experiments/bank.edi').read_text()
    mode = re.search(r'(?m)^_reflns\.merge\s+(\S+)', text)
    actual = {
        'mode': mode.group(1).strip('"') if mode else None,
        'measured': scalar(text, '_reflns.number_measured'),
    }
    for key, tag in {
        'unique': '_reflns.number_total',
        'used': '_refine_ls.number_reflns',
        'excluded': '_reflns.number_excluded',
        'absent': '_reflns.number_absent',
        'rint': '_reflns.R_int',
        'rsigma': '_reflns.R_sigma',
    }.items():
        actual[key] = scalar(text, tag)
    expected_saved = {
        **expected,
        'rint': float(f'{expected["rint"]:.6g}'),
        'rsigma': float(f'{expected["rsigma"]:.6g}'),
    }
    require_summary(actual, expected_saved)
    assert len(column(text, '_refln.index_h')) == expected['measured'], (
        'Admission statistics never remove original measured rows from the saved table'
    )


def reference_observations(reference, raw):
    # The generator's reviewed means/su are inputs; predictors come independently
    # from the physical centring sum, not from its scale formula or reported absences.
    used = [
        (*raw[group[0]][:3], mean, su)
        for group, (mean, su) in zip(reference['groups'], reference['reduced'], strict=True)
        if mean > 2 * su
    ]
    predictor = np.array([4 * BASIS if sum(row[:3]) % 2 == 0 else 0 for row in used])
    return used, predictor


def reference_protocol(scale, rows, predictor):
    # Counterfactual reference qualification through the actual fit checker;
    # this is neither an engine observation nor an engine-derived expectation.
    observed = np.array([row[3] for row in rows])
    sigma = np.array([row[4] for row in rows])
    chi2 = np.sum(((observed - scale * predictor) / sigma) ** 2) / (len(rows) - 1)
    return {'after:link': [['bank', 'phase', 'true', str(scale)]], 'chi2': [[str(chi2)]]}


def require_generated_scale_references():
    directory = Path(__file__).parents[2] / 'fixtures/fitting_correctness'
    for filename in ('admission_reference.json', 'admission_project/reference.json'):
        references = json.loads((directory / filename).read_text())
        for name, reference in references.items():
            raw = (
                [(*row[:3], row[3] * 1.7, row[4]) for row in RICH_ROWS]
                if name == 'replacement'
                else RICH_ROWS
            )
            used, predictor = reference_observations(reference, raw)
            require_fit(
                reference_protocol(reference['scale'], used, predictor), used, basis=predictor
            )
        require_included_absence_reference(references['other'])


def require_included_absence_reference(other):
    used, predictor = reference_observations(other, RICH_ROWS)
    assert np.count_nonzero(predictor == 0) == 1, (
        'The include-policy reference retains one zero-predictor absence in its residual'
    )
    assert len(used) == other['used'], (
        'An included zero-predictor observation counts toward residual degrees of freedom'
    )
    weights = np.array([row[4] ** -2 for row in used])
    constant_scale = np.dot(weights, [row[3] for row in used]) / (4 * BASIS * weights.sum())
    with pytest.raises(AssertionError, match='actual native fit'):
        require_fit(reference_protocol(constant_scale, used, 4 * BASIS), used, basis=predictor)
    allowed = [row for row, calc in zip(used, predictor, strict=True) if calc != 0]
    with pytest.raises(AssertionError, match='objective and degrees of freedom'):
        require_fit(reference_protocol(other['scale'], allowed, 4 * BASIS), used, basis=predictor)
    changed = [tuple(row) for row in RICH_ROWS]
    changed[9] = (*changed[9][:3], 900, changed[9][4])
    recomputed = reference_summary(
        changed, other['groups'], mode='point_group', absent=[9], cutoff=2
    )
    assert recomputed['scale'] == pytest.approx(other['scale'], rel=1e-12), (
        'An included zero-predictor intensity changes neither '
        'numerator nor denominator of the scale'
    )
    changed_used, changed_predictor = reference_observations(recomputed, changed)
    require_fit(
        reference_protocol(recomputed['scale'], changed_used, changed_predictor),
        changed_used,
        basis=changed_predictor,
    )
    before_chi2 = float(reference_protocol(other['scale'], used, predictor)['chi2'][0][0])
    after_chi2 = float(
        reference_protocol(recomputed['scale'], changed_used, changed_predictor)['chi2'][0][0]
    )
    expected_increase = (900**2 - 90**2) / (len(used) - 1)
    assert after_chi2 - before_chi2 == pytest.approx(expected_increase, rel=1e-12), (
        'An included centring absence contributes its squared residual '
        'with unchanged scale and observation count'
    )


def require_precision_controls():
    require_saved_factor('_reflns.R_int 0.333333', '_reflns.R_int', 1 / 3)
    with pytest.raises(AssertionError, match='Saved computed factors'):
        require_saved_factor('_reflns.R_int 0.333', '_reflns.R_int', 1 / 3)


def test_gate_escape_controls_discriminate_index_merge_stats_scale_and_warning():
    # Counterfactual algorithm/observation exercises call the SAME checkers as product gates.
    require_generated_scale_references()
    require_precision_controls()
    for mode in ('none', 'point_group', 'laue_class'):
        groups, excluded = partition(INDEX_ROWS, mode, omit=(1, 2, 3))
        statuses = ['x' if i in excluded else 'o' for i in range(len(INDEX_ROWS))]
        require_omissions(statuses, excluded)
        honly = ['x' if row[0] == 1 else 'o' for row in INDEX_ROWS]
        with pytest.raises(AssertionError, match='complete reduced'):
            require_omissions(honly, excluded)
        if mode != 'none':
            raw = ['x' if row[:3] == (1, 2, 3) else 'o' for row in INDEX_ROWS]
            with pytest.raises(AssertionError, match='complete reduced'):
                require_omissions(raw, excluded)
    correct_groups, _ = partition(INDEX_ROWS, 'point_group')
    expected_rows = [(0, 0, 0, m, s) for m, s in merged(INDEX_ROWS, correct_groups)[0]]

    def fitted(rows):
        values = np.array([row[3] for row in rows])
        su = np.array([row[4] for row in rows])
        scale = np.sum(values / su**2) / np.sum(su**-2) / BASIS
        chi2 = np.sum(((values - scale * BASIS) / su) ** 2) / (len(rows) - 1)
        return {'after:link': [['bank', 'phase', 'true', str(scale)]], 'chi2': [[str(chi2)]]}

    require_fit(fitted(expected_rows), expected_rows)
    for wrong_mode in ('none', 'laue_class'):
        groups, _ = partition(INDEX_ROWS, wrong_mode)
        wrong_rows = [(0, 0, 0, m, s) for m, s in merged(INDEX_ROWS, groups)[0]]
        with pytest.raises(AssertionError, match='actual native fit'):
            require_fit(fitted(wrong_rows), expected_rows)
    expected = rich_reference()
    require_summary(expected, expected)
    for key in ('measured', 'unique', 'used', 'excluded', 'absent', 'mode', 'rint', 'rsigma'):
        wrong = copy.deepcopy(expected)
        wrong[key] = 'none' if key == 'mode' else (None if key == 'rint' else 0)
        with pytest.raises(AssertionError, match='experiment'):
            require_summary(wrong, expected)
        del wrong[key]
        with pytest.raises(AssertionError, match='present'):
            require_summary(wrong, expected)
    used = [(0, 0, 0, m, s) for m, s in expected['reduced'] if m > 2 * s]
    correct = fitted(used)
    unit = copy.deepcopy(correct)
    unit['after:link'][0][3] = str(np.mean([row[3] for row in used]) / BASIS)
    for wrong in (unit, fitted(RICH_ROWS)):
        with pytest.raises(AssertionError, match='actual native fit'):
            require_fit(wrong, used)
    require_absence_notice('Systematic absences: 2 with mean I/sigma 6', 2, 6)
    for mean in (0, 2, 3):
        with pytest.raises(AssertionError, match='No absence warning'):
            require_absence_notice(
                'Systematic absences: 2 with mean I/sigma 6', 0 if mean == 0 else 2, mean
            )
    with pytest.raises(AssertionError, match='exactly one'):
        require_absence_notice('', 2, 6)
