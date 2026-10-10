"""gates for the owner-ruled test cadence and runtime measurement policy.

The independent authority is development hub's committed 2026-08-28 owner rulings: aggregate
suite budgets are retired, unchanged collections keep their banked measurements,
and only newly collected nodes are measured once against fixed per-test bounds.
"""

from __future__ import annotations

import importlib.util
import json
import re
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
RUNTIME_AUDIT = ROOT / 'tools/checks/per_pr_runtimes.py'


def _load_runtime_audit() -> Any:
    spec = importlib.util.spec_from_file_location('e09_t53_edi_runtime_audit', RUNTIME_AUDIT)
    assert spec is not None, 'the runtime audit module must have an import specification'
    assert spec.loader is not None, 'the runtime audit module must have an executable loader'
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _strings(value: object) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, dict):
        return {item for child in value.values() for item in _strings(child)}
    if isinstance(value, list):
        return {item for child in value for item in _strings(child)}
    return set()


def _seed_manifest(audit: Any, path: Path, nodeid: str, seconds: float = 0.060) -> None:
    path.write_text(
        audit.render_manifest({nodeid: seconds}, ['Recorded from: prior-green.log']),
        encoding='utf-8',
    )


def test_owner_cadence_has_only_quick_and_full_entry_points() -> None:
    audit = _load_runtime_audit()
    assert audit.TIER_THRESHOLDS == {
        'unit/py': 0.1,
        'unit/cpp': 0.1,
        'integration': 1.0,
        'system': 5.0,
    }, 'the owner ruling preserves every exact per-test tier threshold'
    distributed = {
        f'tests/system/py/test_distributed_{index}.py::test_cost': 0.9 for index in range(600)
    }
    assert not audit._ratchet_errors(distributed, set()), (
        'individually conforming tests must not acquire an aggregate-total verdict'
    )

    pixi = tomllib.loads((ROOT / 'pixi.toml').read_text(encoding='utf-8'))
    tasks = pixi['tasks']
    assert {'verify-quick', 'verify-full'} <= tasks.keys(), (
        'review and merge need explicit quick/full verification entry points'
    )
    assert not any('per-commit' in name for name in tasks), (
        'the owner-ruled cadence runs nothing per commit'
    )
    executable = '\n'.join(_strings(tasks))
    assert 'verify-wall-clock.py' not in executable, (
        'a full-suite wall-clock wrapper is an aggregate suite budget under another name'
    )
    assert '--ceiling' not in executable, (
        'a full-suite wall-clock ceiling is an aggregate suite budget under another name'
    )

    groups = json.loads((ROOT / 'tests/test-groups.json').read_text(encoding='utf-8'))['groups']
    regular = {
        name: group
        for name, group in groups.items()
        if name not in {'macos-smoke', 'nightly-full'}
    }
    quick = {
        name
        for name, group in regular.items()
        if re.search(r'quick|ci-on-pr', f'{name} {group.get("task", "")}', re.IGNORECASE)
    }
    full = {
        name
        for name, group in regular.items()
        if re.search(r'full|merge', f'{name} {group.get("task", "")}', re.IGNORECASE)
    }
    assert len(quick) == 1, 'the cadence needs exactly one quick/CI-PR group'
    assert len(full) == 1, 'the cadence needs exactly one full/merge group'
    assert set(regular) == quick | full | {'app'}, (
        'regular cadence keeps quick/full and app; macOS policy adds only its two named groups'
    )
    assert groups['app']['tiers'] == ['integration/app'], (
        ': only app-dependent Python integration tests belong to the app group'
    )
    assert groups['app']['task'] == 'group-app', (
        ': the app group declares the entry point shared by app CI and local verification'
    )
    quick_task = groups[next(iter(quick))]['task']
    full_task = groups[next(iter(full))]['task']
    assert quick_task in _strings(tasks['verify-quick']), (
        'the quick verification entry point must execute the declared quick group'
    )
    assert full_task in _strings(tasks['verify-full']), (
        'the full verification entry point must execute the declared full group'
    )


def test_unchanged_collection_keeps_banked_measurement_without_reading_evidence(
    monkeypatch: Any, tmp_path: Path
) -> None:
    audit = _load_runtime_audit()
    existing = 'tests/unit/py/test_alpha.py::test_fast'
    manifest = tmp_path / 'per-pr-runtimes.tsv'
    _seed_manifest(audit, manifest, existing)
    monkeypatch.setattr(audit, 'MANIFEST', manifest)
    monkeypatch.setattr(audit, 'collect_nodeids', lambda: [existing])
    before = manifest.read_bytes()
    never_created = tmp_path / 'unchanged-collection-must-not-read-this.log'

    assert audit.update(never_created, None) == 0, (
        'an unchanged collection must succeed without new measurement evidence'
    )
    assert manifest.read_bytes() == before, (
        'an unchanged collection must preserve the banked manifest byte for byte'
    )


def test_banked_measurement_does_not_expire_when_collection_is_unchanged(tmp_path: Path) -> None:
    audit = _load_runtime_audit()
    existing = 'tests/unit/py/test_alpha.py::test_fast'
    manifest = tmp_path / 'per-pr-runtimes.tsv'
    _seed_manifest(audit, manifest, existing)
    text = manifest.read_text(encoding='utf-8')
    text = re.sub(
        r'(?m)^# measured_utc = \S+$',
        '# measured_utc = 2000-01-01T00:00:00Z',
        text,
    )
    manifest.write_text(text, encoding='utf-8')

    assert audit.load_manifest(manifest)[1] == {existing: 0.060}, (
        'banked measurements must remain valid without an aggregate expiry date'
    )


def test_changed_collection_measures_only_new_nodes_and_rejects_a_new_breach(
    monkeypatch: Any, tmp_path: Path
) -> None:
    audit = _load_runtime_audit()
    existing = 'tests/unit/py/test_alpha.py::test_fast'
    added = 'tests/integration/py/test_beta.py::test_added'
    manifest = tmp_path / 'per-pr-runtimes.tsv'
    log = tmp_path / 'new-node-durations.log'
    fixture_costs = tmp_path / 'fixture-costs.json'
    _seed_manifest(audit, manifest, existing)
    monkeypatch.setattr(audit, 'MANIFEST', manifest)
    monkeypatch.setattr(audit, 'collect_nodeids', lambda: [existing, added])
    fixture_costs.write_text(
        json.dumps({'module_costs': {}, 'completed': [added]}),
        encoding='utf-8',
    )
    log.write_text(
        f'0.10s setup    {added}\n'
        f'0.40s call     {added}\n'
        f'0.10s teardown {added}\n'
        '============================== 1 passed in 0.60s ==============================\n',
        encoding='utf-8',
    )

    assert audit.update(log, fixture_costs) == 0, (
        'a conforming added node must be banked from one focused measurement'
    )
    assert audit.load_manifest(manifest)[1] == {existing: 0.060, added: 0.600}, (
        'the focused update must preserve old evidence and add only the new node'
    )

    _seed_manifest(audit, manifest, existing)
    before_breach = manifest.read_bytes()
    log.write_text(
        f'0.20s setup    {added}\n'
        f'0.70s call     {added}\n'
        f'0.10s teardown {added}\n'
        '============================== 1 passed in 1.00s ==============================\n',
        encoding='utf-8',
    )
    assert audit.update(log, fixture_costs) != 0, (
        'a newly measured per-test threshold breach must refuse the update'
    )
    assert manifest.read_bytes() == before_breach, (
        'a refused threshold breach must not rewrite the banked manifest'
    )
