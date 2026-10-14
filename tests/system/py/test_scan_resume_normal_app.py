"""Continue observes actual suffix work; a completed scan observes no inner fits."""

import os
import sys
import time
import uuid
from pathlib import Path

import pytest

from tests.fixtures.scan_lifecycle.oracle import signals
from tests.fixtures.scan_pair.protocol import App
from tests.fixtures.scan_resume.generate import stage

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('case', ['failed-prefix-tail', 'completed-failed', 'completed-success'])
def test_resume_preserves_carry_forward_and_processed_terminal_state_in_normal_app(tmp_path, case):
    project = tmp_path / 'project'
    vehicle = stage(
        project, completed=case != 'failed-prefix-tail', success=case == 'completed-success'
    )
    binary = Path(os.environ.get('EDI_APP_BINARY', ROOT / 'build/app/app/edi_app')).resolve()
    assert binary.is_file(), 'The resume witness must reuse the actual normal app artifact'
    app = App(
        binary,
        project,
        'resume',
        {
            **os.environ,
            'EDI_TEST_OBSERVERS': '1',
            'QT_QPA_PLATFORM': 'cocoa' if sys.platform == 'darwin' else 'offscreen',
            'QT_QUICK_BACKEND': 'software',
            'XDG_CONFIG_HOME': str(tmp_path / 'settings'),
        },
        tmp_path / 'stderr.log',
        timeout=4.5,
    )
    nonce = uuid.uuid4().hex
    try:
        assert set(app.until('ready')[0]['signals_watched']) == set(signals()), (
            'The actual resume observer must connect every public fit-model signal before Start'
        )
        app.send('start', nonce)
        terminal, ended = app.until('terminal', nonce)
        # Startup and suffix work cannot consume the mandatory post-terminal observation.
        # Retain the same bounded wait; the full live quiet interval is asserted below.
        app.deadline = time.monotonic() + 4.5
        quiet, settled = app.until('quiet_complete', nonce)
        events = app.events
    finally:
        app.close()
    starts = [event for event in events if event['event'] == 'inner_fit_started']
    fits = [event for event in events if event['event'] == 'file_fitted']
    assert terminal['state']['running'] is False and terminal['state']['scanning'] is False, (
        'Continue and completed resume must return to a stopped normal-app state'
    )
    assert settled - ended >= 1200000000, (
        'The actual app must remain live for the full quiet interval'
    )
    assert quiet['state'] == terminal['state'], 'Resume state must remain unchanged after terminal'
    after = events.index(next(e for e in events if e['event'] == 'terminal'))
    assert not any(
        e['event'] in {'inner_fit_started', 'file_fitted', 'fit_signal'}
        for e in events[after + 1 :]
    ), 'A resumed scan must deliver no inner-fit work or fit signal after its terminal boundary'
    assert (project / 'analysis/results.csv').read_bytes().startswith(vehicle[3]), (
        'Continue must retain every existing prefix byte instead of replaying or replacing it'
    )
    if case != 'failed-prefix-tail':
        assert not starts and not fits, 'A completed resume must perform exactly zero inner fits'
        result = terminal['result']
        assert result['success'] is (case == 'completed-success'), (
            'Completed resume must retain the processed tail success bit'
        )
        assert result['iterations'] == 19 and result['reduced_chi_square'] == 7.125, (
            'Completed resume must recover processed tail metrics independently of carry-forward'
        )
        key = vehicle[1][5]
        assert terminal['parameter_values'][key] == pytest.approx(float(vehicle[2][-1][key])), (
            'Completed resume must recover the processed tail model value, even when it failed'
        )
    else:
        assert [e['file'] for e in starts] == [vehicle[0][-1]], (
            'A two-row resume prefix must invoke the actual inner fit exactly once for its suffix'
        )
        assert [e['file'] for e in fits] == [vehicle[0][-1]], (
            'Only the remaining scan file may be fitted'
        )
        key = vehicle[1][5]
        assert float(vehicle[2][0][key]) != float(vehicle[2][1][key]), (
            'The independent successful and failed seed values must remain distinguishable'
        )
        assert starts[0]['start_values'][key] == pytest.approx(float(vehicle[2][0][key])), (
            'The actual inner fit must carry the last successful row and skip the failed tail'
        )
