"""Noiseless inverse recovery uses frozen observations and authored parameter truth."""

import json
import shutil
from decimal import Decimal
from pathlib import Path

import edi as engine
import pytest

from tests.fixtures.parametric_series import cases

FIXTURE = Path(__file__).resolve().parents[2] / 'fixtures/parametric_series'


def test_five_cubic_patterns_recover_shared_profile_and_local_parameters(tmp_path):
    truth = json.loads((FIXTURE / 'cubic-truth.json').read_text())
    root = tmp_path / 'series'
    shutil.copytree(FIXTURE / 'cubic', root)
    engine.Project.load(root).analysis.fit()
    rows = cases.rows(root)
    assert len(rows) == 5, 'Every frozen cubic pattern participates in the parametric solution'
    for index, row in enumerate(rows):
        values = {
            'phase.cell.length_a': truth['cell'][index],
            'phase.atom_site.A.adp_iso': truth['biso'][index],
            'zeta.linked_structure.phase.scale': truth['scale'][index],
            **{'zeta.peak.' + key: value for key, value in truth['profile'].items()},
        }
        for name, expected in values.items():
            assert float(row[name]) == pytest.approx(expected, rel=1e-6), (
                'The noiseless inverse fit recovers the authored shared and per-point truth'
            )


def published_value(row, name):
    """Return the value and its half-place rounding bound under ADR-0092."""
    value = Decimal(row[name])
    uncertainty = Decimal(row[name + '.uncertainty'])
    if uncertainty.is_finite() and uncertainty > 0:
        exponent = min(value.as_tuple().exponent, uncertainty.as_tuple().exponent)
    elif value:
        exponent = value.adjusted() - 5
    else:
        return value, Decimal(0)
    return value, Decimal('0.5').scaleb(exponent)


SCAN_MODES = ('sequential', 'independent', 'parametric')
POINT_FILES = tuple(f'p{index}.xy' for index in range(5))
FIT_COLUMNS = ('success', 'termination', 'iterations', 'reduced_chi_square')
SEED_COLUMNS = (
    'phase.cell.length_a',
    'phase.atom_site.A.adp_iso',
    'zeta.linked_structure.phase.scale',
)


def stage_scan_cubic(root, mode, pattern='p?.xy', *, shared_w=None):
    shutil.copytree(FIXTURE / 'cubic', root)
    analysis = root / 'analysis/analysis.edi'
    text = analysis.read_text().split('loop_', 1)[0]
    analysis.write_text(
        text.replace('_fitting_mode.type parametric', '_fitting_mode.type ' + mode).replace(
            'p?.xy', pattern
        )
    )
    experiment = root / 'experiments/0_zeta.edi'
    w = '0.15' if shared_w is None else f'{shared_w}()'
    experiment.write_text(
        experiment
        .read_text()
        .replace('_peak.broad_gauss_u 0.1()', '_peak.broad_gauss_u 0.12')
        .replace('_peak.broad_gauss_v -0.02()', '_peak.broad_gauss_v -0.03')
        .replace('_peak.broad_gauss_w 0.17()', f'_peak.broad_gauss_w {w}')
    )
    if shared_w is not None:
        cases.append_shared(root, ['zeta.peak.broad_gauss_w'])
    poor_point = root / 'scan/p1.xy'
    lines = poor_point.read_text().splitlines()
    x, intensity, uncertainty = lines[8].split()
    lines[8] = f'{x} {float(intensity) + 100} {uncertainty}'
    poor_point.write_text('\n'.join(lines) + '\n')
    return engine.Project.load(root)


def point_results(root):
    return {Path(row['file_path']).name: row for row in cases.rows(root)}


def template_documents(root):
    return {
        path.relative_to(root): path.read_bytes()
        for folder in ('experiments', 'structures')
        for path in (root / folder).glob('*.edi')
    }


