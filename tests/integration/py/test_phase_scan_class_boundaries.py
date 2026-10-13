"""Free-set, terminal-state and recursive-save invariants from declared inputs."""

import csv

import edi as engine
import pytest

from tests.fixtures import phase_scan


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
    actual = set(result[0]) - {
        'file_path',
        'fit_result.reduced_chi_square',
        'fit_result.success',
        'fit_result.iterations',
    }
    assert actual == expected | {key + '.uncertainty' for key in expected}, (
        'Every declared active free category, including both texture fields per phase, '
        'must have exactly one qualified value and uncertainty column'
    )
    before = (directory / 'analysis/results.csv').read_bytes()
    first = fit(project)
    assert (directory / 'analysis/results.csv').read_bytes() == before, (
        'A completed resume must preserve the complete per-phase result schema and rows'
    )
    assert first.values, 'A completed resume must recover the declared free result population'


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

    fresh = fit(project, on_iteration=refuse_terminal, on_file_complete=completed.append)
    assert failures == ['terminal solver step'], (
        'The terminal refusal must execute after the successful first file and a solver step'
    )
    recorded = rows(directory / 'analysis/results.csv')
    assert [row['fit_result.success'] for row in recorded] == ['True', 'False'], (
        'The terminal-state invariant must reach a refused terminal after success'
    )
    assert fresh.values, 'The refused terminal must return its recoverable fitted parameter state'
    values = [parameter.value for parameter in project.free_parameters]
    resumed = fit(project)
    assert fresh.values == resumed.values, (
        'Fresh refusal and completed no-op resume must expose identical terminal parameters'
    )
    assert [parameter.value for parameter in project.free_parameters] == values, (
        'Edi and engine models must retain the same parameter state across a no-op resume'
    )


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
