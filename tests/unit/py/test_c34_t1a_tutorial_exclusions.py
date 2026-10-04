""": tutorial ports are durable, visible, and honestly execution-disabled."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Iterator
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
TUTORIALS = ROOT / 'docs/user/tutorials'
DECLARATION = TUTORIALS / 'execution-exclusions.yml'
CHECKER = ROOT / 'tools/checks/tutorial_execution_exclusions.py'
EXPECTED = {
    'refine-lbco-hrpt-from-data': 'tutorial-runner',
    'refine-si-sepd': 'tutorial-runner',
    'refine-ncaf-wish': 'tutorial-runner',
    'refine-cosio-d20-tscan': 'sequential-scan-tutorial',
    'simulate-si-tof': 'tutorial-runner',
}


def _walk(value: object) -> Iterator[object]:
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _entries(document: object) -> dict[str, dict[str, object]]:
    entries: dict[str, dict[str, object]] = {}
    for value in _walk(document):
        if not isinstance(value, dict) or 'unblocked_by' not in value:
            continue
        path_values = [
            candidate
            for candidate in value.values()
            if isinstance(candidate, str)
            and Path(candidate).stem in EXPECTED
            and Path(candidate).suffix in {'.py', '.ipynb'}
        ]
        assert len(path_values) == 1, (
            f' every execution-exclusion row must identify exactly one tutorial path; row={value}'
        )
        entries[Path(path_values[0]).stem] = value
    return entries


def _task_command(tasks: object, name: str) -> str:
    row = tasks.get(name) if isinstance(tasks, dict) else None
    if isinstance(row, str):
        return row
    if not isinstance(row, dict):
        return ''
    command = row.get('cmd', '')
    if isinstance(command, list):
        return shlex.join(str(item) for item in command)
    return command if isinstance(command, str) else ''


def _run(checkout: Path) -> subprocess.CompletedProcess[str]:
    checker = checkout / CHECKER.relative_to(ROOT)
    return subprocess.run(
        [sys.executable, os.fspath(checker)],
        cwd=checkout,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def _gate_checkout(base: Path) -> Path:
    assert CHECKER.is_file(), (
        ' requires tools/checks/tutorial_execution_exclusions.py to make exclusions expire'
    )
    checkout = base / 'edi'
    shutil.copytree(ROOT / 'tools/checks', checkout / 'tools/checks')
    shutil.copytree(TUTORIALS, checkout / TUTORIALS.relative_to(ROOT))
    shutil.copy2(ROOT / 'pixi.toml', checkout / 'pixi.toml')
    return checkout


def test_c34_t1a_all_five_ports_and_derived_notebooks_are_committed() -> None:
    assert (TUTORIALS / 'index.md').is_file(), (
        ' tutorials need a docs/user/tutorials landing page for directory auto-navigation'
    )
    for stem in EXPECTED:
        for suffix in ('.py', '.ipynb'):
            path = TUTORIALS / f'{stem}{suffix}'
            assert path.is_file(), f' must commit tutorial port {path.relative_to(ROOT)}'


def test_c34_t1a_exclusion_declaration_is_exact_and_each_notebook_names_its_unblocker() -> None:
    assert DECLARATION.is_file(), (
        ' execution-disabled tutorials require a committed, enumerated declaration'
    )
    entries = _entries(yaml.safe_load(DECLARATION.read_text(encoding='utf-8')))
    assert set(entries) == set(EXPECTED), (
        ' execution exclusions must enumerate exactly the five moved tutorial ports; '
        f'observed={sorted(entries)}'
    )
    for stem, task in EXPECTED.items():
        assert entries[stem].get('unblocked_by') == task, (
            f' exclusion for {stem} must expire when {task} closes'
        )
        source = (TUTORIALS / f'{stem}.py').read_text(encoding='utf-8')
        notebook = (TUTORIALS / f'{stem}.ipynb').read_text(encoding='utf-8')
        assert task in source and task in notebook, (
            f' source and notebook for {stem} must each name unblocking task {task}'
        )


def test_c34_t1a_ports_replace_deferred_switches_and_delete_only_max_workers() -> None:
    for stem, unblocker in EXPECTED.items():
        source_path = TUTORIALS / f'{stem}.py'
        notebook_path = TUTORIALS / f'{stem}.ipynb'
        source = source_path.read_text(encoding='utf-8')
        notebook_text = notebook_path.read_text(encoding='utf-8')
        code = '\n'.join(line for line in source.splitlines() if not line.lstrip().startswith('#'))
        assert re.search(r'\b(?:minimizer|calculator)\b', code, re.IGNORECASE) is None, (
            f' {stem} must not retain an executable minimizer/calculator switch'
        )
        comments = '\n'.join(
            line for line in source.splitlines() if line.lstrip().startswith('#')
        ).casefold()
        assert all(token in comments for token in ('defer', 'minimizer', 'calculator')), (
            f' {stem} must retain both deferred selectors as named public placeholders'
        )
        assert unblocker in source and unblocker in notebook_text, (
            'each deferred placeholder must retain its named public unblocker '
            'in both representations'
        )
        assert 'max_workers' not in source and 'max_workers' not in notebook_text, (
            f' {stem} must delete max_workers without leaving a placeholder'
        )


def test_c34_t1a_notebooks_are_stripped_and_execution_disabled() -> None:
    pixi = tomllib.loads((ROOT / 'pixi.toml').read_text(encoding='utf-8'))
    tasks = pixi.get('tasks', {})
    for task in ('notebook-tests', 'notebook-exec-ci'):
        command = _task_command(tasks, task)
        assert 'docs/user/tutorials' not in command, (
            f' execution-disabled tutorials must stay outside {task}'
        )
        assert 'docs/dev/verification' in command, (
            f' fixture requires {task} to retain its explicit verification-only scope'
        )
    for task in ('notebook-convert', 'notebook-strip'):
        assert 'docs/user/tutorials' in _task_command(tasks, task), (
            f' rendering task {task} must include the moved tutorials'
        )

    for stem in EXPECTED:
        document = json.loads((TUTORIALS / f'{stem}.ipynb').read_text(encoding='utf-8'))
        cells = document.get('cells', []) if isinstance(document, dict) else []
        assert cells, f' derived notebook {stem} must contain its ported cells'
        for cell in cells:
            if isinstance(cell, dict) and cell.get('cell_type') == 'code':
                assert cell.get('execution_count') is None, (
                    f' execution-disabled notebook {stem} must have no execution count'
                )
                assert cell.get('outputs') == [], (
                    f' execution-disabled notebook {stem} must commit no outputs'
                )


def test_c34_t1a_exclusion_checker_is_wired_into_both_verify_chains() -> None:
    pixi = (ROOT / 'pixi.toml').read_text(encoding='utf-8')
    assert 'tutorial-execution-exclusions' in pixi or 'tutorial_execution_exclusions.py' in pixi, (
        ' tutorial exclusion checker must have a named pixi task or direct invocation'
    )
    for task in ('verify-quick', 'verify-full'):
        start = pixi.find(f'{task} =')
        assert start >= 0, f' fixture must resolve the existing {task} task'
        end = pixi.find('\n', start)
        declaration = pixi[start : end if end >= 0 else len(pixi)]
        assert 'tutorial' in declaration, (
            f' tutorial exclusion checker must run in {task}, not remain optional'
        )


def test_c34_t1a_exclusion_gate_rehearses_each_local_red_and_a_clean_checkout(
    tmp_path: Path,
) -> None:
    baseline = _gate_checkout(tmp_path / 'baseline')
    control = _run(baseline)
    assert control.returncode == 0, (
        ' tutorial exclusion gate must be green from edi committed inputs alone; '
        f'output={control.stdout}{control.stderr}'
    )

    unlisted = tmp_path / 'unlisted'
    shutil.copytree(baseline, unlisted)
    (unlisted / TUTORIALS.relative_to(ROOT) / 'c34-unlisted.py').write_text(
        '# %%\nprint("unlisted")\n', encoding='utf-8'
    )
    result = _run(unlisted)
    assert result.returncode != 0, (
        ' local red (a) must reject an unexecuted tutorial source absent from the declaration'
    )

    missing = tmp_path / 'missing'
    shutil.copytree(baseline, missing)
    absent = missing / TUTORIALS.relative_to(ROOT) / f'{next(iter(EXPECTED))}.ipynb'
    absent.unlink()
    result = _run(missing)
    assert result.returncode != 0, (
        ' local red (b) must reject a declared notebook that does not exist'
    )

    executed = tmp_path / 'executed'
    shutil.copytree(baseline, executed)
    pixi_path = executed / 'pixi.toml'
    pixi_text = pixi_path.read_text(encoding='utf-8')
    assert 'docs/dev/verification/' in pixi_text, (
        ' red-(c) fixture must reach an existing nbmake scope before mutating it'
    )
    pixi_path.write_text(
        pixi_text.replace('docs/dev/verification/', 'docs/user/tutorials/', 1),
        encoding='utf-8',
    )
    result = _run(executed)
    assert result.returncode != 0, (
        ' local red (c) must reject a listed notebook that an nbmake task executes'
    )
