"""Runtime inventory reconciliation indexes membership without changing custody."""

import importlib.util
import json
from collections import UserList
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


class IndexedCollection(UserList):
    """A collected inventory must not be searched linearly once per banked row."""

    def __contains__(self, _value):
        raise AssertionError('Repeated linear collection membership is quadratic')


@pytest.fixture
def checker():
    spec = importlib.util.spec_from_file_location(
        'indexed_runtime', ROOT / 'tools/checks/per_pr_runtimes.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('remeasure', [False, True])
def test_indexed_update_preserves_measurements_holes_foreign_rows_and_stale_removal(
    checker, tmp_path, monkeypatch, remeasure
):
    kept = 'tests/unit/py/test_kept.py::test_kept'
    added = 'tests/unit/py/test_added.py::test_added'
    hole = 'tests/unit/py/test_hole.py::test_hole'
    stale = 'tests/unit/py/test_stale.py::test_stale'
    foreign = 'tests/unit/cpp/independent-case'
    manifest = tmp_path / 'per-pr-runtimes.tsv'
    manifest.write_text(
        f'0.040\t{kept}\n0.060\t{stale}\n0.070\t{foreign}\nUNMEASURED:prior-reason\t{hole}\n',
        encoding='utf-8',
    )
    log = tmp_path / 'durations.log'
    log.write_text(f'0.020s call {added}\n0.030s call {kept}\n', encoding='utf-8')
    costs = tmp_path / 'costs.json'
    costs.write_text(
        json.dumps({'module_costs': {}, 'completed': [added, kept]}), encoding='utf-8'
    )
    monkeypatch.setattr(checker, 'MANIFEST', manifest)
    monkeypatch.setattr(checker, 'collect_nodeids', lambda: IndexedCollection([kept, added, hole]))
    assert checker._update(log, costs, [kept] if remeasure else []) == 0
    result = manifest.read_text(encoding='utf-8')
    values = checker._measured_values_in(result)
    assert values == {kept: 0.03 if remeasure else 0.04, added: 0.02, foreign: 0.07}
    assert checker._unmeasured_reasons(result) == {hole: 'prior-reason'}
    assert stale not in result


def test_unknown_remeasurement_still_refuses_before_writing(checker, tmp_path, monkeypatch):
    manifest = tmp_path / 'per-pr-runtimes.tsv'
    manifest.write_text('unchanged sentinel\n', encoding='utf-8')
    monkeypatch.setattr(checker, 'MANIFEST', manifest)
    monkeypatch.setattr(checker, 'collect_nodeids', lambda: IndexedCollection(['known.py::known']))
    with pytest.raises(checker.ManifestError, match='names nodes that are not collected'):
        checker._update(tmp_path / 'absent.log', tmp_path / 'absent.json', ['foreign.py::foreign'])
    assert manifest.read_text(encoding='utf-8') == 'unchanged sentinel\n'


@pytest.mark.parametrize('phase', ['setup', 'call', 'teardown'])
def test_duration_without_completed_node_evidence_remains_unmeasured(
    checker, tmp_path, monkeypatch, phase
):
    node = 'tests/unit/py/test_interrupted.py::test_interrupted'
    manifest = tmp_path / 'per-pr-runtimes.tsv'
    manifest.write_text('', encoding='utf-8')
    log = tmp_path / 'durations.log'
    log.write_text(f'0.020s {phase} {node}\n', encoding='utf-8')
    costs = tmp_path / 'costs.json'
    costs.write_text(json.dumps({'module_costs': {}, 'completed': []}), encoding='utf-8')
    monkeypatch.setattr(checker, 'MANIFEST', manifest)
    monkeypatch.setattr(checker, 'collect_nodeids', lambda: [node])
    assert checker._update(log, costs, []) == 0
    text = manifest.read_text(encoding='utf-8')
    assert node not in checker._measured_values_in(text), (
        'A reported phase duration cannot prove that an interrupted test completed'
    )
    assert checker._unmeasured_reasons(text) == {node: 'not-completed-in-this-run'}
    costs.write_text(json.dumps({'module_costs': {}, 'completed': [node]}), encoding='utf-8')
    assert checker._update(log, costs, [node]) == 0
    assert checker._measured_values_in(manifest.read_text(encoding='utf-8')) == {node: 0.02}
