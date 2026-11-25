#!/usr/bin/env python3
"""The GUI layout rules against every state the runs covered.

ADR-0103 decisions 3, 4, 6 and 7; ADR-0102 R1-R4.

usage: gui_contract_report.py <run dir>...   (each with a summary.tsv from the demo's layout check)
Exits 1 when a rule failed in any state or was checked in none: a rule nobody checked is not a
pass.
A state is a frame's project, width mode and window; a finding line is "<ID>:<kind>", a
measurement "<ID>:checked".
W1/W2 are judged here: within one state every page's sidebar width must be equal.
Prints one row per assertion: states checked, states failed, worst finding (or a measured value),
and writes
contract-matrix.csv (assertion x state) beside the first run.
"""

import collections
import csv
import pathlib
import re
import sys

IDS = [
    'W1',
    'W2',
    'W3',
    'W4',
    'W5',
    'W6',
    'W7',
    'W8',
    'W9',
    'T1',
    'T2',
    'T3',
    'T4',
    'T5',
    'T6',
    'T7',
    'T8',
    'T9',
    'T10',
    'T11',
    'T12',
    'F1',
    'F2',
    'F3',
    'F4',
    'I1',
    'C1',
    'C2',
    'C3',
    'D1',
    'R1',
    'R2',
    'R3',
    'R4',
    'N1',
    'N2',
    'N3',
    'N4',
    'N5',
    'N6',
    'N7',
    'N8',
    'N9',
    'N10',
]


def text_of(path: str) -> str:
    return pathlib.Path(path).read_text(encoding='utf-8', errors='replace')


def state_of(frame: str, run: str) -> str:
    m = re.match(r'e58-sweep-\d+-(.+?)-(?:(auto|full|bounds|values|compact)-)?(\d+x\d+)', frame)
    if m:
        return f'{m.group(1)}/{m.group(2) or "-"}/{m.group(3)}'
    m = re.match(r'(e58-[a-z0-9]+)', frame)
    return f'{pathlib.Path(run).name}/{m.group(1) if m else frame}'


checked = collections.defaultdict(set)  # id -> states
failed = collections.defaultdict(dict)  # id -> state -> first finding
measured = collections.defaultdict(list)  # id -> measurement texts
widths = collections.defaultdict(dict)  # state -> page frame -> width
popup_widths = collections.defaultdict(
    set
)  # popup editor -> its row widths seen (before and after a fit)

for run in sys.argv[1:]:
    path = str(pathlib.Path(run) / 'summary.tsv')
    if not pathlib.Path(path).exists():
        continue
    for line in text_of(path).splitlines(keepends=True):
        parts = line.rstrip('\n').split('\t')
        if len(parts) < 3:
            continue
        frame, kind = parts[0], parts[1]
        rest = '\t'.join(parts[2:])
        state = state_of(frame, run)
        if kind == 'F3:width':
            popup_widths[parts[2]].add(float(parts[3]))
            continue
        if kind == 'W:width':
            mode = parts[2]
            m = re.search(r'(side|below) ([\d.]+) window (\d+x\d+)', rest)
            if m:
                # A state is one window: a scenario that resizes is several states.
                widths[f'{state}@{m.group(3)}'][frame] = (mode, m.group(1), float(m.group(2)))
            continue
        if ':' not in kind:
            continue
        rule, what = kind.split(':', 1)
        if rule not in IDS:
            continue
        checked[rule].add(state)
        if what == 'checked':
            measured[rule].append(rest)
        else:
            failed[rule].setdefault(state, f'{frame}: {rest}'[:220])

for name, seen in popup_widths.items():
    checked['F3'].add(f'popup/{name}')
    measured['F3'].append(f'{name}: popup width {sorted(seen)} before/after a fit')
    if len(seen) > 1:
        failed['F3'][f'popup/{name}'] = measured['F3'][-1]

# W3 and W4 from the Auto width series: the switch point, the growth, the order columns join,
# the stop.
series = []
for run in sys.argv[1:]:
    path = str(pathlib.Path(run) / 'summary.tsv')
    if not pathlib.Path(path).exists():
        continue
    for line in text_of(path).splitlines(keepends=True):
        parts = line.rstrip('\n').split('\t')
        if len(parts) >= 4 and parts[1] == 'W:series':
            m = re.match(
                r'(side|below) ([\d.]+) columns ([\d,]*) spare ([-\d.]+) gap ([\d.]+)', parts[3]
            )
            if m and m.group(1) == 'side':
                series.append((
                    int(parts[2]),
                    float(m.group(2)),
                    set(m.group(3).split(',')) - {''},
                    float(m.group(4)),
                    float(m.group(5)),
                ))
