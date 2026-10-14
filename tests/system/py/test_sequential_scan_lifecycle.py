"""A sequential scan finishes once and its normal app stays stopped."""

import copy
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.fixtures.fast_ci.processes import stop_observer_tree
from tests.fixtures.scan_lifecycle.oracle import assert_settled, signals
from tests.fixtures.scan_lifecycle.prepare import prepare

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = json.loads((ROOT / 'tests/fixtures/scan_lifecycle/interface.json').read_text())


@pytest.mark.parametrize('count', [2, 3])
def test_sequential_scan_ends_and_stays_stopped_in_the_normal_app(tmp_path, count):
    project = tmp_path / 'project'
    names = prepare(project, count)
    binary = Path(os.environ.get('EDI_APP_BINARY', ROOT / 'build/app/app/edi_app')).resolve()
    assert binary.is_file(), 'The lifecycle gate must reuse the app already delivered by app CI'
    env = {
        **os.environ,
        CONTRACT['observer_switch']: '1',
        'EDI_SCAN_LIFECYCLE_QUIET_MS': str(CONTRACT['quiet_ms']),
        'QT_QPA_PLATFORM': 'cocoa' if sys.platform == 'darwin' else 'offscreen',
        'QT_QUICK_BACKEND': 'software',
        'XDG_CONFIG_HOME': str(tmp_path / 'settings'),
    }
    started = time.monotonic()
    process = subprocess.Popen(
        [
            'pixi',
            'run',
            '--as-is',
            '-e',
            'app',
            str(binary),
            *CONTRACT['observer_arguments'],
            str(project),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=CONTRACT['timeout_seconds'])
    except subprocess.TimeoutExpired:
        stop_observer_tree(process)
        pytest.fail(
            'The sequential scan must finish and expose a quiet stopped state before the deadline'
        )
    assert process.returncode == 0, (
        'The opted-in normal app must complete its real sequential scan lifecycle observation: '
        + stderr
    )
    documents = [json.loads(line) for line in stdout.splitlines() if line.startswith('{')]
    assert len(documents) == 1, 'The actual app must publish exactly one complete lifecycle trace'
    assert time.monotonic() - started >= CONTRACT['quiet_ms'] / 1000, (
        'The actual observer process must remain alive for the claimed quiet interval'
    )
    assert_settled(documents[0], names, project, CONTRACT['quiet_ms'])
    result = project / 'analysis/results.csv'
    assert result.is_file(), 'Successful app completion must leave actual scan result rows on disk'
    with result.open() as stream:
        rows = list(csv.DictReader(stream))
    assert [Path(row['file_path']).name for row in rows] == names, (
        'Every input file must have one actual fit-result row, without replayed or omitted files'
    )


def valid_trace():
    state = {
        'running': False,
        'scanning': False,
        'scanProcessed': 0,
        'scanFitted': 0,
        'scanTotal': 3,
        'scanProgress': 0,
        'elapsed': '0.0',
        'iterations': '',
        'status': '',
        'outcome': '',
        'scanText': '',
        'eta': '',
    }
    events = [dict(state, kind='sample', ms=0)]
    events.append(
        dict(state, kind='signal', signal='runningChanged', ms=1, running=True, scanning=True)
    )
    done = dict(
        state,
        running=False,
        scanning=False,
        scanProcessed=3,
        scanFitted=3,
        scanProgress=1,
        elapsed='0.2',
        status='Done',
        outcome='maxIterations',
    )
    events.extend((
        dict(
            done, running=True, scanning=True, kind='signal', signal='scanProcessedChanged', ms=10
        ),
        dict(done, kind='signal', signal='scanFinished', ms=11),
    ))
    events.extend([dict(done, kind='sample', ms=12), dict(done, kind='sample', ms=1211)])
    return {
        'project': '/project',
        'mode': 'sequential',
        'files': ['a', 'b', 'c'],
        'signals_watched': signals(),
        'events': events,
    }


def test_terminal_oracle_accepts_a_completed_and_quiet_scan():
    assert_settled(valid_trace(), ['a', 'b', 'c'], '/project', CONTRACT['quiet_ms'])


@pytest.mark.parametrize(
    'escape',
    [
        'idle',
        'no-end',
        'running',
        'over-count',
        'late-signal',
        'elapsed',
        'short-window',
        'nonfinite',
        'missing-signal',
    ],
)
def test_terminal_oracle_rejects_each_observed_lifecycle_escape(escape):
    observation = copy.deepcopy(valid_trace())
    events = observation['events']
    if escape == 'idle':
        for event in events:
            event['running'] = False
    elif escape == 'no-end':
        events[3]['signal'] = 'statusChanged'
    elif escape == 'running':
        events[3]['running'] = True
    elif escape == 'over-count':
        events[-1]['scanProcessed'] = 4
    elif escape == 'late-signal':
        events[-1].update(kind='signal', signal='elapsedChanged')
    elif escape == 'elapsed':
        events[-1]['elapsed'] = '1.2'
    elif escape == 'short-window':
        events[-1]['ms'] = 1111
    elif escape == 'nonfinite':
        events[-1]['scanProgress'] = float('nan')
    else:
        observation['signals_watched'].remove('elapsedChanged')
    with pytest.raises(AssertionError):
        assert_settled(observation, ['a', 'b', 'c'], '/project', CONTRACT['quiet_ms'])