@pytest.mark.parametrize('mode', SCAN_MODES)
def test_scan_fit_and_save_preserve_template(tmp_path, mode):
    root = tmp_path / 'scan'
    project = stage_scan_cubic(root, mode)
    project.save()
    original = template_documents(root)
    assert {path.parts[0] for path in original} == {'experiments', 'structures'}, (
        'The baseline Save writes both template documents before any fit'
    )
    cell = project.structures['phase'].cell.length_a
    original_cell = (cell.value, cell.free)
    project.analysis.fit()
    results = point_results(root)
    assert tuple(results) == POINT_FILES, 'The fit publishes all five owned point rows'
    assert any(
        abs(float(row[SEED_COLUMNS[0]]) - original_cell[0]) > 1e-6 for row in results.values()
    ), 'At least one fitted cell value differs from the template'
    cell = project.structures['phase'].cell.length_a
    live_unchanged = (cell.value, cell.free) == original_cell
    files_unchanged = template_documents(root) == original
    project.save()
    saved_unchanged = template_documents(root) == original
    assert (live_unchanged, files_unchanged, saved_unchanged) == (True, True, True), (
        'The scan preserves live values, leaves template files alone, and saves identical bytes'
    )


def fit_point_from_row(tmp_path, file, row):
    oracle_root = tmp_path / Path(file).stem
    oracle = stage_scan_cubic(oracle_root, 'independent', file)
    structure = oracle.structures['phase']
    experiment = oracle.experiments['zeta']
    parameters = (
        structure.cell.length_a,
        structure.atom_sites[0].adp_iso,
        experiment.linked_structures['phase'].scale,
    )
    for name, parameter in zip(SEED_COLUMNS, parameters, strict=True):
        parameter.value = float(row[name])
    oracle.analysis.fit()
    return point_results(oracle_root)[file]


@pytest.mark.parametrize('mode', SCAN_MODES)
def test_scan_refit_uses_only_each_files_latest_row(tmp_path, mode):
    root = tmp_path / 'scan'
    project = stage_scan_cubic(root, mode)
    project.analysis.fit()
    first = point_results(root)
    assert tuple(first) == POINT_FILES, 'The first run publishes a seed row for each file'
    assert float(first['p1.xy']['fit_result.reduced_chi_square']) > 1, (
        'The independently perturbed point remains a poor fit'
    )

    expected = {file: fit_point_from_row(tmp_path, file, row) for file, row in first.items()}

    completed = []
    project.analysis.fit(on_file_complete=completed.append)
    assert len(completed) == len(POINT_FILES), 'A second Fit actually processes every point again'
    actual = point_results(root)
    assert tuple(actual) == POINT_FILES, 'The second result generation preserves file identities'
    for file, row in actual.items():
        reference = expected[file]
        for field in FIT_COLUMNS:
            column = 'fit_result.' + field
            assert row[column] == reference[column], (
                'Each repeat fit matches the cold single-file solve seeded with its own row',
                file,
                field,
            )
        for name in SEED_COLUMNS:
            value, rounding = published_value(row, name)
            reference_value, reference_rounding = published_value(reference, name)
            tolerance = abs(reference_value) * Decimal('1e-6')
            assert abs(value - reference_value) <= rounding + reference_rounding + tolerance, (
                'Each repeated fit recovers the values from its own explicitly seeded reference',
                file,
                name,
            )


@pytest.mark.parametrize('mode', SCAN_MODES)
def test_scan_with_results_removed_replays_first_fit(tmp_path, mode):
    root = tmp_path / 'scan'
    project = stage_scan_cubic(root, mode)
    original_analysis = set((root / 'analysis').iterdir())
    project.analysis.fit()
    first = cases.rows(root)
    assert len(first) == len(POINT_FILES), 'The first fit establishes a complete result generation'
    for output in set((root / 'analysis').iterdir()) - original_analysis:
        if output.is_file() and output.suffix == '.csv':
            output.unlink()
    completed = []
    project.analysis.fit(on_file_complete=completed.append)
    assert len(completed) == len(POINT_FILES), 'Clearing result files makes every point fit anew'
    assert cases.rows(root) == first, (
        'Fitting again without saved results reproduces the first scan from the same live template'
    )