if series:
    series.sort()
    state = 'series/auto/cosio_2k'
    for rule in ('W3', 'W4'):
        checked[rule].add(state)
    window, width, columns, _, _ = series[0]
    measured['W3'].append(
        f'switch at {window} px: sidebar {width:g} px ({100 * width / window:.1f} %), '
        f'columns {sorted(columns)}'
    )
    if width > window / 2 + 0.5 or not {'1', '3', '5'} <= columns:
        failed['W3'][state] = measured['W3'][-1]
    shrink = [
        (a[0], a[1], b[1]) for a, b in zip(series, series[1:], strict=False) if b[1] < a[1] - 0.5
    ]
    joins = {
        c: next((w for w, _, cols, _, _ in series if c in cols), None)
        for c in ('2', '7', '8', '6')
    }
    order = [joins[c] for c in ('2', '7', '8', '6')]
    full = [(w, sw, sp, g) for w, sw, cols, sp, g in series if {'2', '6', '7', '8'} <= cols]
    growth = (full[-1][1] - full[0][1]) if full else 0
    gap = full[0][3] if full else 0
    measured['W4'].append(
        f'Start/Min/Max/Change join at {order} px windows; '
        f'all shown at {full[0][1] if full else "-"} px, '
        f'stops at {full[-1][1] if full else "-"} px (+{growth:g}, at most {gap:g})'
    )
    if shrink or None in order or order != sorted(order) or growth > gap + 0.5:
        failed['W4'][state] = f'shrinks {shrink[:3]}; ' + measured['W4'][-1]

# R1 from the gate runs' stall probe: the pauses over 100 ms, the unfold's too (R2 is the demo's
# own frame check). Reported, not judged, until the first-show work brings them under 100 ms
# (ADR-0102, "Where R1 stands"), so the row lists every scenario.
pauses = []
for run in sys.argv[1:]:
    log = str(pathlib.Path(run) / 'app.log')
    if not pathlib.Path(run).name.startswith('cmp-') or not pathlib.Path(log).exists():
        continue
    gaps = [int(g) for g in re.findall(r'stall-probe: gap (\d+) ms', text_of(log))]
    state = pathlib.Path(run).name
    checked['R1'].add(state)
    over = len([g for g in gaps if g > 100])
    pauses.append(f'{state}: longest {max(gaps, default=0)} ms, {over} over 100 ms')
if pauses:
    measured['R1'].append('; '.join(pauses))

# W1 (Auto) and W2 (Full): one width per state across its pages, side layout only.
for state, frames in widths.items():
    side = [(f, w) for f, (mode, where, w) in frames.items() if where == 'side']
    if not side:
        continue
    mode = next(iter(frames.values()))[0]
    rule = 'W1' if mode == 'auto' else 'W2' if mode == 'full' else None
    if rule is None:
        continue
    checked[rule].add(state)
    values = sorted({w for _, w in side})
    measured[rule].append(f'{state}: {", ".join(f"{v:g}" for v in values)} px')
    if len(values) > 1:
        failed[rule].setdefault(state, f'{state}: widths {values}')

# The never-list items that restate a rule take its result: N5 = T12, N6 = W1 + W2 + T6,
# N7 = T7, N8 = T6.
for never, rules in (
    ('N5', ('T12',)),
    ('N6', ('W1', 'W2', 'T6')),
    ('N7', ('T7',)),
    ('N8', ('T6',)),
):
    for rule in rules:
        checked[never] |= checked[rule]
        for state, text in failed[rule].items():
            failed[never].setdefault(state, f'via {rule}: {text}')
        measured[never] += [f'via {rule}: {m}' for m in measured[rule][-1:]]

print('| Assertion | States checked | States failed | Worst finding or measured value |')
print('|---|---|---|---|')
for rule in IDS:
    n, bad = len(checked[rule]), failed[rule]
    if n == 0:
        print(f'| {rule} | 0 | - | not checked in these runs |')
        continue
    example = (
        next(iter(bad.values()))
        if bad
        else (measured[rule][-1] if measured[rule] else 'no finding')
    )
    print(f'| {rule} | {n} | {len(bad)} | {example.replace("|", "/")} |')

states = sorted(set().union(*checked.values())) if checked else []
out = str(pathlib.Path(sys.argv[1]) / 'contract-matrix.csv')
with pathlib.Path(out).open('w', newline='', encoding='utf-8') as handle:
    writer = csv.writer(handle)
    writer.writerow(['assertion'] + states)
    for rule in IDS:
        writer.writerow(
            [rule]
            + [
                ('FAIL' if s in failed[rule] else 'pass') if s in checked[rule] else ''
                for s in states
            ]
        )
print(f'\nmatrix: {out} ({len(states)} states)')
unchecked = [rule for rule in IDS if not checked[rule]]
broken = [rule for rule in IDS if failed[rule]]
if unchecked:
    print('not checked: ' + ' '.join(unchecked))
if broken:
    print('failed: ' + ' '.join(broken))
sys.exit(1 if unchecked or broken else 0)
