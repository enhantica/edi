"""Admission, merging and reporting against independent reflection arithmetic."""

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


def require_fit(result, rows):
    values = np.array([row[3] for row in rows], dtype=float)
    sigma = np.array([row[4] for row in rows], dtype=float)
    scale = np.dot(values, sigma**-2) / (BASIS * np.sum(sigma**-2))
    links = result['after:link']
    assert len(links) == 1, 'The scale-only fit must retain its one declared phase link'
    assert float(links[0][3]) == pytest.approx(scale, rel=3e-5), (
        'The actual native fit must minimize the independently admitted weighted observations'
    )
    chi2 = np.sum(((values - scale * BASIS) / sigma) ** 2) / (len(rows) - 1)
    assert float(result['chi2'][0][0]) == pytest.approx(chi2, rel=5e-5, abs=1e-6), (
        'The actual fit objective and degrees of freedom must use the reduced reflection list'
    )


def test_hkl_omit_is_exact_and_precedes_merge_and_cutoff(native, tmp_path):
    rows = [*MERGE_ROWS, (2, 0, 0, 20, 1), (-2, 0, 0, 22, 2)]
    declaration = '_reflns.merge laue_class\n' + exclusion(1, 0, 0)
    root = stage(tmp_path / 'input', rows=rows, declarations=declaration)
    result = observe(native, root, 'admission')
    assert result['ok'], 'An exact hkl omission must be accepted before Laue merging'
    reduced, _, _ = merged(rows, [[1], [2, 3], [4, 5], [6, 7]])
    require_fit(result, [(0, 0, 0, mean, sigma) for mean, sigma in reduced])
    text = (tmp_path / 'input-saved/experiments/bank.edi').read_text()
    assert column(text, '_refln.include_status')[0] == 'x', (
        'The exact listed hkl must be marked user-excluded'
    )
    assert column(text, '_refln.include_status')[1] != 'x', (
        'The declared exact-index policy must not omit an unlisted Friedel mate'
    )
    assert scalar(text, '_reflns.number_excluded') == 1, (
        'An omitted row must be counted once before equivalents are grouped'
    )


@pytest.mark.parametrize(
    ('mode', 'groups'),
    [
        ('none', [[0], [1], [2], [3], [4], [5]]),
        ('point_group', [[0], [1], [2], [3], [4], [5]]),
        ('laue_class', [[0, 1], [2, 3], [4, 5]]),
    ],
)
def test_merge_modes_weighted_sigma_and_published_r_factors(native, tmp_path, mode, groups):
    root = stage(
        tmp_path / 'input', declarations=f'_reflns.merge {mode}\n_reflns.absences include\n'
    )
    result = observe(native, root, 'admission')
    assert result['ok'], 'Every declared constant-wavelength merge mode must reach the real fit'
    reduced, r_int, r_sigma = merged(MERGE_ROWS, groups)
    require_fit(result, [(0, 0, 0, mean, sigma) for mean, sigma in reduced])
    text = (tmp_path / 'input-saved/experiments/bank.edi').read_text()
    assert scalar(text, '_reflns.number_total') == len(groups), (
        'The unique count must equal groups after admission and before the cutoff'
    )
    assert scalar(text, '_refine_ls.number_reflns') == len(groups), (
        'The used count must equal the residual observation count with no fit cutoff'
    )
    assert scalar(text, '_reflns.R_sigma') == pytest.approx(r_sigma, rel=1e-6), (
        'R-sigma must sum the larger internal/external merged uncertainties '
        'over the used merged intensities'
    )
    if r_int is None or mode == 'none':
        assert '_diffrn_reflns.av_R_equivalents ' not in text, (
            'Rint without repeated merged groups must remain undefined '
            'rather than a fabricated zero'
        )
    else:
        assert scalar(text, '_diffrn_reflns.av_R_equivalents') == pytest.approx(r_int, rel=1e-6), (
            'Published Rint must use repeated original observations and the '
            'weighted group mean on intensities'
        )


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
    assert scalar(text, '_reflns.R_sigma') == pytest.approx(expected_sigma, rel=1e-6), (
        'R-sigma must use only merged observations that survive the fit cutoff'
    )


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
        assert scalar(text, '_diffrn_reflns.av_R_equivalents') == pytest.approx(
            float(expected['r_int']), rel=1e-6
        ), 'The measured-list Rint must agree with the independently computed published definition'

    assert scalar(text, '_reflns.R_sigma') == pytest.approx(
        float(expected['r_sigma_weighted']), rel=1e-6
    ), (
        'Measured-list R-sigma must use the independently calculated '
        'weighted scatter and propagated uncertainty'
    )


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


def test_absence_diagnostic_reports_independent_count_and_mean(native, tmp_path):
    rows = [
        (1, 0, 0, 12, 2),
        (1, 1, 1, 18, 3),
        (2, 0, 0, 10, 1),
        (2, 1, 1, 14, 2),
        (2, 2, 0, -2, 3),
    ]
    root = stage(
        tmp_path / 'input', rows=rows, group='I m -3 m', declarations='_reflns.absences exclude\n'
    )
    result = observe(native, root, 'admission')
    assert result['ok'], (
        'Systematic-absence warning must not prevent the fit of allowed observations'
    )
    notices = [
        line for line in result['notes'].splitlines() if 'systematic absences' in line.lower()
    ]
    assert len(notices) == 1, 'Strong systematic absences must produce one named diagnostic'
    assert re.search(r'\b2\b.*\b6(?:\.0*)?\b', notices[0]), (
        'The diagnostic must name the independently known absent count two and mean I/sigma six'
    )


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


def test_assistant_inspect_project_carries_the_same_merge_statistics(native, tmp_path):
    root = stage(tmp_path / 'input', declarations='_reflns.merge laue_class\n')
    result = observe(native, root, 'admission')
    assert result['ok'], (
        'The real assistant context must be observable after the actual native fit'
    )
    assert len(result['inspect']) == 1, (
        'The native controller must return one actual inspect_project context'
    )
    context = json.loads(bytes.fromhex(result['inspect'][0][0]).decode())
    found = {}

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                normalized = key.lower().replace('_', '').replace('-', '')
                if normalized in {'rint', 'avrequivalents', 'rsigma'}:
                    found[normalized] = item
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(context)
    _, r_int, r_sigma = merged(MERGE_ROWS, [[0, 1], [2, 3], [4, 5]])
    actual_rint = found.get('rint', found.get('avrequivalents'))
    assert actual_rint == pytest.approx(r_int, rel=1e-6), (
        'The actual inspect_project context must expose the independently computed Rint'
    )
    assert found.get('rsigma') == pytest.approx(r_sigma, rel=1e-6), (
        'The actual inspect_project context must carry the same independently computed R-sigma'
    )


def test_exact_hkl_omission_removes_all_repeated_rows_without_omitting_mates(native, tmp_path):
    rows = [*MERGE_ROWS, (1, 0, 0, 1000000, 1)]
    root = stage(tmp_path / 'input', rows=rows, declarations=exclusion(1, 0, 0))
    result = observe(native, root, 'admission')
    assert result['ok'], (
        'An exact hkl omission must admit a valid residual after repeated '
        'matching rows are removed'
    )
    require_fit(result, rows[1:6])
    text = (tmp_path / 'input-saved/experiments/bank.edi').read_text()
    assert scalar(text, '_reflns.number_excluded') == 2, (
        'The declared exact-index policy removes every repeated matching observation, '
        'counted independently of its mate'
    )


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
