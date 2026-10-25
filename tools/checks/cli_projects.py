#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Execute the CLI projects and compare each against its expected.json.

The projects live under ``docs/user/cli/<id>/`` — a ``project/`` directory ``python -m edi``
fits and an ``expected.json`` of the quantities it must reproduce — and the registry
``docs/user/cli/projects.yml`` declares which of them are in the EXECUTING set. Without a
selection this runs the executing set's CI part: CI and ``pixi run verify`` call it that way, so a
project in it cannot drift unnoticed. A project also marked ``offline: true`` (owner: a slow check
does not go into CI) stays executing but runs only when asked for explicitly —
``--offline`` runs every offline project, ``--project <id>`` any executing one. ``--project``
otherwise narrows the run for diagnosis.

Per project, every unit in its ``expected.json`` runs ``python -m edi fit`` on a disposable copy
(the project tree is never written) with ``--report machine --verbosity full``:

- a top-level ``quantities`` block — the default invocation;
- each ``variants.<name>`` block — the descent ``<name>`` with ``-`` spelled ``_`` (the corpus
  names its variants after the descent they pin), DECLARED as ``_minimizer.descent`` in the
  copy's ``analysis/analysis.edi`` (the CLI carries no minimization condition); an unknown
  descent fails;
- an ``edi`` block — the default invocation (the corpus's per-entry-point overlay).

A quantity is a key of the machine record (``param.<label>.value`` included), or
``results[<x>].<column>`` — the ``analysis/results.csv`` row a scan wrote whose ``diffrn.*`` value
is ``<x>``. Every non-null ``tol_abs``/``tol_rel`` bound must hold; the record must say
``status=done``. Every deviation is reported, never only the first, and any deviation is red.

``--settings <project-dir>`` prints :func:`loaded_settings` as JSON instead: an external shipment
check reads a project's settings through edi's own loader this way, never by scanning text.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CLI_DIR = Path('docs') / 'user' / 'cli'
REGISTRY = CLI_DIR / 'projects.yml'
# <technique>_<sample>[-<instrument>]_<variant>, three kebab-case parts (owner, 2026-09-24).
PROJECT_ID = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*(?:_[a-z0-9]+(?:-[a-z0-9]+)*){2}')
RESULTS_KEY = re.compile(r'results\[(?P<key>[^\]]+)\]\.(?P<column>.+)')
FIT_TIMEOUT_S = 900

# Settings the loaded model does not own as physics: file bookkeeping, free text and data.
_SKIPPED_CATEGORIES = frozenset({'edi', 'metadata', 'data', 'refln'})
_NUMBER = re.compile(r'(?P<value>[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)(?P<esd>\(\d*\))?')


# ----------------------------------------------------------------------
#  Registry
# ----------------------------------------------------------------------


def registry(root: Path) -> list[dict]:
    """The registered projects, fail-closed: ``[{'id': str, 'executing': bool}]``.

    An optional boolean ``offline`` is only meaningful on an executing project.
    """
    path = root / REGISTRY
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('schema') != 1:
        raise ValueError(f'{path}: expected a mapping with schema: 1')
    projects = data.get('projects')
    if not isinstance(projects, list) or not projects:
        raise ValueError(f'{path}: projects must be a non-empty list')
    seen: set[str] = set()
    for row in projects:
        if not isinstance(row, dict) or set(row) - {'id', 'executing', 'offline'}:
            raise ValueError(f'{path}: each project is {{id, executing[, offline]}}, got {row!r}')
        pid = row.get('id')
        if not isinstance(pid, str) or not PROJECT_ID.fullmatch(pid):
            raise ValueError(f'{path}: project id {pid!r} is not <technique>_<sample>_<variant>')
        if not isinstance(row.get('executing'), bool):
            raise TypeError(f'{path}: {pid}: executing must be true or false')
        if 'offline' in row and not isinstance(row['offline'], bool):
            raise TypeError(f'{path}: {pid}: offline must be true or false')
        if row.get('offline') and not row['executing']:
            raise ValueError(f'{path}: {pid}: offline applies only to an executing project')
        if pid in seen:
            raise ValueError(f'{path}: duplicate project id {pid!r}')
        seen.add(pid)
    return projects


def ci_projects(projects: list[dict]) -> list[str]:
    """The ids CI and ``pixi run verify`` execute: executing and not offline."""
    return [row['id'] for row in projects if row['executing'] and not row.get('offline')]


def offline_projects(projects: list[dict]) -> list[str]:
    """The executing ids run only on explicit request (``--offline``) — slow checks."""
    return [row['id'] for row in projects if row['executing'] and row.get('offline')]


# ----------------------------------------------------------------------
#  Loaded settings (the shipment check's token source)
# ----------------------------------------------------------------------


def _tokens(line: str) -> list[str]:
    lexer = shlex.shlex(line, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = '#'
    return list(lexer)


def _parse_edi(text: str) -> list[tuple[str, str, str, str | None]]:
    """``(category, attribute, raw value, loop row id)`` for every item of one .edi file."""
    items: list[tuple[str, str, str, str | None]] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if line.startswith(';'):  # a multi-line text field: skip to its closing ';'
            while index < len(lines) and not lines[index].startswith(';'):
                index += 1
            index += 1
            continue
        tokens = _tokens(line)
        if not tokens or tokens[0].startswith('data_'):
            continue
        if tokens[0] == 'loop_':
            names: list[str] = []
            while index < len(lines) and lines[index].strip().startswith('_'):
                names.append(lines[index].strip())
                index += 1
            values: list[str] = []
            while index < len(lines):
                row = lines[index].strip()
                if not row or row.startswith(('_', 'loop_', 'data_')):
                    break
                values.extend(_tokens(row))
                index += 1
            for start in range(0, len(values) - len(names) + 1, len(names) or 1):
                row_values = values[start : start + len(names)]
                row_id = row_values[0] if row_values else None
                for name, value in zip(names, row_values, strict=True):
                    category, _, attribute = name[1:].partition('.')
                    items.append((category, attribute, value, row_id))
            continue
        if tokens[0].startswith('_') and len(tokens) >= 2:
            category, _, attribute = tokens[0][1:].partition('.')
            items.append((category, attribute, ' '.join(tokens[1:]), None))
    return items


def _settings_of_saved_tree(tree: Path) -> dict[str, dict[str, dict]]:
    settings: dict[str, dict[str, dict]] = {}
    for path in sorted(tree.rglob('*.edi')):
        relative = path.relative_to(tree).as_posix()
        for category, attribute, raw, row_id in _parse_edi(path.read_text(encoding='utf-8')):
            if category in _SKIPPED_CATEGORIES or raw in {'?', '.'} or attribute == 'id':
                continue
            where = f'{relative}:_{category}.{attribute}' + (f'[{row_id}]' if row_id else '')
            number = _NUMBER.fullmatch(raw)
            if number:
                setting = {'value': float(number['value']), 'refined': number['esd'] is not None}
                settings.setdefault(attribute, {})[where] = setting
            elif attribute.endswith('type') or category == 'experiment_type':
                settings.setdefault(raw, {})[where] = {'value': raw}
            elif category == 'minimizer':
                # A declared minimization condition that is a name, not a number
                # (`_minimizer.descent`), is exercised under its item name.
                settings.setdefault(attribute, {})[where] = {'value': raw}
    return settings


def loaded_settings(project_dir: str | Path) -> dict[str, dict[str, dict]]:
    """Every exercise token the LOADED model consumes, with each occurrence's setting.

    The project is loaded through edi's own loader and re-saved, and only that canonical output is
    read — so a word in a comment, in ``PROVENANCE.md``, on the docs page or in any field the
    loader ignores is not a token. A token is a numeric setting's name (``broad_gauss_sigma_0``,
    ``scale``), a type value (``tof-jorgensen``) or a named minimization condition's item name
    (``descent``). Returns
    ``{token: {occurrence: setting}}``: the occurrence names the file, item and loop row, so the
    same parameter in two experiments stays two entries; a numeric setting is
    ``{'value': float, 'refined': bool}``, a type value ``{'value': str}``.
    """
    import edi  # noqa: PLC0415 — the compiled loader, imported only where a project is loaded

    with tempfile.TemporaryDirectory(
        prefix='edi-cli-settings-', dir=os.environ.get('RUNNER_TEMP') or None
    ) as scratch:
        saved = Path(scratch) / 'project'
        # save_as narrates on stdout; --settings prints JSON there, so the narration is dropped.
        with contextlib.redirect_stdout(io.StringIO()):
            edi.Project.load(str(project_dir)).save_as(str(saved))
        return _settings_of_saved_tree(saved)


# ----------------------------------------------------------------------
#  Execution
# ----------------------------------------------------------------------


def _units(expected: dict) -> list[tuple[str, dict[str, str], dict]]:
    """``(label, declared conditions, quantities)`` for every unit an expected.json declares.

    The conditions are ``_minimizer.<item>`` values the unit's project copy declares on top of
    the project's own analysis.edi — a variant's descent; empty for the project as committed.
    """
    import edi  # noqa: PLC0415

    units: list[tuple[str, dict[str, str], dict]] = []
    if 'quantities' in expected:
        units.append(('default', {}, expected['quantities']))
    descents = set(edi._descent_ids())
    for name, block in expected.get('variants', {}).items():
        descent = name.replace('-', '_')
        if descent not in descents:
            raise ValueError(f'variant {name!r} names no registered descent {sorted(descents)}')
        units.append((name, {'descent': descent}, block['quantities']))
    if 'edi' in expected:
        units.append(('edi', {}, expected['edi']['quantities']))
    if not units or not all(quantities for _, _, quantities in units):
        raise ValueError('expected.json declares no quantities to compare')
    return units


def declare_conditions(project: Path, conditions: dict[str, str]) -> None:
    """Declare ``conditions`` as ``_minimizer.<item>`` lines in the project's analysis.edi.

    Each declared item replaces any line already declaring it, so the project states every
    condition exactly once; the rest of the file is kept byte for byte.
    """
    if not conditions:
        return
    analysis = project / 'analysis' / 'analysis.edi'
    lines = analysis.read_text(encoding='utf-8').splitlines() if analysis.exists() else []
    tags = {f'_minimizer.{item}' for item in conditions}
    kept = [line for line in lines if not line.split() or line.split()[0] not in tags]
    declared = [f'_minimizer.{item} {value}' for item, value in conditions.items()]
    analysis.parent.mkdir(parents=True, exist_ok=True)
    analysis.write_text('\n'.join([*kept, '', *declared]) + '\n', encoding='utf-8')


def _results_row(project: Path, key: str) -> dict[str, str]:
    path = project / 'analysis' / 'results.csv'
    with path.open(encoding='utf-8', newline='') as handle:
        rows = list(csv.DictReader(handle))
    target = float(key)
    matches = [
        row
        for row in rows
        if any(
            name.startswith('diffrn.') and _float_or_none(value) == target
            for name, value in row.items()
        )
    ]
    if len(matches) != 1:
        raise KeyError(f'{len(matches)} results.csv rows have a diffrn.* value of {key}')
    return matches[0]


def _float_or_none(value: str | None) -> float | None:
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


def _measured(name: str, record: dict[str, str], project: Path) -> float:
    match = RESULTS_KEY.fullmatch(name)
    if match:
        return float(_results_row(project, match['key'])[match['column']])
    return float(record[name])


def _deviations(name: str, spec: dict, measured: float) -> list[str]:
    # Negate the PASS predicate so a NaN measurement fails every bound (as crysta's runner does).
    delta = abs(measured - spec['value'])
    out = []
    compared = f'{name}: {measured} vs {spec["value"]} (|d| {delta:.3g}'
    if spec.get('tol_abs') is not None and not delta <= spec['tol_abs']:
        out.append(f'{compared} > tol_abs {spec["tol_abs"]})')
    if spec.get('tol_rel') is not None and not delta <= spec['tol_rel'] * abs(spec['value']):
        out.append(f'{compared} > tol_rel {spec["tol_rel"]})')
    if spec.get('tol_abs') is None and spec.get('tol_rel') is None and not math.isfinite(measured):
        out.append(f'{name}: {measured} is not finite')
    return out


def run_project(root: Path, pid: str) -> list[str]:
    """Run every unit of one project; return its deviations (empty ⇒ it agrees)."""
    source = root / CLI_DIR / pid
    expected = json.loads((source / 'expected.json').read_text(encoding='utf-8'))
    deviations: list[str] = []
    for label, conditions, quantities in _units(expected):
        with tempfile.TemporaryDirectory(
            prefix=f'edi-cli-{pid}-', dir=os.environ.get('RUNNER_TEMP') or None
        ) as scratch:
            project = Path(scratch) / 'project'
            shutil.copytree(source / 'project', project, symlinks=True)
            declare_conditions(project, conditions)
            argv = [sys.executable, '-m', 'edi', 'fit', str(project), '--report', 'machine']
            argv += ['--verbosity', 'full']
            result = subprocess.run(
                argv, capture_output=True, text=True, timeout=FIT_TIMEOUT_S, check=False
            )
            if result.returncode != 0:
                deviations.append(f'{label}: rc={result.returncode}: {result.stderr[-400:]}')
                continue
            record = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
            if record.get('status') != 'done':
                deviations.append(f'{label}: status={record.get("status")!r}, expected done')
            for name, spec in quantities.items():
                try:
                    measured = _measured(name, record, project)
                except (KeyError, ValueError, OSError) as exc:
                    deviations.append(f'{label}: {name}: not measured ({exc})')
                    continue
                deviations.extend(f'{label}: {line}' for line in _deviations(name, spec, measured))
    return deviations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--root', type=Path, default=ROOT, help='the edi tree (default: this one)')
    parser.add_argument(
        '--project', action='append', help='run only this registered id (diagnostics)'
    )
    parser.add_argument(
        '--offline',
        action='store_true',
        help='run the offline executing projects (slow; never part of CI or pixi run verify)',
    )
    parser.add_argument('--bank', type=Path, help='write per-project elapsed seconds (TSV) here')
    parser.add_argument(
        '--settings', type=Path, metavar='PROJECT_DIR', help='print loaded_settings() as JSON'
    )
    args = parser.parse_args(argv)
    if args.settings is not None:
        print(json.dumps(loaded_settings(args.settings), indent=1, sort_keys=True))
        return 0

    root = args.root.resolve()
    try:
        projects = registry(root)
    except (OSError, ValueError, TypeError, yaml.YAMLError) as exc:
        print(f'cli-projects: REFUSED — {exc}', file=sys.stderr)
        return 1
    executing = [row['id'] for row in projects if row['executing']]
    selected = offline_projects(projects) if args.offline else ci_projects(projects)
    if args.project:
        unknown = sorted(set(args.project) - set(executing))
        if unknown:
            print(f'cli-projects: REFUSED — not in the executing set: {unknown}', file=sys.stderr)
            return 1
        selected = [pid for pid in executing if pid in args.project]

    failed, timings = [], []
    for pid in selected:
        start = time.monotonic()
        try:
            deviations = run_project(root, pid)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            deviations = [f'unrunnable: {exc}']
        elapsed = time.monotonic() - start
        timings.append((pid, elapsed))
        print(f'{"ok  " if not deviations else "FAIL"} {pid}  {elapsed:.1f} s', flush=True)
        for line in deviations:
            print(f'       {line}', flush=True)
        if deviations:
            failed.append(pid)
    if args.bank is not None:
        rows = ''.join(f'{pid}\t{elapsed:.2f}\n' for pid, elapsed in timings)
        args.bank.write_text('project\tseconds\n' + rows, encoding='utf-8')
    total = sum(elapsed for _, elapsed in timings)
    print(f'cli-projects: {len(selected) - len(failed)}/{len(selected)} agree ({total:.1f} s)')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