def test_parametric_refit_uses_the_common_value_and_each_points_row(tmp_path):
    root = tmp_path / 'scan'
    project = stage_scan_cubic(root, 'parametric', shared_w='0.15')
    project.analysis.fit()
    first = point_results(root)
    shared_name = 'zeta.peak.broad_gauss_w'
    assert tuple(first) == POINT_FILES, 'The initial fit produces a row for each scanned point'
    common = first[POINT_FILES[0]][shared_name]
    assert {row[shared_name] for row in first.values()} == {common}, (
        'The first fit publishes one shared value for the whole scan'
    )

    reference_root = tmp_path / 'reference'
    stage_scan_cubic(reference_root, 'parametric', shared_w='0.30')
    shutil.copy2(root / 'analysis/results.csv', reference_root / 'analysis/results.csv')
    engine.Project.load(reference_root).analysis.fit()

    completed = []
    project.analysis.fit(on_file_complete=completed.append)
    assert len(completed) == len(POINT_FILES), 'The shared repeat refits every point'
    assert point_results(root) == point_results(reference_root), (
        'Identical published row starts give the same repeat despite different shared templates'
    )
    cases.assert_no_persisted_starts(root)


def check_refit_against_explicit_seeds(root, reference, seeds):
    expected = {file: fit_point_from_row(reference, file, row) for file, row in seeds.items()}
    completed = []
    engine.Project.load(root).analysis.fit(on_file_complete=completed.append)
    assert len(completed) == len(POINT_FILES), 'A complete scan must refit every admitted point'
    actual = point_results(root)
    assert set(actual) == set(expected), 'The refit must retain each independent point identity'
    for file, row in actual.items():
        for name in SEED_COLUMNS:
            value, rounding = published_value(row, name)
            truth, truth_rounding = published_value(expected[file], name)
            assert abs(value - truth) <= rounding + truth_rounding + abs(truth) * Decimal(
                '1e-6'
            ), (
                'Refit must match the isolated solve from the selected explicit start',
                file,
                name,
            )
    return actual


@pytest.mark.parametrize('mode', SCAN_MODES)
def test_retired_saved_start_does_not_override_latest_row(tmp_path, mode):
    root = tmp_path / 'scan'
    project = stage_scan_cubic(root, mode)
    project.save()
    template = template_documents(root)
    project.analysis.fit()
    first = point_results(root)
    cases.append_retired_starts(
        root, 'p1.xy phase.cell.length_a 4.217 0123456789abcdef', with_over=True
    )
    engine.Project.load(root).save()
    cases.assert_no_persisted_starts(root)
    assert template_documents(root) == template, (
        'Dropping a retired start leaves the structure and experiment template intact'
    )
    second = check_refit_against_explicit_seeds(root, tmp_path / 'repeat', first)
    check_refit_against_explicit_seeds(root, tmp_path / 'second-repeat', second)
    cases.assert_no_persisted_starts(root)
    assert template_documents(root) == template, 'Repeated fits leave the template unchanged'


@pytest.mark.parametrize('mode', SCAN_MODES)
@pytest.mark.parametrize('with_over', [False, True], ids=['three-columns', 'with-over'])
def test_retired_start_without_a_result_row_leaves_template_seed(tmp_path, mode, with_over):
    root = tmp_path / 'scan'
    stage_scan_cubic(root, mode, 'p1.xy')
    row = 'p1.xy phase.cell.length_a 4.217'
    cases.append_retired_starts(root, row + (' none' if with_over else ''), with_over=with_over)
    engine.Project.load(root).save()
    cases.assert_no_persisted_starts(root)
    reference = stage_scan_cubic(tmp_path / 'reference', mode, 'p1.xy')
    reference.analysis.fit()
    engine.Project.load(root).analysis.fit()
    assert point_results(root) == point_results(tmp_path / 'reference'), (
        'Without a result row, a retired on-disk start must have no effect on the template fit'
    )
    cases.assert_no_persisted_starts(root)
