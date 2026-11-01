"""New dedicated-notifier contract on the existing real Main/session/peer owners."""

from __future__ import annotations

import json

import pytest
import test_e11_t5_dev_native_integration as base

main_actor = base.main_actor


def _read_and_retain(actor, label, **setup):
    reply = actor.command('property_notification_read')['reply']
    (actor.folder / (label + '.json')).write_text(
        json.dumps({'setup': setup, 'actual_observation': reply}, ensure_ascii=True, indent=2)
        + '\n',
        encoding='utf-8',
    )
    return reply


def _assert_current_publications(facts):
    assert facts['fired'] and facts['entry']['same_owner_before']
    assert facts['same_owner'] and facts['entry']['same_owner_after']
    for property_fact in facts['properties']:
        assert property_fact['owner_alive']
        assert not property_fact['duplicate'], property_fact
        assert property_fact['last_announced'] == property_fact['current'], property_fact


@pytest.mark.parametrize('action', ['nested', 'delete'])
def test_genuine_restored_draft_notice_retires_after_same_owner_callback(main_actor, action):
    actor = main_actor([[], []])
    base._session_configure(
        actor,
        session_fixture={'threads': [], 'page_size': 12},
        observe_context_continuity=True,
    )
    target, other = base._two_genuine_session_threads(actor)
    restored = 'B actual pending draft retained by its genuine thread.'
    base._type_original_draft(actor, restored)
    base._select_original_pending_draft_view(actor, target)
    base._type_original_draft(actor, 'A actual draft in the other genuine view.')
    actor.command('click', name='assistant.sessions')
    rows = base._session_wait(actor)
    assert other in {row['id'] for row in rows}
    replacement = 'C assigned by the real restored-draft callback.'
    arm = actor.command(
        'property_notification_arm', mode='draft', action=action, replacement=replacement
    )['reply']
    assert arm['armed'], 'New notifier metadata is a required precondition, including baseline'
    before = len(base._session_wire(actor, 'turn/start'))
    clicked = actor.command('session_row_click', thread_id=other)['reply']
    assert clicked['reached'] and clicked['actual_pressed_changes'] > 0
    actor.until(lambda _row: actor.command('property_notification_read')['reply']['fired'])
    facts = _read_and_retain(actor, 'actual-draft-notice-reentry', thread=other, click=clicked)
    assert facts['entry']['thread'] == other
    assert facts['entry']['restored_text'] == restored
    assert facts['entry']['getter_before'] == restored
    assert len(base._session_wire(actor, 'turn/start')) == before, 'View restoration stays unsent'
    if action == 'delete':
        assert not facts['same_owner'] and not facts['entry']['same_owner_after']
        assert all(not item['owner_alive'] for item in facts['properties'])
        assert not actor.last['ui']['alive'], 'The actual owning QQmlEngine was destroyed'
    else:
        _assert_current_publications(facts)
        draft = next(item for item in facts['properties'] if item['name'] == 'sessionDraft')
        assert draft['current'] == replacement
        assert draft['events'].count(replacement) == 1, 'Old restore tail cannot announce C twice'


@pytest.mark.parametrize('action', ['nested', 'delete'])
def test_connected_consent_notice_retires_after_same_owner_approval(main_actor, tmp_path, action):
    actor = main_actor([[]])
    actor.connect()
    assert not actor.last['ui']['context_consent_required']
    armed = actor.command('property_notification_arm', mode='consent', action=action)['reply']
    assert armed['armed'], 'Actual dedicated-notifier metadata is required'
    project = base.copied_estimate_project(tmp_path)
    opened = actor.command('open', path=str(project))
    facts = _read_and_retain(actor, 'actual-consent-notice-reentry', open_reply=opened['reply'])
    assert facts['fired'], 'The actual context-preview legacy event reaches required consent'
    assert facts['entry']['required_before'] and facts['entry']['connected_before']
    assert facts['entry']['same_owner_before']
    if action == 'delete':
        assert not facts['same_owner'] and not facts['entry']['same_owner_after']
        assert all(not item['owner_alive'] for item in facts['properties'])
        assert not opened['ui']['alive'], 'The actual owner dies inside the notification'
    else:
        assert opened['reply']['opened']
        _assert_current_publications(facts)
        consent = next(
            item for item in facts['properties'] if item['name'] == 'contextConsentRequired'
        )
        assert consent['current'] is False
        assert consent['events'].count(False) == 1, 'Nested ordinary approval publishes false once'
        assert not actor.last['ui']['context_consent_required']
    assert not base._session_wire(actor, 'turn/start'), 'Consent observation starts no model work'
