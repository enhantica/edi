# SPDX-License-Identifier: BSD-3-Clause
"""Report each tool call of a tools/dev/assistant-tools.sh run."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Refusals the run asks for: the call must answer, but not do anything.
EXPECTED = {
    'acquire_inputs',
    ('run_fit', 'a scan is fitted by the user'),
    ('undo_fit', 'refused: no fit'),
    ('save_project', 'the folder keeps changing'),
}


def unshown(row: dict, show: str) -> bool:
    """Whether the call has a step that cannot be shown."""
    spoil = row.get('spoil') or ''
    shown = spoil.startswith('soon-') or spoil == 'folder'
    shown = shown or (
        spoil.startswith('covered') and row['tool'] in {'show_report', 'save_project'}
    )
    return show == 'on' and bool(spoil) and not shown


def refusal_wanted(row: dict) -> bool:
    return row['tool'] in EXPECTED or (row['tool'], row['note']) in EXPECTED


def not_pressed(row: dict, show: str, presses: dict[str, list[str]]) -> list[str]:
    """The controls the call was to show and did not."""
    pressed = presses.get(str(row['call']), [])
    return [
        name
        for name in row.get('shown') or []
        if show == 'on' and not any(press.startswith(name) for press in pressed)
    ]


def log_failures(folder: Path, rows: list[dict], show: str) -> int:
    """The log names each step that was not shown as an error, and no other."""
    wanted = sum(unshown(row, show) for row in rows)
    paths = [folder / 'app.log', *folder.glob('settings/**/*.log')]
    logs = ''.join(path.read_text(errors='replace') for path in paths if path.exists())
    errors = len({line for line in logs.splitlines() if 'a shown step could not be shown' in line})
    failures = 0
    if errors != wanted:
        print(f'FAIL log: {errors} steps reported as not shown, {wanted} expected')
        failures = 1
    for row in rows:
        met = row.get('met')
        if not met or show != 'on':
            continue
        named = [
            line for line in logs.splitlines() if f'without showing: tool {row["tool"]} ' in line
        ]
        if not any(met in line for line in named):
            print(f'FAIL log: no report of {row["tool"]} names {met!r}')
            failures += 1
    return failures


def main() -> int:
    folder, show, code = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
    rows = []
    results = folder / 'results.jsonl'
    if results.exists():
        rows = [json.loads(line) for line in results.read_text().splitlines()]
    presses: dict[str, list[str]] = {}
    notes = folder / 'presses.tsv'
    if notes.exists():
        for line in notes.read_text().splitlines():
            call, kind, what = (line.split('\t') + ['', ''])[:3]
            if kind == 'press':
                presses.setdefault(call, []).append(what)
    failures = 0
    for row in rows:
        # A spoiled step is done without showing it, within a few seconds; any other is shown.
        spoiled = unshown(row, show)
        bad = row['hung'] or not (row['success'] or refusal_wanted(row))
        skipped = bool(row['cue_skipped']) or 'without the visible click' in row['message']
        bad = bad or skipped != spoiled or (spoiled and row['seconds'] > row.get('limit', 15))
        bad = bad or bool(missing := not_pressed(row, show, presses))
        failures += bad
        print(
            'FAIL' if bad else 'ok  ',
            f'{row["call"]:3d} {row["tool"]:20s} {row["seconds"]:6.1f} s',
            row['note'] or '-',
            row['arguments'].get('operation', ''),
            '|',
            row['status'],
            row['cue_skipped'] or ('' if row['success'] else row['message']),
            row['error'],
            f'not shown: {missing}' if missing else '',
            '| ' + ' > '.join(presses[str(row['call'])]) if str(row['call']) in presses else '',
        )
    failures += log_failures(folder, rows, show)
    if (folder / 'peer-error').exists():
        print('FAIL peer:', (folder / 'peer-error').read_text().strip())
        failures += 1
    if code or not rows:
        print('FAIL app: exit code', code)
        failures += 1
    print(f'{len(rows)} calls, Show actions {show}, {failures} failure(s)')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
