"""Real consent roles and viewport reachability; no fabricated VM or full-Main substitute."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'consent_native_fixture', ROOT / 'tests/system/py/test_e11_t5_assistant_native.py'
)
native = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(native)
signer = native.signer
LONG_NAME = 'Å long independent project name ' * 120


class Consent(native.Native):
    def __init__(self, binary):
        self.process = native.subprocess.Popen(
            [
                str(binary),
                str(ROOT / 'tests/integration/py/assistant_consent_probe/ConsentHarness.qml'),
            ],
            stdin=native.subprocess.PIPE,
            stdout=native.subprocess.PIPE,
            stderr=native.subprocess.PIPE,
            text=True,
            encoding='utf-8',
        )
        self.reply_timeout = 5.0
        self.last = None
        self.handled = set()
        self.jwt = None
        self.jwks = None
        self.scope = native.SCOPES
        self.catalog = {
            'models': [
                {
                    'slug': 'gpt-6.1-sol',
                    'display_name': 'Independent fixture',
                    'visibility': 'list',
                }
            ]
        }

    def ready(self):
        return self.last['vm']['connected']


@pytest.fixture
def consent(monkeypatch):
    binary = Path(
        os.environ.get(
            'EDI_ASSISTANT_CONSENT_PROBE',
            ROOT / 'build/assistant-consent-tests/assistant_consent_probe',
        )
    )
    assert binary.is_file(), (
        'I12/Q2/Q3: the real Session/VM/production-QML consent consumer must be built '
        'from a coherent current module/header/Qt cohort before behavior is measured'
    )
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    monkeypatch.setenv('QT_QUICK_BACKEND', 'software')
    actor = Consent(binary)
    try:
        actor.command('inspect')
        yield actor
    finally:
        actor.close()


def opened(actor):
    actor.command('open_dialog')
    for _ in range(12):
        if actor.last['ui']['dialog'].get('opened'):
            break
        actor.command('inspect')
    assert actor.last['ui']['dialog']['opened'], (
        'I12/Q2/Q3: real popup transition completes before action or viewport claims'
    )


def closed(actor):
    for _ in range(12):
        if not actor.last['ui']['dialog']['visible']:
            break
        actor.command('inspect')
    assert not actor.last['ui']['dialog']['visible'], (
        'I12/Q2/Q3: actual pointer action dismisses the real dialog after its transition'
    )


def actions(actor):
    ui = actor.last['ui']
    assert all(
        ui[key]['visible'] and ui[key]['enabled'] and ui[key]['whole_reachable']
        for key in ('accept', 'cancel')
    ), (
        'I12/Q3: actual accept and Cancel controls remain wholly reachable inside '
        'the real window and clipping ancestors'
    )


def truthful_role(actor, *, connected):
    expected = 'Approve context' if connected else 'Connect ChatGPT'
    ui = actor.last['ui']
    assert actor.last['vm']['connected'] == connected and ui['accept']['text'] == expected, (
        'I12/Q2: an already open dialog names the current real connected-role action'
    )
    assert ui['dialog']['title'] == (
        'Approve outgoing project context' if connected else 'Connect ChatGPT'
    ), 'I12/Q2: the open dialog title names the same live role as its actual action'
    assert ui['accept']['accessible_name'] == expected, (
        'I12/Q2: the actual standard action accessible name agrees with its current role'
    )
    actions(actor)


def signed_out(actor):
    actor.command('sign_out')
    actor.automatic()
    for index, request in enumerate(actor.last['requests']):
        if index not in actor.handled and request['url'] == native.AUTH + '/independent-revoke':
            actor.respond(index, None)
            actor.handled.add(index)
    actor.automatic()
    assert not actor.ready(), 'I12/Q2: actual synthetic revocation retires the ready connection'


def test_open_dialog_updates_to_approval_and_actual_accept_approves_current_context(
    consent, signer
):
    opened(consent)
    truthful_role(consent, connected=False)
    consent.authenticate(signer)
    assert consent.ready() and consent.last['ui']['dialog']['opened'], (
        'I12/Q2: genuine verified connection becomes ready while the same dialog stays open'
    )
    created = consent.command('create_project', name='Independent new consent scope')
    assert created['reply']['created'] and consent.last['vm']['consent_required'], (
        'I3/Q2: a real newly attached project requires fresh consent before actual approval'
    )
    truthful_role(consent, connected=True)
    context = consent.last['vm']['context']
    browsers = len(consent.last['browsers'])
    consent.command('click_accept')
    closed(consent)
    assert (
        len(consent.last['browsers']) == browsers and not consent.last['vm']['consent_required']
    ), 'I12/Q2: actual ready-role accept approves context instead of starting browser sign-in'
    assert consent.last['vm']['context'] == context, (
        'I3/Q2: changing the action role never rewrites the exact outgoing project disclosure'
    )


def test_open_dialog_updates_to_sign_in_and_actual_accept_starts_only_that_flow(consent, signer):
    consent.authenticate(signer)
    assert consent.ready(), (
        'I12/Q2: the ready-role control uses a genuinely verified offline account'
    )
    opened(consent)
    truthful_role(consent, connected=True)
    signed_out(consent)
    assert consent.last['ui']['dialog']['opened'], (
        'I12/Q2: actual connection retirement does not substitute a reopened dialog control'
    )
    truthful_role(consent, connected=False)
    browsers = len(consent.last['browsers'])
    consent.command('click_accept')
    closed(consent)
    consent.automatic()
    assert len(consent.last['browsers']) == browsers + 1 and not consent.ready(), (
        'I12/Q2: actual disconnected-role accept opens one genuine canonical sign-in '
        'flow without pretending the offline account is already ready'
    )


def test_actual_cancel_dismisses_without_approving_or_starting_a_connection(consent):
    opened(consent)
    actions(consent)
    before = (len(consent.last['requests']), len(consent.last['browsers']))
    context = consent.last['vm']['context']
    consent.command('click_cancel')
    closed(consent)
    assert (len(consent.last['requests']), len(consent.last['browsers'])) == before, (
        'I12/Q2: clicking the actual Cancel action starts no provider/browser operation'
    )
    assert not consent.ready() and consent.last['vm']['context'] == context, (
        'I3/Q2: Cancel preserves real connection state and full project disclosure'
    )


def test_actual_accept_while_busy_preserves_the_current_admitted_turn(consent, signer):
    consent.authenticate(signer)
    consent.command('send_text', text='Independent pending consent-control request')
    assert consent.last['vm']['can_cancel'], (
        'I12/Q2: busy refusal is measured only after the real VM admits a cancellable turn'
    )
    opened(consent)
    actions(consent)
    before = (len(consent.last['requests']), len(consent.last['browsers']))
    state = consent.last['vm']['state']
    consent.command('click_accept')
    closed(consent)
    assert (len(consent.last['requests']), len(consent.last['browsers'])) == before, (
        'I12/Q2: busy accept cannot launch an additional physical provider/browser operation'
    )
    assert consent.last['vm']['can_cancel'] and consent.last['vm']['state'] == state, (
        'I12/Q2: busy consent action preserves the original real pending turn and Stop affordance'
    )
    assert consent.last['vm']['last_error'], (
        'I12/Q2: busy accept produces a visible refusal instead of silently approving another role'
    )


@pytest.mark.parametrize(
    ('width', 'height', 'font_pixels', 'details'),
    [
        (360, 280, 18, False),
        (360, 280, 18, True),
        (1280, 768, 27, True),
    ],
    ids=['narrow-summary', 'narrow-details', 'large-font-details'],
)
def test_long_project_disclosure_actions_and_full_exact_context_remain_reachable(
    consent, width, height, font_pixels, details
):
    result = consent.command('create_project', name=LONG_NAME)
    assert result['reply']['created'], (
        'I12/Q3: real public Session project creation must succeed before layout is measured'
    )
    context = consent.last['vm']['context']
    assert json.loads(context)['project']['name'] == LONG_NAME, (
        'I3/Q3: a valid independent long metadata name enters the real complete context'
    )
    consent.command('viewport', width=width, height=height, font_pixels=font_pixels)
    opened(consent)
    ui = consent.last['ui']
    popup = ui['dialog']
    assert (
        popup['x'] >= -1
        and popup['y'] >= -1
        and (
            popup['x'] + popup['width'] <= width + 1 and popup['y'] + popup['height'] <= height + 1
        )
    ), 'I12/Q3: consent popup bounds follow the actual viewport instead of total content height'
    actions(consent)
    assert LONG_NAME in ui['summary']['text'], (
        'I3/Q3: the genuine long project name remains literal complete disclosure content'
    )
    edges = consent.command('summary_edges')['reply']
    assert edges['top_reachable'] and edges['bottom_reachable'], (
        'I12/Q3: actual interactive scrolling can reach both ends of the complete summary '
        'without moving accept/Cancel outside the viewport'
    )
    actions(consent)
    if details:
        consent.command('toggle_details')
        preview = consent.last['ui']['preview']
        assert preview['visible'] and preview['read_only'] and preview['select_by_mouse'], (
            'I3/Q3: exact technical context is visible, read-only and selectable '
            'in the real control'
        )
        assert preview['text'] == context, (
            'I3/Q3: viewport fitting never truncates, replaces or reserializes outgoing context'
        )
        selected = consent.command('select_preview')['reply']
        assert selected['reachable'] and selected['selected_before_key'] == context, (
            'I3/Q3: real technical text selection retains every outgoing context byte'
        )
        assert consent.last['ui']['preview']['text'] == context, (
            'I3/Q3: keyboard input cannot edit the read-only exact disclosure'
        )
        actions(consent)
    consent.command('click_cancel')
    closed(consent)
    assert consent.last['vm']['context'] == context and not consent.last['requests'], (
        'I3/Q3: reachable long-context Cancel preserves exact disclosure and sends nothing'
    )
