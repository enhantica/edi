"""Exercise clock boundaries, marker straddles and incomplete watchdog runs."""

import copy
import json
import operator
import subprocess
import sys
from pathlib import Path

import pytest

from tests.integration.py.ui_responsiveness_oracle import timing

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = json.loads((ROOT / 'tests/fixtures/ui_responsiveness/contract.json').read_text())
SCENARIO = 'e58-series'
STEPS = CONTRACT['scenarios'][SCENARIO]


def trace_for(interval, markers=()):
    rows = [
        {
            'event': 'clock',
            't_ms': 0,
            'clock': 'monotonic',
            'unit': 'ms',
            'tick_ms': 10,
            'gui_thread': 'gui',
        },
        {'event': 'begin', 't_ms': 0, 'scenario': SCENARIO},
        *[{'event': 'step', 't_ms': i + 1, 'name': step} for i, step in enumerate(STEPS)],
        *[{'event': 'tick', 't_ms': t} for t in (0, interval, interval + 10)],
        {'event': 'complete', 't_ms': interval + 10, 'scenario': SCENARIO},
    ]
    for i, (start, stop) in enumerate(markers):
        rows.extend([
            {'event': 'tool-begin', 't_ms': start, 'id': i},
            {
                'event': 'measurement-enter',
                't_ms': start,
                'id': i,
                'callback': 'QQuickWindow::grabWindow',
                'thread': 'gui',
            },
            {
                'event': 'measurement-leave',
                't_ms': stop,
                'id': i,
                'callback': 'QQuickWindow::grabWindow',
                'thread': 'gui',
            },
            {'event': 'tool-end', 't_ms': stop, 'id': i},
        ])
    return sorted(rows, key=operator.itemgetter('t_ms'))


CASES = [
    ('nominal', 10, (), True),
    ('raw-100-is-90-gap', 100, (), True),
    ('exact-100-gap', 110, (), True),
    ('101-gap', 111, (), False),
    ('fraction-over-boundary', 110.25, (), False),
    ('excluded-grab', 170, ((20, 90),), True),
    ('straddle-keeps-app-block', 170, ((20, 70),), False),
    ('marker-reaches-tick-boundary', 110, ((95, 110),), True),
    ('multiple-tools', 170, ((15, 45), (80, 110)), True),
]


def checker(tmp_path, rows, *, control=False):
    script = ROOT / 'tools/ci/gui_watchdog.py'
    assert script.is_file(), 'Phase-one CI requires the actual machine-readable watchdog checker'
    path = tmp_path / 'trace.jsonl'
    path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
    command = [sys.executable, str(script), '--trace', str(path), '--scenario', SCENARIO]
    if control:
        command.append('--control')
    result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
    assert result.returncode in {0, 1}, (
        'The watchdog must judge its trace rather than fail to start or parse its own CLI: '
        + result.stderr
    )
    assert 'Traceback' not in result.stderr, (
        'Malformed observations require a controlled watchdog refusal'
    )
    return result.returncode == 0


@pytest.mark.parametrize(
    ('name', 'interval', 'markers', 'accepted'), CASES, ids=[row[0] for row in CASES]
)
def test_checker_uses_the_declared_clock_and_exact_marker_intersections(
    tmp_path, name, interval, markers, accepted
):
    assert checker(tmp_path, trace_for(interval, markers)) is accepted, (
        'S5 classifies the fixed interval independently of app output: ' + name
    )


@pytest.mark.parametrize(
    ('name', 'interval', 'markers', 'accepted'), CASES, ids=[row[0] for row in CASES]
)
def test_independent_interval_oracle_boundary_controls(name, interval, markers, accepted):
    assert name, 'Each boundary control must retain its independently named requirement'
    rows = trace_for(interval, markers)
    if accepted:
        timing(rows, SCENARIO, STEPS)
    else:
        with pytest.raises(AssertionError, match='U8 permits no counted gap'):
            timing(rows, SCENARIO, STEPS)


def malformed(name):
    rows = [] if name == 'empty' else trace_for(10)
    if name in {'no-ticks', 'no-complete', 'no-clock', 'no-step'}:
        removed = {
            'no-ticks': 'tick',
            'no-complete': 'complete',
            'no-clock': 'clock',
            'no-step': 'step',
        }[name]
        return [row for row in rows if row['event'] != removed]
    if name == 'wrong-clock':
        rows[0]['clock'] = 'wall'
    elif name == 'wrong-unit':
        rows[0]['unit'] = 'ns'
    elif name == 'duplicate-completion':
        rows.append(copy.deepcopy(rows[-1]))
    elif name == 'wrong-scenario':
        next(row for row in rows if row['event'] == 'complete')['scenario'] = 'e58-pages'
    elif name == 'tick-does-not-cover-end':
        rows = [row for row in rows if not (row['event'] == 'tick' and row['t_ms'] == 20)]
    elif name == 'unterminated-exclusion':
        rows.append({'event': 'tool-begin', 't_ms': 20, 'id': 'lost'})
    elif name == 'unpaired-exclusion':
        rows.append({'event': 'tool-end', 't_ms': 20, 'id': 'lost'})
    elif name == 'nested-exclusion':
        return trace_for(160, ((10, 130), (20, 120)))
    elif name == 'mismatched-exclusion':
        rows = trace_for(160, ((10, 130),))
        next(row for row in rows if row['event'] == 'tool-end')['id'] = 'wrong'
    elif name == 'nonfinite-clock':
        rows[-1]['t_ms'] = float('nan')
    elif name == 'backwards-clock':
        rows[-1]['t_ms'] = -1
    return rows


MALFORMED = [
    'empty',
    'no-ticks',
    'no-complete',
    'no-clock',
    'no-step',
    'wrong-clock',
    'wrong-unit',
    'duplicate-completion',
    'wrong-scenario',
    'tick-does-not-cover-end',
    'unterminated-exclusion',
    'unpaired-exclusion',
    'nested-exclusion',
    'mismatched-exclusion',
    'nonfinite-clock',
    'backwards-clock',
]


@pytest.mark.parametrize('name', MALFORMED)
def test_checker_refuses_incomplete_or_ambiguous_observations(tmp_path, name):
    assert checker(tmp_path, malformed(name)) is False, (
        'A watchdog pass requires complete attributable observations: ' + name
    )


@pytest.mark.parametrize('name', MALFORMED)
def test_independent_oracle_rejects_observation_escapes(name):
    with pytest.raises(AssertionError):
        timing(malformed(name), SCENARIO, STEPS)


def test_checker_sees_a_real_gui_block_instead_of_trusting_control_labels(tmp_path):
    rows = trace_for(170)
    rows.extend([
        {'event': 'block-begin', 't_ms': 5, 'thread': 'gui'},
        {'event': 'block-end', 't_ms': 155, 'thread': 'gui'},
    ])
    rows.sort(key=operator.itemgetter('t_ms'))
    assert checker(tmp_path, rows, control=True) is False, (
        'The 150 ms GUI-thread control must fail the same timing check'
    )


def test_checker_does_not_pass_a_control_with_no_observed_block(tmp_path):
    assert checker(tmp_path, trace_for(10), control=True) is False, (
        'A successful-looking control without an executed block is invalid'
    )
