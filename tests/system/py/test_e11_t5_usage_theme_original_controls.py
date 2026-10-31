"""Actual usage-button theme dependency, with no canonical/formatter substitution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import test_e11_t5_dev_native_integration as base
import test_e11_t5_usage_account_original_controls as canonical

main_actor = base.main_actor
HERE = Path(__file__).resolve().parent


def _command(actor, action):
    source = (HERE / 'e11_t5_usage_theme_observer.js').read_text()
    definition = (
        (HERE / 'e11_t5_usage_theme_capture.qml').read_text() if action == 'install' else ''
    )
    source = source.replace('ACTION', json.dumps(action))
    source = source.replace('DEFINITION', json.dumps(definition))
    envelope = actor.command('evaluate', expression='JSON.stringify(' + source + ')')
    with (actor.folder / 'theme-observations.jsonl').open('a') as output:
        output.write(
            json.dumps({
                'action': action,
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
def theme_actor(main_actor):
    phase = canonical._phase()
    actor = main_actor([[]])
    state = {'installed': False}
    yield actor, state, phase
    # Separate pytest teardown preserves a prior body exception and restores actual theme.
    assert actor.process.poll() is None and not getattr(actor, '_stream_unusable', None)
    value = _command(actor, 'cleanup')
    if state['installed']:
        assert value == {'found': 1, 'restored': True}
    else:
        assert value['found'] in {0, 1}
        if value['found'] == 1:
            assert value['restored']
    actor.until(lambda _row: _command(actor, 'absent')['remaining'] == 0)


def _snapshot(actor, action='snapshot'):
    value = _command(actor, action)
    assert isinstance(value['problem'], str) and not value['problem'], value
    assert all(
        value[key]
        for key in (
            'owner',
            'same_owner',
            'same_button',
            'same_label',
            'same_colors',
            'actual_window',
            'visible',
            'enabled',
        )
    )
    assert not value['hovered'] and not value['down'] and not value['visual_focus']
    assert value['remaining'] == 63 and value['text'] == '37% used'
    assert all(
        actor.last['ui'][key]
        for key in (
            'singleton_identity',
            'engine_parent',
            'cpp_ownership',
        )
    )
    return value


def _settled(actor, dark):
    def current(_row):
        value = _snapshot(actor)
        return value['dark'] is dark and value['matches_foreground']

    actor.until(current)
    value = _snapshot(actor)
    assert value['dark'] is dark and value['matches_foreground']
    assert value['actual'] == value['expected']
    return value


def test_original_usage_same_label_observes_actual_light_dark_light_theme(theme_actor):
    actor, state, phase = theme_actor
    base._session_configure(
        actor,
        session_fixture={'threads': [], 'page_size': 12},
        fixture_usage_default_response={'result': base._original_usage_window(37)},
    )
    base.wait_positive_tab(actor, 'appBar.tab.project')
    actor.command('click', name='appBar.tab.project')
    actor.connect()
    canonical._usage_ready(actor)
    # One ordinary workspace click keeps the physical pointer/focus away from usage.
    actor.command('click', name='appBar.tab.project')
    metadata_before = {
        method: len(base._session_wire(actor, method))
        for method in (
            'account/read',
            'account/rateLimits/read',
        )
    }
    initial = _snapshot(actor, 'install')
    state['installed'] = True
    canonical._retain(actor, 'actual-theme-initial', initial)
    _snapshot(actor, 'light')
    light = _settled(actor, False)
    canonical._retain(actor, 'actual-theme-light', light)
    _snapshot(actor, 'dark')
    dark = _settled(actor, True)
    canonical._retain(actor, 'actual-theme-dark', dark)
    assert dark['actual'] != light['actual'] and dark['changes'] > light['changes']
    _snapshot(actor, 'light')
    again = _settled(actor, False)
    canonical._retain(actor, 'actual-theme-light-again', again)
    assert again['actual'] == light['actual'] and again['changes'] > dark['changes']
    wire = base._session_wire(actor)
    canonical._retain(actor, 'actual-theme-wire', wire)
    assert not any(row.get('method') in {'turn/start', 'account/logout'} for row in wire)
    assert {method: len(base._session_wire(actor, method)) for method in metadata_before} == (
        metadata_before
    )
    assert canonical._phase() == phase
