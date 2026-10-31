"""Real original usage Timer: actual-signal witness and a full closed cold interval."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
import test_e11_t5_dev_native_integration as base
import test_e11_t5_usage_account_original_controls as canonical

main_actor = base.main_actor
HERE = Path(__file__).resolve().parent
INTERVAL_MS = 60_000
# New gate budget: original60000ms + existing MainActor.until normal10s margin.
# No old command/action deadline or production clock/Timer property changes.
TIMER_GATE_SECONDS = INTERVAL_MS / 1000 + 10


def _command(actor, action):
    source = (HERE / 'e11_t5_usage_clock_observer.js').read_text()
    definition = (
        (HERE / 'e11_t5_usage_clock_capture.qml').read_text() if action == 'install' else ''
    )
    source = source.replace('ACTION', json.dumps(action))
    source = source.replace('DEFINITION', json.dumps(definition))
    envelope = actor.command('evaluate', expression='JSON.stringify(' + source + ')')
    with (actor.folder / 'clock-observations.jsonl').open('a') as output:
        output.write(
            json.dumps({
                'action': action,
                'monotonic': time.monotonic(),
                'reply': envelope['reply'],
                'owner': {
                    key: envelope['ui'].get(key)
                    for key in (
                        'singleton_identity',
                        'engine_parent',
                        'cpp_ownership',
                    )
                },
            })
            + '\n'
        )
    return json.loads(envelope['reply']['value'])


@pytest.fixture
def clock_actor(main_actor):
    phase = canonical._phase()  # Mandatory source/119/SDK116 guard BEFORE a host is created.
    started_ms = time.time_ns() // 1_000_000
    actor = main_actor([[]])
    state = {'installed': False}
    yield actor, started_ms, state, phase
    # Pytest teardown is separate: it cannot replace a semantic body failure.
    assert actor.process.poll() is None and not getattr(actor, '_stream_unusable', None)
    cleanup = _command(actor, 'cleanup')
    if state['installed']:
        assert cleanup == {'found': 1, 'destroyed': True}
    else:
        assert cleanup['found'] in {0, 1}  # Partial setup still cleans any actual owned capture.
    actor.until(lambda _row: _command(actor, 'absent')['remaining'] == 0)


def _snapshot(actor, action='snapshot'):
    value = _command(actor, action)
    assert isinstance(value['problem'], str) and not value['problem'], value
    assert value['owner'] and value['same_original'] and value['imported_info']
    assert value['interval'] == INTERVAL_MS and value['repeat'] is True
    assert value['triggered_on_start'] is False
    assert value['running'] == (value['visible'] and value['connected'])
    assert value['count'] == len(value['events'])
    assert all(
        actor.last['ui'][key]
        for key in (
            'singleton_identity',
            'engine_parent',
            'cpp_ownership',
        )
    )
    return value


def _begin(clock_actor):
    actor, started_ms, state, phase = clock_actor
    value = _snapshot(actor, 'install')
    state['installed'] = True
    canonical._retain(actor, 'clock-created-original', value)
    assert not value['visible'] and not value['opened'] and not value['connected']
    assert value['count'] == 0 and not value['running']
    assert started_ms <= value['clock'] <= value['wall_after']
    base._session_configure(
        actor,
        session_fixture={'threads': [], 'page_size': 12},
        fixture_usage_default_response={'result': base._original_usage_window(37)},
    )
    base.wait_positive_tab(actor, 'appBar.tab.project')
    actor.command('click', name='appBar.tab.project')
    actor.connect()
    canonical._usage_ready(actor)
    connected = _snapshot(actor)
    canonical._retain(actor, 'clock-connected-closed', connected)
    assert connected['connected'] and not connected['visible'] and not connected['running']
    assert connected['clock'] == value['clock'] and connected['count'] == 0
    return actor, phase, connected


def _no_model_work(actor, usage_requests):
    wire = base._session_wire(actor)
    canonical._retain(actor, 'clock-final-wire', wire)
    assert len(base._session_wire(actor, 'account/rateLimits/read')) == usage_requests
    assert not any(row.get('method') in {'turn/start', 'account/logout'} for row in wire)


def test_original_usage_clock_open_and_actual_sixty_second_trigger(clock_actor):
    actor, phase, before = _begin(clock_actor)
    canonical._open_usage(actor)
    opened = _snapshot(actor)
    canonical._retain(actor, 'clock-opened-original', opened)
    assert opened['visible'] and opened['opened'] and opened['running']
    assert opened['count'] == 0
    assert before['wall_before'] <= opened['clock'] <= opened['wall_after']
    usage_requests = len(base._session_wire(actor, 'account/rateLimits/read'))
    started = time.monotonic()

    def genuine_tick(_row):
        return _snapshot(actor)['count'] >= 1

    actor.until(genuine_tick, seconds=TIMER_GATE_SECONDS)
    after = _snapshot(actor)
    canonical._retain(
        actor,
        'clock-real-trigger-original',
        {
            'elapsed_since_opened_observation': time.monotonic() - started,
            'facts': after,
        },
    )
    assert after['count'] == 1
    assert after['visible'] and after['opened'] and after['connected']
    assert all(
        event['owner'] and event['visible'] and event['connected'] for event in after['events']
    )
    assert opened['clock'] < after['clock'] <= after['wall_after']
    _no_model_work(actor, usage_requests)
    assert canonical._phase() == phase


def test_original_usage_clock_closed_connected_is_cold_for_full_interval(clock_actor):
    actor, phase, before = _begin(clock_actor)
    usage_requests = len(base._session_wire(actor, 'account/rateLimits/read'))
    started = time.monotonic()

    def complete_cold_interval(_row):
        value = _snapshot(actor)
        assert value['connected'] and not value['visible'] and not value['running']
        assert value['count'] == 0 and value['events'] == []
        assert value['clock'] == before['clock']
        return time.monotonic() - started >= INTERVAL_MS / 1000

    actor.until(complete_cold_interval, seconds=TIMER_GATE_SECONDS)
    canonical._retain(
        actor,
        'clock-full-closed-interval-original',
        {
            'elapsed': time.monotonic() - started,
            'facts': _snapshot(actor),
        },
    )
    _no_model_work(actor, usage_requests)
    assert canonical._phase() == phase
