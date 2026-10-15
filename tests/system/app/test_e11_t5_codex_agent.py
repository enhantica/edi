"""Default real Session with an ordinary offline stdio executable dependency.

These gates never establish provider entitlement or official-runtime/model execution.
Original protocol facts are codex0.162.1 schemas plus committed7f7332ead GR1/GR2.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from operator import itemgetter
from pathlib import Path

import pytest

from tests.system.app import test_e11_t5_vm_retention as prior

ROOT = prior.ROOT
PEER = ROOT / 'tests/integration/py/assistant_vm_probe/codex_stdio_peer.py'


class Generic(prior.Component):
    def __init__(self, binary):
        self.process = subprocess.Popen(
            [str(binary), '--codex'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
        )
        self.reply_timeout = 5.0
        self.last = None
        self.handled = set()


@pytest.fixture
def generic(monkeypatch, tmp_path):
    actors = []

    def create(scenario='complete'):
        owned = tmp_path / str(len(actors))
        owned.mkdir()
        trace = owned / 'original-client-lines.jsonl'
        config = owned / 'peer-input.json'
        config.write_text(json.dumps({'scenario': scenario, 'trace': str(trace)}))
        executable = owned / 'codex'
        executable.write_text(f'#!{sys.executable}\n' + PEER.read_text())
        executable.chmod(0o700)
        monkeypatch.setenv('PATH', str(owned) + os.pathsep + os.environ['PATH'])
        monkeypatch.setenv('EDI_TEST_CODEX_PEER_INPUT', str(config))
        monkeypatch.setenv('TMPDIR', str(owned))
        monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
        monkeypatch.setenv('QT_QUICK_BACKEND', 'software')
        actor = Generic(Path(os.environ['EDI_ASSISTANT_WORKFLOW_VM_PROBE']))
        actor.command('inspect')
        actors.append(actor)
        return actor, trace

    yield create
    for actor in actors:
        actor.close()


def records(trace):
    return [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []


def settle(actor, predicate):
    # Existing owner-event delivery, bounded by40 ordinary30ms inspect commands.
    for _ in range(40):
        if predicate(actor.last['vm']):
            return actor.last['vm']
        actor.command('inspect')
    assert predicate(actor.last['vm']), 'GR: actual public VM reaches the declared finite state'
    return actor.last['vm']


def connect(actor):
    actor.command('sign_in')
    state = settle(actor, lambda value: value['connected'] or bool(value['last_error']))
    assert state['connected'], 'GR: actual default Session admits managed-account/catalog/thread'


def users(actor, text):
    return [
        row
        for row in actor.last['vm']['messages']
        if row.get('kind') == 'user' and row.get('text') == text
    ]


@pytest.mark.parametrize(
    'scenario',
    [
        'different-cwd',
        'network-enabled',
        'different-reviewer',
        'different-provider',
    ],
)
def test_effective_thread_mismatch_refuses_before_turn_and_preserves_user_input(generic, scenario):
    actor, trace = generic(scenario)
    assert not records(trace), 'GR1: default construction does not probe runtime/account/profile'
    actor.command('sign_in')
    state = settle(actor, lambda value: bool(value['last_error']))
    assert not state['connected'], 'GR1: incompatible effective admission never becomes ready'
    actor.command('send_text', text='Original refused prompt')
    assert not any(row.get('method') == 'turn/start' for row in records(trace)), (
        'GR1: effective-policy mismatch cannot dispatch an inference turn'
    )
    assert len(state['last_error'].encode()) <= 512, 'GR2: admission error uses error_bytes'


@pytest.mark.parametrize('scenario', ['complete', 'record-exact'])
def test_default_real_session_completed_text_uses_actual_turn_and_keeps_original(
    generic, scenario
):
    actor, trace = generic(scenario)
    assert not records(trace), 'GR: explicit Sign in is the first runtime action'
    connect(actor)
    actor.command('send_text', text='Original offline request')
    settle(
        actor,
        lambda value: any(
            row.get('kind') == 'assistant' and row.get('text') == 'Original offline reply'
            for row in value['messages']
        ),
    )
    assert len(users(actor, 'Original offline request')) == 1, (
        'GR: actual admitted prompt has exactly one visible user row'
    )
    requests = [row for row in records(trace) if row.get('method') == 'turn/start']
    assert len(requests) == 1, 'GR: one actual user admission produces one runtime turn'
    policy = requests[0]['params']['sandboxPolicy']
    assert (
        policy['type'] == 'workspaceWrite'
        and not policy['networkAccess']
        and policy['excludeSlashTmp']
        and policy['excludeTmpdirEnvVar']
    ), 'GR1: actual turn preserves admitted no-network/workspace boundaries'
    assert not actor.last['vm']['can_cancel'], 'GR: genuine completed turn settles Stop state'


@pytest.mark.parametrize('scenario', ['hold', 'steer-no-ack'])
def test_busy_visible_user_steer_is_once_only_even_when_process_loses_ack(generic, scenario):
    actor, trace = generic(scenario)
    connect(actor)
    actor.command('send_text', text='Original active request')
    settle(actor, itemgetter('can_cancel'))
    actor.command('send_text', text='Original followup')
    row = users(actor, 'Original followup')
    assert len(row) == 1 and row[0]['id'], 'GR: busy input has one immediate stable visible row'
    actor.command('inspect')
    assert [value['id'] for value in users(actor, 'Original followup')] == [row[0]['id']], (
        'GR: asynchronous steering retains the original user identity'
    )
    requests = records(trace)
    started = [value for value in requests if value.get('method') == 'turn/start']
    steered = [value for value in requests if value.get('method') == 'turn/steer']
    assert len(started) == len(steered) == 1, (
        'GR: active followup steers once, never duplicates turn'
    )
    assert steered[0]['params']['threadId'] == started[0]['params']['threadId'], (
        'GR: followup binds the original active thread'
    )
    assert steered[0]['params']['expectedTurnId'] == '019a0290-0000-7000-8000-000000000002', (
        'GR: followup uses the genuine original turn identity'
    )
    assert 'model' not in steered[0]['params'] and 'effort' not in steered[0]['params'], (
        'GR: busy input cannot silently override active model/effort'
    )
    actor.command('cancel')
    settle(actor, lambda value: not value['can_cancel'])
    assert sum(value.get('method') == 'turn/start' for value in records(trace)) == 1, (
        'GR: ack loss/Stop cannot silently resend an uncertain or acknowledged followup'
    )


def test_runtime_policy_amendment_is_declined_without_an_implicit_session_grant(generic):
    actor, trace = generic('approval-expansion')
    connect(actor)
    actor.command('send_text', text='Original request with an escalation')
    settle(
        actor,
        lambda _value: any(value.get('id') == 'original-approval-1' for value in records(trace)),
    )
    replies = [value for value in records(trace) if value.get('id') == 'original-approval-1']
    assert len(replies) == 1 and replies[0].get('result', {}).get('decision') in {
        'decline',
        'cancel',
    }, 'GR1: unadmitted persistent policy expansion is refused once using original request ID'


@pytest.mark.parametrize(
    'scenario',
    [
        'record-overflow',
        'wire-overflow',
        'events-overflow',
        'stderr-overflow',
    ],
)
def test_record_or_aggregate_exhaustion_interrupts_owned_turn_without_truncated_success(
    generic, scenario
):
    actor, trace = generic(scenario)
    connect(actor)
    actor.command('send_text', text='Original bounded turn')
    state = settle(actor, lambda value: bool(value['last_error']))
    assert len(state['last_error'].encode()) <= 512, 'GR2: oversized record has bounded safe error'
    assert not any(
        row.get('kind') == 'assistant' and row.get('status') == 'completed'
        for row in state['messages']
    ), 'GR2: rejected partial record is no completed reply'
    assert any(row.get('method') == 'turn/interrupt' for row in records(trace)), (
        'GR2: record exhaustion fences and interrupts the actual owned turn'
    )
