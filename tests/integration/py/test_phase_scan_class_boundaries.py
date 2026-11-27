"""Free-set, terminal-state and recursive-save invariants from declared inputs."""

import csv

import edi as engine
import pytest

from tests.fixtures import phase_scan
from tests.fixtures.report_units.iucr_reference import rounded_pair
from tests.fixtures.scan_csv import TWO_PHASE_SUFFIX


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def fit(project, **kwargs):
    return project.analysis.fit(on_scan_start=lambda _record: None, **kwargs)


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('background', ['line-segment', 'polynomial', 'chebyshev'])
def test_recorded_columns_equal_every_declared_free_category(tmp_path, mode, background):
    directory, expected = phase_scan.category_scan(tmp_path / 'scan', mode, background)
    project = engine.Project.load(directory)
    fit(project)
    result = rows(directory / 'analysis/results.csv')
    header = list(result[0])
    assert header[-len(TWO_PHASE_SUFFIX) :] == TWO_PHASE_SUFFIX, (
        'ADR-0132 places conditions and derived phase fractions before the agreement factors'
    )
    actual = set(header[: -len(TWO_PHASE_SUFFIX)]) - {
        'file_path',
        'fit_result.reduced_chi_square',
        'fit_result.success',
        'fit_result.iterations',
    }
    assert actual == expected | {key + '.uncertainty' for key in expected}, (
        'Every declared active free category, including both texture fields per phase, '
        'has exactly one qualified value and uncertainty column'
    )
    template = [p.value for p in project.free_parameters]
    completions = []
    repeat = fit(project, on_file_complete=completions.append)
    current = rows(directory / 'analysis/results.csv')
    assert len(completions) == len(current) == len(result), (
        'A completed scan runs every phase-bearing dataset again'
    )
    assert list(current[0]) == header, 'The second generation retains the exact per-phase schema'
    assert [row['file_path'] for row in current] == [row['file_path'] for row in result], (
        'The second generation retains every point identity in order'
    )
    assert repeat.values, 'The new terminal fit provides its declared free result population'
    assert [p.value for p in project.free_parameters] == template, (
        'Refitting does not replace the project template free values'
    )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
def test_texture_only_scan_records_both_phase_rows(tmp_path, mode):
    directory, expected = phase_scan.category_scan(tmp_path / 'scan', mode, texture_only=True)
    fit(engine.Project.load(directory))
    recorded = rows(directory / 'analysis/results.csv')
    assert len(recorded) == 2, 'Texture-only free sets must reach both scan files'
    assert expected <= set(recorded[0]), 'Texture-only fits must record every active phase texture'


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
def test_refused_terminal_returns_same_state_as_completed_resume(tmp_path, mode):
    directory = phase_scan.materialize(tmp_path / 'scan', mode)
    (directory / 'experiments/scan/03.xy').unlink()
    project = engine.Project.load(directory)
    project.structures['alpha'].atom_sites[0].adp_iso.free = True
    completed, failures = [], []

    def refuse_terminal(_record):
        if len(completed) == 1 and not failures:
            failures.append('terminal solver step')
            message = 'Authored terminal refusal after solver entry'
            raise ValueError(message)

    template = [p.value for p in project.free_parameters]
    fresh = fit(project, on_iteration=refuse_terminal, on_file_complete=completed.append)
    assert failures == ['terminal solver step'], (
        'The terminal refusal must execute after the successful first file and a solver step'
    )
    recorded = rows(directory / 'analysis/results.csv')
    assert [row['fit_result.success'] for row in recorded] == ['True', 'False'], (
        'The terminal-state invariant must reach a refused terminal after success'
    )
    assert fresh.values, 'The refused terminal must return its recoverable fitted parameter state'
    raw = dict(fresh.values)
    # Independent fitting restores the original template after each file. Only
    # sequential fitting carries the last completed file forward through CSV.
    expected = (
        raw
        if mode == 'independent'
        else {
            key: rounded_pair(value, fresh.uncertainty.get(key), 'iucr_99')[0]
            for key, value in raw.items()
        }
    )
    csv_path = directory / 'analysis/results.csv'
    header, _first, terminal = csv_path.read_bytes().splitlines(keepends=True)
    retained = header + terminal
    csv_path.write_bytes(retained)
    completions = []
    assert fit(project, on_file_complete=completions.append).values == expected, (
        'Gap fill recovers the exact reported values from the retained terminal row'
    )
    assert fresh.values == raw, 'Filling a gap preserves the earlier returned raw fit result'
    assert [p.value for p in project.free_parameters] == template, (
        'Both the refusing scan and gap fill preserve the caller template values'
    )
    assert csv_path.read_bytes().startswith(retained), 'Gap fill retains the exact terminal row'
    assert len(completions) == 1, 'Gap fill fits only the missing point'


@pytest.mark.parametrize('root_data', [False, True])
@pytest.mark.parametrize('operation', ['same', 'nested', 'existing'])
def test_scan_save_excludes_its_own_destination_and_links_source(tmp_path, root_data, operation):
    directory = phase_scan.materialize(tmp_path / 'source')
    scan = directory / 'experiments/scan'
    if root_data:
        for path in scan.glob('*.xy'):
            path.rename(directory / path.name)
        scan = directory
        analysis = directory / 'analysis/analysis.edi'
        analysis.write_text(
            analysis.read_text().replace('data_dir experiments/scan', 'data_dir .')
        )
    originals = {
        path.name: (path.stat().st_dev, path.stat().st_ino, path.read_bytes())
        for path in scan.glob('*.xy')
    }
    project = engine.Project.load(directory)
    destination = directory if operation == 'same' else scan / 'saved'
    if operation == 'existing':
        destination.mkdir()
        (destination / 'obsolete').write_text('not scan input')
    if operation == 'same':
        project.save()
    else:
        project.save_as(destination)
    copied = destination if root_data else destination / 'experiments/scan'
    for name, expected in originals.items():
        path = copied / name
        assert (path.stat().st_dev, path.stat().st_ino, path.read_bytes()) == expected, (
            'Every unchanged scan dataset must retain its original inode and byte contents'
        )
    assert not (copied / 'saved').exists(), (
        'The scan input walk must exclude both an existing destination and its staging tree'
    )
    assert not any('.tmp' in path.name for path in copied.iterdir()), (
        'An atomic scan save must never include its own staging directory'
    )
