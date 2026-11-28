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

    reference_root = tmp_path / 'explicit'
    stage_scan_cubic(reference_root, 'parametric', shared_w=common)
    analysis = reference_root / 'analysis/analysis.edi'
    start_rows = [
        f'{file} {name} {row[name]}' for file, row in first.items() for name in SEED_COLUMNS
    ]
    analysis.write_text(
        analysis.read_text() + '\nloop_\n' + '\n'.join((*cases.START_TAGS, *start_rows)) + '\n'
    )
    engine.Project.load(reference_root).analysis.fit()

    completed = []
    project.analysis.fit(on_file_complete=completed.append)
    assert len(completed) == len(POINT_FILES), 'The shared repeat refits every point'
    assert point_results(root) == point_results(reference_root), (
        'Automatic continuation matches the explicitly seeded shared and local fit'
    )


def results_row_identity(root, file):
    lines = (root / 'analysis/results.csv').read_bytes().splitlines()
    line = next(line for line in lines if Path(line.split(b',', 1)[0].decode()).name == file)
    # ADR-0136's persisted token is 64-bit FNV-1a over the CSV row bytes.
    identity = 0xCBF29CE484222325
    for byte in line:
        identity = ((identity ^ byte) * 0x100000001B3) % (1 << 64)
    return f'{identity:016x}'


def add_point_start(root, file, value, over):
    analysis = root / 'analysis/analysis.edi'
    tags = cases.START_TAGS
    tail = f'{file} {SEED_COLUMNS[0]} {value}'
    if over is not None:
        tags = (*tags, '_parametric_fit_start.over')
        tail += f' {over}'
    analysis.write_text(analysis.read_text() + '\nloop_\n' + '\n'.join((*tags, tail)) + '\n')


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
def test_saved_point_start_overrides_one_result_generation(tmp_path, mode):
    root = tmp_path / 'scan'
    project = stage_scan_cubic(root, mode)
    project.save()
    template = template_documents(root)
    project.analysis.fit()
    first = point_results(root)
    target = 'p1.xy'
    original = results_row_identity(root, target)
    value = '4.217'
    add_point_start(root, target, value, original)
    project = engine.Project.load(root)
    project.save()
    assert template_documents(root) == template, (
        'Saving a point start leaves the experiment and structure template intact'
    )
    analysis = (root / 'analysis/analysis.edi').read_text()
    assert value in analysis, 'Save preserves the authored start value'
    assert original in analysis, 'Save preserves the identity of the row that the edit overrides'
    seeded = {**first, target: {**first[target], SEED_COLUMNS[0]: value}}
    second = check_refit_against_explicit_seeds(root, tmp_path / 'edited', seeded)
    assert results_row_identity(root, target) != original, (
        'The refit must publish a replacement row before testing start expiry'
    )
    check_refit_against_explicit_seeds(root, tmp_path / 'consumed', second)
    assert template_documents(root) == template, 'Refitting never writes the scan template'


@pytest.mark.parametrize('mode', SCAN_MODES)
@pytest.mark.parametrize('over', [None, 'none'], ids=['legacy', 'explicit'])
def test_start_for_point_without_row_survives_save_and_reopen(tmp_path, mode, over):
    root = tmp_path / 'scan'
    stage_scan_cubic(root, mode, 'p1.xy')
    add_point_start(root, 'p1.xy', '4.217', over)
    project = engine.Project.load(root)
    project.save()
    analysis = (root / 'analysis/analysis.edi').read_text()
    assert '4.217' in analysis, 'A start made with no result row survives Save'
    reference = stage_scan_cubic(tmp_path / 'reference', 'independent', 'p1.xy')
    reference.structures['phase'].cell.length_a.value = 4.217
    reference.analysis.fit()
    engine.Project.load(root).analysis.fit()
    actual = point_results(root)
    expected = point_results(tmp_path / 'reference')
    assert set(actual) == set(expected) == {'p1.xy'}, 'Both fits execute the same admitted point'
    for field in SEED_COLUMNS:
        value, rounding = published_value(actual['p1.xy'], field)
        truth, truth_rounding = published_value(expected['p1.xy'], field)
        assert abs(value - truth) <= rounding + truth_rounding + abs(truth) * Decimal('1e-6'), (
            'A legacy or explicit no-row start reaches the solver after Save and reopen',
            field,
        )
