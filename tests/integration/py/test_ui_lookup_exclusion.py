"""Keep driver lookup time separate from application work and GUI blocks."""

import json
import operator
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.integration.py.test_gui_watchdog import SCENARIO, STEPS, checker, trace_for
from tests.integration.py.ui_responsiveness_oracle import timing


def lookup_trace(interval=170):
    trace = trace_for(interval, ((20, 100),))
    for row in trace:
        if row['event'] == 'tick':
            row['thread'] = 'gui'
        if row['event'] in {'tool-begin', 'tool-end'}:
            row['thread'] = 'gui'
            row['callback'] = 'DemoDriver::find'
        if 'callback' in row:
            row['callback'] = 'DemoDriver::find'
    return trace


def test_lookup_callback_is_excluded_by_both_judges(tmp_path):
    trace = lookup_trace()
    timing(trace, SCENARIO, STEPS)
    assert checker(tmp_path, trace), 'Driver lookup alone must not count as application latency'


@pytest.mark.parametrize('event', ['action', 'build', 'swap', 'render', 'block-begin'])
def test_lookup_cannot_hide_application_work(tmp_path, event):
    trace = lookup_trace()
    trace.append({'event': event, 't_ms': 50, 'thread': 'gui'})
    trace.sort(key=operator.itemgetter('t_ms'))
    with pytest.raises(AssertionError, match='application and reentrant work'):
        timing(trace, SCENARIO, STEPS)
    assert not checker(tmp_path, trace), 'Lookup exclusion must refuse GUI application work'


def test_lookup_keeps_a_separate_real_block_counted(tmp_path):
    trace = lookup_trace(260)
    trace.extend([
        {'event': 'block-begin', 't_ms': 105, 'thread': 'gui'},
        {'event': 'block-end', 't_ms': 255, 'thread': 'gui'},
    ])
    trace.sort(key=operator.itemgetter('t_ms'))
    with pytest.raises(AssertionError, match='U8 permits no counted gap'):
        timing(trace, SCENARIO, STEPS, control=True)
    assert not checker(tmp_path, trace, control=True), (
        'A witnessed 150 ms app block must fail even beside an excluded lookup'
    )
    path = tmp_path / 'control.jsonl'
    path.write_text(''.join(json.dumps(row) + '\n' for row in trace))
    result = subprocess.run(
        [
            sys.executable,
            'tools/ci/gui_watchdog.py',
            '--trace',
            str(path),
            '--scenario',
            SCENARIO,
            '--control',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert 'the control block was seen' in result.stdout, (
        'A parser refusal cannot substitute for detecting the app block beside lookup'
    )


def test_native_lookup_span_contains_only_lookup():
    source = (Path(__file__).resolve().parents[3] / 'app/src/demo_driver.cpp').read_text()
    body = source.split('QQuickItem* DemoDriver::find(', 1)[1].split(
        'QQuickItem* DemoDriver::locate(', 1
    )[0]
    enclosed = body.split('trace_measurement(true,', 1)[1].split('trace_measurement(false,', 1)[0]
    assert re.fullmatch(
        r'\s*id,\s*QStringLiteral\("DemoDriver::find"\)\);\s*'
        r'QQuickItem\*\s+found\s*=\s*locate\(object_name,\s*must_be_usable\);\s*',
        enclosed,
    ), 'The native measurement span ends immediately after lookup, before click delivery'
