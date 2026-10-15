"""Real pointer/Enter -> production Composer/dialog -> real consented native send.

Actual component composition, not full-Main visual/platform qualification. Native
sign-in is independently signed offline; no account/network/provider action.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.system.app import test_e11_t5_consent_dialog as prior

native = prior.native
signer = prior.signer
ROOT = prior.ROOT
PROMPT = 'Original unchanged draft for explicit outgoing consent'


class Submit(prior.Consent):
    def __init__(self, binary):
        self.process = native.subprocess.Popen(
            [
                str(binary),
                str(ROOT / 'tests/integration/py/assistant_consent_probe/SubmitHarness.qml'),
                '--submit',
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
        self.jwt = self.jwks = None
        self.scope = native.SCOPES
        self.catalog = {
            'models': [
                {
                    'slug': 'gpt-6.1-sol',
                    'display_name': 'Original offline model',
                    'visibility': 'list',
                }
            ]
        }


@pytest.fixture
def submit(monkeypatch, signer):
    binary = Path(os.environ['EDI_ASSISTANT_CONSENT_PROBE'])
    assert binary.is_file(), 'SEND SETUP: coherent actual Session/native/QML consumer exists'
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    monkeypatch.setenv('QT_QUICK_BACKEND', 'software')
    actor = Submit(binary)
    try:
        actor.command('inspect')
        for _ in range(16):
            if actor.last['ui']['panel']['opened']:
                break
            actor.command('inspect')
        assert actor.last['ui']['panel']['opened'], (
            'SEND SETUP: actual panel finishes enter before real pointer input'
        )
        actor.authenticate(signer)
        assert actor.ready(), (
            'SEND SETUP: genuine independently signed offline connection is ready'
        )
        created = actor.command('create_project', name='Original newly disclosed send scope')
        assert created['reply']['created'] and actor.last['vm']['consent_required'], (
            'SEND: real project attachment requires current outgoing-context consent'
        )
        actor.command('type_draft', text=PROMPT)
        assert actor.last['ui']['draft'] == PROMPT and actor.last['ui']['send']['enabled'], (
            'SEND: genuine actual-editor typing enables the visible real Send control'
        )
        yield actor
    finally:
        actor.close()


def requests(actor):
    return [request for request in actor.last['requests'] if request['url'].endswith('/responses')]


def opened_from_submit(actor, gesture):
    actor.command(gesture)
    for _ in range(12):
        if actor.last['ui']['dialog'].get('opened'):
            break
        actor.command('inspect')
    assert actor.last['ui']['dialog'].get('opened'), (
        'SEND: real pointer/Enter submission opens current disclosure, not only an '
        'invisible VM refusal'
    )
    assert actor.last['ui']['draft'] == PROMPT and not requests(actor), (
        'SEND: opening consent preserves exact typed draft and performs no physical inference'
    )
    assert not any(row.get('kind') == 'user' for row in actor.last['vm']['messages']), (
        'SEND: unapproved prompt has no hidden admitted history row'
    )


@pytest.mark.parametrize('gesture', ['click_send', 'press_enter'])
def test_explicit_real_submit_opens_consent_then_accept_dispatches_same_draft_once(
    submit, gesture
):
    opened_from_submit(submit, gesture)
    prior.actions(submit)
    context = submit.last['vm']['context']
    submit.command('click_accept')
    prior.closed(submit)
    assert len(requests(submit)) == 1 and submit.last['vm']['can_cancel'], (
        'SEND: actual accepted same-context action resumes exactly one cancellable '
        'physical request'
    )
    users = [row for row in submit.last['vm']['messages'] if row.get('kind') == 'user']
    assert len(users) == 1 and users[0]['text'] == PROMPT and not submit.last['ui']['draft'], (
        'SEND: exact admitted visible prompt acknowledges and clears only the same draft once'
    )
    assert submit.last['vm']['context'] == context, (
        'SEND: successful resume preserves the exact actual disclosed skill/project bytes'
    )
    assert PROMPT in native.json.dumps(requests(submit)[0]['body']), (
        'SEND: actual native outgoing request contains the original consented draft'
    )


def test_actual_cancel_keeps_draft_without_admission_or_physical_send(submit):
    opened_from_submit(submit, 'click_send')
    submit.command('click_cancel')
    prior.closed(submit)
    assert submit.last['ui']['draft'] == PROMPT and not requests(submit), (
        'SEND: actual dialog cancellation preserves editable draft and performs no inference'
    )
    assert (
        not any(row.get('kind') == 'user' for row in submit.last['vm']['messages'])
        and submit.last['vm']['consent_required']
    ), 'SEND: cancellation does not grant consent or leave a hidden prompt'


@pytest.mark.parametrize('change', ['project', 'effort', 'sign-out'])
def test_changed_pending_consent_cannot_auto_dispatch_old_attempt(submit, change):
    opened_from_submit(submit, 'click_send')
    if change == 'project':
        submit.command('create_project', name='Different current disclosure')
    elif change == 'effort':
        submit.command('select_effort', id='low')
    else:
        submit.command('sign_out')
    if submit.last['ui']['dialog'].get('visible'):
        submit.command('click_accept')
    assert submit.last['ui']['draft'] == PROMPT and not requests(submit), (
        'SEND: changed context/effort/account invalidates automatic resume while '
        'retaining exact draft'
    )
    assert not any(row.get('kind') == 'user' for row in submit.last['vm']['messages']), (
        'SEND: stale consent attempt cannot create an invisible or duplicate admitted prompt'
    )
