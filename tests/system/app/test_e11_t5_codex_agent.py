"""Default real Session with an ordinary offline stdio executable dependency.

These gates never establish provider entitlement or official-runtime/model execution.
Original protocol facts are codex0.162.1 schemas plus committed7f7332ead GR1/GR2.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from operator import itemgetter
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest

from tests.fixtures.scan_lifecycle.prepare import prepare as prepare_scan134
from tests.system.app import test_e11_t5_vm_retention as prior

ROOT = prior.ROOT
PEER = ROOT / 'tests/integration/py/assistant_vm_probe/codex_stdio_peer.py'


class Generic(prior.Component):
    def __init__(self, binary, *, ui=False):
        argv = (
            [
                str(binary),
                str(ROOT / 'tests/integration/py/assistant_consent_probe/SubmitHarness.qml'),
                '--usage',
            ]
            if ui
            else [str(binary), '--codex']
        )
        self.process = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
        )
        self.reply_timeout = 5.0
        self.last = None
        self.handled = set()

    def command(self, *args, **kwargs):
        try:
            return super().command(*args, **kwargs)
        except BaseException:
            # Observation only: no wait, signal, event injection or forced teardown.
            if self.last is not None:
                self.last['child_exit_observation'] = {'returncode': self.process.poll()}
            raise


@pytest.fixture
def generic(monkeypatch, tmp_path):
    actors = []

    def create(scenario='complete', *, override='peer', ui=False):
        owned = tmp_path / str(len(actors))
        owned.mkdir()
        trace = owned / 'original-client-lines.jsonl'
        config = owned / 'peer-input.json'
        config.write_text(json.dumps({'scenario': scenario, 'trace': str(trace)}))
        executable = owned / 'codex'
        executable.write_text(f'#!{sys.executable}\n' + PEER.read_text())
        executable.chmod(0o700)
        if override == 'peer':
            selected = str(executable.resolve())
        elif override == 'relative':
            selected = 'codex'
        elif override == 'missing':
            selected = str(owned / 'missing-original-peer')
        else:
            unexecutable = owned / 'nonexecutable-original-peer'
            unexecutable.write_text('Original harmless nonexecutable fixture')
            unexecutable.chmod(0o600)
            selected = str(unexecutable.resolve())
        monkeypatch.setenv('EDI_CODEX_DEVELOPMENT_EXECUTABLE', selected)
        monkeypatch.setenv('PATH', str(owned) + os.pathsep + os.environ['PATH'])
        monkeypatch.setenv('EDI_TEST_CODEX_PEER_INPUT', str(config))
        monkeypatch.setenv('TMPDIR', str(owned))
        monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
        monkeypatch.setenv('QT_QUICK_BACKEND', 'software')
        actor = Generic(
            Path(
                os.environ[
                    'EDI_ASSISTANT_CONSENT_PROBE' if ui else 'EDI_ASSISTANT_WORKFLOW_VM_PROBE'
                ]
            ),
            ui=ui,
        )
        actor.command('inspect')
        actor.peer_pid_file = config.with_suffix('.peer-pid')
        actors.append(actor)
        return actor, trace

    yield create
    for actor in actors:
        actor.close()


def records(trace):
    return [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []


def process_state(pid):
    stat = Path('/proc') / str(pid) / 'stat'
    if sys.platform.startswith('linux'):
        try:
            fields = stat.read_text().split()
            return {'start': fields[21], 'live': fields[2] != 'Z'}
        except FileNotFoundError:
            return None
    # macOS ordinary process metadata; no signal or process-memory inspection.
    result = subprocess.run(
        ['ps', '-p', str(pid), '-o', 'lstart=', '-o', 'stat='],
        capture_output=True,
        text=True,
        timeout=1,
        check=False,
    )
    fields = result.stdout.split()
    return (
        {'start': ' '.join(fields[:-1]), 'live': not fields[-1].startswith('Z')}
        if fields
        else None
    )


def live_original_peer(actor):
    pid = int(actor.peer_pid_file.read_text())
    identity = process_state(pid)
    assert identity and identity['live'], 'GR SETUP: original owned peer is live before the action'
    return pid, identity['start']


def original_peer_is_live(identity):
    pid, started = identity
    state = process_state(pid)
    return bool(state and state['start'] == started and state['live'])


def matching_interrupt(trace):
    return any(
        row.get('method') == 'turn/interrupt'
        and row.get('params', {}).get('turnId') == '019a0290-0000-7000-8000-000000000002'
        and row.get('params', {}).get('threadId') == '019a0290-0000-7000-8000-000000000001'
        for row in records(trace)
    )


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


def clear_conversation_case(generic, scenario):  # noqa: PLR0914, PLR0915 -- two finite lifecycle paths
    """Owner5d69: real managed authentication survives conversation retirement."""
    actor, trace = generic('clear:' + scenario)
    connect(actor)
    account = actor.last['vm']['handoff']['account_label']
    models = actor.last['vm']['models']
    choice = (actor.last['vm']['selected_model'], actor.last['vm']['selected_effort'])
    assert account == 'original@example.invalid' and models, (
        'CLEAR SETUP: real managed account/read and model/list admit the original account'
    )
    assert {'account/read', 'model/list'} <= {row.get('method') for row in records(trace)}, (
        'CLEAR SETUP: public readiness follows actual owned-peer account/catalog replies'
    )
    original_text = 'Original clear prior input'
    fresh_text = 'Original clear fresh input'
    actor.command('send_text', text=original_text)
    if scenario == 'active':
        settle(
            actor,
            lambda value: (
                value['can_cancel']
                and any(
                    row.get('payload', {}).get('id') == 'clear-prior-work'
                    for row in value['messages']
                )
            ),
        )
    else:
        settle(
            actor,
            lambda value: (
                not value['can_cancel']
                and any(
                    row.get('kind') == 'assistant'
                    and row.get('text') == 'Original before Clear reply'
                    for row in value['messages']
                )
            ),
        )
    assert len(users(actor, original_text)) == 1, (
        'CLEAR SETUP: actual original turn has one retained admitted user identity'
    )
    original_row = users(actor, original_text)[0]['id']
    original = started_requests(trace)
    assert len(original) == 1 and original[0]['params']['clientUserMessageId'] == original_row, (
        'CLEAR SETUP: retained original user identity matches its genuine turn/start'
    )
    identity = live_original_peer(actor)
    before = actor.last['vm']
    actor.command('clear_history')
    # Observe retirement before any outgoing-context acknowledgement. The GUI's
    # signIn action also approves current context, but must never repair lost auth here.
    for _ in range(40):
        actor.command('inspect')
        if not actor.last['vm']['can_cancel']:
            break
    cleared = actor.last['vm']
    trace.with_suffix('.clear-public.json').write_text(
        json.dumps(
            {
                'before': before,
                'cleared': cleared,
                'original_peer_identity': identity,
                'original_peer_still_live': original_peer_is_live(identity),
                'requests': records(trace),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    assert cleared['connected'] and cleared['handoff']['account_label'] == account, (
        'CLEAR: retiring a conversation preserves genuine managed authentication/account'
    )
    assert (
        cleared['models'] == models
        and (cleared['selected_model'], cleared['selected_effort']) == choice
    ), 'CLEAR: conversation retirement preserves the actual catalog and user choices'
    if cleared['context_consent_required']:
        actor.command('sign_in')
    actor.command('send_text', text=fresh_text)
    for _ in range(40):
        actor.command('inspect')
        if any(
            row.get('text') == 'Original fresh after Clear reply'
            for row in actor.last['vm']['messages']
        ):
            break
    after = actor.last['vm']
    sent = started_requests(trace)
    peer_events = trace.with_suffix('.clear-events.jsonl')
    observations = records(peer_events)
    trace.with_suffix('.clear-public.json').write_text(
        json.dumps(
            {
                'before': before,
                'cleared': cleared,
                'after': after,
                'original_peer_identity': identity,
                'original_peer_still_live': original_peer_is_live(identity),
                'peer_events': observations,
                'requests': records(trace),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    assert not any((cleared['messages'], cleared['pending_question'], cleared['pending_plan'])), (
        'CLEAR: original history and pending conversation controls are retired'
    )
    assert not cleared['can_cancel'], 'CLEAR: original operation settles after retirement'
    if scenario == 'active':
        interrupts = [row for row in records(trace) if row.get('method') == 'turn/interrupt']
        assert any(
            row['params']['threadId'] == original[0]['params']['threadId']
            and row['params']['turnId'] == observations[0]['turnId']
            for row in interrupts
        ) or not original_peer_is_live(identity), (
            'CLEAR: actual original work is interrupted or its original process has ceased'
        )
    assert after['connected'] and len(sent) == 2, (
        'CLEAR: a fresh conversation dispatches once without another sign-in'
    )
    assert sent[1]['params']['threadId'] != sent[0]['params']['threadId'], (
        'CLEAR: new user input uses a genuine distinct fresh runtime thread'
    )
    fresh_rows = users(actor, fresh_text)
    assert (
        len(fresh_rows) == 1
        and fresh_rows[0]['id'] != original_row
        and (fresh_rows[0]['id'] == sent[1]['params']['clientUserMessageId'])
    ), 'CLEAR: the fresh admitted prompt has its own once-only retained user identity'
    fresh_wire = json.dumps(sent[1]['params']['input'], ensure_ascii=False)
    assert fresh_wire.count(fresh_text) == 1 and original_text not in fresh_wire, (
        'CLEAR: fresh context contains the new input once and never replays the old prompt'
    )
    assert (
        sum(row.get('text') == 'Original fresh after Clear reply' for row in after['messages'])
        == 1
        and not after['can_cancel']
    ), 'CLEAR: genuine fresh turn completes once and settles its own operation'
    assert not any(
        row.get('id') == original_row
        or row.get('text')
        in {
            original_text,
            'Original before Clear reply',
            'Original late reply after Clear',
        }
        for row in after['messages']
    ), 'CLEAR: old retained or delayed conversation events cannot revive retired history'
    assert not any(
        row.get('method') in {'account/login/start', 'account/logout'} for row in records(trace)
    ), 'CLEAR: context approval neither restarts login nor logs out the managed account'


def test_clear_settled_conversation_preserves_real_managed_account_and_fresh_send(generic):
    clear_conversation_case(generic, 'settled')


def test_clear_active_turn_retires_old_authority_without_signing_out(generic):
    clear_conversation_case(generic, 'active')


def clear_control_events(trace):
    return records(trace.with_suffix('.clear-events.jsonl'))


def begin_clear_control_case(generic, scenario):
    actor, trace = generic(scenario)
    connect(actor)
    before = actor.last['vm']
    actor.command('send_text', text='Original Clear ordering turn A')
    settle(
        actor,
        lambda state: (
            state['can_cancel']
            and any(
                row.get('payload', {}).get('id') == 'clear-prior-work' for row in state['messages']
            )
        ),
    )
    assert before['handoff']['account_label'] == 'original@example.invalid', (
        'CLR SETUP: managed account is genuinely admitted before work and retirement'
    )
    original = started_requests(trace)
    assert len(original) == 1 and len(users(actor, 'Original Clear ordering turn A')) == 1, (
        'CLR SETUP: actual original thread/turn and once-only user row are admitted'
    )
    return actor, trace, before, original[0]


def require_clear_settlement(actor, trace, before, original):
    state = settle(
        actor,
        lambda value: (
            not value['can_cancel']
            and {'interrupt-ack', 'control-terminal'}
            <= {event['kind'] for event in clear_control_events(trace)}
        ),
    )
    trace.with_suffix('.clear-control-public.json').write_text(
        json.dumps(
            {
                'state': state,
                'events': clear_control_events(trace),
                'requests': records(trace),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    assert (
        state['connected']
        and state['handoff']['account_label'] == before['handoff']['account_label']
    ), 'CLR: both original terminal and control acknowledgement preserve the managed account'
    assert state['models'] == before['models'], (
        'CLR: actual catalog survives settled conversation retirement'
    )
    assert not any((state['messages'], state['pending_question'], state['pending_plan'])), (
        'CLR: no original or delayed conversation item revives after Clear'
    )
    interrupts = [row for row in records(trace) if row.get('method') == 'turn/interrupt']
    assert (
        len(interrupts) == 1
        and interrupts[0]['params']['threadId'] == original['params']['threadId']
    ), 'CLR: original retirement issues one interrupt bound to its own thread'
    active = next(event for event in clear_control_events(trace) if event['kind'] == 'active')
    assert interrupts[0]['params']['turnId'] == active['turnId'], (
        'CLR: acknowledgement cannot substitute a different original turn identity'
    )
    if state['context_consent_required']:
        actor.command('sign_in')  # Actual context approval only after retained-auth proof.
    actor.command('send_text', text='Original fresh Clear ordering turn B')
    state = settle(
        actor,
        lambda value: any(
            row.get('text') == 'Original fresh after Clear reply' for row in value['messages']
        ),
    )
    sent = started_requests(trace)
    assert len(sent) == 2 and sent[1]['params']['threadId'] != original['params']['threadId'], (
        'CLR: settled Clear admits one genuinely fresh thread, not replay of the old owner'
    )
    row = users(actor, 'Original fresh Clear ordering turn B')
    assert len(row) == 1 and row[0]['id'] == sent[1]['params']['clientUserMessageId'], (
        'CLR: fresh current input is acknowledged by exactly its own retained row identity'
    )
    assert state['connected'] and not state['can_cancel'], (
        'CLR: fresh actual turn completes without logout or stranded cancellation'
    )
    assert not any(
        record.get('method') in {'account/login/start', 'account/logout'}
        for record in records(trace)
    ), 'CLR: context/thread renewal does not fabricate a fresh login or logout'


@pytest.mark.parametrize('order', ['ack-first', 'terminal-first'])
def test_active_clear_settles_both_original_control_orderings(generic, order):
    actor, trace, before, original = begin_clear_control_case(generic, 'clear:ordered:' + order)
    actor.command('clear_history')
    require_clear_settlement(actor, trace, before, original)
    kinds = [event['kind'] for event in clear_control_events(trace)]
    assert (kinds.index('interrupt-ack') < kinds.index('control-terminal')) == (
        order == 'ack-first'
    ), 'CLR SETUP: actual peer emitted the independently selected ACK/terminal ordering'


def test_acknowledged_stop_then_clear_keeps_original_interrupt_once(generic):
    actor, trace, before, original = begin_clear_control_case(generic, 'clear:stop-ack')
    actor.command('cancel')
    settle(
        actor,
        lambda _value: any(
            event['kind'] == 'interrupt-ack' for event in clear_control_events(trace)
        ),
    )
    assert not any(event['kind'] == 'control-terminal' for event in clear_control_events(trace)), (
        'CLR SETUP: real Stop acknowledgement precedes Clear while original terminal is pending'
    )
    actor.command('clear_history')
    require_clear_settlement(actor, trace, before, original)


def test_original_terminal_cannot_release_input_before_its_control_ack(generic):
    actor, trace, before, original = begin_clear_control_case(generic, 'clear:pending-ack')
    actor.command('cancel')
    state = settle(
        actor,
        lambda value: (
            any(event['kind'] == 'control-terminal' for event in clear_control_events(trace))
            and any(row.get('kind') == 'assistant' for row in value['messages'])
        ),
    )
    assert state['connected'] and not state['context_consent_required'], (
        'CLR SETUP: original terminal retains genuine approved context before new input'
    )
    assert not any(event['kind'] == 'interrupt-ack' for event in clear_control_events(trace)), (
        'CLR SETUP: actual original control remains unacknowledged at the attempted new input'
    )
    actor.command('send_text', text='Original pending-control turn B')
    blocked = actor.last['vm']
    events = clear_control_events(trace)
    trace.with_suffix('.pending-control-public.json').write_text(
        json.dumps(
            {
                'blocked': blocked,
                'events': events,
                'requests': records(trace),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    assert not any(event['kind'] == 'interrupt-ack' for event in events), (
        'CLR SETUP: attempted input actually precedes ACK delivery, not a guessed timing interval'
    )
    assert len(started_requests(trace)) == 1 and not users(
        actor, 'Original pending-control turn B'
    ), 'CLR: pending original control refuses new admission without acknowledging editor clearing'
    assert blocked['last_error'] and len(blocked['last_error'].encode()) <= 512, (
        'CLR: nonadmitted input has a truthful bounded visible refusal'
    )
    settle(
        actor,
        lambda value: (
            any(event['kind'] == 'interrupt-ack' for event in clear_control_events(trace))
            and not value['can_cancel']
        ),
    )
    actor.command('send_text', text='Original pending-control turn B')
    state = settle(
        actor,
        lambda value: any(
            row.get('text') == 'Original fresh after Clear reply' for row in value['messages']
        ),
    )
    sent = started_requests(trace)
    assert len(sent) == 2 and len(users(actor, 'Original pending-control turn B')) == 1, (
        'CLR: explicit retry after real original ACK admits the new input exactly once'
    )
    assert (
        state['connected']
        and state['handoff']['account_label'] == before['handoff']['account_label']
        and sent[0]['params']['threadId'] == original['params']['threadId']
    ), 'CLR: settling the owned original control preserves real account and original binding'


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
    identity = live_original_peer(actor)
    actor.command('send_text', text='Original bounded turn')
    state = settle(actor, lambda value: bool(value['last_error']))
    assert len(state['last_error'].encode()) <= 512, 'GR2: oversized record has bounded safe error'
    assert not any(
        row.get('kind') == 'assistant' and row.get('status') == 'completed'
        for row in state['messages']
    ), 'GR2: rejected partial record is no completed reply'
    settle(actor, lambda _value: matching_interrupt(trace) or not original_peer_is_live(identity))
    assert matching_interrupt(trace) or not original_peer_is_live(identity), (
        'GR2: exhaustion interrupts the original turn or actually stops its owned process'
    )
    assert not actor.last['vm']['can_cancel'], 'GR2: cancelled work has settled public Stop state'
    assert len(users(actor, 'Original bounded turn')) == 1, (
        'GR2: quota refusal preserves the complete original visible user input once'
    )


def test_followup_before_turn_identity_refuses_without_retiring_original_work(generic):
    actor, trace = generic('start-pending')
    connect(actor)
    identity = live_original_peer(actor)
    actor.command('send_text', text='Original awaiting turn admission')
    settle(actor, lambda _value: any(row.get('method') == 'turn/start' for row in records(trace)))
    first = users(actor, 'Original awaiting turn admission')
    assert len(first) == 1 and first[0]['id'], (
        'GR: genuine outstanding start request has one actual original admitted user row'
    )
    actor.command('send_text', text='Original not-yet-admissible followup')
    after = actor.last['vm']
    assert after['last_error'] and len(after['last_error'].encode()) <= 512, (
        'GR: missing active turn identity has visible bounded nonadmission'
    )
    assert not users(actor, 'Original not-yet-admissible followup'), (
        'GR: rejected followup creates no row that would acknowledge clearing the actual draft'
    )
    assert [row['id'] for row in users(actor, 'Original awaiting turn admission')] == [
        first[0]['id']
    ], 'GR: refused early followup preserves the original admitted prompt identity'
    assert after['can_cancel'] and original_peer_is_live(identity), (
        'GR: refusing input before a turn ID must keep the original work/process active'
    )
    requests = records(trace)
    assert sum(row.get('method') == 'turn/start' for row in requests) == 1, (
        'GR: nonadmitted followup cannot replay another turn'
    )
    assert not any(row.get('method') == 'turn/steer' for row in requests), (
        'GR: early followup cannot guess an unadmitted turn identity'
    )
    actor.command('cancel')
    settle(actor, lambda value: not value['can_cancel'] and not original_peer_is_live(identity))


# Review62 GN1-GN6. These are public contract invariants, not producer-output pins.
def started_requests(trace):
    return [row for row in records(trace) if row.get('method') == 'turn/start']


def authority_row(state):
    return next(
        (row for row in state['messages'] if row.get('payload', {}).get('id') == 'authority-item'),
        None,
    )


def configure_next_peer(actor, scenario):
    path = actor.peer_pid_file.with_suffix('.json')
    value = json.loads(path.read_text())
    value['scenario'] = scenario
    path.write_text(json.dumps(value))


@pytest.mark.parametrize('scenario', ['hold', 'start-pending'])
def test_gn1_oversized_new_draft_preserves_original_admitted_process(generic, scenario):
    actor, trace = generic(scenario)
    connect(actor)
    identity = live_original_peer(actor)
    actor.command('send_text', text='Original already admitted work')
    settle(actor, lambda _state: len(started_requests(trace)) == 1)
    original = users(actor, 'Original already admitted work')
    assert len(original) == 1, 'GN1 SETUP: original public admission precedes new refusal'
    actor.command('send_text', text='x' * 1048577)
    state = actor.last['vm']
    assert state['last_error'] and len(state['last_error'].encode()) <= 512, (
        'GN1: oversized nonadmission has a bounded visible explanation'
    )
    assert state['can_cancel'] and original_peer_is_live(identity), (
        'GN1: rejecting only the new draft preserves original work and reachable Stop'
    )
    assert [row['id'] for row in users(actor, 'Original already admitted work')] == [
        original[0]['id']
    ], 'GN1: refusing new input does not replace the original acknowledged user row'
    assert len(started_requests(trace)) == 1 and not any(
        row.get('method') == 'turn/steer' for row in records(trace)
    ), 'GN1: a preflight-refused draft produces neither a new turn nor an active steer'


@pytest.mark.parametrize('mode', ['null', 'apikey', 'chatgpt', 'chatgptAuthTokens'])
def test_gn2_account_change_retires_old_authority_and_pending_outcomes(generic, mode):
    actor, trace = generic('gn:account-' + mode)
    connect(actor)
    actor.command('send_text', text='Original account-bound work')
    settle(
        actor,
        lambda state: any(
            row.get('text') == 'Original immutable text' for row in state['messages']
        ),
    )
    actor.command('send_text', text='Original trigger for account notification')
    state = actor.last['vm']
    # A replacement managed account must be read/revalidated, not silently accepted
    # from an auth-mode-only notification. This peer supplies no new identity proof.
    revalidated = sum(row.get('method') == 'account/read' for row in records(trace)) > 1
    assert not state['can_cancel'] and (not state['connected'] or revalidated), (
        'GN2: account change retires old work before any revalidated managed connection'
    )
    assert not any(row.get('status') in {'pending', 'in_progress'} for row in state['messages']), (
        'GN2: account retirement truthfully settles every original pending public row'
    )
    before = len(started_requests(trace))
    if not state['connected']:
        actor.command('send_text', text='Original stale account send')
        assert len(started_requests(trace)) == before, (
            'GN2: no turn uses retired managed authority'
        )


@pytest.mark.parametrize('scenario', ['logout-hold', 'logout-late-start'])
def test_gn2_signout_revokes_before_ack_and_late_start_cannot_revive(generic, scenario):
    actor, trace = generic('gn:' + scenario)
    connect(actor)
    actor.command('send_text', text='Original work before Sign out')
    settle(actor, lambda _state: len(started_requests(trace)) == 1)
    actor.command('sign_out')
    state = actor.last['vm']
    assert not state['connected'], (
        'GN2: Sign out revokes authority before logout acknowledgement and despite late start'
    )
    state = settle(
        actor,
        lambda value: (
            not any(row.get('status') in {'pending', 'in_progress'} for row in value['messages'])
        ),
    )
    assert not any(row.get('status') in {'pending', 'in_progress'} for row in state['messages']), (
        'GN2: Sign out retains actual original work as an interrupted settled outcome'
    )
    actor.command('send_text', text='Original forbidden logout-interval send')
    assert len(started_requests(trace)) == 1, 'GN2: the logout interval cannot admit a new turn'


@pytest.mark.parametrize('suffix', ['missing', 'wrong'])
def test_gn3_steer_ack_requires_actual_expected_turn_id(generic, suffix):
    actor, trace = generic('gn:steer-' + suffix)
    connect(actor)
    actor.command('send_text', text='Original bound turn')
    settle(actor, itemgetter('can_cancel'))
    actor.command('send_text', text='Original unacknowledged steer')
    state = actor.last['vm']
    assert state['last_error'], (
        'GN3: missing or unrelated required steer result.turnId is rejected'
    )
    assert not any(
        row.get('status') == 'completed' for row in users(actor, 'Original unacknowledged steer')
    ), 'GN3: a misbound acknowledgement cannot claim successful user admission'
    assert len(started_requests(trace)) == 1, 'GN3: malformed acknowledgement never replays a turn'


@pytest.mark.parametrize('suffix', ['item', 'delta'])
def test_gn3_known_output_requires_its_actual_turn_binding(generic, suffix):
    actor, trace = generic('gn:missing-' + suffix + '-turn')
    connect(actor)
    actor.command('send_text', text='Original binding control')
    settle(
        actor,
        lambda state: any(
            row.get('text') == 'Original immutable text' for row in state['messages']
        ),
    )
    actor.command('send_text', text='Original trigger for misbound output')
    state = actor.last['vm']
    assert not any(
        row.get('text') == 'Unbound text' or 'UNBOUND APPEND' in row.get('text', '')
        for row in state['messages']
    ), 'GN3: known output lacking required turnId never enters the current public transcript'
    assert len(started_requests(trace)) == 1, (
        'GN3: ignored/refused malformed output does not replay input'
    )


@pytest.mark.parametrize('suffix', ['duplicate', 'type', 'delta'])
def test_gn3_finalized_original_cannot_be_replaced_or_extended(generic, suffix):
    actor, trace = generic('gn:immutable-' + suffix)
    connect(actor)
    actor.command('send_text', text='Original immutable result control')
    state = settle(
        actor,
        lambda value: (
            any(row.get('text') == 'Original immutable text' for row in value['messages'])
            if suffix == 'delta'
            else authority_row(value) is not None
        ),
    )
    original = (
        next(row for row in state['messages'] if row.get('text') == 'Original immutable text')
        if suffix == 'delta'
        else authority_row(state)
    )
    assert original, 'GN3 SETUP: completed original is retained before late input'
    actor.command('send_text', text='Original trigger for finalized contradiction')
    after = next(row for row in actor.last['vm']['messages'] if row['id'] == original['id'])
    assert after['text'] == original['text'] and after['payload'] == original['payload'], (
        'GN3: finalized content survives duplicate completion, type change and late delta'
    )
    assert len(started_requests(trace)) == 1, (
        'GN3: a finalized-item contradiction cannot create a new turn'
    )


@pytest.mark.parametrize('kind', ['commandExecution', 'fileChange'])
def test_gn3_enclosing_success_cannot_fabricate_missing_tool_final_item(generic, kind):
    actor, trace = generic('gn:unfinished-' + kind)
    connect(actor)
    actor.command('send_text', text='Original unfinished operation')
    state = settle(actor, lambda value: authority_row(value) is not None)
    row = authority_row(state)
    assert row['status'] != 'completed', (
        'GN3: turn completion alone cannot invent an authoritative completed command/file outcome'
    )
    assert row['payload']['status'] == 'inProgress', (
        'GN3: the original incomplete operation payload remains truthful and complete'
    )
    assert len(started_requests(trace)) == 1, (
        'GN3: unfinished output refusal never repeats user work'
    )


def test_gn3_wrong_thread_resolved_cannot_consume_current_question(generic):
    actor, _trace = generic('gn:question-wrong-resolve')
    connect(actor)
    actor.command('send_text', text='Original question control')
    state = settle(actor, lambda value: bool(value['pending_question']))
    original = state['pending_question']
    assert original['question_id'] and original['text'] == 'Which original option?', (
        'GN3 SETUP: actual public question identity binds the genuine original question content'
    )
    actor.command('send_text', text='Original trigger for unrelated resolution')
    assert actor.last['vm']['pending_question'] == original, (
        'GN3: a request resolution from another thread cannot erase the current question'
    )


def test_gn3_stale_answer_after_reconnect_preserves_fresh_work(generic):
    actor, trace = generic('gn:question-stale-answer')
    connect(actor)
    actor.command('send_text', text='Original retiring question')
    state = settle(actor, lambda value: bool(value['pending_question']))
    question = state['pending_question']['question_id']
    actor.command('send_text', text='Original trigger for owned process EOF')
    settle(actor, lambda value: not value['connected'])
    configure_next_peer(actor, 'hold')
    connect(actor)
    actor.command('send_text', text='Original fresh unrelated work')
    settle(actor, itemgetter('can_cancel'))
    identity = live_original_peer(actor)
    actor.command('answer', id=question, answer='Original answer')
    assert actor.last['vm']['can_cancel'] and original_peer_is_live(identity), (
        'GN3: an answer owned by a retired thread cannot retire unrelated fresh work'
    )
    assert len(started_requests(trace)) == 2, 'GN3: stale answer never replays a third turn'


@pytest.mark.parametrize('channel', ['events', 'wire', 'stderr'])
def test_gn4_individually_legal_settled_turns_have_independent_resource_lifetimes(
    generic, channel
):
    actor, trace = generic('gn:lifetime-' + channel)
    connect(actor)
    identity = live_original_peer(actor)
    for index in range(2):
        actor.command('send_text', text='Original legal settled turn ' + str(index))
        state = settle(actor, lambda value: not value['can_cancel'] or bool(value['last_error']))
        assert (
            not state['last_error'] and state['connected'] and original_peer_is_live(identity)
        ), 'GN4: settled legal turns do not consume a single process-lifetime stream budget'
        assert len(users(actor, 'Original legal settled turn ' + str(index))) == 1, (
            'GN4: each independently admitted legal turn retains its original user row once'
        )
    assert len(started_requests(trace)) == 2, (
        'GN4: resource reset occurs at genuine independent turns'
    )


@pytest.mark.parametrize('size', ['within', 'over'])
def test_gn4_catalogue_charges_complete_metadata_across_pages(generic, size):
    actor, trace = generic('gn:catalogue-' + size)
    actor.command('sign_in')
    state = settle(actor, lambda value: value['connected'] or bool(value['last_error']))
    # Two independent model objects carry 500000/530000 description bytes each.
    # Small wrappers keep the former below1MiB and the latter above it, while each
    # individual record is below1MiB and there are only two choices.
    if size == 'over':
        assert not state['connected'] and state['last_error'], (
            'GN4: complete aggregate catalogue refuses before ready despite small labels'
        )
        assert not any(row.get('method') == 'thread/start' for row in records(trace)), (
            'GN4: over-cap complete catalogue cannot advance to admitted thread creation'
        )
    else:
        assert state['connected'] and len(state['models']) == 2, (
            'GN4: complete paginated catalogue within inclusive byte/count caps remains available'
        )


def test_gn5_reconnect_stages_current_immutable_inputs_not_modified_recovery(generic, tmp_path):
    actor, trace = generic('gn:workspace-change')
    original = b'Original immutable selected input, not a scientific expected value\n'
    path = tmp_path / 'original-selected.txt'
    path.write_bytes(original)
    request = actor.command('selected_begin')['reply']['request_id']
    actor.command('selected_add', request_id=request, urls=[path.as_uri()])
    assert actor.last['vm']['selected_files'], (
        'GN5 SETUP: real selected-byte intake precedes workspace creation'
    )
    connect(actor)
    first_cwd = Path(
        next(row['params']['cwd'] for row in records(trace) if row.get('method') == 'thread/start')
    )
    assert (first_cwd / 'inputs' / path.name).read_bytes() == original, (
        'GN5 SETUP: first working copy matches independently planted bytes'
    )
    actor.command('send_text', text='Original work before process loss')
    settle(actor, lambda value: not value['connected'])
    changed = (first_cwd / 'inputs' / path.name).read_bytes()
    assert changed != original and path.read_bytes() == original, (
        'GN5 SETUP: only the task-owned staged copy changed before actual process loss'
    )
    configure_next_peer(actor, 'complete')
    connect(actor)
    current_cwd = Path(
        [row['params']['cwd'] for row in records(trace) if row.get('method') == 'thread/start'][-1]
    )
    assert (current_cwd / 'inputs' / path.name).read_bytes() == original, (
        'GN5: a fresh current-input connection cannot silently inherit changed recovery bytes'
    )
    assert (first_cwd / 'inputs' / path.name).read_bytes() == changed, (
        'GN5: original changed recovery artifact is preserved rather than silently overwritten'
    )


@pytest.mark.parametrize('selection', ['auto', 'model'])
def test_gn6_auto_after_explicit_effort_resets_actual_sticky_override(generic, selection):
    actor, trace = generic('gn:effort-' + selection)
    connect(actor)
    actor.command('select_effort', id='high')
    assert actor.last['vm']['selected_effort'] == 'high', (
        'GN6 SETUP: original catalogue permits explicit high'
    )
    actor.command('send_text', text='Original explicit effort turn')
    settle(actor, lambda value: not value['can_cancel'])
    first = started_requests(trace)
    assert len(first) == 1 and first[0]['params'].get('effort') == 'high', (
        'GN6 SETUP: first actual runtime request establishes its sticky explicit override'
    )
    if selection == 'auto':
        actor.command('select_effort', id='')
    else:
        actor.command('select_model', id='gpt-6-sol')
    assert not actor.last['vm']['selected_effort'], (
        'GN6 SETUP: Auto or unavailable old choice exposes actual Provider default'
    )
    actor.command('send_text', text='Original Auto effort turn')
    settle(actor, lambda value: not value['can_cancel'] or bool(value['last_error']))
    turns = started_requests(trace)
    assert (len(turns) == 1 and actor.last['vm']['last_error']) or (
        len(turns) == 2 and turns[1]['params'].get('effort') == 'medium'
    ), 'GN6: Auto resets to the independent default or visibly refuses admission'


def test_gn3_unknown_notification_preserves_bound_active_control(generic):
    actor, trace = generic('gn:unknown-control')
    connect(actor)
    actor.command('send_text', text='Original unknown-notification control')
    settle(actor, itemgetter('can_cancel'))
    identity = live_original_peer(actor)
    actor.command('send_text', text='Original valid steer control')
    assert actor.last['vm']['can_cancel'] and original_peer_is_live(identity), (
        'GN3: an unrelated unknown notification does not fabricate failure of valid bound work'
    )
    assert users(actor, 'Original valid steer control')[0]['status'] == 'completed', (
        'GN3: genuine matching steer acknowledgement still admits the original user input once'
    )
    assert len(started_requests(trace)) == 1, (
        'GN3: a valid busy control remains in its original turn'
    )


def test_gn3_missing_turn_server_question_cannot_claim_current_authority(generic):
    actor, _trace = generic('gn:missing-request-turn')
    connect(actor)
    actor.command('send_text', text='Original request-binding control')
    settle(actor, itemgetter('can_cancel'))
    actor.command('send_text', text='Original trigger for unbound question')
    assert not actor.last['vm']['pending_question'], (
        'GN3: a known server question missing required turnId cannot enter current authority'
    )


@pytest.mark.parametrize('kind', ['commandExecution', 'fileChange'])
def test_gn3_actual_final_tool_original_remains_a_valid_completion(generic, kind):
    actor, trace = generic('gn:finished-' + kind)
    connect(actor)
    actor.command('send_text', text='Original authoritative final operation')
    state = settle(actor, lambda value: authority_row(value) is not None)
    row = authority_row(state)
    assert row['status'] == 'completed' and row['payload']['status'] == 'completed', (
        'GN3: genuine authoritative final command/file item is retained as completed'
    )
    assert not state['can_cancel'] and not state['last_error'], (
        'GN3: complete bound original and genuine turn terminal settle without interruption'
    )
    assert len(started_requests(trace)) == 1, 'GN3: final operation control dispatches once'


def test_gn3r_partial_assistant_text_is_not_a_final_original(generic):
    actor, _trace = generic('gn:r:partial-message')
    connect(actor)
    actor.command('send_text', text='Original partial assistant completion check')
    state = settle(actor, lambda value: not value['can_cancel'])
    assert not any(
        row.get('kind') == 'assistant' and row.get('status') == 'completed'
        for row in state['messages']
    ), 'GN3-R: started text and deltas cannot become final from an empty completed snapshot'
    assert state['last_error'], 'GN3-R: missing actual final message has truthful interruption'


def test_gn3r_actual_final_message_snapshot_is_authoritative(generic):
    actor, _trace = generic('gn:r:final-message-snapshot')
    connect(actor)
    actor.command('send_text', text='Original authoritative message snapshot check')
    state = settle(
        actor,
        lambda value: (
            not value['can_cancel']
            and any(row.get('text') == 'Original immutable text' for row in value['messages'])
        ),
    )
    assert any(
        row.get('text') == 'Original immutable text' and row.get('status') == 'completed'
        for row in state['messages']
    ), 'GN3-R: a genuine matching final snapshot can supply its actual complete message'
    assert not state['last_error'], 'GN3-R: actual final snapshot is not refused as partial text'


@pytest.mark.parametrize('kind', ['mcpToolCall', 'dynamicToolCall', 'collabAgentToolCall'])
@pytest.mark.parametrize('route', ['item', 'snapshot'])
@pytest.mark.parametrize('status', ['inProgress', 'missing'])
def test_gn3r_status_bearing_tools_require_genuine_final_status(generic, kind, route, status):
    actor, _trace = generic(f'gn:r:status-:{kind}:{route}:{status}')
    connect(actor)
    actor.command('send_text', text='Original status-bearing tool check')
    state = settle(actor, lambda value: not value['can_cancel'])
    assert not any(
        row.get('payload', {}).get('id') == 'authority-item' and row.get('status') == 'completed'
        for row in state['messages']
    ), 'GN3-R: missing/inProgress tool status is not final via item or snapshot'
    assert state['last_error'], 'GN3-R: malformed or unfinished successful tool outcome is refused'


@pytest.mark.parametrize('kind', ['mcpToolCall', 'dynamicToolCall', 'collabAgentToolCall'])
def test_gn3r_real_final_status_tool_remains_a_valid_original(generic, kind):
    actor, _trace = generic(f'gn:r:status-:{kind}:item:completed')
    connect(actor)
    actor.command('send_text', text='Original valid status-bearing final tool')
    state = settle(
        actor, lambda value: not value['can_cancel'] and authority_row(value) is not None
    )
    row = authority_row(state)
    assert row and row['status'] == row['payload']['status'] == 'completed', (
        'GN3-R: genuine final status-bearing original remains complete and untruncated'
    )
    assert not state['last_error'], 'GN3-R: valid final tool sibling does not create interruption'


@pytest.mark.parametrize('kind', ['commandExecution', 'fileChange'])
@pytest.mark.parametrize('outcome', ['interrupted', 'failed'])
def test_gn3r_non_success_snapshot_retains_unfinished_and_already_final_evidence(
    generic, kind, outcome
):
    actor, _trace = generic(f'gn:r:interruption:{kind}:{outcome}')
    connect(actor)
    actor.command('send_text', text='Original non-success terminal with unfinished work')
    state = settle(
        actor,
        lambda value: (
            not value['can_cancel']
            and authority_row(value) is not None
            and any(
                row.get('payload', {}).get('id') == 'prior-genuine-final'
                for row in value['messages']
            )
        ),
    )
    assert state['connected'], (
        'GN3-R: valid non-success snapshot settles without rejecting unfinished evidence'
    )
    unfinished = authority_row(state)
    assert unfinished and unfinished['status'] != 'completed', (
        'GN3-R: enclosing non-success retains unfinished work without invented final success'
    )
    assert unfinished['payload']['status'] == 'inProgress', (
        'GN3-R: actual unfinished payload is preserved despite enclosing interrupted outcome'
    )
    complete = next(
        row
        for row in state['messages']
        if row.get('payload', {}).get('id') == 'prior-genuine-final'
    )
    assert complete['status'] == 'completed' and complete['payload']['exitCode'] == 0, (
        'GN3-R: prior genuine complete result survives a sibling interrupted/failed snapshot'
    )


@pytest.mark.parametrize('kind', ['command', 'plan', 'summary', 'reasoning', 'question'])
def test_gn4r_current_progress_siblings_remain_valid_and_reasoning_stays_private(generic, kind):
    actor, trace = generic('gn:r:progress:' + kind)
    connect(actor)
    actor.command('send_text', text='Original current progress control')
    settle(actor, itemgetter('can_cancel'))
    actor.command('send_text', text='Original current progress trigger')
    state = actor.last['vm']
    assert state['can_cancel'] and state['connected'] and not state['last_error'], (
        'GN4-R: bounded bound command/plan/reasoning/question progress is valid active work'
    )
    if kind in {'summary', 'reasoning'}:
        assert not any(
            'Original bounded current progress' in row.get('text', '') for row in state['messages']
        ), 'GN4-R: processing current reasoning progress does not publish its private text'
    if kind == 'question':
        assert state['pending_question'], 'GN4-R: genuine current user-input request is presented'
    assert len(started_requests(trace)) == 1, 'GN4-R: progress never dispatches another turn'
    # This short acceptance control does not prove renewal at the real120s idle deadline.


def test_gn4r_repeated_stop_keeps_original_owned_revoke_request_once(generic):
    actor, trace = generic('gn:r:stop-unsettled')
    connect(actor)
    actor.command('send_text', text='Original unacknowledged Stop request')
    settle(actor, itemgetter('can_cancel'))
    identity = live_original_peer(actor)
    actor.command('cancel')
    assert matching_interrupt(trace), 'GN4-R SETUP: first Stop actually requests the original turn'
    first = [row for row in records(trace) if row.get('method') == 'turn/interrupt']
    actor.command('cancel')
    after = [row for row in records(trace) if row.get('method') == 'turn/interrupt']
    assert len(first) == 1 and after == first, (
        'GN4-R: repeated Stop retains exactly the original owned interrupt and correlation'
    )
    assert actor.last['vm']['can_cancel'] or not original_peer_is_live(identity), (
        'GN4-R: pending revoke stays observable until actual owned process settlement'
    )
    assert len(started_requests(trace)) == 1, 'GN4-R: repeated Stop cannot replay original work'
    # Actual public revoke_ms is10000. Its elapsed bound cannot be measured inside
    # the unchanged5s complete-node budget; clock/deadline timing remains unqualified.


@pytest.mark.parametrize('override', ['relative', 'missing', 'nonexecutable'])
def test_explicit_invalid_development_override_refuses_without_fallback(generic, override):
    # Run only after static/cohort proof that invalid explicit selection is checked
    # before any app-owned runtime launch. Never qualify this by launching Codex.
    actor, trace = generic(override=override)
    actor.command('sign_in')
    state = settle(actor, lambda value: bool(value['last_error']))
    assert not state['connected'] and len(state['last_error'].encode()) <= 512, (
        'PACKAGE: invalid explicit absolute-executable contract has bounded visible refusal'
    )
    assert not records(trace) and not actor.peer_pid_file.exists(), (
        'PACKAGE: invalid explicit override cannot silently launch the valid owned PATH fallback'
    )


@pytest.mark.parametrize('scenario', ['active', 'stale', 'final'])
def test_gn4_mcp_progress_has_real_bound_original_without_rewriting_final(generic, scenario):
    actor, trace = generic('gn:x:mcp-' + scenario)
    connect(actor)
    actor.command('send_text', text='Original MCP progress boundary')
    state = settle(
        actor,
        lambda value: (
            authority_row(value) is not None
            and (
                scenario != 'final' or authority_row(value)['payload'].get('status') == 'completed'
            )
        ),
    )
    original = authority_row(state)
    assert original['payload']['type'] == 'mcpToolCall', (
        'GN4 SETUP: actual current MCP original precedes published progress notification'
    )
    actor.command('send_text', text='Original MCP progress trigger')
    state = actor.last['vm']
    row = authority_row(state)
    assert row and row['payload'] == original['payload'], (
        'GN4: bound/stale/late progress cannot rewrite the actual original tool outcome'
    )
    if scenario != 'final':
        assert state['can_cancel'] and not state['last_error'], (
            'GN4: current valid MCP message remains active and stale-turn progress is inert'
        )
    assert len(started_requests(trace)) == 1, 'GN4: MCP progress does not start another user turn'
    # Real120s idle renewal/current unfinished/nonempty accounting is static-only
    # here. This short acceptance control is not elapsed-deadline qualification.


def successful_question_answers(trace):
    return [
        row
        for row in records(trace)
        if row.get('id') == 'original-question-rpc'
        and any(
            value.get('answers') for value in row.get('result', {}).get('answers', {}).values()
        )
    ]


@pytest.mark.parametrize('stage', ['existing', 'new'])
def test_gn4_stop_retires_question_completion_before_actual_settlement(generic, stage):
    actor, trace = generic('gn:x:stop-' + stage)
    connect(actor)
    actor.command('send_text', text='Original question authority before Stop')
    if stage == 'existing':
        state = settle(actor, lambda value: bool(value['pending_question']))
        captured_id = state['pending_question']['question_id']
    else:
        settle(actor, itemgetter('can_cancel'))
        captured_id = None
    actor.command('cancel')
    after_stop = actor.last['vm']['pending_question']
    if captured_id is None:
        captured_id = after_stop.get('question_id', 'original-unowned-question')
    actor.command('answer', id=captured_id, answer='Original answer')
    assert matching_interrupt(trace), 'GN4 SETUP: actual Stop is pending on the original turn'
    assert not successful_question_answers(trace), (
        'GN4: old queued answer or newly arriving question cannot complete human input after Stop'
    )
    assert not after_stop and not actor.last['vm']['pending_question'], (
        'GN4: pending Stop retires displayed question and cannot expose a new actionable question'
    )
    assert len(started_requests(trace)) == 1, 'GN4: question retirement never replays a turn'


def test_gn4_unrevoked_original_question_still_completes_once(generic):
    actor, trace = generic('gn:x:question-answer')
    connect(actor)
    actor.command('send_text', text='Original genuine question control')
    state = settle(actor, lambda value: bool(value['pending_question']))
    captured = state['pending_question']['question_id']
    actor.command('answer', id=captured, answer='Original answer')
    state = settle(
        actor,
        lambda value: (
            not value['can_cancel']
            and any(row.get('text') == 'Original offline reply' for row in value['messages'])
        ),
    )
    answers = successful_question_answers(trace)
    assert len(answers) == 1 and answers[0]['result']['answers']['original-question'] == {
        'answers': ['Original answer']
    }, 'GN4: genuine current public question maps once to its original runtime answer binding'
    assert not state['pending_question'] and not state['last_error'], (
        'GN4: unrevoked answer and genuine completed originals settle normally'
    )


# RPC1/CTX1/RPC2: pinned092d3acd dispatcher and public text-input semantics.
# Complete disclosure equality is a roundtrip/currentness invariant, not a
# production-generated scientific golden. No official runtime is launched.
@pytest.mark.parametrize('method', ['turn/start', 'turn/steer'])
@pytest.mark.parametrize('opt_in', [False, True])
def test_rpc83_peer_qualifies_actual_experimental_field_negotiation(tmp_path, method, opt_in):
    config = tmp_path / 'original-peer-input.json'
    config.write_text(json.dumps({'scenario': 'hold', 'trace': str(tmp_path / 'wire.jsonl')}))
    messages = [
        {
            'id': 1,
            'method': 'initialize',
            'params': {
                'clientInfo': {'name': 'original-contract-control', 'version': '1'},
                'capabilities': {'experimentalApi': opt_in},
            },
        },
        {
            'id': 2,
            'method': method,
            'params': {
                'threadId': 'original-thread',
                'expectedTurnId': 'original-turn',
                'input': [{'type': 'text', 'text': 'Original harmless input'}],
                'additionalContext': {'original': {'kind': 'untrusted', 'value': 'Original data'}},
            },
        },
    ]
    result = subprocess.run(
        [sys.executable, str(PEER)],
        input=''.join(json.dumps(row) + '\n' for row in messages),
        text=True,
        capture_output=True,
        timeout=2,
        check=False,
        env={**os.environ, 'EDI_TEST_CODEX_PEER_INPUT': str(config)},
    )
    assert result.returncode == 0, 'RPC1 SETUP: ordinary owned peer completes finite input'
    replies = [json.loads(line) for line in result.stdout.splitlines()]
    reply = next(row for row in replies if row.get('id') == 2)
    assert ('result' in reply) == opt_in, (
        'RPC1: actual experimental field is rejected before dispatch unless negotiated'
    )
    if not opt_in:
        assert reply['error'] == {
            'code': -32600,
            'message': method + '.additionalContext requires experimentalApi capability',
        }, 'RPC1: peer enforces the independently pinned dispatcher refusal for both methods'
        assert not any(row.get('method') == 'turn/started' for row in replies), (
            'RPC1: an unnegotiated experimental request never reaches turn admission'
        )


def test_rpc83_real_hello_uses_negotiated_supported_fields_and_completes(generic):
    actor, trace = generic()
    connect(actor)
    actor.command('send_text', text='Hello — original RPC contract control')
    state = settle(
        actor,
        lambda value: (
            bool(value['last_error'])
            or any(row.get('text') == 'Original offline reply' for row in value['messages'])
        ),
    )
    actual = records(trace)
    initialize = next(row for row in actual if row.get('method') == 'initialize')
    started = started_requests(trace)
    assert len(started) == 1, 'RPC1: the original Hello is physically submitted exactly once'
    supplied = started[0]['params'].get('additionalContext') is not None
    assert not supplied or initialize['params'].get('capabilities', {}).get('experimentalApi'), (
        'RPC1: actual supplied experimental context requires genuine initialize opt-in'
    )
    assert (
        state['connected']
        and not state['last_error']
        and any(
            row.get('text') == 'Original offline reply' and row.get('status') == 'completed'
            for row in state['messages']
        )
    ), 'RPC1: strict published request admission completes Hello without an apparent sign-out'
    assert len(users(actor, 'Hello — original RPC contract control')) == 1, (
        'RPC1: successful admission preserves exactly the original public user row'
    )


def rpc83_context_inputs(params):
    found = []
    for item in params.get('input', []):
        if item.get('type') != 'text' or not isinstance(item.get('text'), str):
            continue
        text = item['text']
        for offset, char in enumerate(text):
            if char != '{':
                continue
            try:
                value, _ = json.JSONDecoder().raw_decode(text, offset)
            except ValueError:
                continue
            if isinstance(value, dict) and value.get('schema') == 'edi.assistant.context/1':
                found.append(value)
    return found


@pytest.mark.parametrize('route', ['start', 'steer'])
def test_rpc83_complete_approved_project_context_is_separate_current_user_data(generic, route):
    actor, trace = generic('rpc83:hold')
    opened = actor.command('open', path=str(ROOT / 'tests/fixtures/e04_t1/editable-project'))
    assert opened['reply']['opened'], 'CTX1 SETUP: original project opens through real Session'
    connect(actor)
    expected = actor.last['vm']['context']
    assert expected['project'] is not None and expected['parameters'], (
        'CTX1 SETUP: disclosure includes genuine current project/parameter data'
    )
    # Pinned utils/string truncate.rs uses4 bytes per approximate token. This is
    # its version-specific truncation threshold, not a universal tokenizer claim.
    assert len(json.dumps(expected, ensure_ascii=False, separators=(',', ':')).encode()) > 4000, (
        'CTX1 SETUP: complete original disclosure exceeds pinned additional-context byte budget'
    )
    if actor.last['vm']['context_consent_required']:
        actor.command('sign_in')
    assert not actor.last['vm']['context_consent_required'], (
        'CTX1: actual current disclosure is acknowledged through the existing public action'
    )
    actor.command('send_text', text='Original complete-context initial draft')
    if route == 'steer':
        settle(actor, lambda value: value['can_cancel'] or bool(value['last_error']))
        actor.command('send_text', text='Original complete-context followup draft')
    method = 'turn/' + route
    sent = [row for row in records(trace) if row.get('method') == method]
    assert len(sent) == 1, 'CTX1: actual start or steer reaches its original current wire boundary'
    params = sent[0]['params']
    assert not params.get('additionalContext'), (
        'CTX1: complete project/file data cannot enter privileged or silently truncated fragments'
    )
    assert rpc83_context_inputs(params) == [expected], (
        'CTX1: ordinary user text carries exactly the complete current approved disclosure'
    )
    draft = (
        'Original complete-context ' + ('initial' if route == 'start' else 'followup') + ' draft'
    )
    assert sum(row.get('text') == draft for row in params['input']) == 1, (
        'CTX1: the exact user draft is a separate input once, '
        'never merged into context instructions'
    )
    public = users(actor, draft)
    assert len(public) == 1 and params['clientUserMessageId'] == public[0]['id'], (
        'CTX1: actual once-only input retains the original stable public user identity'
    )
    thread = next(row for row in records(trace) if row.get('method') == 'thread/start')
    assert all(
        'edi.assistant.context/1' not in str(thread['params'].get(field, ''))
        for field in ('developerInstructions', 'baseInstructions')
    ), 'CTX1: project-derived context is not promoted into trusted thread instructions'
    if route == 'steer':
        assert params['expectedTurnId'] == '019a0290-0000-7000-8000-000000000002', (
            'CTX1: admitted followup retains the real active turn, never becomes a new start'
        )
    actor.command('cancel')


@pytest.mark.parametrize('reason', ['no-active', 'review', 'compact'])
def test_rpc83_exact_pre_admission_steer_refusal_preserves_account_and_original(generic, reason):
    actor, trace = generic('rpc83:refuse:' + reason)
    connect(actor)
    actor.command('send_text', text='Original admitted work before definite refusal')
    settle(actor, lambda value: value['can_cancel'] or bool(value['last_error']))
    assert actor.last['vm']['can_cancel'] and not actor.last['vm']['last_error'], (
        'RPC2 SETUP: genuine original turn is admitted before the independent refused followup'
    )
    identity = live_original_peer(actor)
    actor.command('send_text', text='Original definitely refused followup')
    state = settle(actor, lambda value: bool(value['last_error']))
    assert state['connected'] and original_peer_is_live(identity), (
        'RPC2: proven pre-admission refusal retains the genuine authenticated owned process'
    )
    assert 'turn/steer' in state['last_error'] and '-32600' in state['last_error'], (
        'RPC2: bounded refusal identifies actual pending method and numeric structured category'
    )
    assert len(state['last_error'].encode()) <= 512, (
        'RPC2: refusal uses existing bounded diagnostics'
    )
    refused = users(actor, 'Original definitely refused followup')
    assert len(refused) == 1 and refused[0]['status'] not in {'pending', 'completed'}, (
        'RPC2: only its own refused row settles without fabricated successful admission'
    )
    if reason == 'no-active':
        settle(
            actor,
            lambda value: any(
                row.get('text') == 'Original offline reply' for row in value['messages']
            ),
        )
        assert not actor.last['vm']['can_cancel'], (
            'RPC2: genuinely finished original remains settled after delayed steer refusal'
        )
    else:
        assert state['can_cancel'], (
            'RPC2: unrelated admitted original work stays active and stoppable'
        )
        actor.command('cancel')
    assert len(started_requests(trace)) == 1, (
        'RPC2: definite nonadmission never auto-replays input'
    )
    assert sum(row.get('method') == 'turn/steer' for row in records(trace)) == 1, (
        'RPC2: refusal cannot silently retry or convert the followup into another operation'
    )


@pytest.mark.parametrize('variant', ['raw', 'spoof', 'eof'])
def test_rpc83_uncertain_or_unrecognized_failure_remains_private_fenced_and_not_replayed(
    generic, variant
):
    actor, trace = generic('rpc83:unknown:' + variant)
    connect(actor)
    actor.command('send_text', text='Original uncertain prompt must not auto-replay')
    state = settle(actor, lambda value: bool(value['last_error']))
    assert len(state['last_error'].encode()) <= 512 and all(
        secret not in state['last_error']
        for secret in ('ORIGINAL_PRIVATE_PAYLOAD', 'ORIGINAL_PRIVATE_ERROR_DATA')
    ), 'RPC2: arbitrary error text/data and spoofed known prefixes are never exposed'
    for _ in range(3):
        actor.command('inspect')
    assert len(started_requests(trace)) == 1, (
        'RPC2: uncertain/refused/EOF input is never automatically replayed as a new turn'
    )
    assert not any(
        row.get('kind') == 'assistant' and row.get('status') == 'completed'
        for row in actor.last['vm']['messages']
    ), 'RPC2: unknown failure or process loss cannot fabricate a completed response'
    rows = users(actor, 'Original uncertain prompt must not auto-replay')
    assert len(rows) == 1 and rows[0]['status'] != 'completed', (
        'RPC2: uncertain original input remains visible without invented completed admission'
    )


@pytest.mark.parametrize('remove_one', [False, True], ids=['add', 'remove-one-of-two'])
def test_file_selection_context_retirement_preserves_managed_authentication(  # noqa: PLR0914, PLR0915
    generic, tmp_path, remove_one
):
    actor, trace = generic('fileauth')
    connect(actor)
    actor.command('send_text', text='Original retained conversation before file intake')
    before = settle(
        actor,
        lambda value: (
            not value['can_cancel']
            and any(row.get('text') == 'Original fileauth reply 1' for row in value['messages'])
        ),
    )
    identity = live_original_peer(actor)
    assert before['handoff']['account_label'] == 'original@example.invalid' and before['models'], (
        'FILEAUTH SETUP: actual managed account/catalog replies precede file intake'
    )
    retained = {row['id']: row for row in before['messages']}
    auth_methods = {
        'initialize',
        'account/read',
        'model/list',
        'account/login/start',
        'account/logout',
    }
    original_auth = [row for row in records(trace) if row.get('method') in auth_methods]
    original_project = before['project']
    paths = [tmp_path / 'Original-file-alpha.txt', tmp_path / 'Original-file-beta.txt']
    for index, path in enumerate(paths):
        path.write_text(f'Original harmless selected bytes {index}\n')
    request = actor.command('selected_begin')['reply']['request_id']
    admitted = actor.command(
        'selected_add',
        request_id=request,
        urls=[path.as_uri() for path in (paths if remove_one else paths[:1])],
    )
    assert admitted['reply']['accepted'], (
        'FILEAUTH SETUP: actual current file selection admits bytes'
    )
    selected = admitted['vm']['selected_files']
    expected_names = {path.name for path in (paths if remove_one else paths[:1])}
    assert {row['name'] for row in selected} == expected_names, (
        'FILEAUTH: actual selected rows match only the independently planted originals'
    )

    def preserved(state):
        assert (
            state['connected']
            and state['handoff']['account_label'] == before['handoff']['account_label']
        ), 'FILEAUTH: changing selected context preserves the genuine signed-in identity'
        assert state['models'] == before['models'] and (
            state['selected_model'],
            state['selected_effort'],
        ) == (before['selected_model'], before['selected_effort']), (
            'FILEAUTH: original catalog and explicit choices survive selected-file retirement'
        )
        assert original_peer_is_live(identity), (
            'FILEAUTH: context invalidation retains the exact original process identity'
        )
        assert all(row in state['messages'] for row in retained.values()), (
            'FILEAUTH: selected-file changes retain every original conversation row unchanged'
        )
        assert state['project'] == original_project, (
            'FILEAUTH: selecting files does not mutate project'
        )
        assert [
            row for row in records(trace) if row.get('method') in auth_methods
        ] == original_auth, (
            'FILEAUTH: no reinitialization, login/logout or account/catalog refresh repairs action'
        )
        assert state['context_consent_required'], (
            'FILEAUTH: changed selected scope requires actual fresh outgoing-context approval'
        )

    preserved(admitted['vm'])
    if remove_one:
        removed = next(row for row in selected if row['name'] == paths[0].name)
        result = actor.command('selected_remove', id=removed['id'])
        assert result['reply']['accepted'], 'FILEAUTH SETUP: remove addresses the actual opaque ID'
        expected_names.remove(paths[0].name)
        assert result['vm']['selected_files'] == [row for row in selected if row != removed], (
            'FILEAUTH: removal preserves the other original selected identity and bytes metadata'
        )
        preserved(result['vm'])
    assert len(started_requests(trace)) == 1, (
        'FILEAUTH: neither add nor remove silently sends or replays any conversation prompt'
    )
    manifest = actor.last['vm']['context']['selected_files']
    assert {row['name'] for row in manifest['files']} == expected_names, (
        'FILEAUTH: actual disclosed outgoing context contains exactly the remaining selection'
    )
    # The real GUI uses this method to acknowledge current context. Authentication
    # and process preservation have already been proved; this cannot repair either.
    actor.command('sign_in')
    assert not actor.last['vm']['context_consent_required'], (
        'FILEAUTH: explicit current-context approval is distinct from a new login'
    )
    text = 'Original fresh user input after file context change'
    actor.command('send_text', text=text)
    after = settle(
        actor,
        lambda value: (
            not value['can_cancel']
            and any(row.get('text') == 'Original fileauth reply 2' for row in value['messages'])
        ),
    )
    assert after['connected'] and original_peer_is_live(identity), (
        'FILEAUTH: the preserved managed connection completes genuine subsequent work'
    )
    sent = started_requests(trace)
    assert len(sent) == 2 and len(users(actor, text)) == 1, (
        'FILEAUTH: actual new input dispatches once with one retained admitted user row'
    )
    wire = json.dumps(sent[-1]['params']['input'], ensure_ascii=False)
    assert wire.count(text) == 1 and all(name in wire for name in expected_names), (
        'FILEAUTH: approved actual new wire includes current selected scope and draft exactly once'
    )
    if remove_one:
        assert paths[0].name not in wire, (
            'FILEAUTH: removed file is absent from new outgoing scope'
        )
    assert all(row in after['messages'] for row in retained.values()), (
        'FILEAUTH: completing new work still retains the original conversation unchanged'
    )
    assert [row for row in records(trace) if row.get('method') in auth_methods] == original_auth, (
        'FILEAUTH: context approval/new work never repairs auth through another account flow'
    )


# Private append proposal only. Uses existing module helpers and no new peer mode.


def test_fileauth_repeated_manual_context_keeps_one_original_pending_interrupt(generic):
    actor, trace = generic('clear:pending-ack')
    assert actor.command('open', path=str(ROOT / 'tests/fixtures/e04_t1/editable-project'))[
        'reply'
    ]['opened'], 'FILEAUTH SETUP: actual original measured project opens'
    connect(actor)
    before = actor.last['vm']
    identity = live_original_peer(actor)
    actor.command('send_text', text='Original active context retirement work')
    settle(
        actor,
        lambda state: (
            state['can_cancel']
            and any(
                row.get('payload', {}).get('id') == 'clear-prior-work' for row in state['messages']
            )
        ),
    )
    parameter = next(
        row
        for row in actor.last['vm']['project']['parameters']
        if row['path'] == 'structure.cell.length_a'
    )
    for step in (1, 2):
        edited = actor.command(
            'manual_value', path=parameter['path'], value=parameter['value'] + step * 0.001
        )
        assert not edited['reply']['error'], 'FILEAUTH: the real manual edit itself commits'
        events = clear_control_events(trace)
        assert any(event['kind'] == 'control-terminal' for event in events), (
            'FILEAUTH SETUP: original terminal arrived while its control remains unsettled'
        )
        assert not any(event['kind'] == 'interrupt-ack' for event in events), (
            'FILEAUTH SETUP: both real revisions occur before original ACK emission'
        )
        assert edited['vm']['connected'] and original_peer_is_live(identity), (
            'FILEAUTH: repeated actual context revision preserves account and original process'
        )
        assert edited['vm']['handoff']['account_label'] == before['handoff']['account_label']
        assert edited['vm']['models'] == before['models']
        current = next(
            row
            for row in edited['vm']['project']['parameters']
            if row['path'] == parameter['path']
        )
        assert current['value'] == parameter['value'] + step * 0.001
    interrupts = [row for row in records(trace) if row.get('method') == 'turn/interrupt']
    active = next(event for event in clear_control_events(trace) if event['kind'] == 'active')
    assert len(interrupts) == 1 and interrupts[0]['params'] == {
        'threadId': active['threadId'],
        'turnId': active['turnId'],
    }, 'FILEAUTH: two real context revisions cannot duplicate or rebind the original interrupt'
    settled = settle(
        actor,
        lambda state: (
            not state['can_cancel']
            and any(event['kind'] == 'interrupt-ack' for event in clear_control_events(trace))
        ),
    )
    assert settled['connected'] and original_peer_is_live(identity)
    assert not any(
        row.get('method') in {'account/login/start', 'account/logout'} for row in records(trace)
    )


def test_fileauth_archive_refusal_preserves_committed_selection_and_manual_revision(
    generic, tmp_path
):
    actor, trace = generic('clear:pending-ack')
    assert actor.command('open', path=str(ROOT / 'tests/fixtures/e04_t1/editable-project'))[
        'reply'
    ]['opened']
    path = tmp_path / 'Original-committed-selected.txt'
    path.write_text('Original immutable selected bytes before storage failure\n')
    token = actor.command('selected_begin')['reply']['request_id']
    admission = actor.command('selected_add', request_id=token, urls=[path.as_uri()])
    assert admission['reply']['accepted']
    connect(actor)
    if actor.last['vm']['context_consent_required']:
        actor.command('sign_in')
    actor.command('send_text', text='Original durable conversation before failed retirement')
    before = settle(
        actor,
        lambda state: (
            state['can_cancel']
            and any(
                row.get('payload', {}).get('id') == 'clear-prior-work' for row in state['messages']
            )
        ),
    )
    assert not before['last_error'], 'FILEAUTH SETUP: no earlier error can mask storage diagnostic'
    assert actor.last['archive']['is_file'] and actor.last['archive']['bytes'] > 0
    archived_hash = actor.last['archive']['sha256']
    barrier = actor.command('persistence_barrier')
    assert barrier['archive']['is_directory'] and (
        barrier['reply']['preserved_sha256'] == archived_hash
    ), 'FILEAUTH SETUP: actual QSaveFile target is blocked and original bytes preserved'
    parameter = next(
        row for row in before['project']['parameters'] if row['path'] == 'structure.cell.length_a'
    )
    edited = actor.command(
        'manual_value', path=parameter['path'], value=parameter['value'] + 0.001
    )
    assert not edited['reply']['error'], (
        'FILEAUTH: archive refusal cannot undo a genuine manual action'
    )
    assert edited['vm']['selected_files'] == before['selected_files'], (
        'FILEAUTH: committed selected identities survive history-publication refusal'
    )
    assert (
        next(
            row
            for row in edited['vm']['project']['parameters']
            if row['path'] == parameter['path']
        )['value']
        == parameter['value'] + 0.001
    )
    assert edited['vm']['last_error'] and len(edited['vm']['last_error'].encode()) <= 512, (
        'FILEAUTH: actual failed retirement remains publicly explained and bounded'
    )
    assert edited['vm']['connected'], 'FILEAUTH: storage refusal does not sign out managed auth'
    settled = settle(
        actor,
        lambda state: (
            not state['can_cancel']
            and any(event['kind'] == 'interrupt-ack' for event in clear_control_events(trace))
        ),
    )
    assert settled['last_error'], (
        'FILEAUTH: public storage failure survives actual original control settlement'
    )
    if settled['context_consent_required']:
        actor.command('sign_in')
    attempted = 'Original input blocked by unresolved publication failure'
    actor.command('send_text', text=attempted)
    assert len(started_requests(trace)) == 1 and not users(actor, attempted), (
        'FILEAUTH: unresolved publication failure cannot admit hidden or unsafe new work'
    )
    assert actor.last['vm']['selected_files'] == before['selected_files']
    assert actor.last['vm']['last_error'], (
        'FILEAUTH: another attempt cannot erase unresolved error'
    )


def test_fileauth_repeated_session_replacement_keeps_original_pending_interrupt(generic, tmp_path):
    original = ROOT / 'tests/fixtures/e04_t1/editable-project'
    replacements = [tmp_path / 'Original-project-B', tmp_path / 'Original-project-C']
    for replacement in replacements:
        shutil.copytree(original, replacement)
        for source in original.rglob('*'):
            if source.is_file():
                assert (
                    replacement / source.relative_to(original)
                ).read_bytes() == source.read_bytes()
    actor, trace = generic('clear:pending-ack')
    assert actor.command('open', path=str(original))['reply']['opened']
    connect(actor)
    before = actor.last['vm']
    identity = live_original_peer(actor)
    actor.command('send_text', text='Original active work before genuine Session replacement')
    settle(
        actor,
        lambda state: (
            state['can_cancel']
            and any(
                row.get('payload', {}).get('id') == 'clear-prior-work' for row in state['messages']
            )
        ),
    )
    original_start = started_requests(trace)[0]
    for replacement in replacements:
        changed = actor.command('open', path=str(replacement))
        assert changed['reply']['opened'], (
            'FA1 SETUP: Session.openProject admits each distinct real project replacement; '
            'a replacement guard refusal leaves the repeated-bind class unqualified'
        )
        current_path = Path(changed['vm']['project']['host_snapshot']['path']).resolve()
        assert current_path == replacement.resolve(), (
            'FA1 SETUP: actual replacement becomes current project, not a same-path no-op'
        )
        events = clear_control_events(trace)
        assert any(event['kind'] == 'control-terminal' for event in events)
        assert not any(event['kind'] == 'interrupt-ack' for event in events), (
            'FA1 SETUP: both actual binds occur before original control ACK emission'
        )
        assert changed['vm']['connected'] and original_peer_is_live(identity), (
            'FA1: genuine repeated Session bind retains managed account and original process'
        )
        assert changed['vm']['handoff']['account_label'] == before['handoff']['account_label']
        assert changed['vm']['models'] == before['models']
        interrupts = [row for row in records(trace) if row.get('method') == 'turn/interrupt']
        active = next(event for event in events if event['kind'] == 'active')
        assert len(interrupts) == 1 and interrupts[0]['params'] == {
            'threadId': original_start['params']['threadId'],
            'turnId': active['turnId'],
        }, 'FA1: each bind keeps the single interrupt proof bound to its original operation'
    state = settle(
        actor,
        lambda state: (
            not state['can_cancel']
            and any(event['kind'] == 'interrupt-ack' for event in clear_control_events(trace))
        ),
    )
    assert state['connected'] and original_peer_is_live(identity)
    assert len(started_requests(trace)) == 1, (
        'FA1: replacing context never silently replays user work'
    )
    assert not any(
        row.get('method') in {'account/login/start', 'account/logout'} for row in records(trace)
    )


# Actual report authority is supplied by genuine default Session rows, never seeded history.
def report_prepared(generic, variant='complete'):
    actor, trace = generic('report:' + variant)
    assert actor.command('open', path=str(ROOT / 'tests/fixtures/e04_t1/editable-project'))[
        'reply'
    ]['opened'], 'REPORT SETUP: original complete project is the real current owner'
    observer = actor.last['vm']['report_observer']
    assert observer['method_present'], 'REPORT SETUP: actual openReport public method exists'
    config_path = trace.parent / 'peer-input.json'
    config = json.loads(config_path.read_text())
    config['report_limits'] = observer['limits']
    config_path.write_text(json.dumps(config))
    control = actor.command('desktop_control')
    assert control['reply']['ok'] and control['vm']['report_observer']['urls'] == [
        control['reply']['control_url']
    ], 'REPORT SETUP: unrelated actual Qt URL dispatch reaches the no-browser observer'
    actor.command('report_observer_reset')
    connect(actor)
    actor.command('send_text', text='Original report-producing user input')
    settle(
        actor,
        lambda value: (
            (variant == 'forged' and (value['last_error'] or not value['connected']))
            or any(
                (
                    row.get('kind') == 'assistant'
                    and '[Original HTML report]' in row.get('text', '')
                    and (variant == 'unfinished' or row.get('status') == 'completed')
                )
                for row in value['messages']
            )
        ),
    )
    record = json.loads(trace.with_suffix('.report.json').read_text())
    row = next(
        (
            row
            for row in actor.last['vm']['messages']
            if row.get('kind') == 'assistant' and '[Original HTML report]' in row.get('text', '')
        ),
        None,
    )
    assert (variant == 'forged' or (row and row['id'])) and record['cwd']
    assert len(started_requests(trace)) == 1
    assert not actor.last['vm']['report_observer']['urls'], 'REPORT: no automatic viewer dispatch'
    return actor, trace, row, record


def report_opened(actor, row, record, which='href'):
    before = actor.last['vm']
    opened = actor.command('open_report', row_id=row['id'], href=record[which])
    assert opened['reply']['method_present'] and opened['reply']['invoked']
    state = settle(
        actor,
        lambda value: (
            bool(value['report_observer']['urls'])
            or bool(value['last_error'] or value['handoff']['last_error'])
        ),
    )
    urls = state['report_observer']['urls']
    assert len(urls) == 1, 'REPORT: actual completed-row capability dispatches exactly one viewer'
    parsed = urlparse(urls[0])
    assert parsed.scheme == 'file' and not parsed.netloc
    copied = Path(unquote(parsed.path))
    assert copied.is_file() and not copied.is_symlink()
    assert not copied.resolve().is_relative_to(Path(record['cwd']).resolve()), (
        'REPORT: actual opened artifact is a host snapshot outside mutable runtime workspace'
    )
    assert (
        hashlib.sha256(copied.read_bytes()).hexdigest() == record['files'][record[which]]['sha256']
    ), 'REPORT: original report bytes are exact even if later workspace was retired'
    assert state['connected'] and state['models'] == before['models']
    assert state['messages'] == before['messages'], 'REPORT: opening never rewrites conversation'
    return copied


@pytest.mark.parametrize('which', ['href', 'pdf_href'], ids=['html-assets', 'pdf'])
def test_report_completed_original_dispatches_bounded_snapshot(generic, which):
    actor, _, row, record = report_prepared(generic)
    copied = report_opened(actor, row, record, which)
    if which == 'href':
        for name in ('style.css', 'pixel.png'):
            assert (copied.parent / name).read_bytes() == (
                Path(record['cwd']) / Path(record['href']).parent / name
            ).read_bytes(), 'REPORT: safe original relative assets stay complete in the snapshot'
    preserved = copied.read_bytes()
    (Path(record['cwd']) / record[which]).write_text('Late original workspace mutation')
    assert copied.read_bytes() == preserved, (
        'REPORT: later workspace writes cannot change snapshot'
    )


@pytest.mark.parametrize(
    'variant',
    [
        'unknown-row',
        'unfinished',
        'missing',
        'traversal',
        'symlink',
        'asset-symlink',
        'external',
        'absolute',
        'scheme',
    ],
)
def test_report_untrusted_or_incomplete_target_refuses_without_viewer(generic, variant):
    actor, trace, row, record = report_prepared(
        generic, 'complete' if variant == 'unknown-row' else variant
    )
    before = actor.last['vm']
    original = live_original_peer(actor)
    target_row = 'original-unknown-row' if variant == 'unknown-row' else row['id']
    actor.command('open_report', row_id=target_row, href=record['href'])
    state = settle(
        actor,
        lambda value: (
            bool(value['report_observer']['urls'])
            or bool(value['last_error'] or value['handoff']['last_error'])
        ),
    )
    assert not state['report_observer']['urls'], 'REPORT: rejected target never reaches any viewer'
    explanation = state['last_error'] or state['handoff']['last_error']
    assert explanation and len(explanation.encode()) <= 512
    assert state['connected'] and original_peer_is_live(original)
    assert state['messages'] == before['messages'] and state['project'] == before['project']
    assert state['models'] == before['models']
    assert not any(
        value.get('method') in {'account/login/start', 'account/logout'}
        for value in records(trace)
    ), 'REPORT: refusing a target never repairs auth'


@pytest.mark.parametrize(
    'variant', ['file-bytes', 'asset-count', 'collection-bytes', 'name-bytes']
)
def test_report_existing_public_resource_limits_refuse_before_viewer(generic, variant):
    actor, _, row, record = report_prepared(generic, variant)
    limits = actor.last['vm']['report_observer']['limits']
    original = Path(record['cwd']) / record['href']
    if variant == 'file-bytes':
        assert original.stat().st_size == limits['file_bytes'] + 1
    elif variant == 'name-bytes':
        assert len(record['href'].encode()) > limits['name_bytes']
    else:
        referenced = [original] + sorted(original.parent.glob('original-*.css'))
        if variant == 'asset-count':
            assert len(referenced) > limits['files']
        else:
            assert all(path.stat().st_size <= limits['file_bytes'] for path in referenced)
            assert sum(path.stat().st_size for path in referenced) > limits['collection_bytes']
    before = actor.last['vm']
    actor.command('open_report', row_id=row['id'], href=record['href'])
    state = settle(
        actor,
        lambda value: (
            bool(value['report_observer']['urls'])
            or bool(value['last_error'] or value['handoff']['last_error'])
        ),
    )
    assert not state['report_observer']['urls'], 'REPORT: actual over-budget snapshot never opens'
    assert state['last_error'] or state['handoff']['last_error']
    assert state['messages'] == before['messages'] and state['project'] == before['project']
    assert state['connected'], 'REPORT: local quota refusal never signs out managed account'


def test_report_historical_original_provenance_survives_context_but_clear_revokes(
    generic, tmp_path
):
    actor, trace, row, record = report_prepared(generic)
    copied = report_opened(actor, row, record)
    original_bytes = copied.read_bytes()
    actor.command('report_observer_reset')
    selected = tmp_path / 'Original-new-context.txt'
    selected.write_text('Original new selected context, not original report bytes')
    token = actor.command('selected_begin')['reply']['request_id']
    assert actor.command('selected_add', request_id=token, urls=[selected.as_uri()])['reply'][
        'accepted'
    ]
    assert actor.last['vm']['connected'] and row in actor.last['vm']['messages']
    if actor.last['vm']['context_consent_required']:
        actor.command('sign_in')
    actor.command('send_text', text='Original user in the new selected scope')
    settle(
        actor,
        lambda value: (
            not value['can_cancel']
            and any(
                item.get('kind') == 'assistant' and item['id'] != row['id']
                for item in value['messages']
            )
        ),
    )
    latest = json.loads(trace.with_suffix('.report.json').read_text())
    assert latest['cwd'] != record['cwd'], 'REPORT SETUP: later work has a genuinely new workspace'
    again = report_opened(actor, row, record)
    assert again.read_bytes() == original_bytes, 'REPORT: old row uses ORIGINAL trusted provenance'
    actor.command('report_observer_reset')
    actor.command('clear_history')
    settle(actor, lambda value: not value['can_cancel'] and not value['messages'])
    actor.command('open_report', row_id=row['id'], href=record['href'])
    state = settle(
        actor,
        lambda value: (
            bool(value['report_observer']['urls'])
            or bool(value['last_error'] or value['handoff']['last_error'])
        ),
    )
    assert not state['report_observer']['urls'] and not state['messages'], (
        'REPORT: actual Clear revokes original report capability and cannot revive old rows'
    )
    assert state['connected']


@pytest.mark.parametrize('retirement', ['clear', 'context'])
@pytest.mark.parametrize('order', ['ack-first', 'terminal-first'])
def test_healthy_retirement_keeps_pending_steer_rpc_until_known_refusal(
    generic, retirement, order
):
    actor, trace = generic('notice-race:' + retirement + ':' + order)
    assert actor.command('open', path=str(ROOT / 'tests/fixtures/e04_t1/editable-project'))[
        'reply'
    ]['opened']
    connect(actor)
    before = actor.last['vm']
    identity = live_original_peer(actor)
    actor.command('send_text', text='Original admitted turn without durable output')
    settle(actor, itemgetter('can_cancel'))
    actor.command('send_text', text='Original pending steer before healthy retirement')
    settle(
        actor,
        lambda _value: any(
            event['kind'] == 'race-steer-received' for event in clear_control_events(trace)
        ),
    )
    assert not any(row.get('kind') == 'assistant' for row in actor.last['vm']['messages']), (
        'NOTICE SETUP: no durable assistant output can substitute for actual control authority'
    )
    if retirement == 'clear':
        actor.command('clear_history')
    else:
        parameter = next(
            p for p in before['project']['parameters'] if p['path'] == 'structure.cell.length_a'
        )
        assert not actor.command(
            'manual_value', path=parameter['path'], value=parameter['value'] + 0.001
        )['reply']['error']
    state = settle(
        actor,
        lambda value: (
            not value['can_cancel']
            and any(event['kind'] == 'race-refusal' for event in clear_control_events(trace))
        ),
    )
    sequence = [event['kind'] for event in clear_control_events(trace)]
    assert (sequence.index('race-ack') < sequence.index('race-terminal')) == (order == 'ack-first')
    assert sequence.index('race-terminal') < sequence.index('race-refusal')
    assert state['connected'] and original_peer_is_live(identity)
    assert state['handoff']['account_label'] == before['handoff']['account_label']
    assert state['models'] == before['models'] and len(started_requests(trace)) == 1
    if state['context_consent_required']:
        actor.command('sign_in')
    actor.command('send_text', text='Original explicit fresh work after healthy retirement')
    state = settle(
        actor,
        lambda value: (
            not value['can_cancel']
            and any(row.get('text') == 'Original offline reply' for row in value['messages'])
        ),
    )
    assert state['connected'] and len(started_requests(trace)) == 2, (
        'NOTICE: exact known nonadmission settles owned RPCs without logout or automatic replay'
    )
    assert not any(
        value.get('method') in {'account/login/start', 'account/logout'}
        for value in records(trace)
    )


# Native bridge acceptance: original fixture/prestate is the scientific oracle.
def native_records(trace, suffix):
    path = trace.with_suffix(suffix)
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def native_case(generic, calls, *, project=None, hold=False, script=None, connect_now=True):
    actor, trace = generic('native:original')
    if project is not None:
        owned_project = trace.parent / 'original-owned-project'
        shutil.copytree(project, owned_project)
        assert actor.command('open', path=str(owned_project))['reply']['opened'], (
            'NATIVE SETUP: owned copy of genuine complete committed project opens '
            'through actual Session'
        )
    config_path = trace.parent / 'peer-input.json'
    config = json.loads(config_path.read_text())
    config.update(
        native_calls=calls(actor.last['vm']) if callable(calls) else calls,
        native_hold_after_calls=hold,
    )
    config.update(script or {})
    config_path.write_text(json.dumps(config))
    if connect_now:
        connect(actor)
        if actor.last['vm']['context_consent_required']:
            assert not json.loads(actor.last['vm']['native_context']).get('error'), (
                'NATIVE SETUP: outgoing approval applies to complete actual disclosure, '
                'never error JSON'
            )
            actor.command(
                'sign_in'
            )  # Existing actual GUI outgoing approval while already authenticated.
    return actor, trace


def native_call(tool, **arguments):
    return {
        'tool': tool,
        'arguments': {'purpose': 'Original bounded native operation', **arguments},
    }


def native_send(actor, trace, count):
    actor.command('send_text', text='Inspect and perform the original bounded native project task')
    state = settle(
        actor,
        lambda value: (
            len(native_records(trace, '.native-replies.jsonl')) >= count
            or bool(value['last_error'])
            or not value['connected']
        ),
    )
    replies = native_records(trace, '.native-replies.jsonl')
    assert len(replies) == count, (
        'NATIVE: each genuine reverse RPC settles on its original envelope'
    )
    assert not native_records(trace, '.native-wrong-envelope.jsonl'), (
        'NATIVE: call identity is never substituted for original JSON-RPC response identity'
    )
    for index, reply in enumerate(replies, 1):
        assert reply['response']['id'] == reply['original']['id'], 'NATIVE: native send'
        assert reply['response']['id'] != reply['original']['params']['callId'], (
            'NATIVE: native send'
        )
        result = reply['response'].get('result')
        assert isinstance(result, dict) and type(result.get('success')) is bool, (
            'NATIVE: native send'
        )
        contents = result.get('contentItems')
        assert isinstance(contents, list) and len(contents) == 1, 'NATIVE: native send'
        assert contents[0]['type'] == 'inputText' and isinstance(contents[0]['text'], str), (
            'NATIVE: native send'
        )
        decoded = json.loads(contents[0]['text'])
        reply['decoded'] = decoded
        assert decoded is not None and index <= count, 'NATIVE: native send'
    return state, replies


def native_parameter(state, path='structure.cell.length_a'):
    matches = [row for row in state['project']['parameters'] if row['path'] == path]
    assert len(matches) == 1, 'NATIVE SETUP: independently named actual scalar is unambiguous'
    return matches[0]


def native_inputs(state):
    return state['project']['host_snapshot']['experiments']


def test_native125_registered_reads_use_original_rpc_and_retained_purpose(generic):
    calls = [native_call(name) for name in ('inspect_project', 'list_parameters', 'diagnostics')]
    actor, trace = native_case(
        generic, calls, project=ROOT / 'tests/fixtures/e04_t1/editable-project'
    )
    before = actor.last['vm']
    state, replies = native_send(actor, trace, 3)
    registered = next(
        row['params'] for row in records(trace) if row.get('method') == 'thread/start'
    )
    tools = registered.get('dynamicTools')
    assert isinstance(tools, list), 'NATIVE: actual thread declares supported dynamic native tools'
    assert {tool['name'] for tool in tools} == {
        'inspect_project',
        'list_parameters',
        'diagnostics',
        'set_parameters',
        'set_free',
        'run_fit',
        'create_cwl_project',
        'add_relations',
        'save_project',
        'edit_background',
    }, 'NATIVE: this declared background increment advertises exactly ten wired capabilities'
    initialize = next(row['params'] for row in records(trace) if row.get('method') == 'initialize')
    assert initialize['capabilities']['experimentalApi'] is True, (
        'NATIVE: registered reads use original rpc and retained purpose'
    )
    assert all(reply['response']['result']['success'] for reply in replies), (
        'NATIVE: registered reads use original rpc and retained purpose'
    )
    assert 'native_state' in replies[0]['decoded'], (
        'NATIVE: registered reads use original rpc and retained purpose'
    )
    assert isinstance(replies[0]['decoded']['native_state']['calculating'], bool), (
        'NATIVE: registered reads use original rpc and retained purpose'
    )
    assert isinstance(replies[0]['decoded']['native_state']['fitting'], bool), (
        'NATIVE: registered reads use original rpc and retained purpose'
    )
    assert isinstance(replies[1]['decoded']['parameters'], list), (
        'NATIVE: registered reads use original rpc and retained purpose'
    )
    assert 'diagnostics' in replies[2]['decoded'], (
        'NATIVE: registered reads use original rpc and retained purpose'
    )
    assert state['project'] == before['project'], (
        'NATIVE: read tools do not mutate scientific model'
    )
    assert (
        state['connected'] and state['models'] == before['models'] and not state['pending_plan']
    ), 'NATIVE: registered reads use original rpc and retained purpose'
    for call in calls:
        assert any(
            row.get('payload', {}).get('arguments') == call['arguments']
            for row in state['messages']
        ), 'NATIVE: actual activity retains the original purpose and literal arguments'


@pytest.mark.parametrize('tool', ['set_parameters', 'set_free'])
def test_native125_actual_editor_batch_is_undoable_and_keeps_managed_account(generic, tool):
    original = ROOT / 'tests/fixtures/e04_t1/editable-project'

    # Two independent original fixture fields exercise ONE recorded value batch;
    # cubic followers may change legitimately, so restoration compares the full model.
    value_paths = ('structure.cell.length_a', 'experiment.instrument.setup_wavelength')

    def calls(before):
        scalar = native_parameter(before)
        assert scalar['independent'], (
            'NATIVE SETUP: actual independent scalar, not dependent override'
        )
        if tool == 'set_parameters':
            fields = [native_parameter(before, path) for path in value_paths]
            assert all(row['independent'] for row in fields), (
                'NATIVE SETUP: both originally exposed physical fields are independent'
            )
            assert all(row['value'] > 0 for row in fields), (
                'NATIVE SETUP: original positive cell/wavelength domains are preserved'
            )
            arguments = {
                'values': [
                    {'path': row['path'], 'value': row['value'] + delta}
                    for row, delta in zip(fields, (0.01, 0.001), strict=True)
                ]
            }
        else:
            arguments = {'flags': [{'path': scalar['path'], 'free': not scalar['free']}]}
        return [native_call(tool, **arguments)]

    actor, trace = native_case(generic, calls, project=original, hold=True)
    scalar = native_parameter(actor.last['vm'])
    before = actor.last['vm']
    identity = live_original_peer(actor)
    state, replies = native_send(actor, trace, 1)
    assert replies[0]['response']['result']['success'], (
        'NATIVE: admitted valid edit reaches actual editor'
    )
    if tool == 'set_parameters':
        for path, delta in zip(value_paths, (0.01, 0.001), strict=True):
            assert (
                native_parameter(state, path)['value']
                == native_parameter(before, path)['value'] + delta
            ), 'NATIVE: BOTH independent values in one actual batch are adopted'
        assert [row['free'] for row in state['project']['parameters']] == [
            row['free'] for row in before['project']['parameters']
        ], 'NATIVE: value batch preserves all actual free flags'
        assert [
            row
            for row in state['project']['parameters']
            if row['independent'] and row['path'] not in value_paths
        ] == [
            row
            for row in before['project']['parameters']
            if row['independent'] and row['path'] not in value_paths
        ], 'NATIVE: value batch preserves unrelated independent parameter state'
    else:
        assert native_parameter(state)['free'] == (not scalar['free']), (
            'NATIVE: actual editor batch is undoable and keeps managed account'
        )
    assert state['project']['native_observer']['can_undo'], (
        'NATIVE: actual editor batch is undoable and keeps managed account'
    )
    assert native_inputs(state) == native_inputs(before), (
        'NATIVE: actual editor batch is undoable and keeps managed account'
    )
    restored = actor.command('native_undo')
    assert restored['reply']['was_available'], (
        'NATIVE: actual editor batch is undoable and keeps managed account'
    )
    assert restored['vm']['project']['parameters'] == before['project']['parameters'], (
        'NATIVE: genuine normal project Undo restores original values and free flags'
    )
    assert (
        restored['vm']['project']['native_observer']['can_undo']
        == before['project']['native_observer']['can_undo']
    ), 'NATIVE: ONE normal Undo consumes the whole value batch, not only its last member'
    assert restored['vm']['connected'] and original_peer_is_live(identity), (
        'NATIVE: actual editor batch is undoable and keeps managed account'
    )
    assert restored['vm']['handoff']['account_label'] == before['handoff']['account_label'], (
        'NATIVE: actual editor batch is undoable and keeps managed account'
    )
    assert restored['vm']['models'] == before['models'] and not restored['vm']['pending_plan'], (
        'NATIVE: actual editor batch is undoable and keeps managed account'
    )
    assert not any(
        row.get('method') in {'account/login/start', 'account/logout'} for row in records(trace)
    ), 'NATIVE: actual editor batch is undoable and keeps managed account'


@pytest.mark.parametrize(
    'variant',
    [
        'missing-purpose',
        'long-purpose',
        'unknown-outer',
        'duplicate-path',
        'late-invalid',
        'physical-domain',
        'dependent',
        'forged-receipt',
    ],
)
def test_native125_refused_batch_never_partially_mutates_real_project(generic, variant):
    path = 'structure.cell.length_a'
    args = {'purpose': 'Original explicit bounded edit', 'values': [{'path': path, 'value': 3.89}]}
    if variant == 'missing-purpose':
        args.pop('purpose')
    elif variant == 'long-purpose':
        args['purpose'] = 'Original ' + 'x' * 121
    elif variant == 'unknown-outer':
        args['unexpected'] = 'Original unknown field'
    elif variant == 'duplicate-path':
        args['values'].append({'path': path, 'value': 3.90})
    elif variant == 'late-invalid':
        args['values'].append({'path': 'original.absent.parameter', 'value': 4.0})
    elif variant == 'physical-domain':
        args['values'].append({'path': 'structure.cell.angle_alpha', 'value': -90.0})
    elif variant == 'dependent':
        args['values'].append({'path': 'structure.cell.length_b', 'value': 4.0})
    else:
        args['request_receipt'] = {'objective': 'Provider invented unbounded authority'}
    actor, trace = native_case(
        generic,
        [{'tool': 'set_parameters', 'arguments': args}],
        project=ROOT / 'tests/fixtures/e04_t1/editable-project',
    )
    before = actor.last['vm']
    state, replies = native_send(actor, trace, 1)
    assert not replies[0]['response']['result']['success'], (
        'NATIVE: invalid whole batch is refused'
    )
    assert state['project'] == before['project'], (
        'NATIVE: invalid later member, physical/dependent or scope error preserves the model'
    )
    assert state['connected'] and state['models'] == before['models'], (
        'NATIVE: refused batch never partially mutates real project'
    )


@pytest.mark.parametrize('binding', ['thread_id', 'turn_id'])
def test_native125_foreign_binding_never_uses_current_project_authority(generic, binding):
    call = native_call(
        'set_parameters', values=[{'path': 'structure.cell.length_a', 'value': 3.90}]
    )
    call[binding] = '019a0290-0000-7000-8000-000000000099'
    actor, trace = native_case(
        generic, [call], project=ROOT / 'tests/fixtures/e04_t1/editable-project'
    )
    before = actor.last['vm']['project']
    actor.command('send_text', text='Original current owner, not a foreign native call')
    state = settle(
        actor,
        lambda value: (
            bool(value['last_error'])
            or not value['connected']
            or bool(native_records(trace, '.native-replies.jsonl'))
        ),
    )
    assert state['project'] == before, (
        'NATIVE: foreign thread/turn cannot borrow current-project authority'
    )
    for reply in native_records(trace, '.native-replies.jsonl'):
        assert not reply.get('response', {}).get('result', {}).get('success'), (
            'NATIVE: foreign reverse RPC can never claim native edit success'
        )


def test_native125_reused_call_identity_cannot_change_second_argument_batch(generic):
    first = native_call(
        'set_parameters', values=[{'path': 'structure.cell.length_a', 'value': 3.89}]
    )
    second = native_call(
        'set_parameters', values=[{'path': 'structure.cell.length_a', 'value': 3.90}]
    )
    first['call_id'] = second['call_id'] = 'original-reused-native-call'
    actor, trace = native_case(
        generic, [first, second], project=ROOT / 'tests/fixtures/e04_t1/editable-project'
    )
    before = actor.last['vm']
    actor.command('send_text', text='Original one native edit; do not repeat it')
    state = settle(
        actor,
        lambda value: (
            bool(value['last_error'])
            or not value['connected']
            or len(native_records(trace, '.native-replies.jsonl')) == 2
        ),
    )
    replies = native_records(trace, '.native-replies.jsonl')
    assert replies and replies[0]['response']['result']['success'], (
        'NATIVE: reused call identity cannot change second argument batch'
    )
    assert native_parameter(state)['value'] == 3.89, (
        'NATIVE: reused immutable call identity cannot authorize changed second arguments'
    )
    assert native_inputs(state) == native_inputs(before), (
        'NATIVE: reused call identity cannot change second argument batch'
    )


@pytest.mark.parametrize(
    'project_path',
    ['docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project', 'tests/fixtures/e04_t5/joint'],
)
def test_native125_real_worker_result_is_published_before_reverse_rpc_success(
    generic, project_path
):
    calls = [native_call('run_fit')]
    actor, trace = native_case(generic, calls, project=ROOT / project_path)
    before = actor.last['vm']
    if project_path.endswith('/joint'):
        assert before['project']['mode'] == 'joint' and len(native_inputs(before)) == 2, (
            'NATIVE FIT SETUP: genuine independent two-experiment joint input, not '
            'cloned single-fit output'
        )
    assert before['project']['native_observer']['fit_available'], (
        'NATIVE FIT SETUP: genuine linked backend is available, with no fake/no-step substitute'
    )
    state, replies = native_send(actor, trace, 1)
    result = replies[0]['decoded']
    assert result['status'] in {'done', 'max_iterations'}, (
        'NATIVE FIT SETUP: genuine adopted moving fit, not unavailable/error/cancel/no-step'
    )
    assert result['adopted'] and type(result['converged']) is bool, (
        'NATIVE: real worker result is published before reverse rpc success'
    )
    observer = state['project']['native_observer']
    assert not observer['fit_running'] and observer['record']['kind'], (
        'NATIVE: real worker result is published before reverse rpc success'
    )
    assert observer['record']['iterations'] == result['iterations'] > 0, (
        'NATIVE: real worker result is published before reverse rpc success'
    )
    assert observer['record']['success'] == result['converged'], (
        'NATIVE: real worker result is published before reverse rpc success'
    )
    assert observer['fit_results'] and observer['fit_can_undo'], (
        'NATIVE FIT: actual record and normal fit Undo are published before answering the model'
    )
    assert state['project']['parameters'] != before['project']['parameters'], (
        'NATIVE FIT SETUP: actual optimizer changes parameters, with no cached/no-step witness'
    )
    assert native_inputs(state) == native_inputs(before), (
        'NATIVE: real worker result is published before reverse rpc success'
    )
    assert state['connected'] and not state['pending_plan'], (
        'NATIVE: real worker result is published before reverse rpc success'
    )


@pytest.mark.parametrize('retirement', ['stop', 'manual', 'replace'])
def test_native125_actual_running_fit_retirement_cannot_publish_into_obsolete_owner(
    generic, retirement
):
    actor, trace = native_case(
        generic,
        [native_call('run_fit')],
        project=ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project',
    )
    before = actor.last['vm']
    actor.command(
        'send_text', text='Run the original native fit with normal Stop and owner fences'
    )
    state = settle(
        actor,
        lambda value: (
            value['project']['native_observer']['fit_running']
            or bool(native_records(trace, '.native-replies.jsonl'))
            or bool(value['last_error'])
        ),
    )
    assert state['project']['native_observer']['fit_running'], (
        'NATIVE FIT SETUP: worker is still running at retirement, not already completed'
    )
    if retirement == 'replace':
        replaced = actor.command('open', path=str(ROOT / 'tests/fixtures/e04_t1/editable-project'))
        assert replaced['reply']['opened'], (
            'NATIVE FIT SETUP: real Session admits replacement while the old worker retires'
        )
        expected = replaced['vm']['project']['parameters']
    elif retirement == 'manual':
        target = native_parameter(state)
        attempted = actor.command(
            'manual_value', path=target['path'], value=target['value'] + 0.01
        )
        assert attempted['reply']['fit_running_at_entry'], (
            'NATIVE FIT SETUP: ordinary edit reached a genuinely running fit, not a stale snapshot'
        )
        assert attempted['reply']['error'], (
            'ADR0020: ordinary manual edits are lawfully refused while a fit runs'
        )
        assert attempted['reply']['parameters_after'] == attempted['reply']['parameters_before'], (
            'ADR0020: refused concurrent manual edit writes nothing'
        )
        settled = settle(
            actor,
            lambda value: (
                not value['project']['native_observer']['fit_running'] and not value['can_cancel']
            ),
        )
        assert native_inputs(settled) == native_inputs(before), (
            'NATIVE: lawful readonly fit preserves genuine observations and exclusions'
        )
        target = native_parameter(settled)
        admitted = actor.command('manual_value', path=target['path'], value=target['value'] + 0.01)
        assert not admitted['reply']['fit_running_at_entry'] and not admitted['reply']['error'], (
            'ADR0020: normal actual manual edit is admitted AFTER real fit settlement'
        )
        assert native_parameter(admitted['vm'])['value'] == target['value'] + 0.01, (
            'NATIVE: real post-settlement edit is visible, not a forced concurrent core write'
        )
        expected = admitted['vm']['project']['parameters']
        # Concurrent manual supersession is unqualified: the ordinary app rejects it.
    else:
        actor.command('cancel')
        expected = None
    final = settle(
        actor,
        lambda value: (
            not value['project']['native_observer']['fit_running'] and not value['can_cancel']
        ),
    )
    if expected is not None:
        assert final['project']['parameters'] == expected, (
            'NATIVE FIT: old fit cannot overwrite the replacement or later manual revision'
        )
    else:
        assert final['project']['native_observer']['fit_outcome'] in {'cancelled', 'stopped'}, (
            'NATIVE FIT: real Stop cancels the actual fit, beyond model-turn cancellation'
        )
        # Same-owner CANCELLED may adopt a partial result under FitReport's public policy.
        assert native_inputs(final) == native_inputs(before), (
            'NATIVE: actual running fit retirement cannot publish into obsolete owner'
        )
    assert final['connected'] and final['models'] == before['models'], (
        'NATIVE: actual running fit retirement cannot publish into obsolete owner'
    )
    assert len(started_requests(trace)) == 1, (
        'NATIVE FIT: no automatic retry of retired fitting work'
    )


@pytest.mark.parametrize('tool', ['set_parameters', 'create_project'])
def test_native125_no_current_project_or_unwired_capability_cannot_mint_authority(generic, tool):
    args = (
        {'values': [{'path': 'structure.cell.length_a', 'value': 3.90}]}
        if tool == 'set_parameters'
        else {}
    )
    actor, trace = native_case(generic, [native_call(tool, **args)])
    assert not actor.last['vm']['project_present'], (
        'NATIVE: no current project or unwired capability cannot mint authority'
    )
    actor.command('send_text', text='Original projectless input has no existing project to mutate')
    state = settle(
        actor,
        lambda value: (
            bool(value['last_error'])
            or not value['connected']
            or bool(native_records(trace, '.native-replies.jsonl'))
        ),
    )
    assert not state['project_present'], (
        'NATIVE: provider cannot create project or borrow absent-project authority'
    )
    for reply in native_records(trace, '.native-replies.jsonl'):
        assert not reply['response'].get('result', {}).get('success'), (
            'NATIVE: unregistered or ownerless operation never claims native execution success'
        )


# Review144/146 siblings use ordinary published messages and actual owners.
@pytest.mark.parametrize('order', ['start-late', 'steers-reversed'])
def test_native129_reordered_real_admissions_keep_current_user_ids_and_native_actions(
    generic, order
):
    call = native_call(
        'set_parameters', values=[{'path': 'structure.cell.length_a', 'value': 3.91}]
    )
    actor, trace = native_case(
        generic,
        [],
        hold=True,
        project=ROOT / 'tests/fixtures/e04_t1/editable-project',
        script={'native_ack_order': order, 'native_after_steer': [call]},
    )
    actor.command('send_text', text='Original initial native objective')
    settle(actor, itemgetter('can_cancel'))
    objectives = ['Original intermediate bounded objective', 'Original LATEST bounded objective']
    for text in objectives:
        actor.command('send_text', text=text)
    state = settle(
        actor,
        lambda value: (
            bool(native_records(trace, '.native-replies.jsonl'))
            or bool(value['last_error'])
            or not value['connected']
        ),
    )
    steers = [record for record in records(trace) if record.get('method') == 'turn/steer']
    assert len(steers) == 2, 'N1 SETUP: both genuine inputs reach the published steer channel'
    events = clear_control_events(trace)
    ack = [event['id'] for event in events if event['kind'] == 'native-steer-ack']
    assert ack == [steers[1]['id'], steers[0]['id']], (
        'N1 SETUP: actual newer ACK precedes older ACK'
    )
    if order == 'start-late':
        kinds = [event['kind'] for event in events]
        assert kinds.index('native-old-start-ack') > kinds.index('native-steer-ack'), (
            'NATIVE: reordered real admissions keep current user ids and native actions'
        )
    assert all(len(users(actor, text)) == 1 for text in objectives), (
        'NATIVE: reordered real admissions keep current user ids and native actions'
    )
    assert all(
        users(actor, text)[0]['status'] not in {'refused', 'interrupted'} for text in objectives
    ), 'NATIVE: reordered real admissions keep current user ids and native actions'
    assert native_parameter(state)['value'] == 3.91 and state['connected'], (
        'NATIVE: reordered real admissions keep current user ids and native actions'
    )
    assert not state['pending_plan'], (
        'N1: delegated native objective adds no fabricated second approval'
    )
    # No public tool result reveals the private cached objective bytes. Static monotonic-selection
    # review complements these actual admission/currentness/action boundaries.


def test_native129_once_identity_survives_genuine_steer_receipt_replacement(generic):
    first = native_call(
        'set_parameters', values=[{'path': 'structure.cell.length_a', 'value': 3.89}]
    )
    replay = native_call(
        'set_parameters', values=[{'path': 'structure.cell.length_a', 'value': 3.90}]
    )
    first['call_id'] = replay['call_id'] = 'original-once-across-steer'
    actor, trace = native_case(
        generic,
        [first],
        hold=True,
        project=ROOT / 'tests/fixtures/e04_t1/editable-project',
        script={'native_steer_count': 1, 'native_after_steer': [replay]},
    )
    state, _ = native_send(actor, trace, 1)
    assert native_parameter(state)['value'] == 3.89, (
        'NATIVE: once identity survives genuine steer receipt replacement'
    )
    actor.command('send_text', text='Original admitted follow-up, preserving prior call identity')
    state = settle(
        actor,
        lambda value: (
            len(native_records(trace, '.native-replies.jsonl')) >= 2
            or bool(value['last_error'])
            or not value['connected']
        ),
    )
    assert any(row.get('method') == 'turn/steer' for row in records(trace)), (
        'N1 SETUP: genuine steer occurred'
    )
    assert native_parameter(state)['value'] == 3.89, (
        'N1: a new receipt never resurrects an executed call ID'
    )


@pytest.mark.parametrize('field', ['item_namespace', 'rpc_namespace'])
def test_native129_original_and_reverse_rpc_namespaces_must_match(generic, field):
    call = native_call(
        'set_parameters', values=[{'path': 'structure.cell.length_a', 'value': 3.90}]
    )
    call[field] = 'original-foreign-namespace'
    actor, trace = native_case(
        generic, [call], project=ROOT / 'tests/fixtures/e04_t1/editable-project'
    )
    before = actor.last['vm']['project']
    actor.command('send_text', text='Original namespace binding cannot be substituted')
    state = settle(
        actor,
        lambda value: (
            bool(value['last_error'])
            or not value['connected']
            or bool(native_records(trace, '.native-replies.jsonl'))
        ),
    )
    assert state['project'] == before, (
        'N1: either namespace mismatch refuses BEFORE actual native writes'
    )
    for reply in native_records(trace, '.native-replies.jsonl'):
        assert not reply['response'].get('result', {}).get('success'), (
            'NATIVE: original and reverse rpc namespaces must match'
        )


@pytest.mark.parametrize('route', ['item', 'snapshot'])
def test_native129_actual_host_outcome_and_canonical_call_survive_later_provider_claim(
    generic, route
):
    call = native_call(
        'set_parameters', values=[{'path': 'structure.cell.length_a', 'value': 3.89}]
    )
    actor, trace = native_case(
        generic,
        [call],
        project=ROOT / 'tests/fixtures/e04_t1/editable-project',
        script={'native_conflicting_final': route},
    )
    state, replies = native_send(actor, trace, 1)
    assert (
        replies[0]['response']['result']['success'] and native_parameter(state)['value'] == 3.89
    ), 'NATIVE: actual host outcome and canonical call survive later provider claim'
    state = settle(actor, lambda value: not value['can_cancel'] or bool(value['last_error']))
    call_id = replies[0]['original']['params']['callId']
    rows = [
        row
        for row in state['messages']
        if row['kind'] == 'activity'
        and row.get('payload', {}).get('type') == 'dynamicToolCall'
        and row.get('payload', {}).get('id') == call_id
    ]
    assert len(rows) == 1, (
        'N2: actual committed native outcome remains retained once after provider traffic'
    )
    payload = rows[0]['payload']
    assert rows[0]['status'] == 'completed' and payload['nativeOutcome']['status'] == 'edited', (
        'N2: retained public outcome reports the actual successful host edit'
    )
    assert isinstance(payload['nativeOutcome']['calculation_pending'], bool), (
        'N2: asynchronous calculation state remains truthful after native publication'
    )
    assert not state['connected'] and state['last_error'], (
        'N2: contradictory canonical provider identity remains a genuine protocol fence'
    )
    assert payload['tool'] == call['tool'] and payload.get('namespace') is None, (
        'NATIVE: actual host outcome and canonical call survive later provider claim'
    )
    assert payload['arguments'] == call['arguments'], (
        'N2: provider final cannot rewrite canonical native call'
    )
    assert 'Original provider contradicts actual host outcome' not in json.dumps(rows[0]), (
        'N2: provider snapshot text is never substituted for the actual host execution result'
    )


def test_native129_archive_outcome_admission_precedes_any_model_write(generic):
    call = native_call(
        'set_parameters', values=[{'path': 'structure.cell.length_a', 'value': 3.89}]
    )
    actor, trace = native_case(
        generic,
        [call],
        project=ROOT / 'tests/fixtures/e04_t1/editable-project',
        script={'native_delay': True},
    )
    before = actor.last['vm']['project']
    actor.command(
        'send_text', text='Original native edit must retain its own outcome before writing'
    )
    assert actor.last['archive']['is_file'] and actor.last['archive']['bytes'] > 0, (
        'NATIVE: archive outcome admission precedes any model write'
    )
    barrier = actor.command('persistence_barrier')
    assert barrier['archive']['is_directory'], (
        'NATIVE: archive outcome admission precedes any model write'
    )
    assert not any(
        event['kind'] == 'native-call-emitted' for event in clear_control_events(trace)
    ), 'N2 SETUP: real archive barrier precedes the reverse request, after genuine user retention'
    state = settle(
        actor,
        lambda value: (
            bool(value['last_error']) or bool(native_records(trace, '.native-replies.jsonl'))
        ),
    )
    assert state['project'] == before, (
        'N2: failed outcome admission cannot leave unreported native mutation'
    )
    assert state['last_error'], 'N2: actual retention refusal stays visible and bounded'
    assert len(state['last_error'].encode()) <= 512, (
        'NATIVE: archive outcome admission precedes any model write'
    )


def test_native129_foreign_resolved_event_cannot_cancel_actual_running_native_fit(generic):
    actor, trace = native_case(
        generic,
        [native_call('run_fit')],
        project=ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project',
        script={'native_foreign_resolve': True},
    )
    actor.command(
        'send_text', text='Original genuine fit cannot be resolved by foreign thread authority'
    )
    state = settle(
        actor,
        lambda value: (
            value['project']['native_observer']['fit_running']
            or bool(native_records(trace, '.native-replies.jsonl'))
        ),
    )
    assert state['project']['native_observer']['fit_running'], (
        'N1 SETUP: actual native worker is visibly active'
    )
    state = settle(actor, lambda _value: bool(native_records(trace, '.native-replies.jsonl')))
    emitted = [
        event for event in clear_control_events(trace) if event['kind'] == 'native-foreign-resolve'
    ]
    assert emitted and emitted[0]['still_pending'], (
        'N1 SETUP: actual foreign resolution precedes original native settlement'
    )
    reply = native_records(trace, '.native-replies.jsonl')[0]['response']['result']
    outcome = json.loads(reply['contentItems'][0]['text'])
    assert outcome['status'] in {'done', 'max_iterations'} and outcome['adopted'], (
        'N1: a foreign-thread resolved notification cannot cancel the genuine current fit'
    )
    assert state['connected'], (
        'NATIVE: foreign resolved event cannot cancel actual running native fit'
    )


@pytest.mark.parametrize('retirement', ['clear', 'context', 'signout'])
def test_native129_retirement_cancels_real_worker_without_repopulating_retired_rows(
    generic, tmp_path, retirement
):
    actor, trace = native_case(
        generic,
        [native_call('run_fit')],
        project=ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project',
    )
    actor.command('send_text', text='Original real native worker with current-owner retirement')
    running = settle(
        actor,
        lambda value: (
            value['project']['native_observer']['fit_running']
            or bool(native_records(trace, '.native-replies.jsonl'))
        ),
    )
    assert running['project']['native_observer']['fit_running'], (
        'N3 SETUP: real native worker is running before Clear/context/signout, not a '
        'finished stand-in'
    )
    if retirement == 'clear':
        retired = actor.command('clear_history')['vm']
        assert not retired['messages'], 'N3: actual Clear retires visible conversation immediately'
    elif retirement == 'signout':
        retired = actor.command('sign_out')['vm']
        assert not retired['connected'], (
            'N3: real account signout immediately revokes authentication'
        )
    else:
        replacement = tmp_path / 'Original-native-current-project'
        shutil.copytree(ROOT / 'tests/fixtures/e04_t1/editable-project', replacement)
        replaced = actor.command('open', path=str(replacement))
        assert replaced['reply']['opened'], (
            'N3 SETUP: ordinary Session admits a genuine project-context replacement'
        )
        retired = replaced['vm']
    ids = {row['id'] for row in retired['messages']}
    final = settle(
        actor,
        lambda value: (
            not value['project']['native_observer']['fit_running'] and not value['can_cancel']
        ),
    )
    assert {row['id'] for row in final['messages']} <= ids, (
        'N3: late actual native report cannot append into discarded or retired conversation'
    )
    if retirement == 'clear':
        assert not final['messages'] and actor.command('archive')['reply']['rows'] == [], (
            'NATIVE: retirement cancels real worker without repopulating retired rows'
        )
    elif retirement == 'signout':
        assert not final['connected'], (
            'NATIVE: retirement cancels real worker without repopulating retired rows'
        )
    else:
        assert final['connected'] and final['selected_files'] == retired['selected_files'], (
            'NATIVE: retirement cancels real worker without repopulating retired rows'
        )
        assert final['project']['parameters'] == retired['project']['parameters'], (
            'N3: late old fit never rewrites the actual replacement project context'
        )


def test_native129_completed_context_overflow_cannot_approve_error_json_or_admit_work(
    generic, tmp_path
):
    project = tmp_path / 'Original-native-large-context'
    shutil.copytree(ROOT / 'tests/fixtures/e04_t1/editable-project', project)
    bank = project / 'experiments/hrpt.edi'
    text = bank.read_text()
    original = '_excluded_region.end\n1 0. 5.\n2 165. 180.'
    assert text.count(original) == 1, 'N6 SETUP: original documented exclusion loop is unique'
    entries = [{'id': 'owned-' + str(i), 'first': 1.25, 'second': 2.75} for i in range(23000)]
    assert len(json.dumps(entries, separators=(',', ':')).encode()) > 1048576, (
        'N6 SETUP: independent complete exclusion encoding alone exceeds public context_bytes'
    )
    bank.write_text(
        text.replace(
            original,
            '_excluded_region.end\n' + '\n'.join(row['id'] + ' 1.25 2.75' for row in entries),
        )
    )
    actor, trace = native_case(generic, [native_call('inspect_project')])
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'N6 SETUP: genuine manual attachment replaces current context under already real '
        'managed account'
    )
    context = json.loads(actor.last['vm']['native_context'])
    assert context.get('error'), 'N6 SETUP: actual complete context reached bounded refusal'
    actor.command('sign_in')
    state = settle(actor, lambda value: value['connected'] or bool(value['last_error']))
    assert state['connected'], (
        'N6: context refusal does not fabricate or lose genuine managed account'
    )
    before = state['project']
    actor.command(
        'sign_in'
    )  # Actual outgoing disclosure approval method, while genuinely connected.
    actor.command(
        'send_text',
        text='Original work cannot treat refusal JSON as complete approved project data',
    )
    assert not started_requests(trace) and not native_records(trace, '.native-emitted.jsonl'), (
        'N6: context error JSON cannot be silently approved into new context-dependent '
        'model/native work'
    )
    assert actor.last['vm']['project'] == before and actor.last['vm']['last_error'], (
        'NATIVE: completed context overflow cannot approve error json or admit work'
    )


def test_native129_presubmit_busy_refusal_is_distinct_from_admitted_worker_cancellation(generic):
    actor, trace = native_case(
        generic,
        [native_call('run_fit'), native_call('run_fit')],
        project=ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project',
        script={'native_parallel': True},
    )
    actor.command(
        'send_text', text='Original single native fit with one overlapping refused request'
    )
    state = settle(
        actor,
        lambda value: (
            bool(native_records(trace, '.native-replies.jsonl')) or bool(value['last_error'])
        ),
    )
    assert state['project']['native_observer']['fit_running'], (
        'N3 SETUP: genuine first worker is still active when second reverse request settles'
    )
    replies = native_records(trace, '.native-replies.jsonl')
    assert len(replies) == 1, 'N3: an admitted running fit cannot answer before its actual report'
    refused = json.loads(replies[0]['response']['result']['contentItems'][0]['text'])
    assert refused['status'] in {'busy', 'refused'} and not refused.get('adopted', False), (
        'N3: pre-submit refusal is not represented as cancellation/adoption of the running worker'
    )
    actor.command('cancel')
    state = settle(
        actor,
        lambda value: (
            not value['project']['native_observer']['fit_running'] and not value['can_cancel']
        ),
    )
    replies = native_records(trace, '.native-replies.jsonl')
    assert len({row['original']['id'] for row in replies}) == len(replies) <= 2, (
        'N3: original busy and admitted-fit envelopes can never settle more than once'
    )
    assert state['project']['native_observer']['fit_outcome'] in {'cancelled', 'stopped'}, (
        'N3: normal Stop reaches actual final worker outcome, beyond a running-false or '
        'turn-only proxy'
    )
    if len(replies) == 2:
        outcomes = [
            json.loads(row['response']['result']['contentItems'][0]['text']) for row in replies
        ]
        assert any(row['status'] == 'cancelled' for row in outcomes), (
            'N3: still-owned admitted-fit response truthfully reports actual cancellation'
        )
    else:
        assert matching_interrupt(trace), (
            'N3: intentionally retired RPC requires genuine turn retirement, never fake settlement'
        )
    assert state['connected'], 'N3: ordinary own cancellation preserves managed account'


@pytest.mark.parametrize('channel', ['logout', 'eof'])
def test_native129_retired_fit_handle_does_not_block_fresh_authenticated_native_work(
    generic, channel
):
    actor, trace = native_case(
        generic,
        [native_call('run_fit')],
        project=ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project',
        script={'native_exit_while_running': channel == 'eof'},
    )
    actor.command('send_text', text='Original native worker whose process/account will retire')
    state = settle(
        actor,
        lambda value: (
            value['project']['native_observer']['fit_running']
            or bool(native_records(trace, '.native-replies.jsonl'))
            or not value['connected']
        ),
    )
    assert state['project']['native_observer']['fit_running'], (
        'N3-R SETUP: genuine worker active before original logout/process EOF, not a '
        'finished stand-in'
    )
    old = native_records(trace, '.native-emitted.jsonl')[0]
    if channel == 'logout':
        actor.command('sign_out')
    state = settle(
        actor,
        lambda value: (
            not value['connected'] and not value['project']['native_observer']['fit_running']
        ),
    )
    assert not state['connected'], (
        'N3-R: process/account retirement revokes old authenticated work'
    )
    assert not any(
        row['response']['id'] == old['id']
        for row in native_records(trace, '.native-replies.jsonl')
    ), 'N3-R: retired reverse RPC never answers on original or a replacement process'
    if channel == 'logout':
        assert any(row.get('method') == 'account/logout' for row in records(trace)), (
            'N3-R SETUP: real logout was actually sent to original owned peer'
        )
    else:
        assert any(row['kind'] == 'native-original-eof' for row in clear_control_events(trace)), (
            'N3-R SETUP: original process EOF occurred while its original RPC was pending'
        )
    config_path = trace.parent / 'peer-input.json'
    configuration = json.loads(config_path.read_text())
    configuration.update(
        native_calls=[native_call('inspect_project')],
        native_exit_while_running=False,
        native_hold_after_calls=False,
    )
    config_path.write_text(json.dumps(configuration))
    connect(actor)
    if actor.last['vm']['context_consent_required']:
        actor.command(
            'sign_in'
        )  # Genuine connected outgoing-context approval, not account repair.
    previous = len(native_records(trace, '.native-replies.jsonl'))
    actor.command('send_text', text='Original fresh native inspection after genuine reconnection')
    final = settle(
        actor,
        lambda value: (
            len(native_records(trace, '.native-replies.jsonl')) > previous
            or bool(value['last_error'])
        ),
    )
    replies = native_records(trace, '.native-replies.jsonl')
    assert len(replies) == previous + 1 and replies[-1]['response']['result']['success'], (
        'N3-R: a retired finished worker handle cannot block explicit fresh native inspection'
    )
    assert final['connected'], 'N3-R: fresh native work uses real reauthenticated managed account'


def test_native129_real_postfit_storage_failure_settles_then_disconnected_clear_recovers(generic):
    actor, trace = native_case(
        generic,
        [native_call('run_fit')],
        project=ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project',
    )
    actor.command(
        'send_text', text='Original native fit with actual final-publication archive refusal'
    )
    state = settle(
        actor,
        lambda value: (
            value['project']['native_observer']['fit_running']
            or bool(native_records(trace, '.native-replies.jsonl'))
        ),
    )
    assert state['project']['native_observer']['fit_running'], (
        'N4 SETUP: genuine worker admitted before ordinary owned archive barrier'
    )
    assert actor.last['archive']['is_file'], (
        'N4 SETUP: original user/active native rows durably retained'
    )
    actor.command('persistence_barrier')
    assert actor.last['archive']['is_directory'], (
        'N4 SETUP: actual storage refuses replacement now'
    )
    state = settle(
        actor,
        lambda value: (
            not value['project']['native_observer']['fit_running'] and bool(value['last_error'])
        ),
    )
    assert state['last_error'] and len(state['last_error'].encode()) <= 512, (
        'N4: actual final-publication failure is contained and bounded, never exception through Qt'
    )
    actor.command('sign_out')
    settle(actor, lambda value: not value['connected'])
    actor.command('clear_history')
    assert actor.last['vm']['last_error'], (
        'N4-R: genuinely failed disconnected Clear retains honest warning'
    )
    actor.command('persistence_restore')
    actor.command('clear_history')
    assert not actor.last['vm']['messages'], (
        'N4-R: successful real disconnected Clear releases held records'
    )
    config_path = trace.parent / 'peer-input.json'
    config = json.loads(config_path.read_text())
    config['native_calls'] = [native_call('inspect_project')]
    config_path.write_text(json.dumps(config))
    connect(actor)
    if actor.last['vm']['context_consent_required']:
        actor.command('sign_in')
    actor.command('send_text', text='Original new native read after explicit successful recovery')
    final = settle(
        actor,
        lambda value: (
            (bool(native_records(trace, '.native-replies.jsonl')) and not value['can_cancel'])
            or bool(value['last_error'])
        ),
    )
    assert final['connected'] and not final['last_error'], (
        'N4-R: successful disconnected Clear releases sign-in/recovery fence without '
        'hidden provider replay'
    )
    assert any(
        row['original']['params']['tool'] == 'inspect_project'
        and row['response'].get('result', {}).get('success')
        for row in native_records(trace, '.native-replies.jsonl')
    ), 'N4-R: actual newly admitted native work succeeds after explicit storage recovery'


# Usage-v2 root-frozen public projection + pinned protocol; no actual quota/account witness.
def usage_case(generic, *, mode='normal', ui=False, many=False):
    actor, trace = generic('usage:original', ui=ui)
    config_path = trace.parent / 'peer-input.json'
    config = json.loads(config_path.read_text())
    config.update(usage_mode=mode, usage_many=many)
    config_path.write_text(json.dumps(config))
    observed = actor.last['vm']['usage_observer']
    assert observed['property_present'] and observed['refresh_present'], (
        'US SETUP: real default Session exposes accepted read-only usage/refresh surface'
    )
    assert observed['value'] == {'available': False, 'stale': False, 'buckets': []}, (
        'US: no genuine current-account snapshot is honestly unavailable, not zero quota'
    )
    connect(actor)
    return actor, trace


def usage_value(state):
    return state['usage_observer']['value']


def usage_primary(state):
    return [
        window['usedPercent']
        for bucket in usage_value(state)['buckets']
        for window in bucket['windows']
        if window['kind'] == 'primary'
    ]


def test_usage129_bootstrap_automatic_read_delivers_original_result_not_just_request(generic):
    actor, trace = usage_case(generic)
    state = settle(actor, lambda value: usage_value(value)['available'])
    current = usage_value(state)
    assert not current['stale'] and usage_primary(state) == [17], (
        'US1R: automatic optional read actually reaches VM after complete required bootstrap'
    )
    assert (
        len([row for row in records(trace) if row.get('method') == 'account/rateLimits/read']) == 1
    ), 'US1R: genuine account/catalog bootstrap performs one optional read, without polling'
    bucket = current['buckets'][0]
    assert bucket['id'] == 'original-codex' and bucket['limitName'] == 'Original owned limit', (
        'US: bootstrap automatic read delivers original result not just request'
    )
    assert bucket['credits'] == {'hasCredits': True, 'unlimited': False, 'balance': '12.50'}, (
        'US: bootstrap automatic read delivers original result not just request'
    )
    assert [(row['kind'], row['usedPercent']) for row in bucket['windows']] == [
        ('primary', 17),
        ('secondary', 83),
    ], 'US: independent original windows remain distinct'
    assert current.get('observedAt'), 'US: delivered data includes actual observation time'
    methods = {row.get('method') for row in records(trace)}
    assert {'account/read', 'model/list', 'skills/list'} <= methods, (
        'US1R SETUP: real managed bootstrap completed, not optional-read-only fake readiness'
    )
    identity = live_original_peer(actor)
    for _ in range(4):
        actor.command('inspect')
    assert (
        original_peer_is_live(identity)
        and len([row for row in records(trace) if row.get('method') == 'account/rateLimits/read'])
        == 1
    ), 'US: ordinary idle deliveries do not start a usage polling loop'


@pytest.mark.parametrize('channel', ['control-capacity', 'reverse-capacity'])
def test_usage129_outstanding_optional_read_never_starves_real_required_channels(generic, channel):
    actor, trace = usage_case(generic, mode=channel)
    settle(
        actor,
        lambda value: (
            any(row.get('method') == 'account/rateLimits/read' for row in records(trace))
            or bool(value['last_error'])
            or not value['connected']
        ),
    )
    assert any(row.get('method') == 'account/rateLimits/read' for row in records(trace)), (
        'US1 SETUP: genuine optional request is outstanding on original channel'
    )
    actor.command('send_text', text='Original work while optional usage read remains pending')
    state = settle(actor, lambda value: value['can_cancel'] or bool(value['pending_question']))
    if channel == 'control-capacity':
        texts = ['Original pending steer ' + str(index) for index in range(3)]
        for text in texts:
            actor.command('send_text', text=text)
        assert len([row for row in records(trace) if row.get('method') == 'turn/steer']) == 3, (
            'US1: optional read does not consume three genuinely available required steer slots'
        )
        actor.command('cancel')
        state = settle(actor, lambda value: not value['can_cancel'])
        assert matching_interrupt(trace), 'US1: Stop still reaches real required interrupt channel'
        assert all(len(users(actor, text)) == 1 for text in texts), (
            'US1: genuine pending user identities are retained once, without false nonadmission'
        )
    else:
        assert state['pending_question'], (
            'US1 SETUP: genuine reverse input request is actually presented'
        )
        actor.command(
            'answer', id=state['pending_question']['question_id'], answer='Original answer'
        )
        state = settle(actor, lambda value: not value['can_cancel'])
        replies = [
            event
            for event in clear_control_events(trace)
            if event['kind'] == 'usage-question-result'
        ]
        assert replies and replies[0]['response']['id'] == 'original-question-rpc', (
            'US1: original incoming reverse request settles despite outstanding optional usage'
        )
    assert state['connected'], (
        'US1: optional read never tears down managed account to free capacity'
    )


def test_usage129_repeated_refresh_coalesces_one_pending_optional_request(generic):
    actor, trace = usage_case(generic, mode='popup')
    settle(actor, lambda value: usage_value(value)['available'])
    for _ in range(3):
        assert actor.command('refresh_usage')['reply']['invoked'], (
            'US: actual public refresh invoked'
        )
    pending = [row for row in records(trace) if row.get('method') == 'account/rateLimits/read']
    assert len(pending) == 2, (
        'US1: multiple refreshes while one read is pending coalesce into that read'
    )
    state = settle(
        actor,
        lambda value: usage_value(value)['available'] and usage_primary(value) == [43],
    )
    assert state['connected'] and usage_primary(state) == [43], (
        'US: coalesced genuine result reaches actual usage projection, not request-only '
        'bookkeeping'
    )
    for _ in range(4):
        actor.command('inspect')
    assert (
        len([row for row in records(trace) if row.get('method') == 'account/rateLimits/read']) == 2
    ), 'US1: completed coalesced refresh does not secretly poll or schedule redundant refresh'


def test_usage129_sparse_update_prevents_older_read_becoming_fresh(generic):
    actor, trace = usage_case(generic, mode='freshness')
    settle(actor, lambda value: usage_value(value)['available'])
    actor.command('refresh_usage')
    settle(
        actor,
        lambda _value: any(
            event['kind'] == 'usage-older-reply' for event in clear_control_events(trace)
        ),
    )
    # Marker proves the older line was written, not parsed. An actual later
    # retained completed reply on SAME ordered stdout supplies the client-side barrier.
    barrier = 'Original user request establishing ordered usage delivery'
    actor.command('send_text', text=barrier)
    state = settle(
        actor,
        lambda value: (
            not value['can_cancel']
            and any(
                row.get('kind') == 'assistant'
                and row.get('status') == 'completed'
                and row.get('text') == 'Original offline reply'
                for row in value['messages']
            )
        ),
    )
    assert len(users(actor, barrier)) == 1, (
        'US2 SETUP: real later message acknowledged once on original channel'
    )
    assert usage_value(state)['stale'] or usage_primary(state) != [17], (
        'US2: old pending response after newer notification cannot be labelled fresh'
    )
    actor.command('refresh_usage')
    state = settle(
        actor,
        lambda value: (
            usage_primary(value) == [43]
            and usage_value(value)['available']
            and not usage_value(value)['stale']
        ),
    )
    assert state['connected'], (
        'US2: explicit later genuine read restores fresh same-account result'
    )


def test_usage129_optional_failure_retains_only_stale_same_account_data(generic):
    actor, trace = usage_case(generic, mode='failure')
    state = settle(actor, lambda value: usage_value(value)['available'])
    original = usage_value(state)
    actor.command('refresh_usage')
    state = settle(actor, lambda value: usage_value(value)['stale'])
    later = usage_value(state)
    assert not later['available'] and later['buckets'] == original['buckets'], (
        'US: optional same-account failure retains truthful stale data, never fictional '
        'fresh quota'
    )
    assert later.get('observedAt') == original.get('observedAt') and state['connected'], (
        'US: optional failure preserves original observation time and genuine managed account'
    )
    assert not any(row.get('method') == 'account/logout' for row in records(trace)), (
        'US: usage failure does not become account retirement'
    )


def test_usage129_signout_hides_old_account_before_new_real_account_read(generic):
    actor, trace = usage_case(generic)
    settle(actor, lambda value: usage_value(value)['available'])
    retired = actor.command('sign_out')['vm']
    assert not retired['connected'] and usage_value(retired) == {
        'available': False,
        'stale': False,
        'buckets': [],
    }, 'US3: signout immediately hides original account usage before any replacement reply'
    config_path = trace.parent / 'peer-input.json'
    config = json.loads(config_path.read_text())
    config.update(
        account_email='new-original@example.invalid',
        usage_account='new-original-account',
        usage_mode='over-hundred',
    )
    config_path.write_text(json.dumps(config))
    connect(actor)
    state = settle(actor, lambda value: usage_value(value)['available'])
    assert state['handoff']['account_label'] == 'new-original@example.invalid', (
        'US3 SETUP: actual account/read admits independently distinct replacement account'
    )
    assert usage_primary(state) == [137], (
        'US3: new-account usage replaces old cache; >100 is retained honestly'
    )


@pytest.mark.parametrize('retirement', ['clear', 'context'])
def test_usage129_normal_clear_preserves_account_owned_usage(generic, tmp_path, retirement):
    actor, trace = usage_case(generic)
    state = settle(actor, lambda value: usage_value(value)['available'])
    original = usage_value(state)
    if retirement == 'clear':
        actor.command('clear_history')
    else:
        path = tmp_path / 'Original usage context.txt'
        path.write_text('Original harmless selected context')
        request = actor.command('selected_begin')['reply']['request_id']
        assert actor.command('selected_add', request_id=request, urls=[path.as_uri()])['reply'][
            'accepted'
        ], 'US3 SETUP: actual selected bytes genuinely replace outgoing context'
    assert actor.last['vm']['connected'] and usage_value(actor.last['vm']) == original, (
        'US3: conversation Clear does not retire genuine same-account usage ownership'
    )
    assert not any(row.get('method') == 'account/logout' for row in records(trace)), (
        'US3: account-owned usage preservation uses real session, not automatic re-login'
    )


def test_usage129_real_canvas_distinguishes_zero_missing_and_recovered_zero(generic):
    actor, trace = usage_case(generic, mode='zero-empty', ui=True)
    state = settle(actor, lambda value: usage_value(value)['available'])
    assert usage_primary(state) == [0], (
        'US4 SETUP: genuine explicit zero, not missing provider window'
    )
    zero = actor.command('inspect')['ui']['usage']['canvas']
    assert zero['window_available'] is True, 'US4: actual Canvas treats genuine zero as available'
    actor.command('refresh_usage')
    settle(
        actor,
        lambda value: (
            not usage_value(value)['available']
            and not usage_value(value)['stale']
            and usage_value(value)['buckets'] == []
            and bool(usage_value(value).get('observedAt'))
            and any(
                event['kind'] == 'usage-result-reply' and event['number'] == 2 and event['empty']
                for event in clear_control_events(trace)
            )
        ),
    )
    missing = actor.command('inspect')['ui']['usage']['canvas']
    assert missing['window_available'] is False, (
        'US4: actual missing window is distinct from genuine zero'
    )
    assert missing['frame']['sha256'] != zero['frame']['sha256'], (
        'US4: real rendered Canvas invalidates zero-to-missing, beyond a correct '
        'nonpainted property'
    )
    actor.command('refresh_usage')
    settle(actor, lambda value: usage_primary(value) == [0])
    recovered = actor.command('inspect')['ui']['usage']['canvas']
    assert (
        recovered['window_available'] is True
        and recovered['frame']['sha256'] != missing['frame']['sha256']
    ), 'US4: actual rendered Canvas also invalidates missing-to-zero without reopening the dialog'
    assert all(
        row['frame']['width'] > 0 and row['frame']['height'] > 0
        for row in (zero, missing, recovered)
    ), 'US4 SETUP: actual framebuffer regions are nonempty'


def test_usage129_actual_small_enlarged_dialog_scrolls_with_shared_ea_component(generic):
    actor, trace = usage_case(generic, mode='popup', ui=True, many=True)
    settle(actor, lambda value: usage_value(value)['available'])
    actor.command('click_usage')
    settle(actor, lambda value: usage_primary(value) == [43] * 8)
    assert (
        len([row for row in records(trace) if row.get('method') == 'account/rateLimits/read']) == 2
    ), (
        'US1: actual popup requests and delivers one fresh result separately from '
        'bootstrap, without polling'
    )
    before = actor.command('inspect')['ui']['usage']['popup']
    assert before['visible'] and before['opened'], (
        'US5 SETUP: physical usage button opens actual dialog'
    )
    fonts = [
        row['pixel_size'] for row in before['labels'] if row['visible'] and row['text'].strip()
    ]
    assert fonts and min(fonts) > 0, 'US5 SETUP: actual rendered label font sizes are measurable'
    actor.command('usage_scale', percent=150)
    actor.command('viewport', width=480, height=420, font_pixels=21)
    actual = actor.command('inspect')['ui']['usage']['popup']
    changed = [
        row['pixel_size'] for row in actual['labels'] if row['visible'] and row['text'].strip()
    ]
    assert changed and max(changed) > max(fonts), (
        'US5 SETUP: existing actual EA scale knob genuinely enlarges rendered labels, '
        'not just app font metadata'
    )
    assert actual['geometry']['whole_reachable'], (
        'US5: actual dialog fits the real small viewport at genuinely enlarged font'
    )
    bars = [bar for bar in actual['scrollbars'] if bar['visible']]
    assert bars and any(
        bar['matches_ea_type']
        and 'EasyApplication' in bar['ea_reference_url']
        and bar['ea_reference_url'].endswith('/ScrollBar.qml')
        for bar in bars
    ), 'US5: real overflow uses the same loaded EA scrollbar component as ordinary manual sidebar'
    initial = max((row['content_y'] for row in actual['scrollables']), default=0)
    for _ in range(16):
        actor.command('usage_wheel')  # Actual finite pointer wheel input, no contentY setter.
    after = actor.command('inspect')['ui']['usage']['popup']
    assert max((row['content_y'] for row in after['scrollables']), default=0) > initial, (
        'US5: actual ordinary pointer scrolling reaches overflow, not merely an attached scrollbar'
    )
    context = [row for row in after['labels'] if 'context' in row['text'].lower()]
    assert context and any(row['center_reachable'] and row['visible'] for row in context), (
        'US5: actual final context-occupancy section becomes reachable through real scrolling'
    )
    text = '\n'.join(row['text'] for row in after['labels'])
    assert 'unavailable' in text.lower(), (
        'US5: independent context occupancy stays honestly unavailable; rate limits '
        'never invent token occupancy'
    )
    assert actor.last['vm']['connected'], (
        'US5: viewing real usage never changes genuine managed account'
    )


@pytest.mark.parametrize('replacement', ['close', 'replace'])
def test_native129_disconnected_clear_then_owner_change_during_real_cancel_releases_recovery(
    generic, replacement
):
    actor, trace = native_case(
        generic,
        [native_call('run_fit')],
        project=ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project',
    )
    actor.command(
        'send_text', text='Original native fit with real cancellation and owner retirement'
    )
    running = settle(
        actor,
        lambda value: (
            value['project']['native_observer']['fit_running']
            or bool(native_records(trace, '.native-replies.jsonl'))
        ),
    )
    assert running['project']['native_observer']['fit_running'], (
        'N4-R2 SETUP: genuine native worker is active before the ordinary publication fence'
    )
    actor.command('persistence_barrier')
    actor.command(
        'send_text', text='Original pending user input whose durable admission genuinely fails'
    )
    assert actor.last['vm']['last_error'], (
        'N4-R2 SETUP: real archive refusal has produced a public fence'
    )
    actor.command('sign_out')
    assert not actor.last['vm']['connected'], (
        'N4-R2: actual account retirement revokes the old conversation'
    )
    actor.command('clear_history')
    assert actor.last['vm']['last_error'], (
        'N4-R2: failed Clear cannot silently release held records'
    )
    actor.command('persistence_restore')
    actor.command('clear_history')
    assert actor.command('archive')['reply']['rows'] == [], (
        'N4-R2 SETUP: successful disconnected Clear has actually persisted the empty archive'
    )
    assert actor.last['vm']['project']['native_observer']['fit_running'], (
        'N4-R2 SETUP: real old worker cancellation is still pending BEFORE owner replacement; '
        'an already finished worker does not qualify this interval'
    )
    if replacement == 'close':
        actor.command('close_project')
        assert not actor.last['vm']['project_present'], (
            'N4-R2 SETUP: genuine Session close admits the owner transition during retirement'
        )
    else:
        assert actor.command('open', path=str(ROOT / 'tests/fixtures/e04_t1/editable-project'))[
            'reply'
        ]['opened'], (
            'N4-R2 SETUP: genuine Session replacement admits the owner transition during '
            'retirement'
        )
    if not actor.last['vm']['project_present']:
        assert actor.command('open', path=str(ROOT / 'tests/fixtures/e04_t1/editable-project'))[
            'reply'
        ]['opened'], (
            'N4-R2 SETUP: real fresh current project is available for a later native control'
        )
    expected = actor.last['vm']['project']['parameters']
    config_path = trace.parent / 'peer-input.json'
    config = json.loads(config_path.read_text())
    config['native_calls'] = [native_call('inspect_project')]
    config_path.write_text(json.dumps(config))
    connect(actor)
    if actor.last['vm']['context_consent_required']:
        actor.command('sign_in')
    actor.command(
        'send_text',
        text='Original fresh bounded read after disconnected Clear and owner replacement',
    )
    state = settle(actor, lambda value: not value['can_cancel'] or bool(value['last_error']))
    assert state['connected'] and not state['last_error'], (
        'N4-R2: retired old worker cannot strand successful Clear recovery or future sign-in'
    )
    assert state['project']['parameters'] == expected, (
        'N4-R2: late old report cannot mutate replacement owner'
    )
    assert any(
        row['original']['params']['tool'] == 'inspect_project'
        and row['response'].get('result', {}).get('success')
        for row in native_records(trace, '.native-replies.jsonl')
    ), 'N4-R2: genuine new native inspection works after recovery, without a stale worker fence'


def test_native129_real_shared_transport_admission_refuses_before_later_native_write(generic):
    actor, trace = native_case(
        generic,
        [
            native_call(
                'set_parameters', values=[{'path': 'structure.cell.length_a', 'value': 3.89}]
            )
        ],
        project=ROOT / 'tests/fixtures/e04_t1/editable-project',
        connect_now=False,
    )
    bounds = actor.last['vm']['policy']
    config_path = trace.parent / 'peer-input.json'
    config = json.loads(config_path.read_text())
    # Exact original committed measurement text is untrusted protocol fixture DATA,
    # not private reasoning, scientific output, padding or a held native request.
    source = (
        ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project/experiments/d20.edi'
    ).read_text()
    owned_source = trace.parent / 'original-capacity-measurement.edi'
    owned_source.write_text(source)
    count = bounds['stream_retained_bytes'] // len(source.encode()) + 1
    items = [
        {
            'type': 'reasoning',
            'id': 'original-live-source-' + str(index),
            'summary': [],
            'content': [source],
        }
        for index in range(count)
    ]

    def encoded(value):
        return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()

    # These are unfinalized known originals in ONE still-active turn. All remain
    # current simultaneously: no item/completed, replacement or turn terminal releases one.
    wires = [
        {
            'method': 'item/started',
            'params': {
                'threadId': '019a0290-0000-7000-8000-000000000001',
                'turnId': '019a0290-0000-7000-8000-000000000002',
                'item': item,
            },
        }
        for item in items
    ]
    source_bytes = sum(len(encoded(item)) for item in items)
    assert count * len(source.encode()) > bounds['stream_retained_bytes'], (
        'N2-R SETUP: original content bytes ALONE exceed retained output, '
        'independent of JSON overhead'
    )
    assert source_bytes > bounds['stream_retained_bytes'], (
        'N2-R SETUP: simultaneous unfinalized original output exceeds '
        'its declared retained-output cap'
    )
    assert count < bounds['stream_items'], (
        'N2-R SETUP: every original fits the separate item-count role'
    )
    assert max(len(encoded(item)) for item in items) < bounds['stream_retained_bytes'], (
        'N2-R SETUP: each original alone fits retained output; this is genuine aggregate growth'
    )
    assert max(len(encoded(wire)) for wire in wires) + 1 <= bounds['record_bytes'], (
        'N2-R SETUP: EVERY complete original JSONL wire fits its individual source bound'
    )
    assert sum(len(encoded(wire)) + 1 for wire in wires) < bounds['stream_wire_bytes'], (
        'N2-R SETUP: the complete original wire group fits the separate total wire role'
    )
    # Pinned reasoning originals are not copied to public message/history rows;
    # the old command copy exceeded presentation capacity before this transport role.
    config.update(
        native_capacity='retained-live-reasoning',
        native_capacity_source=str(owned_source),
        native_capacity_count=count,
    )
    config_path.write_text(json.dumps(config))
    connect(actor)
    before = actor.last['vm']['project']['parameters']
    actor.command(
        'send_text', text='Original bounded native write cannot bypass shared incoming ownership'
    )
    state = settle(actor, lambda value: bool(value['last_error']) or not value['connected'])
    measurements = [
        event for event in clear_control_events(trace) if event['kind'] == 'native-shared-capacity'
    ]
    assert measurements and measurements[0]['source_bytes'] > bounds['stream_retained_bytes'], (
        'N2-R SETUP: independently encoded retained originals exceed the public shared cap'
    )
    assert measurements[0]['source_bytes'] == source_bytes and measurements[0]['count'] == count, (
        'N2-R SETUP: peer BEFORE-emission measurement matches independently encoded '
        'known originals'
    )
    assert measurements[0]['source_sha256'] == hashlib.sha256(source.encode()).hexdigest(), (
        'N2-R SETUP: exact committed original bytes, not fabricated padding/native receipts'
    )
    assert measurements[0]['max_wire_bytes'] + 1 <= bounds['record_bytes'], (
        'N2-R SETUP: the escape is simultaneous aggregate ownership, not one oversized source'
    )
    assert measurements[0]['presentation_rows'] == 0 and measurements[0]['finalized_items'] == 0, (
        'N2-R SETUP: no presentation overflow or terminal release masks the intended original role'
    )
    assert state['project']['parameters'] == before, (
        'N2-R: actual shared-budget failure precedes any later genuine native mutation'
    )
    assert state['last_error'] and not state['can_cancel'], (
        'N2-R: aggregate refusal remains bounded and visibly noncompleted, never silent authority'
    )
    assert not any(
        row['response'].get('result', {}).get('success')
        for row in native_records(trace, '.native-replies.jsonl')
    ), 'N2-R: failed incoming admission cannot report successful physical native write'
    # This externally reached aggregate control does not itself prove every internal
    # canonical/active-row replacement allocation is charged BEFORE copying; static review does.


def test_usage129_actual_process_retirement_hides_original_account_snapshot(generic):
    actor, trace = usage_case(generic, mode='eof')
    settle(actor, lambda value: usage_value(value)['available'])
    actor.command('send_text', text='Original bounded work before genuine owned-process EOF')
    final = settle(actor, lambda value: not value['connected'])
    assert any(event['kind'] == 'usage-process-eof' for event in clear_control_events(trace)), (
        'US3 SETUP: the original actual stdio process retired, not a fake disconnected property'
    )
    assert usage_value(final) == {'available': False, 'stale': False, 'buckets': []}, (
        'US3: process retirement immediately hides original-account usage, independently '
        'of later cache clearing'
    )
    assert len(started_requests(trace)) == 1, (
        'US3: optional state retirement never automatically replays user work'
    )


# R2/R3 use real synchronous Qt observers and existing public operations, not
# a replacement engine/worker or production fault flag.
def publication134_case(generic, tmp_path, *, scan=False, seed_undo=False):
    source = ROOT / 'tests/fixtures/e04_t1/editable-project'
    if scan:
        source = tmp_path / 'Original-two-measured-file-scan'
        original_names = prepare_scan134(source, 2)
        assert len(original_names) == 2, 'R2 SETUP: actual independent two-file scan prior art'
    actor, trace = native_case(generic, [], project=source, hold=True, connect_now=False)
    if scan:
        actor.command('publication_scan_start')
        actual = settle(
            actor,
            lambda value: (
                value['publication_current']['scan_processed'] == 2
                and not value['project']['native_observer']['fit_running']
            ),
        )
        facts = actor.command('publication_inspect')['reply']
        assert facts['scan'] and facts['scan_processed'] == 2 and facts['can_reset'], (
            'R2 SETUP: actual normal scan completed its two measured files and exposes Reset'
        )
        assert not actual['project']['native_observer']['fit_running'], (
            'R2 SETUP: no forced running state or fabricated scan result'
        )
    if seed_undo:
        assert not actor.command('publication_seed_undo')['reply']['error'], (
            'R2 SETUP: older normal free-flag edit creates a real recorded Undo'
        )
        settle(actor, lambda value: not value['publication_current']['calculating'])
        assert actor.last['vm']['project']['native_observer']['can_undo'], (
            'R2 SETUP: callback Undo must have real prior work to consume'
        )
    before = actor.last['vm']
    scalar = native_parameter(before)
    config_path = trace.parent / 'peer-input.json'
    config = json.loads(config_path.read_text())
    config['native_calls'] = [
        native_call(
            'set_parameters', values=[{'path': scalar['path'], 'value': scalar['value'] + 0.01}]
        )
    ]
    config_path.write_text(json.dumps(config))
    connect(actor)
    if actor.last['vm']['context_consent_required']:
        actor.command('sign_in')
    return actor, trace


@pytest.mark.parametrize(
    'action',
    [
        'report-setting',
        'save',
        'undo',
        'fit-start',
        'fit-reset',
        'restore-patterns',
        'scan-prepare',
        'scan-reset',
    ],
)
def test_native134_synchronous_publication_observer_cannot_bypass_shared_editor_fence(
    generic, tmp_path, action
):
    scan = action in {'fit-reset', 'scan-prepare', 'scan-reset'}
    actor, trace = publication134_case(generic, tmp_path, scan=scan, seed_undo=True)
    before = actor.last['vm']
    destination = tmp_path / 'Original-reentrant-save-must-not-exist'
    assert not destination.exists(), 'R2 SETUP: callback Save has a genuine fresh destination'
    assert actor.command(
        'publication_arm', signal='projectEdited', action=action, destination=str(destination)
    )['reply']['armed'], 'R2 SETUP: genuine synchronous public signal observer is armed'
    actor.command('send_text', text='Original native value edit with independent Qt consumer')
    final = settle(actor, lambda _value: len(native_records(trace, '.native-replies.jsonl')) == 1)
    observed = final['publication_observer']
    assert observed['entered'] and observed['same_owner_at_entry'] and observed['returned'], (
        'R2 SETUP: actual callback completed inside the original publication, not after it'
    )
    previous, after = observed['before'], observed['after']
    assert previous['can_undo'], 'R2 SETUP: synchronous Undo has an actual older record'
    # Error text may honestly become a refusal. Every actual scientific/view/persistence
    # field observed on the same synchronous stack must stay unchanged.
    for field in (
        'parameters',
        'patterns',
        'path',
        'report_pdf',
        'report_html_offline',
        'can_undo',
        'fit_running',
        'can_reset',
        'scan_processed',
        'scan_fitted',
    ):
        assert after[field] == previous[field], (
            'R2: callback alternative cannot bypass shared editor publication authority: ' + field
        )
    assert not observed['destination_exists'] and not destination.exists(), (
        'R2: reentrant Save must not publish disk bytes or move the live path'
    )
    if action == 'undo':
        assert after['error'], 'R2: a real synchronous Undo refusal is honestly explained'
        # A healthy outer publication may retire an ephemeral nested busy warning.
        # Retention after an applied-edit/syncUndo held failure remains a distinct,
        # currently uninjectable application-level qualification obligation.
    replies = native_records(trace, '.native-replies.jsonl')
    assert len(replies) == 1 and replies[0]['response']['id'] == replies[0]['original']['id'], (
        'R2: original native envelope settles once after actual host publication'
    )
    assert replies[0]['response']['result']['success'], (
        'R2: refused nested mutation cannot destroy the valid original value edit'
    )
    assert final['connected'] and final['models'] == before['models'], (
        'R2: real publication observer cannot fabricate signout or lose the current catalog'
    )
    recovered = actor.command('native_undo')
    assert recovered['reply']['was_available'], (
        'R2: normal outside-callback Undo remains available'
    )
    assert recovered['vm']['project']['parameters'] == before['project']['parameters'], (
        'R2: one genuine recovery Undo restores the original committed pre-batch state'
    )


@pytest.mark.parametrize('signal', ['modifiedChanged', 'rowsInserted'])
@pytest.mark.parametrize('owner_action', ['close', 'replace'])
def test_native134_real_qt_consumer_may_retire_project_without_dangling_publication(
    generic, tmp_path, signal, owner_action
):
    actor, trace = publication134_case(generic, tmp_path)
    before = actor.last['vm']
    replacement = tmp_path / 'Original-replacement-project'
    shutil.copytree(ROOT / 'tests/fixtures/e04_t1/editable-project', replacement)
    assert actor.command(
        'publication_arm', signal=signal, action=owner_action, replacement=str(replacement)
    )['reply']['armed'], 'R3 SETUP: actual lifetime callback armed before real model publication'
    if signal == 'modifiedChanged':
        actor.command(
            'send_text', text='Original native edit while a real consumer changes page owner'
        )
    else:
        actor.command('publication_create_structure')
    final = settle(
        actor, lambda value: bool(value.get('publication_observer', {}).get('returned'))
    )
    observed = final['publication_observer']
    assert observed['entered'] and observed['same_owner_at_entry'] and observed['returned'], (
        'R3 SETUP: real Qt model/registry consumer reached actual Session operation'
    )
    if owner_action == 'close':
        assert not final['project_present'], 'R3: real Session close is honored safely'
    else:
        assert observed['replacement_opened'] and final['project_present'], (
            'R3: real Session replacement is honored safely'
        )
        assert final['project']['host_snapshot']['path'] == str(replacement), (
            'R3: current owner is the independently copied replacement, not the old object'
        )
        assert native_parameter(final)['value'] == 3.88, (
            'R3: old publication cannot write the replacement model'
        )
    actor.command('publication_flush_retired')
    final = settle(actor, lambda value: not value['publication_owner_alive'])
    assert not final['publication_owner_alive'], (
        'R3: old QObject is actually released after safe publication, '
        'not leaked to hide lifetime errors'
    )
    assert final['connected'] and final['models'] == before['models'], (
        'R3: normal manual Session ownership change preserves genuine managed account'
    )
    assert actor.command('inspect')['vm']['connected'], (
        'R3: real owner and event loop remain usable after callback retirement'
    )
    assert len(native_records(trace, '.native-replies.jsonl')) <= 1, (
        'R3: no duplicate or replacement response is invented for a retired old native operation'
    )


@pytest.mark.parametrize('owner_action', ['close', 'replace'])
def test_native135_replacement_does_not_suppress_new_owner_manual_context(
    generic, tmp_path, owner_action
):
    actor, trace = publication134_case(generic, tmp_path)
    replacement = tmp_path / 'Original-new-owner-for-context'
    shutil.copytree(ROOT / 'tests/fixtures/e04_t1/editable-project', replacement)
    assert actor.command(
        'publication_arm',
        signal='modifiedChanged',
        action=owner_action,
        replacement=str(replacement),
    )['reply']['armed']
    actor.command('send_text', text='Original native edit retired by actual Session consumer')
    state = settle(
        actor, lambda value: value.get('publication_observer', {}).get('returned', False)
    )
    assert state['publication_observer']['entered'], (
        'R3-R4 SETUP: real native edit reached the public callback'
    )
    if owner_action == 'close':
        assert not state['project_present']
        assert actor.command('open', path=str(replacement))['reply']['opened']
    else:
        assert state['publication_observer']['replacement_opened']
    state = settle(
        actor,
        lambda value: not value['can_cancel'] and not value['publication_current']['calculating'],
    )
    assert state['connected'], 'R3-R4: actual native retirement preserves managed account'
    assert state['project']['host_snapshot']['path'] == str(replacement)
    if state['context_consent_required']:
        actor.command('sign_in')  # Existing connected GUI context approval, not account repair.
    before = actor.last['vm']
    assert before['connected'] and not before['context_consent_required'], (
        'R3-R4 SETUP: genuinely approved replacement context'
    )
    target = native_parameter(before)
    changed = actor.command('manual_value', path=target['path'], value=target['value'] + 0.001)
    assert not changed['reply']['error'], (
        'R3-R4 SETUP: ordinary replacement-owner manual edit was admitted'
    )
    state = changed['vm']
    assert native_parameter(state)['value'] == target['value'] + 0.001
    assert state['context_consent_required'], (
        'R3-R4: old native suppression cannot swallow new-owner context retirement'
    )
    assert state['context'] != before['context'], (
        'R3-R4: actual current disclosed context changes with the manual edit'
    )
    assert state['connected'] and state['models'] == before['models']
    assert state['handoff']['account_label'] == before['handoff']['account_label']
    assert len(native_records(trace, '.native-replies.jsonl')) <= 1


@pytest.mark.parametrize('attachment', ['ordinary', 'managed-result'])
@pytest.mark.parametrize('owner_action', ['close', 'replace'])
def test_native135_real_conversation_retirement_callback_keeps_latest_session_owner(
    generic, tmp_path, attachment, owner_action
):
    replacement = tmp_path / 'Original-newest-real-owner'
    shutil.copytree(ROOT / 'tests/fixtures/e04_t1/editable-project', replacement)
    actor, trace = generic('result:complete' if attachment == 'managed-result' else 'complete')
    if attachment == 'managed-result':
        original = ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project'
        fixture = tmp_path / 'Original-complete-measured-result'
        for source in original.rglob('*.edi'):
            destination = fixture / source.relative_to(original)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        assert len(list(fixture.rglob('*.edi'))) == 4
        config_path = trace.parent / 'peer-input.json'
        config = json.loads(config_path.read_text())
        config['result_fixture'] = str(fixture)
        config_path.write_text(json.dumps(config))
    else:
        original = tmp_path / 'Original-before-outer-bind'
        shutil.copytree(ROOT / 'tests/fixtures/e04_t1/editable-project', original)
        assert actor.command('open', path=str(original))['reply']['opened']
    connect(actor)
    before = actor.last['vm']
    assert actor.command('retirement_arm', action=owner_action, replacement=str(replacement))[
        'reply'
    ]['armed']
    if attachment == 'ordinary':
        outer = tmp_path / 'Original-obsolete-outer-target'
        shutil.copytree(ROOT / 'tests/fixtures/e04_t1/editable-project', outer)
        actor.command('open', path=str(outer))
    else:
        from tests.system.app import (  # noqa: PLC0415 -- existing circular vehicle
            test_e11_t5_assistant_result as result_inputs,
        )

        result_inputs.start(
            actor, trace
        )  # Genuine admitted intent, original complete receipt and terminal.
    state = settle(
        actor, lambda value: value.get('retirement_observer', {}).get('returned', False)
    )
    observed = state['retirement_observer']
    assert observed['entered'] and observed['calls'] == 1, (
        'R3-R5 SETUP: actual once-only public retirement callback returned'
    )
    if owner_action == 'close':
        assert not state['project_present'], (
            'R3-R5: old bind cannot reinstall a genuinely closed target'
        )
    else:
        assert observed['replacement_opened'] and state['project_present']
        assert state['project']['host_snapshot']['path'] == str(replacement), (
            'R3-R5: newest actual nested owner stays authoritative'
        )
        assert native_parameter(state)['value'] == 3.88
        assert state['handoff']['location'] == str(replacement)
    assert state['connected'] and state['models'] == before['models']
    assert state['handoff']['account_label'] == before['handoff']['account_label']
    assert actor.command('inspect')['vm']['connected'], (
        'R3-R5: real event-loop owner remains usable after nested bind'
    )


def managed_file_retirement_after_terminal(actor):
    assert actor.command(
        'selected_after_terminal_arm', text='Create the original measured LBCO result'
    )['reply']['armed'], '143 SETUP: actual idle/retained-terminal observer armed before real Send'


def assert_managed_file_retirement_after_terminal(actor, state):
    observed = state.get('terminal_selection_observer', {})
    assert observed.get('entered') and observed.get('returned'), (
        '143 SETUP: real idle notification follows durable original terminal before adoption'
    )
    assert observed['state_at_entry'] == 'idle' and observed['connected_at_entry']
    assert not observed['project_present_at_entry'], (
        '143 SETUP: ordinary queued host attachment has not committed yet'
    )
    assert observed['original_user_id'] == actor.result_user_id, (
        '143: actual terminal observation belongs to the once-only admitted original input'
    )
    retained = observed['retained_rows']
    assert any(
        row.get('id') == actor.result_user_id and row.get('kind') == 'user' for row in retained
    )
    assert any(
        row.get('kind') == 'assistant' and row.get('status') == 'completed' for row in retained
    ), '143 SETUP: successful original assistant terminal was genuinely durable'
    assert observed['retained_sha256'] and observed['request_id'] and not observed['last_error'], (
        '143 SETUP: actual public chooser is admitted after successful terminal retention'
    )
    assert observed['request_id'] in state['retired_selections'], (
        '143: genuine admitted request reaches the later real fileSelectionRetired signal'
    )


@pytest.mark.parametrize(
    ('attachment', 'signal', 'authenticated', 'queued'),
    [
        ('ordinary', 'conversationRetired', True, False),
        ('ordinary', 'fileSelectionRetired', True, False),
        ('managed-result', 'conversationRetired', True, False),
        ('managed-result', 'fileSelectionRetired', True, False),
        ('ordinary', 'conversationRetired', False, False),
        ('ordinary', 'fileSelectionRetired', False, False),
        ('ordinary', 'conversationRetired', True, True),
        ('ordinary', 'fileSelectionRetired', True, True),
    ],
)
def test_native139_assistant_only_clear_during_real_bind_keeps_current_owner_usable(  # noqa: PLR0912, PLR0915 -- finite public owner/callback outcomes
    generic, tmp_path, attachment, signal, authenticated, queued
):
    actor, trace = generic('result:complete' if attachment == 'managed-result' else 'complete')
    replacement = tmp_path / 'Original-current-owner-after-assistant-Clear'
    shutil.copytree(ROOT / 'tests/fixtures/e04_t1/editable-project', replacement)
    if attachment == 'ordinary':
        original = tmp_path / 'Original-owner-before-Clear-bind'
        shutil.copytree(ROOT / 'tests/fixtures/e04_t1/editable-project', original)
        assert actor.command('open', path=str(original))['reply']['opened']
    else:
        fixture = tmp_path / 'Original-complete-Clear-managed-result'
        source_root = ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project'
        for source in source_root.rglob('*.edi'):
            destination = fixture / source.relative_to(source_root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        assert len(list(fixture.rglob('*.edi'))) == 4
        config_path = trace.parent / 'peer-input.json'
        config = json.loads(config_path.read_text())
        config['result_fixture'] = str(fixture)
        config_path.write_text(json.dumps(config))
    if authenticated:
        connect(actor)
    before = actor.last['vm']
    if signal == 'fileSelectionRetired':
        if attachment == 'managed-result':
            managed_file_retirement_after_terminal(actor)
        else:
            assert actor.command('selected_begin')['reply']['request_id'], (
                'R3-R6 SETUP: genuine current native chooser request is pending'
            )
    assert actor.command('retirement_arm', action='clear', signal=signal, queued=queued)['reply'][
        'armed'
    ]
    if attachment == 'ordinary':
        actor.command('open', path=str(replacement))
    else:
        from tests.system.app import (  # noqa: PLC0415 -- existing circular vehicle
            test_e11_t5_assistant_result as result_inputs,
        )

        result_inputs.start(actor, trace)
    state = settle(
        actor, lambda value: value.get('retirement_observer', {}).get('returned', False)
    )
    if attachment == 'managed-result' and signal == 'fileSelectionRetired':
        assert_managed_file_retirement_after_terminal(actor, state)
    observed = state['retirement_observer']
    assert observed['entered'] and observed['calls'] == 1, (
        'R3-R6 SETUP: one actual retirement receiver returned'
    )
    assert observed['signal'] == signal and observed['queued'] == queued
    assert observed['connected_at_entry'] == authenticated
    assert state['connected'] == authenticated, (
        'R3-R6: assistant-only Clear cannot fabricate account transition'
    )
    if authenticated:
        assert state['models'] == before['models']
        assert state['handoff']['account_label'] == before['handoff']['account_label']
    if attachment == 'ordinary':
        assert state['project_present'], (
            'R3-R6: assistant-only Clear cannot strand the committed incoming Session owner'
        )
        assert state['project']['host_snapshot']['path'] == str(replacement)
        assert state['handoff']['location'] == str(replacement)
        assert native_parameter(state)['value'] == 3.88
    elif not state['project_present']:
        # Successful user Clear may revoke an uncommitted intent without an error.
        # Check the captured post-retirement frame BEFORE any archive/inspect
        # command drains another queued renderer delivery. This is outside the
        # actual Qt notification callback, never halfway through begin/end rows.
        assert_clear_projection156(state)
        assert actor.command('archive')['reply']['rows'] == [], (
            'R3-R6: successful Clear durably discards the original conversation'
        )
        assert_clear_projection156(actor.last['vm'])
        assert actor.command('open', path=str(replacement))['reply']['opened']
    else:
        result_inputs.project_readback(state)
    assert not actor.last['vm']['messages'], (
        'R3-R6: Clear retires retained conversation, not the host project'
    )
    assert_clear_projection156(actor.last['vm'])
    assert actor.command('archive')['reply']['rows'] == [], (
        'R3-R6: settled public empty rows match the canonical cleared archive'
    )
    if not authenticated:
        connect(actor)
    state = actor.last['vm']
    assert state['connected'] and state['project_present']
    if state['context_consent_required']:
        actor.command('sign_in')  # Existing connected GUI disclosure approval only.
    approved = actor.last['vm']
    assert approved['connected'] and not approved['context_consent_required'], (
        'R3-R6 SETUP: actual newest-owner disclosure is approved before manual change'
    )
    target = native_parameter(approved)
    changed = actor.command('manual_value', path=target['path'], value=target['value'] + 0.001)
    assert not changed['reply']['error'], 'R3-R6: actual newest-owner manual editor remains usable'
    assert native_parameter(changed['vm'])['value'] == target['value'] + 0.001
    assert changed['vm']['connected']
    assert changed['vm']['context'] != approved['context'], (
        'R3-R6: actual manual change updates the complete newest-owner disclosure'
    )
    assert changed['vm']['context_consent_required'], (
        'R3-R6: actual newest-owner context notifications remain usable'
    )
    assert not any(
        row.get('method') in {'account/login/start', 'account/logout'} for row in records(trace)
    )


@pytest.mark.parametrize(
    ('attachment', 'signal'),
    [
        ('managed-result', 'conversationRetired'),
        ('managed-result', 'fileSelectionRetired'),
        ('ordinary', 'conversationRetired'),
    ],
)
def test_native140_failed_clear_inside_actual_attachment_cannot_commit_aborted_candidate(  # noqa: PLR0912, PLR0914, PLR0915 -- finite actual fault boundary
    generic, tmp_path, attachment, signal
):
    actor, trace = generic('result:complete' if attachment == 'managed-result' else 'complete')
    original = ROOT / 'tests/fixtures/e04_t1/editable-project'
    manual_owner = tmp_path / 'Original-manual-owner-after-failed-Clear'
    shutil.copytree(original, manual_owner)
    if attachment == 'ordinary':
        prior_owner = tmp_path / 'Original-prior-disk-owner'
        shutil.copytree(original, prior_owner)
        assert actor.command('open', path=str(prior_owner))['reply']['opened']
    else:
        fixture = tmp_path / 'Original-measured-precommit-candidate'
        source_root = ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project'
        for source in source_root.rglob('*.edi'):
            destination = fixture / source.relative_to(source_root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        config_path = trace.parent / 'peer-input.json'
        config = json.loads(config_path.read_text())
        config['result_fixture'] = str(fixture)
        config_path.write_text(json.dumps(config))
    connect(actor)
    before = actor.last['vm']
    if attachment == 'ordinary':
        if before['context_consent_required']:
            actor.command('sign_in')
        actor.command('send_text', text='Original completed history before actual failed Clear')
        settle(
            actor,
            lambda value: (
                not value['can_cancel']
                and any(row.get('kind') == 'assistant' for row in value['messages'])
            ),
        )
    if signal == 'fileSelectionRetired':
        managed_file_retirement_after_terminal(actor)
    assert actor.command('retirement_arm', action='clear-archive-refusal', signal=signal)['reply'][
        'armed'
    ]
    if attachment == 'ordinary':
        actor.command('open', path=str(manual_owner))
    else:
        from tests.system.app import (  # noqa: PLC0415 -- existing circular vehicle
            test_e11_t5_assistant_result as result_inputs,
        )

        observed_result = result_inputs.start(actor, trace)
    state = settle(
        actor, lambda value: value.get('retirement_observer', {}).get('returned', False)
    )
    if attachment == 'managed-result' and signal == 'fileSelectionRetired':
        assert_managed_file_retirement_after_terminal(actor, state)
    observed = state['retirement_observer']
    assert observed['entered'] and observed['calls'] == 1
    assert not observed.get('barrier_error'), (
        '165 SETUP: real ordinary write refusal vehicle was installed successfully'
    )
    assert observed['clear_called'] and observed['archive_is_directory']
    assert observed['archive_before_clear']['is_file']
    assert observed['preserved_sha256'] == observed['archive_before_clear']['sha256']
    retained = observed['retained_rows']
    assert any(
        row.get('kind') == 'assistant' and row.get('status') == 'completed' for row in retained
    ), '165 SETUP: genuine successful terminal was durable BEFORE archive refusal'
    state = settle(actor, lambda value: bool(value['last_error']) and not value['can_cancel'])
    assert state['last_error'], (
        '165: failed Clear remains honestly refused after deferred settlement'
    )
    assert all(row in state['messages'] for row in retained), (
        '165: failed Clear cannot discard already retained history'
    )
    assert state['connected'] and state['models'] == before['models']
    assert state['handoff']['account_label'] == before['handoff']['account_label']
    if attachment == 'managed-result':
        assert not observed['host_published_before_clear'], (
            '165 SETUP: callback reached genuine precommit attachment'
        )
        assert not state['project_present'], (
            '165: failed nested Clear cannot acknowledge or commit the obsolete candidate'
        )
        for entry in observed_result['files']:
            path = fixture / entry['path']
            assert path.stat().st_size == entry['bytes']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']
    else:
        assert observed['host_published_before_clear'] and state['project_present']
        assert state['project']['host_snapshot']['path'] == str(manual_owner)
    assert actor.last['archive']['is_directory']
    actor.command('persistence_restore')
    assert actor.last['archive']['is_file']
    actor.command('clear_history')  # A genuine explicit retry after real storage recovery.
    assert actor.last['vm']['connected']
    if not actor.last['vm']['project_present']:
        assert actor.command('open', path=str(manual_owner))['reply']['opened']
    state = actor.last['vm']
    if state['context_consent_required']:
        actor.command('sign_in')
    approved = actor.last['vm']
    target = native_parameter(approved)
    edited = actor.command('manual_value', path=target['path'], value=target['value'] + 0.001)
    assert not edited['reply']['error']
    assert edited['vm']['connected'] and edited['vm']['context'] != approved['context']
    assert edited['vm']['context_consent_required']


# PRIVATE independent capability gates; append to the existing real Session module only.
def native145_recipe():
    recipe = Path('/tmp/relay-e11-t5-tests/seq85-private/inputs/recipe.json')
    assert hashlib.sha256(recipe.read_bytes()).hexdigest() == (
        'e7971d4dccdbab940806455d5590e8899e9a4757636be5361ea93c20896639a5'
    ), 'CREATE SETUP: independent original experiment recipe is unchanged'
    supplied = json.loads(recipe.read_text(encoding='utf-8'))
    return {
        'project_name': 'Original measured PbSO4',
        'description': 'Selected classic CIF and GSAS-derived measured XYE; no refinement claim',
        'experiment_name': supplied['name'],
        **supplied['experiment_type'],
        'peak_profile': supplied['peak']['type'],
        'wavelength': supplied['instrument']['setup_wavelength'],
        'zero_offset': supplied['instrument']['calib_twotheta_offset'],
        'phase_scale': supplied['linked_structure']['scale'],
        'background': [
            dict(zip(('position', 'intensity'), pair, strict=True))
            for pair in supplied['background']
        ],
        'exclusions': [
            dict(zip(('first', 'second'), pair, strict=True))
            for pair in supplied['excluded_regions']
        ],
        'initial_parameters': [
            {'path': 'experiment.peak.' + field, 'value': supplied['peak'][field]}
            for field in [
                'broad_gauss_u',
                'broad_gauss_v',
                'broad_gauss_w',
                'broad_lorentz_x',
                'broad_lorentz_y',
            ]
        ],
    }


@pytest.mark.parametrize('extension', ['.cif', '.edi'])
def test_native159_genuine_dotted_cif_selected_creation_preserves_original_inputs(  # noqa: PLR0914, PLR0915 -- literal input, recipe and independent preservation witnesses
    generic, tmp_path, extension
):
    original = ROOT / 'tests/fixtures/assistant/reference/easydiffraction-ddlm'
    provenance = json.loads((original / 'provenance.json').read_text())
    actor, trace = native_case(generic, [], connect_now=False)
    assert actor.command('native_science_enable')['reply']['enabled'], (
        'CIF159: preserve original input science, bytes and authenticated owner'
    )
    owned = []
    for entry in provenance['inputs']:
        data = (original / entry['path']).read_bytes()
        assert len(data) == entry['bytes'], (
            'CIF159: preserve original input science, bytes and authenticated owner'
        )
        assert hashlib.sha256(data).hexdigest() == entry['sha256'], (
            'CIF159: preserve original input science, bytes and authenticated owner'
        )
        destination = tmp_path / (
            'original-lbco' + extension if entry['path'] == 'lbco.cif' else entry['path']
        )
        destination.write_bytes(data)
        owned.append(destination)
    original_bytes = [path.read_bytes() for path in owned]
    token = actor.command('selected_begin')['reply']['request_id']
    assert token, (
        'CIF159: preserve original input science, bytes and authenticated owner'
    )
    assert actor.command('selected_add', request_id=token, urls=[p.as_uri() for p in owned])[
        'reply'
    ]['accepted'], (
        'CIF159: preserve original input science, bytes and authenticated owner'
    )
    selected_state = settle(
        actor, lambda value: len(value['selected_files']) == 2 and not value['can_cancel']
    )
    selected = {row['name']: row['id'] for row in selected_state['selected_files']}
    metadata = provenance['experiment_metadata']
    recipe = {
        'project_name': 'Original LBCO HRPT inputs',
        'description': 'Original DDLm and measured XYE; owner-specified wavelength, no fit claim',
        'experiment_name': 'NPD',
        'sample_form': 'powder',
        'beam_mode': 'constant wavelength',
        'radiation_probe': 'neutron',
        'scattering_type': 'bragg',
        'peak_profile': 'cwl-tch-pseudo-voigt',
        'wavelength': 1.49,
        'zero_offset': metadata['zero_offset_degrees'],
        'phase_scale': metadata['phase_scale'],
        'background': [
            dict(zip(('position', 'intensity'), pair, strict=True))
            for pair in metadata['background']
        ],
        'exclusions': [],
        'initial_parameters': [
            {'path': 'experiment.peak.' + key, 'value': value}
            for key, value in metadata['profile_parameters'].items()
        ],
    }
    native145_configure(
        actor,
        trace,
        [
            [
                native_call(
                    'create_cwl_project',
                    cif_file_id=selected[owned[0].name],
                    data_file_id=selected[owned[1].name],
                    recipe=recipe,
                )
            ]
        ],
    )
    before = actor.last['vm']
    state, replies = native_send(actor, trace, 1)
    assert replies[0]['response']['result']['success'], replies[0]['decoded']
    state = settle(actor, lambda value: value['project_present'] and not value['can_cancel'])
    assert state['connected'] and state['models'] == before['models'], (
        'CIF159: preserve original input science, bytes and authenticated owner'
    )
    assert state['handoff']['account_label'] == before['handoff']['account_label'], (
        'CIF159: preserve original input science, bytes and authenticated owner'
    )
    assert state['messages'] and not state['pending_plan'], (
        'CIF159: preserve original input science, bytes and authenticated owner'
    )
    experiments = native_inputs(state)
    assert len(experiments) == 1, (
        'CIF159: preserve original input science, bytes and authenticated owner'
    )
    expected = [
        [float(item) for item in line.split()]
        for line in owned[1].read_text().splitlines()
        if line.strip() and not line.startswith('#')
    ]
    assert len(expected) == provenance['measurement_rows'], (
        'CIF159: preserve original input science, bytes and authenticated owner'
    )
    for key, index in [('axis', 0), ('intensity', 1), ('sigma', 2)]:
        assert experiments[0][key] == [row[index] for row in expected], (
            'CIF159: preserve original input science, bytes and authenticated owner'
        )
    assert experiments[0]['weight'] == 1.0 and experiments[0]['exclusions'] == [], (
        'CIF159: preserve original input science, bytes and authenticated owner'
    )
    science = state['project']['science_observer']
    assert len(science['structures']) == 1, (
        'CIF159: preserve original input science, bytes and authenticated owner'
    )
    structure = science['structures'][0]
    assert structure['space_group'] == 'P m -3 m', (
        'CIF159: preserve original input science, bytes and authenticated owner'
    )
    assert experiments[0]['phases'] == [structure['id']], (
        'CIF159: preserve original input science, bytes and authenticated owner'
    )
    sites = {row['id']: row for row in structure['sites']}
    assert set(sites) == {'La', 'Ba', 'Co', 'O'}, (
        'CIF159: preserve original input science, bytes and authenticated owner'
    )
    for label, coordinates, occupancy in [
        ('La', [0, 0, 0], 0.5),
        ('Ba', [0, 0, 0], 0.5),
        ('Co', [0.5, 0.5, 0.5], 1),
        ('O', [0, 0.5, 0.5], 1),
    ]:
        assert sites[label]['type_symbol'] == label, (
            'CIF159: preserve original input science, bytes and authenticated owner'
        )
        assert sites[label]['fractional'] == coordinates, (
            'CIF159: preserve original input science, bytes and authenticated owner'
        )
        assert sites[label]['occupancy'] == occupancy, (
            'CIF159: preserve original input science, bytes and authenticated owner'
        )
        assert sites[label]['adp_type'] == 'Biso' and sites[label]['adp_iso'] == 0, (
            'CIF159: preserve original input science, bytes and authenticated owner'
        )
    for axis in 'abc':
        assert native_parameter(state, 'structure.cell.length_' + axis)['value'] == 3.88, (
            'CIF159: preserve original input science, bytes and authenticated owner'
        )
    for angle in ('alpha', 'beta', 'gamma'):
        assert native_parameter(state, 'structure.cell.angle_' + angle)['value'] == 90, (
            'CIF159: preserve original input science, bytes and authenticated owner'
        )
    calculation = science['calculations']
    assert len(calculation) == 1 and calculation[0]['peak_profile'] == recipe['peak_profile'], (
        'CIF159: preserve original input science, bytes and authenticated owner'
    )
    assert calculation[0]['wavelength'] == 1.49, (
        'CIF159: preserve original input science, bytes and authenticated owner'
    )
    assert [path.read_bytes() for path in owned] == original_bytes, (
        'CIF159: preserve original input science, bytes and authenticated owner'
    )
    assert not any(
        row.get('method') in {'account/login/start', 'account/logout'} for row in records(trace)
    ), (
        'CIF159: preserve original input science, bytes and authenticated owner'
    )


def test_native159_advertised_profile_recipe_is_constructible_from_public_catalog(
    generic, tmp_path
):
    actor, trace, arguments, owned = native145_selected(generic, tmp_path)
    catalog = actor.last['vm']['native_profile_catalog']
    assert catalog['beam_mode'] == 'constant wavelength', (
        'PROFILE159: expose the public CW catalog and construct its canonical recipe'
    )
    profiles = catalog['profiles']
    assert profiles and len(profiles) == len(set(profiles)), (
        'PROFILE159: expose the public CW catalog and construct its canonical recipe'
    )
    assert all(isinstance(value, str) and value for value in profiles), (
        'PROFILE159: expose the public CW catalog and construct its canonical recipe'
    )
    assert 'cwl-tch-pseudo-voigt' in profiles, (
        'PROFILE159: expose the public CW catalog and construct its canonical recipe'
    )
    arguments['recipe']['peak_profile'] = next(
        value for value in profiles if value == 'cwl-tch-pseudo-voigt'
    )
    original_bytes = [path.read_bytes() for path in owned]
    native145_configure(actor, trace, [[native_call('create_cwl_project', **arguments)]])
    thread = next(row['params'] for row in records(trace) if row.get('method') == 'thread/start')
    tools = {tool['name']: tool for tool in thread['dynamicTools']}
    assert set(tools) == {
        'inspect_project',
        'list_parameters',
        'diagnostics',
        'set_parameters',
        'set_free',
        'run_fit',
        'create_cwl_project',
        'add_relations',
        'save_project',
        'edit_background',
    }, (
        'PROFILE159: expose the public CW catalog and construct its canonical recipe'
    )
    recipe_schema = tools['create_cwl_project']['inputSchema']['properties']['recipe']
    advertised = recipe_schema['properties']['peak_profile'].get('enum')
    assert isinstance(advertised, list) and advertised, (
        'PROFILE159: the actual advertised recipe exposes accepted canonical choices'
    )
    assert all(isinstance(value, str) and value for value in advertised), (
        'PROFILE159: expose the public CW catalog and construct its canonical recipe'
    )
    assert len(advertised) == len(set(advertised)) and set(advertised) == set(profiles), (
        'PROFILE159: expose the public CW catalog and construct its canonical recipe'
    )
    state, replies = native_send(actor, trace, 1)
    assert replies[0]['response']['result']['success'], replies[0]['decoded']
    state = native145_science_settled(actor)
    assert state['connected'] and state['project_present'], (
        'PROFILE159: expose the public CW catalog and construct its canonical recipe'
    )
    assert (
        state['project']['science_observer']['calculations'][0]['peak_profile']
        == (arguments['recipe']['peak_profile'])
    ), (
        'PROFILE159: expose the public CW catalog and construct its canonical recipe'
    )
    assert [path.read_bytes() for path in owned] == original_bytes, (
        'PROFILE159: expose the public CW catalog and construct its canonical recipe'
    )


def native145_selected(generic, tmp_path, *, project=None, bad_cif=False):
    actor, trace = native_case(generic, [], project=project, connect_now=False)
    assert actor.command('native_science_enable')['reply']['enabled']
    sources = [
        ROOT / 'tests/fixtures/assistant/reference/PbSO4-Wyckoff.cif',
        Path('/tmp/relay-e11-t5-tests/seq85-private/inputs/observed.xye'),
    ]
    expected_hashes = [
        '9bc19d0995561afd78a5f0563599c032751621da994e36c7570b4f515d9f0e2f',
        'd032f549e4b7ed321595be4c0833dd917f38674037c1c87a0f0555546cdc01e9',
    ]
    owned = []
    for source, expected in zip(sources, expected_hashes, strict=True):
        assert hashlib.sha256(source.read_bytes()).hexdigest() == expected, (
            'CREATE SETUP: independently sealed originals unchanged'
        )
        destination = tmp_path / source.name
        shutil.copyfile(source, destination)
        owned.append(destination)
    if bad_cif:
        owned[0].write_text('data_original_unsupported\n_cell_length_a 8.48\n')
    token = actor.command('selected_begin')['reply']['request_id']
    assert token, 'CREATE SETUP: actual current native chooser admitted'
    assert actor.command('selected_add', request_id=token, urls=[path.as_uri() for path in owned])[
        'reply'
    ]['accepted']
    state = settle(
        actor, lambda value: len(value['selected_files']) == 2 and not value['can_cancel']
    )
    selected = {row['name']: row for row in state['selected_files']}
    assert set(selected) == {path.name for path in owned}
    arguments = {
        'cif_file_id': selected[owned[0].name]['id'],
        'data_file_id': selected[owned[1].name]['id'],
        'recipe': native145_recipe(),
    }
    assert arguments['cif_file_id'] != arguments['data_file_id']
    return actor, trace, arguments, owned


def native145_configure(actor, trace, turns):
    # All genuine-turn calls, initial selected IDs and recipe are fixed BEFORE
    # the ordinary dependency reads its config once. Later address references
    # come only from an explicit earlier successful list_parameters response.
    path = trace.parent / 'peer-input.json'
    assert not actor.peer_pid_file.exists(), 'CREATE SETUP: peer has not read prelaunch admission'
    config = json.loads(path.read_text())
    index = 0
    for calls in turns:
        for call in calls:
            index += 1
            call['call_id'] = 'original-native145-call-' + str(index)
    config['native_turn_calls'] = turns
    path.write_text(json.dumps(config))
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    connect(actor)
    loaded = json.loads(path.with_suffix('.peer-loaded.json').read_text())
    assert loaded['sha256'] == expected and loaded['native_turn_calls'] == turns, (
        'CREATE SETUP: genuine process consumed the complete original prelaunch script once'
    )
    native145_approve(actor)


def native145_approve(actor):
    if actor.last['vm']['context_consent_required']:
        assert not json.loads(actor.last['vm']['native_context']).get('error'), (
            'NATIVE SETUP: complete actual disclosure, never error JSON, is approved'
        )
        actor.command('sign_in')  # Actual connected GUI context approval, never account repair.
    assert actor.last['vm']['connected'] and not actor.last['vm']['context_consent_required']


def native145_science_settled(actor):
    return settle(
        actor,
        lambda value: (
            value['project_present']
            and not value['can_cancel']
            and not value['project']['science_observer']['calculating']
            and all(
                row['geometry_current']
                for row in value['project']['science_observer']['structures']
            )
        ),
    )


def native145_original_orbits(x, y, z):
    # All eight literal operations in the independently committed original classic CIF.
    positions = [
        (x, y, z),
        (0.5 - x, 0.5 + y, 0.5 + z),
        (x, 0.5 - y, z),
        (0.5 - x, -y, 0.5 + z),
        (-x, -y, -z),
        (0.5 + x, 0.5 - y, 0.5 - z),
        (-x, 0.5 + y, -z),
        (0.5 + x, y, 0.5 - z),
    ]
    return sorted({tuple(round(value % 1.0, 12) for value in position) for position in positions})


def test_native145_real_selected_creation_preserves_structure_measured_inputs_and_account(  # noqa: PLR0914 -- independent input, geometry and account witnesses
    generic, tmp_path
):
    actor, trace, arguments, owned = native145_selected(generic, tmp_path)
    assert not actor.last['vm']['project_present']
    input_bytes = [path.read_bytes() for path in owned]
    native145_configure(
        actor,
        trace,
        [
            [native_call('create_cwl_project', **arguments), native_call('inspect_project')],
            [
                native_call(
                    'set_parameters',
                    values=[
                        {
                            'path': 'structure.cell.length_a',
                            'value': 8.48 + 0.002,
                        }
                    ],
                ),
                native_call('set_free', flags=[{'path': 'structure.cell.length_a', 'free': True}]),
            ],
        ],
    )
    before = actor.last['vm']
    state, replies = native_send(actor, trace, 2)
    assert all(row['response']['result']['success'] for row in replies)
    state = native145_science_settled(actor)
    expected_columns = [
        [float(item) for item in line.split()]
        for line in owned[1].read_text().splitlines()
        if line.strip() and not line.lstrip().startswith('#')
    ]
    experiments = native_inputs(state)
    assert len(experiments) == 1 and experiments[0]['weight'] == 1.0
    for key, index in [('axis', 0), ('intensity', 1), ('sigma', 2)]:
        assert experiments[0][key] == [row[index] for row in expected_columns]
    assert experiments[0]['exclusions'] == [
        [row['first'], row['second']] for row in arguments['recipe']['exclusions']
    ]
    assert len(experiments[0]['phases']) == 1
    science = state['project']['science_observer']
    assert len(science['structures']) == 1
    structure = science['structures'][0]
    # Literal original CIF values and multiplicities, independent of created output.
    original = {
        'Pb': ('Pb', [0.1882, 0.25, 0.167], 4),
        'S': ('S', [0.063, 0.25, 0.686], 4),
        'O1': ('O', [-0.095, 0.25, 0.6], 4),
        'O2': ('O', [0.181, 0.25, 0.543], 4),
        'O3': ('O', [0.085, 0.026, 0.806], 8),
    }
    assert {row['id'] for row in structure['sites']} == set(original)
    assert structure['space_group'] == 'P n m a'
    for row in structure['sites']:
        symbol, coordinates, multiplicity = original[row['id']]
        assert row['type_symbol'] == symbol and row['occupancy'] == 1.0
        assert row['adp_type'] == 'Uiso' and row['adp_iso'] == 0.01
        assert any(
            tuple(value % 1.0 for value in row['fractional']) == pytest.approx(position, abs=1e-12)
            for position in native145_original_orbits(*coordinates)
        ), 'CREATE: canonicalization preserves the original physical orbit'
        actual = sorted({
            tuple(round(value % 1.0, 12) for value in atom['fractional'])
            for atom in structure['expanded']
            if atom['site_id'] == row['id']
        })
        expected = native145_original_orbits(*coordinates)
        assert all(
            atom['occupancy'] == 1.0 and atom['u_iso'] == pytest.approx(0.01, abs=1e-12)
            for atom in structure['expanded']
            if atom['site_id'] == row['id']
        )
        assert len(actual) == len(expected) == multiplicity
        for actual_position, expected_position in zip(actual, expected, strict=True):
            assert actual_position == pytest.approx(expected_position, abs=1e-12)
    assert sum(len(native145_original_orbits(*row[1])) for row in original.values()) == 24
    assert len(structure['expanded']) == 24, 'CREATE: original unit-cell composition Pb4 S4 O16'
    for path, expected in [
        ('structure.cell.length_a', 8.48),
        ('structure.cell.length_b', 5.398),
        ('structure.cell.length_c', 6.958),
    ]:
        assert native_parameter(state, path)['value'] == expected
    assert experiments[0]['phases'] == [structure['id']]
    assert state['connected'] and state['models'] == before['models']
    assert state['handoff']['account_label'] == before['handoff']['account_label']
    assert not state['pending_plan'] and not state['pending_question']
    assert [path.read_bytes() for path in owned] == input_bytes
    assert not any(
        row.get('method') in {'account/login/start', 'account/logout'} for row in records(trace)
    )
    # Real normal manual editing and a subsequent native value/free batch use this same owner.
    scalar = native_parameter(state)
    changed = actor.command('manual_value', path=scalar['path'], value=scalar['value'] + 0.001)
    assert not changed['reply']['error'] and changed['vm']['context_consent_required']
    native145_science_settled(actor)
    native145_approve(actor)
    old_count = len(native_records(trace, '.native-replies.jsonl'))
    actor.command(
        'send_text', text='Make the original bounded cell edit and free it in this created owner'
    )
    state = settle(
        actor, lambda _value: len(native_records(trace, '.native-replies.jsonl')) == old_count + 2
    )
    assert (
        native_parameter(state)['value'] == scalar['value'] + 0.002
        and native_parameter(state)['free']
    )
    assert native_inputs(state) == experiments and state['connected']


@pytest.mark.parametrize(
    'accident',
    [
        'wrong-id',
        'same-id',
        'stale-id',
        'missing-field',
        'unknown-field',
        'negative-wavelength',
        'unsorted-background',
        'late-invalid-parameter',
        'unsupported-beam',
        'malformed-cif',
        'preexisting-owner',
    ],
)
def test_native145_creation_refusals_leave_owner_and_selected_originals_whole(
    generic, tmp_path, accident
):
    existing = (
        ROOT / 'tests/fixtures/e04_t1/editable-project'
        if accident == 'preexisting-owner'
        else None
    )
    actor, trace, arguments, owned = native145_selected(
        generic, tmp_path, project=existing, bad_cif=accident == 'malformed-cif'
    )
    if accident == 'wrong-id':
        arguments['cif_file_id'] = 'Original never admitted identity'
    elif accident == 'same-id':
        arguments['data_file_id'] = arguments['cif_file_id']
    elif accident == 'stale-id':
        assert actor.command('selected_remove', id=arguments['cif_file_id'])['reply']['accepted']
    elif accident == 'missing-field':
        arguments['recipe'].pop('wavelength')
    elif accident == 'unknown-field':
        arguments['recipe']['forged_grant'] = 'Original untrusted permission'
    elif accident == 'negative-wavelength':
        arguments['recipe']['wavelength'] = -1.0
    elif accident == 'unsorted-background':
        arguments['recipe']['background'].reverse()
    elif accident == 'late-invalid-parameter':
        arguments['recipe']['initial_parameters'].append({
            'path': 'original.absent.parameter',
            'value': 1.0,
        })
    elif accident == 'unsupported-beam':
        arguments['recipe']['beam_mode'] = 'time of flight'
    original_bytes = [path.read_bytes() for path in owned]
    native145_configure(actor, trace, [[native_call('create_cwl_project', **arguments)]])
    before = actor.last['vm']
    state, replies = native_send(actor, trace, 1)
    assert not replies[0]['response']['result']['success']
    assert state['project_present'] == before['project_present'] and state['connected']
    if before['project_present']:
        assert state['project']['parameters'] == before['project']['parameters']
        assert native_inputs(state) == native_inputs(before)
        assert (
            state['project']['science_observer']['aliases']
            == before['project']['science_observer']['aliases']
        )
        assert (
            state['project']['science_observer']['constraints']
            == before['project']['science_observer']['constraints']
        )
        assert (
            state['project']['host_snapshot']['path'] == before['project']['host_snapshot']['path']
        )
    assert (
        state['models'] == before['models']
        and state['handoff']['account_label'] == before['handoff']['account_label']
    )
    assert state['selected_files'] == before['selected_files']
    assert [path.read_bytes() for path in owned] == original_bytes


def test_native145_created_project_runs_actual_fit_with_truthful_publication(generic, tmp_path):
    actor, trace, arguments, _owned = native145_selected(generic, tmp_path)
    native145_configure(
        actor,
        trace,
        [
            [native_call('create_cwl_project', **arguments), native_call('list_parameters')],
            [
                native_call(
                    'set_free',
                    flags=[
                        {
                            'path': {'$original_parameter_suffix': '.scale'},
                            'free': True,
                        }
                    ],
                )
            ],
            [native_call('run_fit')],
        ],
    )
    state, replies = native_send(actor, trace, 2)
    assert all(row['response']['result']['success'] for row in replies)
    state = native145_science_settled(actor)
    before_inputs = native_inputs(state)
    scales = [
        row
        for row in state['project']['parameters']
        if row['path'].endswith('.scale') and row['independent'] and row['fittable']
    ]
    assert len(scales) == 1, 'CREATE/FIT SETUP: actual single phase has one independent scale'
    native145_approve(actor)
    state, replies = native_send(actor, trace, 3)
    assert replies[-1]['original']['params']['arguments']['flags'] == [
        {'path': scales[0]['path'], 'free': True}
    ], 'CREATE/FIT: original script resolves only the genuinely disclosed current scale address'
    assert replies[-1]['response']['result']['success']
    state = native145_science_settled(actor)
    assert state['project']['native_observer']['fit_available'], (
        'CREATE/FIT SETUP: genuine configured normal backend must be available'
    )
    fitted_before = state
    assert not fitted_before['project']['native_observer']['record']['kind']
    native145_approve(actor)
    state, replies = native_send(actor, trace, 4)
    outcome = replies[-1]['decoded']
    assert outcome['status'] in {
        'done',
        'max_iterations',
        'no_step',
        'cancelled',
        'error',
        'superseded',
        'unavailable',
    }, 'CREATE/FIT: actual final worker report, not running=false, establishes outcome'
    report = state['project']['native_observer']
    assert not report['fit_running'] and report['record']['kind']
    assert type(outcome['adopted']) is bool and type(outcome['converged']) is bool
    assert outcome['status'] in {'done', 'max_iterations'} and outcome['adopted'], (
        'CREATE/FIT SETUP: genuine adopted moving fit, never no-step/error/unavailable substitute'
    )
    assert state['project']['parameters'] != fitted_before['project']['parameters'], (
        'CREATE/FIT SETUP: actual optimizer changes the independently captured starting model'
    )
    assert outcome['iterations'] > 0
    assert outcome['iterations'] == report['record']['iterations']
    # Existing public FitVM presentation keys differ from native wire status tokens.
    presentation = {
        'done': 'success',
        'max_iterations': 'maxIterations',
        'no_step': 'noStep',
        'cancelled': 'stopped',
        'error': 'failed',
        'superseded': 'superseded',
        'unavailable': 'failed',
    }
    assert report['fit_outcome'] == presentation[outcome['status']]
    assert report['record']['success'] == outcome['converged']
    assert native_inputs(state) == before_inputs and state['connected']
    # MAX_ITER/NO_STEP are accepted explicit statuses, never declared convergence or adequacy here.


@pytest.mark.parametrize('loaded', [False, True], ids=['empty', 'loaded'])
def test_bootstrap149_all_shipped_skills_reach_real_context_and_managed_native_thread(
    generic, loaded
):
    # Oracle: immutable package INPUT bytes plus the declared native eight-tool stage.
    # No generated Controller manifest or successful VM output supplies expectations.
    resource_root = ROOT / 'data/assistant/skills'
    entries = json.loads((resource_root / 'index.json').read_text())['skills']
    originals = {}
    for entry in entries:
        content = (resource_root / entry['path']).read_text()
        assert hashlib.sha256(content.encode()).hexdigest() == entry['sha256'], (
            'BOOTSTRAP: each independently read shipped skill retains its declared content bond'
        )
        originals[entry['id']] = {**entry, 'content': content}
    actor, trace = native_case(
        generic,
        [native_call('inspect_project')],
        project=ROOT / 'tests/fixtures/e04_t1/editable-project' if loaded else None,
        connect_now=False,
    )
    initial = actor.last['vm']
    assert 'error' not in initial['context'], (
        'BOOTSTRAP: genuine empty and loaded owners expose complete context, '
        'not an invalid-metadata envelope mislabeled as capacity exhaustion'
    )
    assert initial['context']['skills'] == [
        {
            key: originals['project-assistance'][key]
            for key in ['id', 'version', 'sha256', 'content']
        }
    ], 'BOOTSTRAP: initial disclosure preserves the complete original default guidance bond'
    assert (initial['context']['project'] is not None) == loaded, (
        'BOOTSTRAP: initial context preserves genuine projectless versus loaded ownership'
    )
    # OWNER7972 supersedes restricted4507 manual selection for this generic path.
    # The real runtime discovers all prepared resources during account/bootstrap.
    connect(actor)  # Explicit ordinary public Sign in; only the absolute owned stdio peer.
    state = actor.last['vm']
    assert state['connected'] and state['models'] and not state['last_error'], (
        'BOOTSTRAP: healthy shipped context permits real managed account/catalog readiness'
    )
    assert not state['context_consent_required'], (
        'BOOTSTRAP: genuine Sign in acknowledges exactly the disclosed current context'
    )
    thread = next(row['params'] for row in records(trace) if row.get('method') == 'thread/start')
    assert {tool['name'] for tool in thread['dynamicTools']} == {
        'inspect_project',
        'list_parameters',
        'diagnostics',
        'set_parameters',
        'set_free',
        'run_fit',
        'create_cwl_project',
        'add_relations',
        'save_project',
        'edit_background',
    }, 'BOOTSTRAP: native background stage truthfully advertises exactly ten implemented tools'
    actual = {entry['id']: entry for entry in state['skills']}
    assert set(actual) == set(originals), (
        'BOOTSTRAP: actual automatic discovery registers every shipped resource, '
        'never a trimmed passing subset'
    )
    workspace = Path(thread['cwd'])
    discoveries = [row['params'] for row in records(trace) if row.get('method') == 'skills/list']
    assert any(str(workspace) in request['cwds'] for request in discoveries), (
        'BOOTSTRAP: actual skill discovery and admitted thread use the same owned workspace'
    )
    for identity, original in originals.items():
        staged = workspace / '.agents/skills' / original['path']
        assert Path(actual[identity]['path']) == staged and staged.is_file(), (
            'BOOTSTRAP: each actual registration refers to its prepared original workspace file'
        )
        assert staged.read_bytes() == original['content'].encode(), (
            'BOOTSTRAP: prepared skills preserve exact original bytes/version/provenance'
        )
        assert actual[identity]['content'] == original['content'], (
            'BOOTSTRAP: optional catalogue exposes full registered original content, not a URL'
        )
        assert hashlib.sha256(staged.read_bytes()).hexdigest() == original['sha256'], (
            'BOOTSTRAP: every discovered original retains its independently declared content hash'
        )
        assert json.loads((resource_root / 'index.json').read_text())['skills'] == entries, (
            'BOOTSTRAP: automatic registration preserves all original packaged metadata'
        )
    methods = [row.get('method') for row in records(trace)]
    assert {'initialize', 'account/read', 'model/list', 'skills/list', 'thread/start'} <= set(
        methods
    ), 'BOOTSTRAP: readiness follows real account/catalog/workspace responses, never fake auth'
    assert not {'account/login/start', 'account/logout'} & set(methods), (
        'BOOTSTRAP: healthy managed bootstrap does not invent login or logout to repair context'
    )
    state, replies = native_send(actor, trace, 1)
    assert replies[0]['response']['result']['success'] and state['connected'], (
        'BOOTSTRAP: original reverse RPC native read works after actual context preparation'
    )
    assert (replies[0]['decoded']['project'] is not None) == loaded, (
        'BOOTSTRAP: native read reports the same real owner after bootstrap'
    )


def assert_clear_projection156(state):
    # Final public Qt topology, never an assertion halfway through begin/end rows.
    assert state['messages'] == [], 'CLEAR: no role-null placeholder may survive durable discard'
    model = state['message_model']
    assert model['count'] == model['row_count'] == 0 and model['role_count'] > 0, (
        'CLEAR: settled actual Qt model topology agrees with empty canonical history'
    )


@pytest.mark.parametrize(
    'signal',
    [
        'rowsAboutToBeRemoved',
        'rowsRemoved',
        'countChanged',
        'rowsAboutToBeInserted',
        'rowsInserted',
        'dataChanged',
    ],
)
def test_clear156_real_message_notification_reentry_preserves_final_topology_and_owner(
    generic, signal
):
    actor, trace = native_case(
        generic,
        [],
        project=ROOT / 'tests/fixtures/e04_t1/editable-project',
        script={'scenario': 'fileauth'},  # Genuine distinct successive turn/item identities.
    )
    actor.command(
        'send_text', text='Original complete history before notification reentrant Clear'
    )
    before = settle(
        actor,
        lambda value: (
            not value['can_cancel']
            and any(
                row.get('kind') == 'assistant' and row.get('status') == 'completed'
                for row in value['messages']
            )
        ),
    )
    retained = actor.command('archive')['reply']['rows']
    assert any(row.get('kind') == 'assistant' for row in retained), (
        'CLEAR SETUP: genuine completed original is durable before ordinary Qt notification'
    )
    original_owner = before['project']['host_snapshot']['path']
    assert actor.command('retirement_arm', action='clear', signal=signal)['reply']['armed']
    if signal in {'rowsAboutToBeInserted', 'rowsInserted', 'dataChanged'}:
        # A genuine later Send changes the real message projection. Its ordinary
        # Qt receiver calls actual Clear; no rows/signals are manufactured.
        actor.command('send_text', text='Original next input interrupted by notification Clear')
    else:
        actor.command('clear_history')
    state = settle(
        actor,
        lambda value: (
            value.get('retirement_observer', {}).get('returned', False) and not value['can_cancel']
        ),
    )
    observed = state['retirement_observer']
    assert observed['calls'] == 1 and observed['signal'] == signal, (
        'CLEAR SETUP: genuine ordinary Qt notification receiver reentered Clear exactly once'
    )
    assert actor.command('archive')['reply']['rows'] == [], (
        'CLEAR: successful explicit discard publishes canonical empty history'
    )
    state = actor.last['vm']
    assert_clear_projection156(state)
    assert state['connected'] and state['models'] == before['models'], (
        'CLEAR: notification reentry preserves genuinely managed account and model catalog'
    )
    assert state['handoff']['account_label'] == before['handoff']['account_label']
    assert state['project_present'] and state['project']['host_snapshot']['path'] == original_owner
    assert state['project']['parameters'] == before['project']['parameters'], (
        'CLEAR: ordinary model notification cannot edit or replace the actual owner'
    )
    native145_approve(actor)
    approved = actor.last['vm']
    scalar = native_parameter(approved)
    changed = actor.command('manual_value', path=scalar['path'], value=scalar['value'] + 0.001)
    assert not changed['reply']['error'], (
        'CLEAR: preserved owner remains genuinely manually editable'
    )
    assert changed['vm']['connected'] and changed['vm']['context_consent_required']
    assert changed['vm']['context'] != approved['context'], (
        'CLEAR: actual same-owner manual edit still publishes fresh disclosure after reentry'
    )
    assert not any(
        row.get('method') in {'account/login/start', 'account/logout'} for row in records(trace)
    ), 'CLEAR: no fabricated authentication repair masks notification retirement'


# FUTURE AFFINE8: original nine affine oracles, rebased onto actual prelaunch admission.
def native145_affine_owner(generic, tmp_path, *, with_declarations=True):
    fixture = tmp_path / 'Original-chosen-mixed-site-model'
    shutil.copytree(ROOT / 'tests/fixtures/e04_t1/editable-project', fixture)
    analysis = fixture / 'analysis/analysis.edi'
    text = analysis.read_text().replace('_edi.schema_version 2', '_edi.schema_version 3')
    if with_declarations:
        # A deliberate disabled unrelated declaration must survive append/Undo exactly.
        text += (
            '\nloop_\n_alias.id\n_alias.parameter_unique_name\n'
            'original_co_biso lbco.atom_site.Co.adp_iso\nloop_\n'
            '_constraint.id\n_constraint.expression\n_constraint.enabled\n'
            'original_inactive_co "original_co_biso = 0.5" false\n'
        )
    analysis.write_text(text)
    actor, trace = native_case(generic, [], project=fixture, connect_now=False)
    assert actor.command('native_science_enable')['reply']['enabled']
    params = actor.last['vm']['project']['parameters']
    la = next(row for row in params if row['path'] == 'structure.atom_sites[La].adp_iso')
    ba = next(row for row in params if row['path'] == 'structure.atom_sites[Ba].adp_iso')
    assert la['value'] == ba['value'] == 0.5
    changed = actor.command('manual_value', path=ba['path'], value=0.8)
    assert not changed['reply']['error']
    state = native145_science_settled(actor)
    return actor, trace, la['path'], ba['path'], state


def native145_relation_args(la, ba):
    return {
        'aliases': [
            {'id': 'original_la_biso', 'path': la},
            {'id': 'original_ba_biso', 'path': ba},
        ],
        'constraints': [
            {
                'id': 'original_chosen_shared_biso',
                'expression': 'original_ba_biso = original_la_biso',
                'enabled': True,
            }
        ],
    }


def test_native145_chosen_same_site_affine_append_and_one_complete_undo(generic, tmp_path):
    actor, trace, la, ba, before = native145_affine_owner(generic, tmp_path)
    args = native145_relation_args(la, ba)
    native145_configure(actor, trace, [[native_call('add_relations', **args)]])
    connected = native145_science_settled(actor)
    assert connected['project']['parameters'] == before['project']['parameters'], (
        'AFFINE SETUP: real managed bootstrap preserves the independently prepared model'
    )
    assert native_inputs(connected) == native_inputs(before), (
        'AFFINE SETUP: bootstrap preserves every original observation/sigma/exclusion/link'
    )
    assert connected['project']['science_observer'] == before['project']['science_observer'], (
        'AFFINE SETUP: bootstrap preserves all original declarations and refreshed geometry'
    )
    before = connected
    state, replies = native_send(actor, trace, 1)
    assert replies[0]['response']['result']['success']
    state = native145_science_settled(actor)
    science = state['project']['science_observer']
    old = before['project']['science_observer']
    assert native_parameter(state, ba)['value'] == native_parameter(state, la)['value'] == 0.5
    assert (
        len(science['aliases']) == len(old['aliases']) + 2
        and len(science['constraints']) == len(old['constraints']) + 1
    )
    assert all(row in science['aliases'] for row in old['aliases']) and all(
        row in science['constraints'] for row in old['constraints']
    )
    assert any(
        row['id'] == 'original_chosen_shared_biso'
        and row['expression'] == args['constraints'][0]['expression']
        and row['enabled'] is True
        for row in science['constraints']
    )
    assert native_inputs(state) == native_inputs(before) and state['connected']
    assert state['project']['native_observer']['can_undo']
    restored = actor.command('native_undo')
    assert restored['reply']['was_available']
    restored = native145_science_settled(actor)
    after = restored['project']['science_observer']
    assert restored['project']['parameters'] == before['project']['parameters'], (
        'AFFINE: ONE normal Undo restores complete values/free/SU, not just declarations'
    )
    assert after['aliases'] == old['aliases'] and after['constraints'] == old['constraints']
    assert after['structures'] == old['structures'], (
        'AFFINE: actual refreshed geometry describes restored original model'
    )
    assert native_inputs(restored) == native_inputs(before)
    assert (
        restored['connected']
        and restored['models'] == before['models']
        and restored['handoff']['account_label'] == before['handoff']['account_label']
    )


@pytest.mark.parametrize(
    'accident',
    [
        'late-invalid-path',
        'duplicate-alias',
        'duplicate-constraint',
        'existing-id',
        'cycle',
        'symmetry-dependent',
        'unphysical-follower',
        'structureless',
    ],
)
def test_native145_affine_refusal_is_atomic_for_declarations_and_parameter_state(
    generic, tmp_path, accident
):
    actor, trace, la, ba, before = native145_affine_owner(
        generic, tmp_path, with_declarations=accident != 'structureless'
    )
    args = native145_relation_args(la, ba)
    if accident == 'late-invalid-path':
        args['aliases'].append({'id': 'original_missing', 'path': 'original.absent.parameter'})
    elif accident == 'duplicate-alias':
        args['aliases'].append(dict(args['aliases'][0]))
    elif accident == 'duplicate-constraint':
        args['constraints'].append(dict(args['constraints'][0]))
    elif accident == 'existing-id':
        args['aliases'][0]['id'] = 'original_co_biso'
    elif accident == 'cycle':
        args['constraints'].append({
            'id': 'original_cycle',
            'expression': 'original_la_biso = original_ba_biso',
            'enabled': True,
        })
    elif accident == 'symmetry-dependent':
        args['aliases'][1]['path'] = 'structure.cell.length_b'
    elif accident == 'unphysical-follower':
        args['constraints'][0]['expression'] = 'original_ba_biso = -1'
    else:
        removed = actor.command('native_remove_structure', index=0)
        assert removed['reply']['remaining'] == 0, (
            'AFFINE SETUP: actual public structure removal reaches structureless owner'
        )
        before = native145_science_settled(actor)
    native145_configure(actor, trace, [[native_call('add_relations', **args)]])
    connected = native145_science_settled(actor)
    assert connected['project']['parameters'] == before['project']['parameters'], (
        'AFFINE SETUP: real managed bootstrap preserves the independently prepared model'
    )
    assert native_inputs(connected) == native_inputs(before), (
        'AFFINE SETUP: bootstrap preserves every original observation/sigma/exclusion/link'
    )
    assert connected['project']['science_observer'] == before['project']['science_observer'], (
        'AFFINE SETUP: bootstrap preserves all original declarations and refreshed geometry'
    )
    before = connected
    state, replies = native_send(actor, trace, 1)
    assert not replies[0]['response']['result']['success']
    assert state['project_present'] and state['connected']
    assert state['project']['parameters'] == before['project']['parameters']
    assert (
        state['project']['science_observer']['aliases']
        == before['project']['science_observer']['aliases']
    )
    assert (
        state['project']['science_observer']['constraints']
        == before['project']['science_observer']['constraints']
    )
    assert native_inputs(state) == native_inputs(before)
    assert (
        state['project']['native_observer']['can_undo']
        == before['project']['native_observer']['can_undo']
    )
    assert (
        state['models'] == before['models']
        and state['handoff']['account_label'] == before['handoff']['account_label']
    )


# Working-folder callbacks are the real public picker route; no OS gesture or
# official-runtime filesystem enforcement is claimed by this owned stdio peer.
def folder167_owner(generic, *, loaded):
    actor, trace = generic('fileauth')
    if loaded:
        project = trace.parent / 'Original-folder-owner'
        shutil.copytree(ROOT / 'tests/fixtures/e04_t1/editable-project', project)
        assert actor.command('open', path=str(project))['reply']['opened'], (
            'FOLDER SETUP: genuine original model opens through actual Session'
        )
    connect(actor)
    state = folder167_send(actor, trace, 'Original conversation before folder selection')
    surface = state['folder_observer']
    assert surface['property_present'] and all(
        surface[key]
        for key in ('begin_method', 'complete_method', 'cancel_method', 'temporary_method')
    ), 'FOLDER: the ordinary picker callback surface exists on the actual managed VM'
    assert isinstance(surface['value'], str) and not surface['value'], (
        'FOLDER: initial temporary mode discloses no chosen directory'
    )
    assert state['connected'] and state['models'] and state['handoff']['account_label'], (
        'FOLDER SETUP: genuine account/catalog and completed original conversation'
    )
    return actor, trace, state


def folder167_send(actor, trace, text):
    old_count = len(started_requests(trace))
    native145_approve(actor)  # Only actual connected approval of the current disclosure.
    actor.command('send_text', text=text)
    state = settle(
        actor,
        lambda value: (
            len(started_requests(trace)) == old_count + 1
            and not value['can_cancel']
            and any(
                row.get('kind') == 'assistant'
                and row.get('text') == 'Original fileauth reply ' + str(old_count + 1)
                and row.get('status') == 'completed'
                for row in value['messages']
            )
        ),
    )
    assert len(users(actor, text)) == 1 and state['connected'], (
        'FOLDER: original prompt is admitted once and completes without authentication repair'
    )
    return state


def folder167_preserved(before, state, trace):
    assert (
        state['connected']
        and state['handoff']['account_label'] == before['handoff']['account_label']
    ), 'FOLDER: picker/context changes retain the genuine managed identity'
    assert state['models'] == before['models'] and (
        state['selected_model'],
        state['selected_effort'],
    ) == (before['selected_model'], before['selected_effort']), (
        'FOLDER: catalog and explicit model/effort choices remain owned'
    )
    assert all(row in state['messages'] for row in before['messages']), (
        'FOLDER: choosing a directory cannot discard or rewrite retained original history'
    )
    assert state['project_present'] == before['project_present'], (
        'FOLDER: a filesystem grant cannot create or replace a native project'
    )
    if before['project_present']:
        assert state['project']['parameters'] == before['project']['parameters'], (
            'FOLDER: current project values/free/SU remain unchanged by directory selection'
        )
        assert native_inputs(state) == native_inputs(before), (
            'FOLDER: every actual observation/sigma/exclusion/link remains unchanged'
        )
        assert (
            state['project']['host_snapshot']['path'] == before['project']['host_snapshot']['path']
        ), 'FOLDER: chosen write scope does not silently move or Save As the live project'
    assert not any(
        row.get('method') in {'account/login/start', 'account/logout'} for row in records(trace)
    ), 'FOLDER: account preservation is not simulated by logging in or out again'


def folder167_policy(trace, chosen):
    traffic = records(trace)
    turn_index = max(
        index for index, row in enumerate(traffic) if row.get('method') == 'turn/start'
    )
    request = traffic[turn_index]['params']
    policy = request['sandboxPolicy']
    assert policy['type'] == 'workspaceWrite' and not policy['networkAccess'], (
        'FOLDER: chosen local scope retains the admitted no-network write policy'
    )
    assert policy['excludeSlashTmp'] and policy['excludeTmpdirEnvVar'], (
        'FOLDER: choosing one directory cannot grant global temporary roots'
    )
    cwd_value = request.get('cwd')
    if cwd_value is None:
        cwd_value = next(
            row for row in reversed(traffic[:turn_index]) if row.get('method') == 'thread/start'
        )['params']['cwd']
    cwd = Path(cwd_value).resolve()
    roots = [Path(value).resolve() for value in policy['writableRoots']]
    owned = trace.parent.resolve()
    assert roots and all(root in {chosen, cwd} for root in roots), (
        'FOLDER: writable roots are only the chosen directory and actual owned runtime workspace'
    )
    assert cwd == chosen or cwd.is_relative_to(owned), (
        'FOLDER: runtime cwd is the chosen directory or this isolated actor temporary workspace'
    )
    if chosen is None:
        assert all(root.is_relative_to(owned) for root in roots), (
            'FOLDER: temporary mode retires the external directory grant'
        )
    else:
        assert chosen in roots and chosen.parent not in roots, (
            'FOLDER: grant the user-selected directory without broadening to its parent'
        )


@pytest.mark.parametrize('loaded', [False, True], ids=['empty', 'loaded'])
def test_folder167_actual_picker_callback_grants_only_chosen_scope_and_keeps_owner(
    generic, tmp_path, loaded
):
    actor, trace, before = folder167_owner(generic, loaded=loaded)
    chosen = tmp_path / 'Original chosen working folder'
    chosen.mkdir()
    sentinel = chosen / 'Original existing user bytes.txt'
    sentinel.write_bytes(b'Original file is not overwrite authorization\n')
    intent = actor.command('working_folder_begin')['reply']
    assert intent['invoked'] and intent['intent'], 'FOLDER: actual picker mints one live intent'
    completed = actor.command(
        'working_folder_complete', intent=intent['intent'], directory=str(chosen)
    )
    assert completed['reply']['invoked'] and completed['reply']['accepted'], (
        'FOLDER: genuine local-directory callback grants its own current intent'
    )
    assert completed['vm']['folder_observer']['value'] == str(chosen.resolve()), (
        'FOLDER: actual selected physical path is disclosed to the user'
    )
    folder167_preserved(before, completed['vm'], trace)
    state = folder167_send(actor, trace, 'Original task within explicitly chosen folder')
    folder167_policy(trace, chosen.resolve())
    folder167_preserved(before, state, trace)
    assert sentinel.read_bytes() == b'Original file is not overwrite authorization\n', (
        'FOLDER: selecting a scope alone does not write an existing user file'
    )


@pytest.mark.parametrize('accident', ['cancelled', 'superseded', 'replaced-owner'])
def test_folder167_stale_picker_callback_cannot_grant_a_different_current_owner(
    generic, tmp_path, accident
):
    actor, trace, before = folder167_owner(generic, loaded=True)
    rejected = tmp_path / 'Original ungranted stale destination'
    rejected.mkdir()
    intent = actor.command('working_folder_begin')['reply']
    assert intent['invoked'] and intent['intent'], 'FOLDER SETUP: real current picker intent'
    replacement_intent = None
    if accident == 'cancelled':
        assert actor.command('working_folder_cancel', intent=intent['intent'])['reply'][
            'invoked'
        ], 'FOLDER SETUP: actual native picker cancellation callback'
    elif accident == 'superseded':
        replacement_intent = actor.command('working_folder_begin')['reply']['intent']
        assert replacement_intent and replacement_intent != intent['intent'], (
            'FOLDER SETUP: a later genuine picker request owns a distinct one-shot intent'
        )
    else:
        replacement = trace.parent / 'Original replacement native project'
        shutil.copytree(ROOT / 'tests/fixtures/e04_t1/editable-project', replacement)
        assert actor.command('open', path=str(replacement))['reply']['opened'], (
            'FOLDER SETUP: ordinary Session replaces the actual owner before delayed callback'
        )
        # This legitimate explicit project replacement is the new comparison owner.
        state = actor.last['vm']
        assert state['connected'] and state['models'] == before['models'], (
            'FOLDER SETUP: explicit owner replacement retains genuine managed account/catalog'
        )
        before = state
    rejected_reply = actor.command(
        'working_folder_complete', intent=intent['intent'], directory=str(rejected)
    )
    assert rejected_reply['reply']['invoked'] and not rejected_reply['reply']['accepted'], (
        'FOLDER: cancelled/superseded/old-owner callback cannot grant new filesystem authority'
    )
    assert (
        isinstance(rejected_reply['vm']['folder_observer']['value'], str)
        and not rejected_reply['vm']['folder_observer']['value']
    ), 'FOLDER: failed callback preserves temporary selection'
    folder167_preserved(before, rejected_reply['vm'], trace)
    if replacement_intent:
        actor.command('working_folder_cancel', intent=replacement_intent)
    state = folder167_send(actor, trace, 'Original task after refused stale folder callback')
    folder167_policy(trace, None)
    folder167_preserved(before, state, trace)
    assert list(rejected.iterdir()) == [], 'FOLDER: refused destination remains untouched'


def test_folder167_consumed_callback_is_once_only_and_temporary_retires_path_authority(
    generic, tmp_path
):
    actor, trace, before = folder167_owner(generic, loaded=True)
    chosen = tmp_path / 'Original grant'
    unrelated = tmp_path / 'Original path only mentioned in chat'
    chosen.mkdir()
    unrelated.mkdir()
    intent = actor.command('working_folder_begin')['reply']['intent']
    assert intent, 'FOLDER SETUP: genuine nonempty picker intent'
    reply = actor.command('working_folder_complete', intent=intent, directory=str(chosen))
    assert reply['reply']['invoked'] and reply['reply']['accepted'], (
        'FOLDER SETUP: genuine chosen scope is admitted before replay'
    )
    replayed = actor.command('working_folder_complete', intent=intent, directory=str(unrelated))
    assert replayed['reply']['invoked'] and not replayed['reply']['accepted'], (
        'FOLDER: consumed one-shot callback cannot move authority to a second directory'
    )
    assert replayed['vm']['folder_observer']['value'] == str(chosen.resolve()), (
        'FOLDER: refused replay retains only the originally chosen physical path'
    )
    temporary = actor.command('working_folder_temporary')
    assert temporary['reply']['invoked'] and temporary['reply']['accepted'], (
        'FOLDER: ordinary temporary-mode action revokes the selected external scope'
    )
    assert (
        isinstance(temporary['vm']['folder_observer']['value'], str)
        and not temporary['vm']['folder_observer']['value']
    ), 'FOLDER: temporary mode is disclosed by the declared empty selected-path value'
    folder167_preserved(before, temporary['vm'], trace)
    state = folder167_send(actor, trace, 'Please use this chat path: ' + str(unrelated))
    assert (
        isinstance(state['folder_observer']['value'], str)
        and not state['folder_observer']['value']
    ), 'FOLDER: a path in model/user prose cannot mint the native-picker capability'
    folder167_policy(trace, None)
    folder167_preserved(before, state, trace)
    assert list(chosen.iterdir()) == list(unrelated.iterdir()) == [], (
        'FOLDER: callback replay and prose alone cannot create files in either external path'
    )


SIGNIN206_CANARY = 'SIGNIN206_PRIVATE_REPLY_CANARY'
SIGNIN206_AUTH_URL = 'https://auth.openai.com/oauth/authorize?state=SIGNIN206_URL_CANARY'


def signin206_case(generic, variant):
    # Existing fileauth IDs/terminal machinery stay intact across genuine context refresh.
    actor, trace = generic('fileauth')
    config_path = trace.parent / 'peer-input.json'
    config = json.loads(config_path.read_text())
    config['signin206_variant'] = variant
    if variant == 'skills:unrelated':
        global_skill = trace.parent / 'original-user-skills/unrelated-original/SKILL.md'
        global_skill.parent.mkdir(parents=True)
        global_skill.write_text('---\nname: [original malformed global metadata\n---\n')
        config['signin206_unrelated_path'] = str(global_skill)
    config_path.write_text(json.dumps(config))  # Before the peer's one-time process read.
    return actor, trace


def signin206_emissions(trace):
    return native_records(trace, '.signin206-emissions.jsonl')


def signin206_diagnostic(state, method, codes, *, canary=SIGNIN206_CANARY):
    error = state['last_error']
    assert error.startswith('ChatGPT sign-in could not continue while '), (
        'SIGNIN206: original bootstrap failure has an app-authored human-readable stage'
    )
    assert any(error.endswith('[' + method + ': ' + code + '].') for code in codes), (
        'SIGNIN206: diagnostic correlates the original app request method and fixed cause family'
    )
    assert canary not in json.dumps(state), (
        'SIGNIN206: no public row/context/status field leaks the original private reply canary'
    )
    if method == 'skills/list':
        assert 'checking bundled skills' in error, (
            'SIGNIN206: skills reply is diagnosed at its original discovery stage'
        )
    assert len(error.encode()) <= 512 and not any(value in error for value in (
        canary, 'SIGNIN206_URL_CANARY', 'original@example.invalid',
        'https://auth.openai.com', '/.agents/skills/',
    )), 'SIGNIN206: bounded public diagnostics contain no raw reply/credential/URL/path canary'


def signin206_shipped(state, trace):
    resource = ROOT / 'data/assistant/skills'
    entries = json.loads((resource / 'index.json').read_text())['skills']
    expected = {entry['id']: entry for entry in entries}
    actual = {entry['id']: entry for entry in state['skills']}
    assert len(state['skills']) == len(expected) and set(actual) == set(expected), (
        'SIGNIN206: every real required shipped registration survives unrelated discovery errors'
    )
    thread = [row for row in records(trace) if row.get('method') == 'thread/start'][-1]
    workspace = Path(thread['params']['cwd'])
    for identifier, original in expected.items():
        content = (resource / original['path']).read_bytes()
        assert hashlib.sha256(content).hexdigest() == original['sha256'], (
            'SIGNIN206 SETUP: independent shipped input matches original declared content bond'
        )
        staged = workspace / '.agents/skills' / original['path']
        assert Path(actual[identifier]['path']) == staged and staged.read_bytes() == content, (
            'SIGNIN206: actual registration is its genuine immutable admitted workspace file'
        )
        assert actual[identifier]['content'].encode() == content, (
            'SIGNIN206: registering a healthy skill preserves its original complete guidance'
        )
    assert {tool['name'] for tool in thread['params']['dynamicTools']} == {
        'inspect_project', 'list_parameters', 'diagnostics', 'set_parameters', 'set_free',
        'run_fit', 'create_cwl_project', 'add_relations',
        'save_project',
        'edit_background',
    }, 'SIGNIN206: discovery errors cannot silently expand or trim the real ten-tool background stage'


@pytest.mark.parametrize('loaded', [False, True], ids=['empty', 'loaded'])
def test_signin206_unrelated_discovery_error_preserves_shipped_bootstrap_and_context(
    generic, tmp_path, loaded
):
    actor, trace = signin206_case(generic, 'skills:unrelated')
    if loaded:
        owned = trace.parent / 'original-owned-project'
        shutil.copytree(ROOT / 'tests/fixtures/e04_t1/editable-project', owned)
        assert actor.command('open', path=str(owned))['reply']['opened'], (
            'SIGNIN206 SETUP: actual owned original project opens before managed bootstrap'
        )
    original_project = actor.last['vm']['project']
    connect(actor)
    before = actor.last['vm']
    assert before['models'] and not before['last_error'], (
        'SIGNIN206: well-formed unrelated discovery failure cannot reject intact required skills'
    )
    signin206_shipped(before, trace)
    assert before['project'] == original_project, (
        'SIGNIN206: initial managed bootstrap preserves the actual empty/loaded original owner'
    )
    identity = live_original_peer(actor)
    actor.command('send_text', text='Original healthy discovery conversation')
    before = settle(actor, lambda state: not state['can_cancel'] and any(
        row.get('text') == 'Original fileauth reply 1' for row in state['messages']
    ))
    retained = {row['id']: row for row in before['messages']}
    selected = tmp_path / 'original-context-refresh.txt'
    selected.write_text('Original harmless independently supplied selected bytes\n')
    intent = actor.command('selected_begin')['reply']['request_id']
    assert intent and actor.command('selected_add', request_id=intent,
                                    urls=[selected.as_uri()])['reply']['accepted'], (
        'SIGNIN206 SETUP: genuine settled public file intake changes disclosed context'
    )
    changed = actor.last['vm']
    assert changed['connected'] and changed['context_consent_required'], (
        'SIGNIN206: context retirement preserves real authentication and requires fresh disclosure'
    )
    actor.command('sign_in')  # Existing actual GUI consent method, already-authenticated only.
    assert not actor.last['vm']['context_consent_required'], (
        'SIGNIN206: genuine connected context approval consumes only current disclosure'
    )
    actor.command('send_text', text='Original fresh input after discovery/context retirement')
    after = settle(actor, lambda state: not state['can_cancel'] and any(
        row.get('text') == 'Original fileauth reply 2' for row in state['messages']
    ))
    assert after['connected'] and original_peer_is_live(identity), (
        'SIGNIN206: healthy refreshed context uses the preserved actual managed process'
    )
    assert after['models'] == before['models'] and (
        after['handoff']['account_label'] == before['handoff']['account_label']
    ), 'SIGNIN206: discovery/context refresh preserves original account and complete model catalog'
    assert all(row in after['messages'] for row in retained.values()), (
        'SIGNIN206: refreshing required skill context retains every original conversation row'
    )
    assert len(started_requests(trace)) == 2, (
        'SIGNIN206: only the two explicit genuine inputs are admitted once; no automatic replay'
    )
    signin206_shipped(after, trace)
    responses = [row for row in signin206_emissions(trace) if row.get('method') == 'skills/list']
    assert responses and all(row['envelope']['result']['data'] for row in responses), (
        'SIGNIN206 SETUP: original skills replies actually carry healthy registrations and errors'
    )
    for response in responses:
        for entry in response['envelope']['result']['data']:
            assert entry['errors'] and all(
                Path(error['path']).is_file() and not Path(error['path']).is_relative_to(
                    Path(entry['cwd'])
                ) for error in entry['errors']
            ), 'SIGNIN206 SETUP: actual unrelated global errors are outside every staged workspace'
    assert not any(row.get('method') in {'account/login/start', 'account/logout'}
                   for row in records(trace)), (
        'SIGNIN206: unrelated discovery errors never repair authentication through login/logout'
    )


@pytest.mark.parametrize(('variant', 'codes'), [
    ('required-error', {'SKILL_DISCOVERY'}),
    ('malformed-error', {'SKILL_SHAPE', 'SKILL_DISCOVERY'}),
    ('missing', {'BUNDLED_SKILL_MISSING'}),
    ('disabled', {'BUNDLED_SKILL_DISABLED'}),
    ('duplicate', {'SKILL_SHAPE', 'BUNDLED_SKILL_CHANGED'}),
])
def test_signin206_relevant_malformed_or_incomplete_required_discovery_refuses(
    generic, variant, codes
):
    actor, trace = signin206_case(generic, 'skills:' + variant)
    actor.command('sign_in')
    state = settle(actor, lambda value: value['connected'] or bool(value['last_error']))
    assert not state['connected'] and state['last_error'], (
        'SIGNIN206: relevant/malformed/missing/disabled/duplicate required skills fail closed'
    )
    signin206_diagnostic(state, 'skills/list', codes)
    assert not any(
        row.get('method') in {'thread/start', 'turn/start'} for row in records(trace)
    ), (
        'SIGNIN206: failed required registration cannot mint thread or inference authority'
    )
    assert signin206_emissions(trace)[-1]['method'] == 'skills/list', (
        'SIGNIN206 SETUP: the original correlated discovery reply reached its real parser door'
    )


@pytest.mark.parametrize(
    ('variant', 'code'), [('shape', 'RESULT_SHAPE'), ('rpc-refused', 'RPC_REFUSED')]
)
def test_signin206_original_bad_reply_reports_fixed_stage_without_raw_canary(
    generic, variant, code
):
    actor, trace = signin206_case(generic, 'stage:' + variant)
    actor.command('sign_in')
    state = settle(actor, lambda value: value['connected'] or bool(value['last_error']))
    assert not state['connected'], (
        'SIGNIN206: original malformed/refused reply never becomes ready'
    )
    signin206_diagnostic(state, 'skills/list', {code})
    original = signin206_emissions(trace)
    assert len(original) == 1 and original[0]['method'] == 'skills/list', (
        'SIGNIN206 SETUP: exact original bad reply and original request identity are retained'
    )
    request = next(row for row in records(trace) if row.get('method') == 'skills/list')
    assert original[0]['envelope']['id'] == request['id'], (
        'SIGNIN206: failure-stage attribution belongs to the original app-owned RPC envelope'
    )
    assert SIGNIN206_CANARY in json.dumps(original[0]['envelope']), (
        'SIGNIN206 SETUP: the untrusted response actually contains the private leak canary'
    )


@pytest.mark.parametrize('kind', ['api-key', 'bedrock', 'none'])
def test_signin206_explicit_chatgpt_selection_uses_real_public_login_response_and_url(
    generic, kind
):
    actor, trace = signin206_case(generic, 'account:' + kind)
    initial_messages = actor.last['vm']['messages']
    control = actor.command('desktop_control')
    assert control['reply']['ok'] and control['vm']['report_observer']['urls'] == [
        control['reply']['control_url']
    ], 'SIGNIN206 SETUP: genuine Qt URL handler is installed before any browser handoff'
    actor.command('report_observer_reset')
    actor.command('sign_in')
    state = settle(actor, lambda value: value['connected'] or bool(value['last_error']))
    assert state['connected'] and not state['last_error'] and state['models'], (
        'SIGNIN206: explicit ChatGPT sign-in reaches real managed account/catalog readiness'
    )
    requests = records(trace)
    logins = [row for row in requests if row.get('method') == 'account/login/start']
    assert len(logins) == 1 and logins[0]['params']['type'] == 'chatgpt', (
        'SIGNIN206: known nonmanaged/null account triggers one explicit ChatGPT route'
    )
    assert state['report_observer']['urls'] == [SIGNIN206_AUTH_URL], (
        'SIGNIN206: original public login auth URL reaches Qt observer once, never a real browser'
    )
    assert state['handoff']['account_label'] == 'original@example.invalid', (
        'SIGNIN206: readiness follows fresh authoritative managed account read'
    )
    emissions = signin206_emissions(trace)
    completed = next(
        row for row in emissions if row.get('notification') == 'account/login/completed'
    )
    login_reply = next(row for row in emissions if row.get('method') == 'account/login/start')
    assert login_reply['envelope']['id'] == logins[0]['id'] and (
        login_reply['envelope']['result']['loginId'] == completed['params']['loginId']
    ), 'SIGNIN206: original login response and completed notification bind the same actual login'
    account_reads = [row for row in requests if row.get('method') == 'account/read']
    assert len(account_reads) >= 2 and (
        requests.index(account_reads[0]) < requests.index(logins[0])
        < requests.index(account_reads[-1])
    ), 'SIGNIN206: authoritative account is re-read after the original explicit login request'
    assert not any(row.get('method') in {'account/logout', 'turn/start'} for row in requests), (
        'SIGNIN206: selecting ChatGPT neither logs out another account nor sends inference'
    )
    signin206_shipped(state, trace)
    initial_ids = {row['id'] for row in initial_messages}
    assert not any(row['id'] not in initial_ids and row.get('kind') in {'user', 'assistant'}
                   for row in state['messages']), (
        'SIGNIN206: login alone cannot invent user or assistant conversation'
    )


@pytest.mark.parametrize('kind', ['unknown', 'malformed'])
def test_signin206_unknown_or_malformed_account_remains_closed_without_browser(generic, kind):
    actor, trace = signin206_case(generic, 'account:' + kind)
    actor.command('sign_in')
    state = settle(actor, lambda value: value['connected'] or bool(value['last_error']))
    assert not state['connected'], (
        'SIGNIN206: unknown/malformed account cannot acquire managed authority'
    )
    signin206_diagnostic(state, 'account/read', {'ACCOUNT_KIND', 'RESULT_SHAPE'})
    assert not state['report_observer']['urls'] and not any(
        row.get('method') in {'account/login/start', 'thread/start', 'turn/start'}
        for row in records(trace)
    ), 'SIGNIN206: malformed/unknown kind cannot trigger browser or inference fallback'


def roots207_case(generic, variant):
    actor, trace = generic('fileauth')
    config_path = trace.parent / 'peer-input.json'
    config = json.loads(config_path.read_text())
    ungranted = trace.parent / 'Original ungranted root'
    ungranted.mkdir()
    config.update(roots207_variant=variant, roots207_ungranted=str(ungranted))
    config_path.write_text(json.dumps(config))  # Genuine one-time prelaunch peer input.
    return actor, trace


def roots207_responses(trace):
    return native_records(trace, '.roots207-responses.jsonl')


def roots207_policy(response):
    policy = response['sandbox']
    assert policy['type'] == 'workspaceWrite' and policy['networkAccess'] is False and (
        policy['excludeSlashTmp'] is True and policy['excludeTmpdirEnvVar'] is True
    ), 'ROOTS207: implicit workspace representation cannot loosen network/temporary policy'
    assert response['response_cwd'] == response['request_cwd'], (
        'ROOTS207: fixtures preserve exact original cwd identity while varying explicit root shape'
    )


@pytest.mark.parametrize('variant', ['implicit', 'extra', 'duplicate-cwd'])
def test_roots207_implicit_workspace_connects_but_extra_or_duplicate_explicit_roots_refuse(
    generic, variant
):
    actor, trace = roots207_case(generic, variant)
    actor.command('sign_in')
    state = settle(actor, lambda value: value['connected'] or bool(value['last_error']))
    responses = roots207_responses(trace)
    assert len(responses) == 1, 'ROOTS207 SETUP: one original effective thread reply is observed'
    response = responses[0]
    roots207_policy(response)
    assert all(root == response['request_cwd'] for root in response['requested_roots']), (
        'ROOTS207 SETUP: genuine temporary mode admits no separately chosen directory'
    )
    if variant == 'implicit':
        assert response['returned_roots'] == [], (
            'ROOTS207 SETUP: actual original reply omits implicit cwd from additional roots'
        )
        assert state['connected'] and state['models'] and not state['last_error'], (
            'ROOTS207: validated implicit workspace access with zero additional roots connects'
        )
        signin206_shipped(state, trace)
        after = folder167_send(actor, trace, 'Original input within implicit workspace')
        assert after['connected'] and len(started_requests(trace)) == 1, (
            'ROOTS207: real current input works once after implicit-root admission'
        )
        folder167_policy(trace, None)
    else:
        if variant == 'duplicate-cwd':
            assert response['returned_roots'].count(response['request_cwd']) == 2, (
                'ROOTS207 SETUP: actual explicit array repeats cwd twice despite implicit access'
            )
        else:
            assert len(response['returned_roots']) == 1 and (
                response['returned_roots'][0] not in response['requested_roots']
            ), 'ROOTS207 SETUP: actual reply grants a real unrequested additional directory'
        assert not state['connected'], (
            'ROOTS207: implicit workspace does not forgive extra or duplicate explicit roots'
        )
        signin206_diagnostic(state, 'thread/start', {'THREAD_ROOTS'})
        assert not started_requests(trace), (
            'ROOTS207: invalid effective roots refuse before original inference admission'
        )
    assert not any(row.get('method') in {'account/login/start', 'account/logout'}
                   for row in records(trace)), (
        'ROOTS207: root validation never repairs auth by login'
    )


@pytest.mark.parametrize('variant', ['chosen-only', 'missing-chosen', 'duplicate-chosen'])
def test_roots207_real_chosen_grant_remains_required_with_implicit_workspace(
    generic, tmp_path, variant
):
    actor, trace = roots207_case(generic, variant)
    connect(actor)  # Initial response has implicit workspace and no chosen additional root.
    assert roots207_responses(trace)[0]['returned_roots'] == [], (
        'ROOTS207 SETUP: actual healthy implicit-root bootstrap precedes real picker grant'
    )
    before = folder167_send(actor, trace, 'Original conversation before current chosen grant')
    identity = live_original_peer(actor)
    chosen = tmp_path / 'Original explicitly chosen scope'
    chosen.mkdir()
    sentinel = chosen / 'Original user bytes.txt'
    sentinel.write_bytes(b'Original bytes are not overwrite authorization\n')
    intent = actor.command('working_folder_begin')['reply']
    assert intent['invoked'] and intent['intent'], 'ROOTS207 SETUP: genuine current picker intent'
    completed = actor.command(
        'working_folder_complete', intent=intent['intent'], directory=str(chosen)
    )
    assert completed['reply']['invoked'] and completed['reply']['accepted'], (
        'ROOTS207 SETUP: genuine local callback, not chat text, grants this selected path'
    )
    if variant == 'chosen-only':
        folder167_preserved(before, completed['vm'], trace)
        native145_approve(actor)
        text = 'Original current input requiring the actual selected grant'
        actor.command('send_text', text=text)
    state = settle(actor, lambda value: bool(value['last_error']) or (
        not value['can_cancel'] and len(started_requests(trace)) == 2
        and any(row.get('text') == 'Original fileauth reply 2' for row in value['messages'])
    ))
    responses = roots207_responses(trace)
    selected = [response for response in responses if str(chosen.resolve()) in (
        response['requested_roots']
    )]
    assert len(selected) == 1, (
        'ROOTS207 SETUP: real selected scope reaches one new original thread policy reply'
    )
    response = selected[0]
    roots207_policy(response)
    assert str(chosen.resolve()) != response['request_cwd'], (
        'ROOTS207 SETUP: chosen grant is genuinely additional to the current workspace'
    )
    if variant == 'chosen-only':
        assert response['returned_roots'] == [str(chosen.resolve())], (
            'ROOTS207 SETUP: effective reply retains only the genuine additional chosen grant'
        )
        assert state['connected'] and not state['last_error'] and (
            len(started_requests(trace)) == 2
        ), (
            'ROOTS207: implicit workspace plus the actual chosen grant admits original work'
        )
        folder167_preserved(before, state, trace)
        folder167_policy(trace, chosen.resolve())
        signin206_shipped(state, trace)
    else:
        if variant == 'missing-chosen':
            assert response['returned_roots'] == [], (
                'ROOTS207 SETUP: actual reply omits the genuinely requested additional grant'
            )
        else:
            assert response['returned_roots'] == [str(chosen.resolve())] * 2, (
                'ROOTS207 SETUP: actual explicit array duplicates the genuinely selected grant'
            )
        signin206_diagnostic(state, 'thread/start', {'THREAD_ROOTS'})
        assert len(started_requests(trace)) == 1, (
            'ROOTS207: missing/duplicate chosen grant cannot admit the new original input'
        )
        assert all(row in state['messages'] for row in before['messages']), (
            'ROOTS207: failed new admission retains the genuine original conversation'
        )
    assert state['folder_observer']['value'] == str(chosen.resolve()), (
        'ROOTS207: effective-policy refusal cannot discard the actual selected capability'
    )
    assert state['project_present'] == before['project_present'], (
        'ROOTS207: returning a root policy does not invent or replace the native project'
    )
    assert sentinel.read_bytes() == b'Original bytes are not overwrite authorization\n', (
        'ROOTS207: no original file is written merely by granting/refusing filesystem scope'
    )
    if variant == 'chosen-only':
        assert original_peer_is_live(identity), (
            'ROOTS207: successful selected grant uses the same genuine managed process'
        )
    assert not any(row.get('method') in {'account/login/start', 'account/logout'}
                   for row in records(trace)), (
        'ROOTS207: grant validation cannot add account/login/logout repair traffic'
    )


# SAVE211: existing native RPC + real Session loader/writer only. Expected numeric
# persistence follows the ordinary Save As control, including its IUCr rounding;
# no fitted optimum, candidate-generated golden or private save helper is used.
def save211_files(directory):
    assert directory.is_dir() and not directory.is_symlink(), (
        'SAVE: original scientific tree is a real owned directory'
    )
    paths = sorted(path for path in directory.rglob('*') if path.is_file())
    assert not any(path.is_symlink() for path in directory.rglob('*')), (
        'SAVE: native output cannot conceal an untrusted linked descendant'
    )
    return {str(path.relative_to(directory)): path.read_bytes() for path in paths}


def save211_owner(generic, tmp_path, turns, *, declared_mode=None):
    source = ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project'
    fixture = tmp_path / 'Original scientific input'
    shutil.copytree(source, fixture)
    analysis = fixture / 'analysis/analysis.edi'
    # Derived input: explicit user-declared occupancy and a disabled unrelated
    # declaration, consistent with original Co2SiO4 O1 occupancy=1/Biso=.5.
    analysis.write_text(analysis.read_text().replace('_edi.schema_version 2',
                                                  '_edi.schema_version 3') + (
        '\nloop_\n_alias.id\n_alias.parameter_unique_name\n'
        'original_o1_occupancy cosio.atom_site.O1.occupancy\n'
        'original_co1_biso cosio.atom_site.Co1.adp_iso\n'
        'loop_\n_constraint.id\n_constraint.expression\n_constraint.enabled\n'
        'original_oxygen_full "original_o1_occupancy = 1" true\n'
        'original_inactive_co "original_co1_biso = 0.5" false\n'
    ))
    if declared_mode is not None:
        assert declared_mode in {'', 'single'}, (
            'SAVE217 SETUP: only the declared blank/explicit-single paired input is selected'
        )
        text = analysis.read_text()
        row = '_fitting_mode.type single\n'
        assert text.count(row) == 1, (
            'SAVE217 SETUP: original analysis has one independently known explicit mode row'
        )
        analysis.write_text(text.replace(row, '' if not declared_mode else row, 1))
        assert ('_fitting_mode.type' not in analysis.read_text()) == (not declared_mode), (
            'SAVE217 SETUP: undeclared mode is a real omitted input row before Session loading'
        )
    actor, trace = native_case(generic, [], project=fixture, connect_now=False)
    assert actor.command('native_science_enable')['reply']['enabled'], (
        'SAVE SETUP: existing actual model/relations observer is enabled'
    )
    native145_configure(actor, trace, turns)
    state = native145_science_settled(actor)
    science = state['project']['science_observer']
    assert {row['id'] for row in science['constraints']} == {
        'original_oxygen_full', 'original_inactive_co',
    }, 'SAVE SETUP: real loader admits both original enabled/disabled declarations'
    owned = Path(state['project']['host_snapshot']['path'])
    return actor, trace, owned


def save211_grant(actor, trace, parent):
    parent.mkdir()
    sentinel = parent / 'Original user bytes.txt'
    sentinel.write_bytes(b'Original data is never overwrite authorization\n')
    before = actor.last['vm']
    intent = actor.command('working_folder_begin')['reply']
    assert intent['invoked'] and intent['intent'], (
        'SAVE SETUP: actual current native folder picker mints its own intent'
    )
    completed = actor.command('working_folder_complete', intent=intent['intent'],
                              directory=str(parent))
    assert completed['reply']['invoked'] and completed['reply']['accepted'], (
        'SAVE SETUP: actual local callback grants the selected physical parent'
    )
    state = settle(actor, lambda value: value['connected'] and not value['can_cancel'])
    folder167_preserved(before, state, trace)
    assert state['folder_observer']['value'] == str(parent.resolve()), (
        'SAVE SETUP: genuine selected directory, never a model-supplied path grant'
    )
    native145_approve(actor)
    return sentinel


def save211_send(actor, trace, count, name):
    actor.command('send_text', text=(
        'Save my current displayed project under the working folder I selected. '
        'Use this fresh child-directory name: ' + name
    ))
    state = settle(actor, lambda value: (
        len(native_records(trace, '.native-replies.jsonl')) >= count
        or bool(value['last_error']) or not value['connected']
    ))
    replies = native_records(trace, '.native-replies.jsonl')
    assert len(replies) == count and not native_records(trace, '.native-wrong-envelope.jsonl'), (
        'SAVE: each explicitly requested native operation answers its original RPC exactly once'
    )
    for reply in replies:
        assert reply['response']['id'] == reply['original']['id'] and (
            reply['response']['id'] != reply['original']['params']['callId']
        ), 'SAVE: original JSON-RPC identity is preserved, never replaced by a call ID'
        result = reply['response'].get('result')
        assert isinstance(result, dict) and type(result.get('success')) is bool, (
            'SAVE: original reverse response retains its real success/failure type'
        )
        contents = result.get('contentItems')
        assert isinstance(contents, list) and len(contents) == 1 and (
            contents[0]['type'] == 'inputText' and isinstance(contents[0]['text'], str)
        ), 'SAVE: original native outcome uses the existing official text-content envelope'
        reply['decoded'] = json.loads(contents[0]['text'])
    return state, replies


def save211_settled(actor):
    state = native145_science_settled(actor)
    assert state['connected'] and not state['can_cancel'], (
        'SAVE: genuine account and original operation have settled'
    )
    return state


def save211_compare_model(expected, actual):
    assert actual['project']['parameters'] == expected['project']['parameters'], (
        'SAVE: every value/free/SU follows ordinary native save/readback rounding'
    )
    assert native_inputs(actual) == native_inputs(expected), (
        'SAVE: all measured coordinates/intensities/sigmas/exclusions/weights/phase links survive'
    )
    assert actual['project']['mode'] == expected['project']['mode'], (
        'SAVE: actual single/joint objective mode is preserved'
    )
    old, new = (value['project']['science_observer'] for value in (expected, actual))
    assert new['aliases'] == old['aliases'] and new['constraints'] == old['constraints'], (
        'SAVE: complete alias/expression/enabled declarations survive native readback'
    )
    assert new['structures'] == old['structures'] and new['calculations'] == old['calculations'], (
        'SAVE: physical sites/occupancy/geometry and applicable calculated model survive'
    )
    assert actual['project']['native_observer']['record'] == (
        expected['project']['native_observer']['record']
    ), 'SAVE: real final fit status/iterations/success/statistics survive normal serialization'
    assert actual['project']['native_observer']['fit_can_undo'] == (
        expected['project']['native_observer']['fit_can_undo']
    ), 'SAVE: persisted normal fit recovery availability is not discarded'


def test_save211_fitted_current_project_uses_native_writer_and_real_reopen(  # noqa: PLR0914, PLR0915 -- finite real fit/writer/reopen facts
    generic, tmp_path
):
    leaf = 'Original fitted project'
    actor, trace, source = save211_owner(generic, tmp_path, [
        [native_call('run_fit')], [native_call('save_project', name=leaf)],
    ])
    parent = tmp_path / 'Original selected save parent'
    sentinel = save211_grant(actor, trace, parent)
    before_fit = actor.last['vm']
    assert before_fit['project']['native_observer']['fit_available'], (
        'SAVE SETUP: actual linked fit backend, never a replayed/fake worker'
    )
    _state, replies = native_send(actor, trace, 1)
    outcome = replies[0]['decoded']
    fitted = save211_settled(actor)
    assert outcome['status'] in {'done', 'max_iterations'} and outcome['adopted'], (
        'SAVE SETUP: a genuine adopted worker result precedes saving'
    )
    assert outcome['iterations'] > 0 and fitted['project']['parameters'] != (
        before_fit['project']['parameters']
    ), 'SAVE SETUP: actual moving fit, not no-step/unavailable/cached state'
    assert any(row['uncertainty'] is not None and row['uncertainty'] > 0
               for row in fitted['project']['parameters']), (
        'SAVE SETUP: actual nonzero fitted SUs must exercise native persistence'
    )
    assert fitted['project']['native_observer']['record']['kind'] and (
        fitted['project']['native_observer']['fit_results']
    ), 'SAVE SETUP: real fit report/results are published before saving'
    assert native_inputs(fitted) == native_inputs(before_fit), (
        'SAVE: fitting cannot replace original measured observations or objective weights'
    )
    chi_square = fitted['project']['native_observer']['record']['reduced_chi_square']
    assert type(chi_square) in {int, float} and (
        float('-inf') < chi_square < float('inf')
    ), 'SAVE SETUP: actual published fit statistic is finite, never invented success'
    # Existing ordinary native Save As supplies the pre-existing serialization
    # contract, not an unrounded-bit oracle for fitted values/SUs.
    control = tmp_path / 'Original ordinary Save As control'
    control.mkdir()
    intent = actor.command('save_as_begin')['reply']
    assert intent['invoked'] and intent['intent'], (
        'SAVE SETUP: existing ordinary Session Save As captures the settled fitted model'
    )
    manual = actor.command('save_as_complete', intent=intent['intent'],
                           parent=str(control), leaf='')
    assert manual['reply']['invoked'] and manual['reply']['accepted'], (
        'SAVE SETUP: genuine ordinary native writer establishes its SU-rounding control'
    )
    ordinary = save211_settled(actor)
    assert native_inputs(ordinary) == native_inputs(fitted), (
        'SAVE CONTROL: ordinary serialization preserves original measured columns and weights'
    )
    for key in ('kind', 'exit_reason', 'success', 'iterations'):
        assert ordinary['project']['native_observer']['record'][key] == (
            fitted['project']['native_observer']['record'][key]
        ), 'SAVE CONTROL: ordinary saving retains the genuine final fit identity'
    input_files, control_files = save211_files(source), save211_files(control)
    native145_approve(actor)
    _state, replies = save211_send(actor, trace, 2, leaf)
    saved = save211_settled(actor)
    result = replies[-1]['decoded']
    destination = parent / leaf
    assert replies[-1]['response']['result']['success'] and result['status'] == 'succeeded', (
        'SAVE: successful original native RPC truthfully reports the completed save'
    )
    assert all(result.get(key) is True for key in ('committed', 'reopened', 'active')), (
        'SAVE: success requires actual disk commit, verified reopen and displayed active adoption'
    )
    assert Path(result['destination']).resolve() == destination.resolve(), (
        'SAVE: destination is exactly the fresh basename under the genuine chosen grant'
    )
    assert Path(saved['project']['host_snapshot']['path']).resolve() == destination.resolve(), (
        'SAVE: displayed project acquires the verified saved path, not a copy-only claim'
    )
    assert not saved['project']['host_snapshot']['modified'] and not (
        saved['handoff']['needs_save_as']
    ), 'SAVE: displayed current project becomes normally saved/unmodified'
    assert saved['connected'] and saved['handoff']['account_label'] == (
        fitted['handoff']['account_label']
    ), 'SAVE: native saving preserves genuine managed authentication'
    assert saved['models'] == fitted['models'] and (
        saved['selected_model'], saved['selected_effort']
    ) == (fitted['selected_model'], fitted['selected_effort']), (
        'SAVE: native saving retains original model catalog and explicit choices'
    )
    assert all(row in saved['messages'] for row in fitted['messages']), (
        'SAVE: real fitted-project saving cannot discard the originating retained conversation'
    )
    assert save211_files(source) == input_files and save211_files(control) == control_files, (
        'SAVE: native save never rewrites original source or the ordinary control'
    )
    assert sentinel.read_bytes() == b'Original data is never overwrite authorization\n', (
        'SAVE: unrelated user bytes remain exact after native publication'
    )
    assert sorted(path.name for path in parent.iterdir()) == [leaf, sentinel.name], (
        'SAVE: fresh publication leaves only the requested child and original user file'
    )
    saved_files = save211_files(destination)
    assert save212_ordinary_bytes({
        name: data for name, data in saved_files.items() if name.endswith('.edi')
    }) == save212_ordinary_bytes({
        name: data for name, data in control_files.items() if name.endswith('.edi')
    }), 'SAVE: same ordinary native science/fit bytes differ only by valid last-modified timestamp'
    loader, _ = generic('fileauth')
    assert loader.command('native_science_enable')['reply']['enabled'], (
        'SAVE: second real Session exposes existing structural readback'
    )
    assert loader.command('open', path=str(control))['reply']['opened'], (
        'SAVE CONTROL: independent real Session loader reads the ordinary native tree'
    )
    expected = native145_science_settled(loader)
    assert loader.command('open', path=str(destination))['reply']['opened'], (
        'SAVE: a second genuine Session independently reopens committed native files'
    )
    reopened = native145_science_settled(loader)
    save211_compare_model(expected, reopened)
    save211_compare_model(expected, saved)
    assert not any(row.get('method') in {'account/login/start', 'account/logout'}
                   for row in records(trace)), 'SAVE: saving never repairs account by login/logout'


@pytest.mark.parametrize('accident', [
    'no-grant', 'existing-directory', 'existing-file', 'existing-symlink',
    'parent-traversal', 'nested-path', 'absolute-path',
])
def test_save211_refusal_preserves_current_owner_original_inputs_and_user_bytes(  # noqa: PLR0914 -- finite original refusal state
    generic, tmp_path, accident
):
    parent = tmp_path / 'Original selected save parent'
    outside = tmp_path / 'Original outside scope'
    outside.mkdir()
    outside_file = outside / 'Original owner bytes'
    outside_file.write_bytes(b'Independent original outside bytes\n')
    leaf = 'Original save target'
    names = {'parent-traversal': '../Original outside scope/escaped',
             'nested-path': 'nested/child', 'absolute-path': str(outside / 'escaped')}
    requested = names.get(accident, leaf)
    actor, trace, source = save211_owner(generic, tmp_path, [
        [native_call('save_project', name=requested)],
    ])
    if accident != 'no-grant':
        save211_grant(actor, trace, parent)
    else:
        parent.mkdir()
        assert isinstance(actor.last['vm']['folder_observer']['value'], str) and not (
            actor.last['vm']['folder_observer']['value']
        ), (
            'SAVE SETUP: chat name/input cannot substitute for a real selected grant'
        )
    target = parent / leaf
    if accident == 'existing-directory':
        target.mkdir()
        (target / 'Original collision bytes').write_bytes(b'Original directory collision\n')
    elif accident == 'existing-file':
        target.write_bytes(b'Original file collision\n')
    elif accident == 'existing-symlink':
        target.symlink_to(outside, target_is_directory=True)
    original_files = save211_files(source)
    outside_bytes = save211_files(outside)
    parent_entries = sorted(path.name for path in parent.iterdir())
    before = actor.last['vm']
    native145_approve(actor)
    state, replies = save211_send(actor, trace, 1, requested)
    result = replies[0]['decoded']
    assert not replies[0]['response']['result']['success'] and (
        isinstance(result.get('status'), str) and result['status']
        and result['status'] != 'succeeded'
    ), (
        'SAVE: absent grant/collision/path escape refuses on the original RPC before success'
    )
    assert not any(result.get(key) for key in ('committed', 'reopened', 'active')), (
        'SAVE: before-commit refusal cannot manufacture disk/reopen/adoption facts'
    )
    assert isinstance(result.get('message'), str) and result['message'], (
        'SAVE: refused original request retains an honest human-readable outcome'
    )
    assert state['project'] == before['project'], (
        'SAVE: rejected save preserves actual current values/free/SUs/relations/fit/path/modified'
    )
    assert state['connected'] and state['handoff']['account_label'] == (
        before['handoff']['account_label']
    ), 'SAVE: before-write save refusal preserves genuine account ownership'
    assert state['models'] == before['models'], (
        'SAVE: refused native save retains the original real model catalog'
    )
    assert all(row in state['messages'] for row in before['messages']), (
        'SAVE: before-write refusal retains the original conversation'
    )
    assert save211_files(source) == original_files and save211_files(outside) == outside_bytes, (
        'SAVE: failed native save cannot rewrite original input or external user bytes'
    )
    assert sorted(path.name for path in parent.iterdir()) == parent_entries, (
        'SAVE: refused publication leaves no additional staged or partially saved child'
    )
    if accident == 'existing-directory':
        assert (target / 'Original collision bytes').read_bytes() == (
            b'Original directory collision\n'
        ), 'SAVE: occupied directory bytes remain exact on refusal'
    elif accident == 'existing-file':
        assert target.read_bytes() == b'Original file collision\n', (
            'SAVE: occupied file bytes remain exact on refusal'
        )
    elif accident == 'existing-symlink':
        assert target.is_symlink() and target.resolve() == outside.resolve(), (
            'SAVE: collision with an existing link neither follows nor replaces the user entry'
        )
    else:
        assert not target.exists() and not (outside / 'escaped').exists(), (
            'SAVE: absent grant or invalid basename cannot publish inside or outside scope'
        )


def test_save211_first_native_save_clears_real_current_modified_state(
    generic, tmp_path
):
    leaf = 'Original first native save'
    actor, trace, source = save211_owner(generic, tmp_path, [
        [native_call('save_project', name=leaf)],
    ])
    parent = tmp_path / 'Original first-save chosen parent'
    save211_grant(actor, trace, parent)
    original = native_parameter(actor.last['vm'])
    requested = original['value'] + 0.01  # Explicit finite test edit, no fit/optimum oracle.
    changed = actor.command('manual_value', path=original['path'], value=requested)
    assert not changed['reply']['error'], (
        'SAVE SETUP: real ordinary edit changes the current model'
    )
    before = save211_settled(actor)
    assert before['project']['host_snapshot']['modified'] and (
        native_parameter(before)['value'] == requested
    ), 'SAVE SETUP: actual dirty displayed model, never a fabricated modified flag'
    original_files = save211_files(source)
    native145_approve(actor)
    state, replies = save211_send(actor, trace, 1, leaf)
    saved = save211_settled(actor)
    result = replies[0]['decoded']
    assert replies[0]['response']['result']['success'] and result['status'] == 'succeeded', (
        'SAVE: first native save of the dirty current model actually succeeds'
    )
    assert all(result.get(key) is True for key in ('committed', 'reopened', 'active')), (
        'SAVE: first-save success includes real native commit/reopen/active ownership'
    )
    assert Path(saved['project']['host_snapshot']['path']).resolve() == (
        parent / leaf
    ).resolve(), (
        'SAVE: first native save changes the displayed active path to its verified child'
    )
    assert not saved['project']['host_snapshot']['modified'] and not (
        saved['handoff']['needs_save_as']
    ), 'SAVE: real dirty displayed model becomes normally saved/unmodified'
    assert native_parameter(saved)['value'] == requested and (
        native_parameter(saved)['free'] == original['free']
    ), 'SAVE: the actual current edited value/free state is saved, never the older disk model'
    assert native_inputs(saved) == native_inputs(before), (
        'SAVE: first active save retains original observations/sigmas/exclusions/weights'
    )
    assert save211_files(source) == original_files and saved['connected'], (
        'SAVE: first active save preserves source inputs and genuine account'
    )
    assert state['project_present'], (
        'SAVE: truthful native result keeps a displayed current project'
    )


def save212_ordinary_bytes(files):
    normalized = dict(files)
    assert 'project.edi' in files, 'SAVE: native closure retains its complete project document'
    lines = files['project.edi'].splitlines(keepends=True)
    matched = []
    tag = b'_metadata.last_modified'
    for index, line in enumerate(lines):
        if not line.startswith(tag) or line[len(tag):len(tag) + 1] not in {b' ', b'\t'}:
            continue
        scalar = line[len(tag):].strip()
        words = shlex.split(scalar.decode('utf-8'))
        assert len(words) == 1, 'SAVE: only one well-formed last-modified timestamp is volatile'
        datetime.strptime(words[0], '%d %b %Y %H:%M:%S').replace(tzinfo=UTC)
        matched.append(index)
        lines[index] = line.replace(scalar, b"'ordinary native save timestamp'", 1)
    assert len(matched) == 1, (
        'SAVE: only the named last-modified scalar may differ between legitimate saves'
    )
    normalized['project.edi'] = b''.join(lines)
    return normalized


@pytest.mark.parametrize('declared_mode', ['', 'single'], ids=['undeclared', 'explicit-single'])
def test_save217_undeclared_single_keeps_real_fit_and_native_roundtrip(  # noqa: PLR0914, PLR0915 -- finite real fit/default-mode/persistence facts
    generic, tmp_path, declared_mode
):
    leaf = 'Original default-mode save'
    actor, trace, source = save211_owner(generic, tmp_path, [
        [native_call('run_fit')], [native_call('save_project', name=leaf)],
    ], declared_mode=declared_mode)
    assert actor.last['vm']['project']['mode'] == declared_mode, (
        'SAVE217 SETUP: actual Session retains the declared or genuinely omitted input mode'
    )
    parent = tmp_path / 'Original mode-save chosen parent'
    sentinel = save211_grant(actor, trace, parent)
    before_fit = actor.last['vm']
    assert before_fit['project']['native_observer']['fit_available'], (
        'SAVE217 SETUP: actual linked fit backend, never a synthetic worker'
    )
    _state, fit_replies = native_send(actor, trace, 1)
    outcome = fit_replies[0]['decoded']
    fitted = save211_settled(actor)
    assert outcome['status'] in {'done', 'max_iterations'} and outcome['adopted'], (
        'SAVE217 SETUP: a genuine adopted fit precedes saving in both mode representations'
    )
    assert outcome['iterations'] > 0 and fitted['project']['parameters'] != (
        before_fit['project']['parameters']
    ), 'SAVE217 SETUP: actual moving fit, never no-step/unavailable/cached success'
    assert any(row['uncertainty'] is not None and row['uncertainty'] > 0
               for row in fitted['project']['parameters']), (
        'SAVE217 SETUP: real fitted SUs exercise normal native rounding'
    )
    chi_square = fitted['project']['native_observer']['record']['reduced_chi_square']
    assert type(chi_square) in {int, float} and float('-inf') < chi_square < float('inf'), (
        'SAVE217 SETUP: actual fit statistic is finite without an optimum golden'
    )
    assert fitted['project']['mode'] == declared_mode, (
        'SAVE217: default-single fitting preserves the original raw declaration before save'
    )
    assert native_inputs(fitted) == native_inputs(before_fit), (
        'SAVE217: default mode fitting preserves original observations/sigmas/masks/weights'
    )
    original_files = save211_files(source)
    native145_approve(actor)
    assert actor.last['vm']['project']['mode'] == declared_mode, (
        'SAVE217 SETUP: first native save actually receives the undeclared or explicit mode'
    )
    _state, replies = save211_send(actor, trace, 2, leaf)
    saved = save211_settled(actor)
    result = replies[-1]['decoded']
    destination = parent / leaf
    assert replies[-1]['response']['result']['success'] and result['status'] == 'succeeded', (
        'SAVE217: blank effective-single and explicit-single both save on the original RPC'
    )
    assert all(result.get(key) is True for key in ('committed', 'reopened', 'active')), (
        'SAVE217: success requires actual disk commit, real reopen and current active adoption'
    )
    assert Path(result['destination']).resolve() == destination.resolve() and (
        Path(saved['project']['host_snapshot']['path']).resolve() == destination.resolve()
    ), 'SAVE217: the actual displayed saved path is the requested child under the genuine grant'
    assert not saved['project']['host_snapshot']['modified'] and not (
        saved['handoff']['needs_save_as']
    ), 'SAVE217: the actual displayed model is normally saved/unmodified'
    assert (saved['project']['mode'] or 'single') == 'single', (
        'SAVE217: active adoption preserves effective single, allowing ordinary canonical storage'
    )
    assert native_inputs(saved) == native_inputs(fitted), (
        'SAVE217: mode admission never replaces original measured data or objective weights'
    )
    assert [(row['path'], row['free']) for row in saved['project']['parameters']] == [
        (row['path'], row['free']) for row in fitted['project']['parameters']
    ], 'SAVE217: saving default single preserves every actual parameter free declaration'
    for key in ('kind', 'exit_reason', 'success', 'iterations'):
        assert saved['project']['native_observer']['record'][key] == (
            fitted['project']['native_observer']['record'][key]
        ), 'SAVE217: native saving retains the original actual final fit identity'
    assert saved['connected'] and saved['handoff']['account_label'] == (
        fitted['handoff']['account_label']
    ) and saved['models'] == fitted['models'], (
        'SAVE217: both mode representations preserve genuine account/catalog ownership'
    )
    assert all(row in saved['messages'] for row in fitted['messages']), (
        'SAVE217: native saving preserves the originating retained conversation'
    )
    assert save211_files(source) == original_files and sentinel.read_bytes() == (
        b'Original data is never overwrite authorization\n'
    ), 'SAVE217: the original raw-mode input and unrelated user bytes remain exact'
    assert sorted(path.name for path in parent.iterdir()) == [leaf, sentinel.name], (
        'SAVE217: publication creates only the requested child, without residual staging'
    )
    saved_files = save211_files(destination)
    control = tmp_path / 'Original ordinary mode control'
    control.mkdir()
    intent = actor.command('save_as_begin')['reply']
    assert intent['invoked'] and intent['intent'], (
        'SAVE217 CONTROL: ordinary Save As captures the actual saved fitted model'
    )
    manual = actor.command('save_as_complete', intent=intent['intent'],
                           parent=str(control), leaf='')
    assert manual['reply']['invoked'] and manual['reply']['accepted'], (
        'SAVE217 CONTROL: the existing ordinary native writer provides real readback bytes'
    )
    save211_settled(actor)
    assert save211_files(destination) == saved_files and save212_ordinary_bytes({
        name: data for name, data in saved_files.items() if name.endswith('.edi')
    }) == save212_ordinary_bytes({
        name: data for name, data in save211_files(control).items() if name.endswith('.edi')
    }), 'SAVE217: saved native science/fit bytes are ordinary-writer stable except valid timestamp'
    loader, _ = generic('fileauth')
    assert loader.command('native_science_enable')['reply']['enabled'], (
        'SAVE217: a second real Session exposes existing structural readback'
    )
    assert loader.command('open', path=str(control))['reply']['opened'], (
        'SAVE217 CONTROL: the ordinary native tree genuinely reopens'
    )
    expected = native145_science_settled(loader)
    assert loader.command('open', path=str(destination))['reply']['opened'], (
        'SAVE217: the first native saved tree genuinely reopens in an independent Session'
    )
    reopened = native145_science_settled(loader)
    assert expected['project']['mode'] == reopened['project']['mode'] == 'single', (
        'SAVE217: ordinary persisted/readback mode is canonical single for either declaration'
    )
    save211_compare_model(expected, reopened)
    assert reopened['project']['parameters'] == saved['project']['parameters'] and (
        native_inputs(reopened) == native_inputs(saved)
    ), 'SAVE217: current adopted rounded values/free/SUs/data match the real saved-file loader'
    assert reopened['project']['science_observer'] == saved['project']['science_observer'], (
        'SAVE217: current physical sites/geometry/aliases/relations match genuine native readback'
    )
    assert reopened['project']['native_observer']['record'] == (
        saved['project']['native_observer']['record']
    ), 'SAVE217: the complete adopted fit record matches actual persisted native readback'
    assert not any(row.get('method') in {'account/login/start', 'account/logout'}
                   for row in records(trace)), (
        'SAVE217: saving never repairs auth through login/logout'
    )


@pytest.mark.parametrize('case', ['unsaved', 'saved', 'invalid-recipe', 'structure-residue'])
def test_completion254_real_named_empty_owner_and_native_creation(generic, tmp_path, case):  # noqa: PLR0914, PLR0915 -- independent source science and actual owner/Undo witnesses
    """Complete the genuine named empty owner, never substitute a new project."""
    saved = case == 'saved'
    requested = {
        'name': 'Original named empty owner',
        'title': 'Original owner title',
        'description': 'Original owner description, distinct from the supplied recipe',
        'authors': 'Original independent author',
        'su_rule': 'iucr_99',
        'report_libraries': True,
        'location': str(tmp_path / 'original-empty-owner') if saved else '',
    }

    def make_original_owner(scenario):
        # Same real generic Session/stdio fixture: create the real owner BEFORE
        # the ordinary selected-file helper mints its actual current IDs.
        actor, trace = generic(scenario)
        created = actor.command('named_empty_create', **requested)
        assert created['reply']['created'] and created['vm']['project_present'], (
            'COMPLETE: actual public Session creates a genuine named empty owner'
        )
        return actor, trace

    actor, trace, arguments, owned = native145_selected(make_original_owner, tmp_path)
    if case == 'structure-residue':
        assert actor.command('publication_create_structure')['reply']['created'], (
            'COMPLETE: real ordinary structure creation supplies genuine nonempty residue'
        )
        settle(actor, lambda value: not value['project']['science_observer']['calculating'])
    if case == 'invalid-recipe':
        arguments['recipe'].pop('wavelength')
    native145_configure(actor, trace, [[native_call('create_cwl_project', **arguments),
                                       native_call('inspect_project')]])
    before = actor.last['vm']
    original = before['project']['empty_completion_observer']
    assert original['same_owner'] and original['same_core'], (
        'COMPLETE: original live PVM and embedded core identities are actually observed'
    )
    assert original['metadata']['name'] == requested['name'] and (
        original['metadata']['title'] == requested['title']
        and original['metadata']['description'] == requested['description']
        and original['metadata']['authors'] == requested['authors']
        and original['metadata']['created']
    ), 'COMPLETE: original user metadata is independent of supplied recipe defaults'
    assert original['settings']['su_rule'] == 'iucr_99' and (
        original['settings']['html_offline'] is True
    ), 'COMPLETE: explicit original project settings exist before native admission'
    assert original['experiments'] == 0 and original['structures'] == (
        1 if case == 'structure-residue' else 0
    ), 'COMPLETE: empty or genuine residue premise is observed, never fabricated'
    source_directory = Path(original['path']) if saved else None
    source_files = None
    if saved:
        assert source_directory.is_dir() and source_directory.resolve() == (
            Path(requested['location']).resolve()
        ) and source_directory.resolve().is_relative_to(tmp_path.resolve()) and (
            source_directory / 'project.edi'
        ).is_file(), (
            'COMPLETE: saved named empty setup really owns a normally written native project'
        )
        source_files = save211_files(source_directory)
    else:
        assert not original['path'], 'COMPLETE: actual unsaved owner has no saved directory'
    original_bytes = [path.read_bytes() for path in owned]
    state, replies = native_send(actor, trace, 2)
    actual = state['project']['empty_completion_observer']
    assert actual['same_owner'] and actual['same_core'] and (
        actual['owner_identity'] == original['owner_identity']
        and actual['core_identity'] == original['core_identity']
    ), 'COMPLETE: original Session PVM/core identity survives success or before-write refusal'
    assert actual['metadata'] == original['metadata'] and (
        actual['settings'] == original['settings']
        and actual['path'] == original['path']
        and actual['metadata_path'] == original['metadata_path']
    ), 'COMPLETE: user metadata/settings/location survive independently of recipe project naming'
    assert state['selected_files'] == before['selected_files'] and (
        [path.read_bytes() for path in owned] == original_bytes
    ), 'COMPLETE: genuine selected IDs and every immutable original input byte remain owned'
    assert state['connected'] and state['models'] == before['models'] and (
        state['handoff']['account_label'] == before['handoff']['account_label']
        and state['handoff']['needs_save_as'] == before['handoff']['needs_save_as']
    ), 'COMPLETE: same owner keeps genuine account/catalog and ordinary save lifecycle'
    assert not state['pending_plan'] and not state['pending_question'], (
        'COMPLETE: delegated original objective does not invent a second approval flow'
    )
    assert all(row in state['messages'] for row in before['messages']), (
        'COMPLETE: original retained history remains after native completion or refusal'
    )
    if saved:
        assert save211_files(source_directory) == source_files, (
            'COMPLETE: completion does not silently overwrite the saved empty source'
        )
    if case in {'invalid-recipe', 'structure-residue'}:
        assert not replies[0]['response']['result']['success'], (
            'COMPLETE: malformed recipe or actual populated residue refuses before mutation'
        )
        assert state['project']['parameters'] == before['project']['parameters'] and (
            native_inputs(state) == native_inputs(before)
            and state['project']['science_observer'] == before['project']['science_observer']
            and actual == original
            and state['project']['native_observer']['can_undo']
            == before['project']['native_observer']['can_undo']
        ), 'COMPLETE: refused original owner remains wholly unchanged with prior Undo intact'
        return
    assert all(row['response']['result']['success'] for row in replies), (
        'COMPLETE: genuine create and inspect settle on their original once-only envelopes'
    )
    state = native145_science_settled(actor)
    actual = state['project']['empty_completion_observer']
    assert actual['structures'] == actual['experiments'] == 1 and actual['same_owner'] and (
        actual['same_core'] and state['project']['host_snapshot']['modified']
    ), 'COMPLETE: real completion populates and dirties this same owner without claiming saved'
    expected_columns = [
        list(map(float, line.split())) for line in owned[1].read_text().splitlines()
        if line.strip() and not line.lstrip().startswith('#')
    ]
    experiments = native_inputs(state)
    assert len(experiments) == 1 and experiments[0]['weight'] == 1.0, (
        'COMPLETE: original single measured experiment and unit dataset weight are preserved'
    )
    for key, column in [('axis', 0), ('intensity', 1), ('sigma', 2)]:
        assert experiments[0][key] == [row[column] for row in expected_columns], (
            'COMPLETE: every literal independent coordinate/intensity/sigma is preserved'
        )
    assert experiments[0]['exclusions'] == [
        [row['first'], row['second']] for row in arguments['recipe']['exclusions']
    ], 'COMPLETE: explicitly supplied measurement masks survive same-owner population'
    science = state['project']['science_observer']
    assert len(science['structures']) == 1 and all(
        row['current'] for row in science['calculations']
    ), 'COMPLETE: actual real worker publishes current geometry/calculation after creation'
    structure = science['structures'][0]
    original_sites = {
        'Pb': ('Pb', [0.1882, 0.25, 0.167], 4),
        'S': ('S', [0.063, 0.25, 0.686], 4),
        'O1': ('O', [-0.095, 0.25, 0.6], 4),
        'O2': ('O', [0.181, 0.25, 0.543], 4),
        'O3': ('O', [0.085, 0.026, 0.806], 8),
    }
    assert structure['space_group'] == 'P n m a' and (
        {row['id'] for row in structure['sites']} == set(original_sites)
    ), 'COMPLETE: original classic-CIF space group and all literal atom sites remain'
    for row in structure['sites']:
        symbol, coordinates, multiplicity = original_sites[row['id']]
        assert row['type_symbol'] == symbol and row['occupancy'] == 1.0 and (
            row['adp_type'] == 'Uiso' and row['adp_iso'] == 0.01
        ), 'COMPLETE: original species/occupancy/ADP convention and value are independent literals'
        expected_orbit = native145_original_orbits(*coordinates)
        images = [atom for atom in structure['expanded'] if atom['site_id'] == row['id']]
        actual_orbit = sorted({tuple(round(x % 1.0, 12) for x in atom['fractional'])
                               for atom in images})
        assert len(actual_orbit) == len(expected_orbit) == multiplicity, (
            'COMPLETE: original site multiplicity survives modulo lattice translations'
        )
        for position, expected in zip(actual_orbit, expected_orbit, strict=True):
            assert position == pytest.approx(expected, abs=1e-12), (
                'COMPLETE: every canonical physical position follows original CIF symmetry'
            )
        assert all(
            atom['occupancy'] == 1.0 and atom['u_iso'] == pytest.approx(0.01, abs=1e-12)
            for atom in images
        ), 'COMPLETE: every image keeps original occupancy/ADP'
    assert experiments[0]['phases'] == [structure['id']], (
        'COMPLETE: actual measured pattern is linked to the original single imported phase'
    )
    for path, value in [('structure.cell.length_a', 8.48), ('structure.cell.length_b', 5.398),
                        ('structure.cell.length_c', 6.958)]:
        parameter = native_parameter(state, path)
        assert parameter['value'] == value and not parameter['free'] and (
            parameter['uncertainty'] == 0
        ), 'COMPLETE: original bare CIF cell value/fixed flag/numeric zero SU remain exact'
    assert state['project']['native_observer']['can_undo'], (
        'COMPLETE: real same-owner population installs its ordinary complete Undo record'
    )
    assert actor.command('native_undo')['reply']['was_available'], (
        'COMPLETE: exactly one actual ordinary Undo is consumed for complete population'
    )
    undone = settle(actor, lambda value: (
        value['project']['empty_completion_observer']['structures'] == 0
        and value['project']['empty_completion_observer']['experiments'] == 0
        and not value['project']['science_observer']['calculating']
    ))
    empty = undone['project']['empty_completion_observer']
    assert empty == original and (
        undone['project']['parameters'] == before['project']['parameters']
        and undone['project']['science_observer'] == before['project']['science_observer']
        and undone['project']['mode'] == before['project']['mode']
        and undone['project']['native_observer']['record']
        == before['project']['native_observer']['record']
        and undone['project']['native_observer']['can_undo']
        == before['project']['native_observer']['can_undo']
    ), 'COMPLETE: one Undo restores original empty science/settings/identity and prior history'
    assert undone['connected'] and undone['models'] == before['models'] and (
        undone['selected_files'] == before['selected_files']
        and undone['handoff']['account_label'] == before['handoff']['account_label']
    ), 'COMPLETE: actual account/catalog/source ownership survive complete native Undo'
    if saved:
        assert save211_files(source_directory) == source_files, (
            'COMPLETE: one model Undo does not overwrite the independent saved empty tree'
        )


@pytest.mark.parametrize('variant', ['effective', 'missing', 'false', 'malformed'])
def test_ephemeral257_actual_thread_admission_and_live_turn_clear_ownership(  # noqa: PLR0914, PLR0915 -- original reply/turn/Clear facts
    generic, tmp_path, variant
):
    actor, trace = generic('fileauth')
    config_path = trace.parent / 'peer-input.json'
    config = json.loads(config_path.read_text())
    config['ephemeral257_variant'] = variant
    config_path.write_text(json.dumps(config))  # Original one-time prelaunch peer input.
    fixture = ROOT / 'tests/fixtures/e04_t1/editable-project'
    original_files = {str(path.relative_to(fixture)): path.read_bytes()
                      for path in fixture.rglob('*') if path.is_file()}
    owned = tmp_path / 'Original ephemeral current owner'
    shutil.copytree(fixture, owned)
    assert actor.command('open', path=str(owned))['reply']['opened'], (
        'EPHEMERAL SETUP: genuine ordinary Session opens the original owned project'
    )
    before = actor.last['vm']
    actor.command('sign_in')
    state = settle(actor, lambda value: value['connected'] or bool(value['last_error']))
    observations = native_records(trace, '.ephemeral257-responses.jsonl')
    assert len(observations) == 1, 'EPHEMERAL SETUP: one real bootstrap thread reply observed'
    observation = observations[0]
    request = observation['request']
    assert request['method'] == 'thread/start' and (
        type(request['params'].get('ephemeral')) is bool
        and request['params']['ephemeral'] is True
    ), 'EPHEMERAL: actual outgoing request explicitly requires boolean true before readiness'
    assert observation['response']['id'] == request['id'], (
        'EPHEMERAL: the effective projection belongs to that original outstanding request'
    )
    effective = observation['response']['result']['thread']
    assert state['project'] == before['project'], (
        'EPHEMERAL: bootstrap policy cannot change current owner/science/path/Undo state'
    )
    if variant == 'effective':
        assert effective['ephemeral'] is True and state['connected'] and (
            state['models'] and state['handoff']['account_label'] and not state['last_error']
        ), 'EPHEMERAL: actual boolean true is acknowledged before genuine readiness'
        signin206_shipped(state, trace)
        connected = state
        first = folder167_send(actor, trace, 'Original ephemeral live turn A')
        second = folder167_send(actor, trace, 'Original ephemeral live turn B')
        turns = started_requests(trace)
        assert len(turns) == 2 and all(
            row['params']['threadId'] == effective['id'] for row in turns
        ), 'EPHEMERAL: ordinary live turns reuse their admitted thread without new bootstrap'
        assert len([row for row in records(trace) if row.get('method') == 'thread/start']) == 1
        assert all(row in second['messages'] for row in first['messages']), (
            'EPHEMERAL: nondurable backend mode preserves ordinary retained Edi history'
        )
        actor.command('clear_history')
        cleared = settle(actor, lambda value: value['connected'] and (
            not value['can_cancel'] and not value['messages']
        ))
        assert cleared['models'] == connected['models'] and (
            cleared['handoff']['account_label'] == connected['handoff']['account_label']
        ), 'EPHEMERAL: genuine settled Clear retains the original account and catalog'
        final = folder167_send(actor, trace, 'Original ephemeral fresh turn after Clear')
        turns = started_requests(trace)
        assert len(turns) == 3 and turns[-1]['params']['threadId'] != effective['id'], (
            'EPHEMERAL: Clear resets model memory through a genuinely new admitted thread'
        )
        later = native_records(trace, '.ephemeral257-responses.jsonl')
        assert len(later) == 2 and all(
            type(row['request']['params'].get('ephemeral')) is bool
            and row['request']['params']['ephemeral'] is True
            and row['response']['result']['thread']['ephemeral'] is True
            for row in later
        ), 'EPHEMERAL: both original and genuinely fresh threads require effective true'
        assert not any(row.get('text') in {
            'Original ephemeral live turn A', 'Original ephemeral live turn B'
        } for row in final['messages']), (
            'EPHEMERAL: retired conversation cannot revive after Clear'
        )
        assert final['project'] == before['project'], (
            'EPHEMERAL: live turns and Clear preserve all original current project facts'
        )
    else:
        if variant == 'missing':
            assert 'ephemeral' not in effective
        elif variant == 'false':
            assert effective['ephemeral'] is False
        else:
            assert effective['ephemeral'] == 'true' and type(effective['ephemeral']) is str
        assert not state['connected'] and state['last_error'] and (
            len(state['last_error'].encode()) <= 512
        ), 'EPHEMERAL: missing/false/malformed proof cannot be silently admitted as ephemeral'
        actor.command('send_text', text='Original refused ephemeral request')
        assert not started_requests(trace), (
            'EPHEMERAL: incompatible original reply refuses before any inference admission'
        )
        assert actor.last['vm']['project'] == before['project'], (
            'EPHEMERAL: attempted nonadmitted input cannot mutate the original owner'
        )
    assert not any(row.get('method') in {
        'account/login/start', 'account/logout', 'thread/archive', 'thread/unarchive',
        'thread/name/set', 'thread/list', 'thread/read',
    } for row in records(trace)), (
        'EPHEMERAL: policy admission does not repair auth or inspect/alter personal histories'
    )
    assert {str(path.relative_to(fixture)): path.read_bytes()
            for path in fixture.rglob('*') if path.is_file()} == original_files, (
        'EPHEMERAL: original committed scientific input bytes remain unchanged'
    )


@pytest.mark.parametrize('case', [
    'ascii-below', 'ascii-equal', 'ascii-above', 'cjk-equal', 'escaped-equal',
    'pair-equal', 'row-over', 'cancelled-intent', 'replayed-intent',
])
def test_import265_public_manual_recipe_admission_and_same_owner(generic, tmp_path, case):
    """Public ordinary Apply boundary; this is not million-character pointer typing."""
    def original_empty(scenario):
        actor, trace = generic(scenario)
        assert actor.command('named_empty_create', name='Original manual owner',
                             title='Original title', authors='Original author',
                             description='Original metadata distinct from recipe',
                             su_rule='iucr_99', report_libraries=True)['reply']['created'], (
            'IMPORT265 SETUP: actual public Session creates the original empty owner'
        )
        return actor, trace

    actor, trace, arguments, owned = native145_selected(original_empty, tmp_path)
    assert not actor.last['vm']['connected'] and not actor.peer_pid_file.exists(), (
        'IMPORT265: ordinary offline import does not require or launch a provider'
    )
    original_bytes = [path.read_bytes() for path in owned]
    before = actor.last['vm']
    original = before['project']['empty_completion_observer']
    recipe = arguments['recipe']
    # Public NI-RES1 contract: inclusive1MiB COMPLETE recipe JSON UTF8 spelling,
    # not just description length. All valid values remain independent fixture facts.
    cap = 1048576
    target = cap + (1 if case == 'ascii-above' else -1 if case == 'ascii-below' else 0)
    if case in {'ascii-below', 'ascii-equal', 'ascii-above', 'cjk-equal', 'escaped-equal', 'pair-equal'}:
        recipe['description'] = ''
        empty = json.dumps(recipe, ensure_ascii=False, separators=(',', ':'))
        remaining = target - len(empty.encode('utf-8'))
        unit = {'cjk-equal': '中', 'escaped-equal': '\x01', 'pair-equal': '😀'}.get(case, 'x')
        contribution = len(json.dumps(unit, ensure_ascii=False).encode('utf-8')) - 2
        recipe['description'] = unit * (remaining // contribution) + 'x' * (remaining % contribution)
        encoded = json.dumps(recipe, ensure_ascii=False, separators=(',', ':'))
        assert len(encoded.encode('utf-8')) == target, (
            'IMPORT265 SETUP: independently serialized complete valid recipe has exact declared boundary size'
        )
    else:
        if case == 'row-over':
            recipe['background'] = [{'position': float(i), 'intensity': 200.0} for i in range(257)]
        encoded = json.dumps(recipe, ensure_ascii=False, separators=(',', ':'))
    intent = actor.command('import265_begin')['reply']['intent']
    assert intent and actor.last['vm']['native_import_observer']['state'] == 'draft', (
        'IMPORT265 SETUP: actual public ordinary intent is a fresh offline draft'
    )
    if case == 'cancelled-intent':
        actor.command('import265_cancel', intent=intent)
    applied = actor.command('import265_apply', intent=intent,
                            cif_id=arguments['cif_file_id'], data_id=arguments['data_file_id'],
                            recipe_json=encoded)
    if case in {'ascii-above', 'row-over', 'cancelled-intent'}:
        assert not applied['reply']['admitted'], (
            'IMPORT265: over-cap/over-row/cancelled ordinary request refuses before worker admission'
        )
        state = applied['vm']
        projection = state['native_import_observer']
        assert not state['can_cancel'] and projection['state'] != 'preparing', (
            'IMPORT265: a false admission cannot hide a genuinely pending native worker'
        )
        if case == 'cancelled-intent':
            assert projection['state'] == 'retired' and projection['retryable'] is False, (
                'IMPORT265: the cancelled original intent stays retired without retry authority'
            )
        else:
            assert projection['state'] == 'refused' and projection['retryable'] is True, (
                'IMPORT265: a current invalid recipe is a quiescent before-write refusal, not preparation'
            )
        assert state['project'] == before['project'] and state['selected_files'] == before['selected_files'], (
            'IMPORT265: refused boundary cannot partially alter original science/metadata/owner/Undo or source grants'
        )
    else:
        assert applied['reply']['admitted'], (
            'IMPORT265: complete valid inclusive-cap recipe enters the real native worker'
        )
        state = settle(actor, lambda value: value['native_import_observer'].get('state') == 'created')
        state = native145_science_settled(actor)
        presentation = state['native_import_observer']
        assert presentation['retryable'] is False and presentation['outcome']['adopted'] is True, (
            'IMPORT265: real ordinary worker adoption is truthful and never retry authority'
        )
        assert presentation['outcome']['completed_existing'] is True and presentation['outcome']['saved'] is False, (
            'IMPORT265: same-owner completion is modified science, never a fabricated saved result'
        )
        actual = state['project']['empty_completion_observer']
        assert actual['same_owner'] and actual['same_core'] and (
            actual['owner_identity'] == original['owner_identity']
            and actual['core_identity'] == original['core_identity']
            and actual['metadata'] == original['metadata']
            and actual['settings'] == original['settings']
            and actual['path'] == original['path']
        ), 'IMPORT265: the real original empty owner retains all metadata/settings/path identities'
        expected = [list(map(float, line.split())) for line in owned[1].read_text().splitlines()
                    if line.strip() and not line.lstrip().startswith('#')]
        inputs = native_inputs(state)
        assert len(inputs) == 1 and inputs[0]['weight'] == 1.0, (
            'IMPORT265: one actual original measured dataset keeps its independent unit weight'
        )
        for name, column in [('axis', 0), ('intensity', 1), ('sigma', 2)]:
            assert inputs[0][name] == [row[column] for row in expected], (
                'IMPORT265: every literal original coordinate/intensity/sigma survives real import'
            )
        assert inputs[0]['exclusions'] == [[row['first'], row['second']] for row in recipe['exclusions']], (
            'IMPORT265: actual native import preserves the explicit original exclusion intervals'
        )
        structure = state['project']['science_observer']['structures'][0]
        assert structure['space_group'] == 'P n m a' and {
            row['id']: (row['type_symbol'], row['occupancy'], row['adp_type'], row['adp_iso'])
            for row in structure['sites']
        } == {label: (symbol, 1.0, 'Uiso', 0.01)
              for label, symbol in [('Pb', 'Pb'), ('S', 'S'), ('O1', 'O'), ('O2', 'O'), ('O3', 'O')]}, (
            'IMPORT265: original independent PbSO4 species/site occupancy/ADP convention survive'
        )
        coordinates = {'Pb': [0.1882, 0.25, 0.167], 'S': [0.063, 0.25, 0.686],
                       'O1': [-0.095, 0.25, 0.6], 'O2': [0.181, 0.25, 0.543],
                       'O3': [0.085, 0.026, 0.806]}
        for site in structure['sites']:
            assert site['fractional'] == coordinates[site['id']], (
                'IMPORT265: literal original five-site fractional geometry survives import'
            )
            expected_orbit = native145_original_orbits(*coordinates[site['id']])
            images = [atom for atom in structure['expanded'] if atom['site_id'] == site['id']]
            actual_orbit = sorted({tuple(round(x % 1.0, 12) for x in atom['fractional']) for atom in images})
            assert len(actual_orbit) == len(expected_orbit), (
                'IMPORT265: physical site multiplicity survives inclusive-view lattice images'
            )
            for position, expected_position in zip(actual_orbit, expected_orbit, strict=True):
                assert position == pytest.approx(expected_position, abs=1e-12), (
                    'IMPORT265: actual canonical orbit follows independently derived original CIF symmetry'
                )
        assert inputs[0]['phases'] == [structure['id']], (
            'IMPORT265: real measured dataset is linked to the one original imported phase'
        )
        assert all(atom['occupancy'] == 1.0 and atom['u_iso'] == pytest.approx(0.01, abs=1e-12)
                   for atom in structure['expanded']), (
            'IMPORT265: every actual visual image retains original occupancy and isotropic ADP'
        )
        for name, value in [('length_a', 8.48), ('length_b', 5.398), ('length_c', 6.958)]:
            parameter = native_parameter(state, 'structure.cell.' + name)
            assert parameter['value'] == value and parameter['free'] is False and parameter['uncertainty'] == 0, (
                'IMPORT265: original bare fixed cell literals and exact numeric-zero SU survive'
            )
        assert state['project']['native_observer']['can_undo'] and (
            actor.command('native_undo')['reply']['was_available']
        ), 'IMPORT265: complete same-owner import has one real ordinary Undo'
        undone = settle(actor, lambda value: value['project']['empty_completion_observer']['structures'] == 0
                        and not value['project']['science_observer']['calculating'])
        assert undone['project']['empty_completion_observer'] == original and (
            undone['project']['parameters'] == before['project']['parameters']
            and undone['project']['native_observer']['record'] == before['project']['native_observer']['record']
            and undone['project']['native_observer']['can_undo'] == before['project']['native_observer']['can_undo']
        ), 'IMPORT265: one Undo restores the complete original empty owner and prior recorded history'
        if case == 'replayed-intent':
            again = actor.command('import265_apply', intent=intent, cif_id=arguments['cif_file_id'],
                                  data_id=arguments['data_file_id'], recipe_json=encoded)
            assert not again['reply']['admitted'] and again['vm']['project'] == undone['project'], (
                'IMPORT265: already adopted original intent never grants a second write after Undo'
            )
            projection = again['vm']['native_import_observer']
            previous_projection = undone['native_import_observer']
            assert not again['vm']['can_cancel'] and projection['state'] != 'preparing', (
                'IMPORT265: refused replay owns no genuinely pending worker or preparing projection'
            )
            assert projection['retryable'] is False and projection['state'] == previous_projection['state'], (
                'IMPORT265: replay neither reopens authority nor erases the prior committed/retired presentation'
            )
            if previous_projection['state'] == 'created':
                assert projection.get('outcome') == previous_projection.get('outcome') and (
                    projection.get('adopted') == previous_projection.get('adopted')
                    and projection.get('saved') == previous_projection.get('saved')
                    and projection.get('presentation_complete') == previous_projection.get('presentation_complete')
                ), 'IMPORT265: refused replay preserves the truthful historical committed outcome'
            assert again['vm']['selected_files'] == undone['selected_files'], (
                'IMPORT265: rejected replay preserves actual current source grants as well as science'
            )
    assert [path.read_bytes() for path in owned] == original_bytes, (
        'IMPORT265: original complete selected-source bytes are unchanged by admission/refusal/Undo'
    )
    assert not actor.last['vm']['connected'] and not actor.peer_pid_file.exists() and not trace.exists(), (
        'IMPORT265: ordinary offline form API cannot silently bootstrap a provider/account'
    )


@pytest.mark.parametrize('saved', [False, True], ids=['unsaved', 'saved'])
def test_import272_exact_close_after_real_committed_owner_retirement_cannot_be_overwritten(
    generic, tmp_path, saved
):
    """Synchronous real projectEdited -> original public cancel, not a fake worker window."""
    def original_empty(scenario):
        actor, trace = generic(scenario)
        assert actor.command('named_empty_create', name='Original Close-boundary owner',
                             title='Original retained title', authors='Original author',
                             description='Original owner metadata, not recipe defaults',
                             su_rule='iucr_99', report_libraries=True,
                             location=str(tmp_path / 'original-saved-empty') if saved else '')[
            'reply'
        ]['created'], 'MI-CLOSE SETUP: actual public Session creates the original empty owner'
        return actor, trace
    actor, trace, arguments, owned = native145_selected(original_empty, tmp_path)
    before = actor.last['vm']
    original = before['project']['empty_completion_observer']
    original_bytes = [path.read_bytes() for path in owned]
    saved_files = save211_files(Path(original['path'])) if saved else None
    intent = actor.command('import265_begin')['reply']['intent']
    assert intent and actor.last['vm']['native_import_observer']['state'] == 'draft', (
        'MI-CLOSE SETUP: one actual original public manual intent owns the complete recipe'
    )
    armed = actor.command('publication_arm', action='import272-cancel', signal='projectEdited',
                          import_intent=intent)
    assert armed['reply']['armed'], (
        'MI-CLOSE SETUP: existing one-shot real projectEdited receiver is armed before Apply'
    )
    applied = actor.command('import265_apply', intent=intent,
                            cif_id=arguments['cif_file_id'], data_id=arguments['data_file_id'],
                            recipe_json=json.dumps(arguments['recipe'], separators=(',', ':')))
    assert applied['reply']['admitted'], (
        'MI-CLOSE SETUP: actual original manual Apply genuinely submits native creation'
    )
    state = settle(actor, lambda value: (
        value.get('publication_observer', {}).get('import272', {}).get('returned')
        and not value['can_cancel'] and not value['project']['science_observer']['calculating']
        and all(row['current'] for row in value['project']['science_observer']['calculations'])
    ))
    publication = state['publication_observer']
    observed = publication['import272']
    assert publication['entered'] and publication['signal'] == 'projectEdited' and (
        publication['same_owner_at_entry'] and publication['current_owner_is_original']
        and publication['returned']
    ), 'MI-CLOSE SETUP: genuine original owner publication actually invokes/returns the receiver'
    assert observed['intent'] == intent and observed['before']['id'] == intent and (
        observed['before']['state'] == 'retired' and observed['before']['retryable'] is False
        and observed['can_cancel_at_entry'] and observed['structures_at_entry'] == 1
        and observed['experiments_at_entry'] == 1
    ), (
        'MI-CLOSE SETUP: actual scientific commit and own retired projection precede the exact '
        'public Close cancellation while original final delivery still owns cancellable work'
    )
    assert observed['after']['id'] == intent and observed['after']['state'] == 'retired' and (
        observed['after']['retryable'] is False
    ), 'MI-CLOSE: exact original public cancellation remains a truthful withdrawn presentation'
    projection = state['native_import_observer']
    assert projection == observed['after'] and projection['state'] == 'retired', (
        'MI-CLOSE: old final delivery cannot overwrite explicit withdrawal with created/partial status'
    )
    assert state['project']['empty_completion_observer'] == {
        **original, 'structures': 1, 'experiments': 1,
    }, 'MI-CLOSE: explicit postcommit Close preserves actual same-owner/core metadata/settings/path'
    assert [(row['path'], row['value'], row['free'], row['uncertainty'])
            for row in state['project']['parameters']] == [
        (row['path'], row['value'], row['free'], row['uncertainty'])
        for row in publication['before']['parameters']
    ], 'MI-CLOSE: explicit withdrawal/final delivery cannot alter any alreadycommitted value/free/SU'
    inputs = native_inputs(state)
    expected = [list(map(float, row.split())) for row in owned[1].read_text().splitlines()
                if row.strip() and not row.lstrip().startswith('#')]
    assert len(inputs) == 1 and inputs[0]['weight'] == 1.0, (
        'MI-CLOSE: genuine alreadycommitted measurement remains one unit-weight dataset'
    )
    for key, column in [('axis', 0), ('intensity', 1), ('sigma', 2)]:
        assert inputs[0][key] == [row[column] for row in expected], (
            'MI-CLOSE: explicit presentation withdrawal preserves every original measured input/sigma'
        )
    assert inputs[0]['exclusions'] == [[row['first'], row['second']]
                                     for row in arguments['recipe']['exclusions']], (
        'MI-CLOSE: alreadycommitted original masks survive genuine public cancellation'
    )
    structure = state['project']['science_observer']['structures'][0]
    assert inputs[0]['phases'] == [structure['id']], (
        'MI-CLOSE: actual committed measured pattern retains its original single-phase link'
    )
    sites = {row['id']: row for row in structure['sites']}
    expected_sites = {'Pb': ('Pb', [0.1882, 0.25, 0.167]), 'S': ('S', [0.063, 0.25, 0.686]),
                      'O1': ('O', [-0.095, 0.25, 0.6]), 'O2': ('O', [0.181, 0.25, 0.543]),
                      'O3': ('O', [0.085, 0.026, 0.806])}
    assert structure['space_group'] == 'P n m a' and set(sites) == set(expected_sites), (
        'MI-CLOSE: committed original crystal symmetry/allfive independent site identities survive'
    )
    for name, (symbol, position) in expected_sites.items():
        site = sites[name]
        assert site['type_symbol'] == symbol and any(
            tuple(value % 1.0 for value in site['fractional']) == pytest.approx(orbit, abs=1e-12)
            for orbit in native145_original_orbits(*position)
        ) and (
            site['occupancy'] == 1.0 and site['adp_type'] == 'Uiso' and site['adp_iso'] == 0.01
        ), 'MI-CLOSE: original literal species/geometry/occupancy/ADP is not undone or replaced'
    for name, value in [('length_a', 8.48), ('length_b', 5.398), ('length_c', 6.958)]:
        parameter = native_parameter(state, 'structure.cell.' + name)
        assert parameter['value'] == value and parameter['free'] is False and (
            parameter['uncertainty'] == 0
        ), 'MI-CLOSE: original fixed cell and exact public numeric-zero SU remain committed'
    assert state['selected_files'] == before['selected_files'] and not state['connected'] and (
        [path.read_bytes() for path in owned] == original_bytes
        and not actor.peer_pid_file.exists()
    ), 'MI-CLOSE: ordinary public Close preserves sources and stays genuinely offline'
    # A real stale original Apply is refused before any additional scientific edit.
    replay = actor.command('import265_apply', intent=intent,
                           cif_id=arguments['cif_file_id'], data_id=arguments['data_file_id'],
                           recipe_json=json.dumps(arguments['recipe'], separators=(',', ':')))
    assert not replay['reply']['admitted'] and not replay['vm']['can_cancel'] and (
        replay['vm']['project'] == state['project']
        and replay['vm']['native_import_observer']['id'] == intent
        and replay['vm']['native_import_observer']['state'] == 'retired'
        and replay['vm']['native_import_observer']['retryable'] is False
    ), 'MI-CLOSE: withdrawn original ID cannot Apply again or reopen its historical presentation'
    assert actor.command('native_undo')['reply']['was_available'], (
        'MI-CLOSE: actual committed scientific addition still has exactly its normal one Undo'
    )
    undone = settle(actor, lambda value: (
        value['project']['empty_completion_observer']['structures'] == 0
        and value['project']['empty_completion_observer']['experiments'] == 0
        and not value['project']['science_observer']['calculating']
    ))
    assert undone['project']['empty_completion_observer'] == original and (
        undone['project']['parameters'] == before['project']['parameters']
        and undone['project']['mode'] == before['project']['mode']
        and undone['project']['native_observer']['record']
        == before['project']['native_observer']['record']
        and undone['project']['science_observer'] == before['project']['science_observer']
        and undone['project']['native_observer']['can_undo']
        == before['project']['native_observer']['can_undo']
    ), 'MI-CLOSE: one real Undo restores original complete empty owner without late science'
    # Genuine reachable old-A/new-B draft separation after A's settled final delivery.
    current_id = actor.command('import265_begin')['reply']['intent']
    draft = actor.last['vm']['native_import_observer']
    assert current_id and current_id != intent and draft['id'] == current_id and (
        draft['state'] == 'draft'
    ), 'MI-CLOSE SETUP: actual current empty owner admits a genuinely new B draft'
    actor.command('import265_cancel', intent=intent)
    assert actor.last['vm']['native_import_observer'] == draft and (
        actor.last['vm']['project'] == undone['project']
    ), 'MI-CLOSE: stale old A Close cannot withdraw B or mutate its current empty owner'
    actor.command('import265_cancel', intent=current_id)
    assert actor.last['vm']['native_import_observer']['state'] == 'retired' and (
        not actor.last['vm']['can_cancel']
        and actor.last['vm']['project'] == undone['project']
    ), 'MI-CLOSE: only the actual current B ID can explicitly withdraw its own draft'
    if saved:
        assert save211_files(Path(original['path'])) == saved_files, (
            'MI-CLOSE: Close/replay/oneUndo/newdraft never overwrites the independent saved source tree'
        )


# Owner same-project conversation contract, public243/SURFACE plus original public228/BOUNDARIES; these are
# normal native-runtime gates, not restricted/browser or physical GUI proofs.
def reuse269_configure(trace, *, stage_name=None):
    path = trace.parent / 'peer-input.json'
    config = json.loads(path.read_text())
    assert not path.with_suffix('.peer-pid').exists(), 'REUSE SETUP: complete opt-in config precedes original process read'
    config['reuse269'] = {'stage_name': stage_name}
    path.write_text(json.dumps(config))


def reuse269_account(before, after, trace):
    assert after['connected'] and after['models'] == before['models'] and (
        after['handoff']['account_label'] == before['handoff']['account_label']
    ), 'REUSE: real scientific/session actions preserve the admitted managed account/catalog'
    assert not any(row.get('method') in {'account/login/start', 'account/logout'}
                   for row in records(trace)), (
        'REUSE: conversation maintenance does not repair authentication by login/logout'
    )


def reuse269_send(actor, trace, text, *, native_count=None):
    # Deliberately NO auto-approval here: unchanged scope must already be admitted.
    before = actor.last['vm']
    assert before['connected'] and not before['can_cancel'] and not (
        before['context_consent_required']
    ), 'REUSE: admitted unchanged scope is ready without another disclosure approval'
    context = before['context']
    prior = len(started_requests(trace))
    prior_ids = {row['id'] for row in before['messages']}
    actor.command('send_text', text=text)
    state = settle(actor, lambda value: (
        len(started_requests(trace)) == prior + 1 and not value['can_cancel']
        and any(row.get('kind') == 'user' and row.get('text') == text
                and row.get('status') == 'completed' and row['id'] not in prior_ids
                for row in value['messages'])
    ))
    sent = started_requests(trace)
    assert len(sent) == prior + 1 and rpc83_context_inputs(sent[-1]['params']) == [context], (
        'REUSE: one original turn carries exactly the complete CURRENT GUI context bytes'
    )
    user_rows = [row for row in state['messages'] if row.get('kind') == 'user'
                 and row.get('text') == text and row['id'] not in prior_ids]
    assert len(user_rows) == 1 and (
        sent[-1]['params']['clientUserMessageId'] == user_rows[0]['id']
    ), 'REUSE: fresh original input/RPC authority never reuses a historical row identity'
    if native_count is not None:
        replies = native_records(trace, '.native-replies.jsonl')
        assert len(replies) == native_count and not native_records(
            trace, '.native-wrong-envelope.jsonl'
        ), 'REUSE: every original native envelope responds once without identity substitution'
        assert len({row['response']['id'] for row in replies}) == native_count and all(
            row['response']['id'] == row['original']['id'] for row in replies
        ), 'REUSE: retained conversation cannot duplicate an old original reverse response'
    assert all(row in state['messages'] for row in before['messages']), (
        'REUSE: same-conversation work preserves all already retained public history'
    )
    return state


def reuse269_thread(trace):
    starts = [row for row in records(trace) if row.get('method') == 'thread/start']
    assert starts, 'REUSE SETUP: real original thread/start has reached the owned peer'
    replies = native_records(trace, '.reuse280-threads.jsonl')
    assert len(replies) == len(starts) and all(
        row['params'].get('ephemeral') is True for row in starts
    ) and all(row['effective_ephemeral'] is True for row in replies), (
        'REUSE: actual original outgoing/effective thread admission remains explicitly ephemeral'
    )
    assert [row['id'] for row in starts] == [row['request_id'] for row in replies], (
        'REUSE: every observed effective reply belongs to its exact original bootstrap request'
    )
    return starts[-1]['params']['cwd'], starts


@pytest.mark.parametrize('change', ['value', 'background'])
def test_reuse269_manual_science_keeps_thread_workspace_and_fresh_context(
    generic, tmp_path, change
):
    actor, trace = generic('fileauth')
    source = ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project'
    owned = tmp_path / 'Original same-owner measured project'
    shutil.copytree(source, owned)
    original_files = save211_files(owned)
    assert actor.command('open', path=str(owned))['reply']['opened'], (
        'REUSE SETUP: original measured project loads through public Session'
    )
    assert actor.command('native_science_enable')['reply']['enabled']
    selected = tmp_path / 'Original selected scope.txt'
    selected.write_bytes(b'Original unchanged disclosure bytes\n')
    intent = actor.command('selected_begin')['reply']['request_id']
    assert actor.command('selected_add', request_id=intent, urls=[selected.as_uri()])[
        'reply'
    ]['accepted'], 'REUSE SETUP: real immutable selected input is admitted before bootstrap'
    reuse269_configure(trace, stage_name=selected.name)
    connect(actor)
    native145_approve(actor)  # Initial explicit approval only; never after ordinary edit.
    initial = native145_science_settled(actor)
    first = reuse269_send(actor, trace, 'Original admitted conversation before scientific edit')
    cwd, starts = reuse269_thread(trace)
    witness = native_records(trace, '.reuse269.jsonl')[-1]
    assert witness['stage_changed'] and witness['stage_original_sha256'] == (
        hashlib.sha256(selected.read_bytes()).hexdigest()
    ), 'REUSE SETUP: actual peer modified only its genuinely staged copy of selected bytes'
    staged = Path(witness['stage_path'])
    provider_bytes = staged.read_bytes()
    selected_before = first['selected_files']
    selected.write_bytes(selected.read_bytes())  # Actual equal-content original backing-file write.
    original_context = first['context']
    choices = [row for row in first['project']['parameters'] if row['independent'] and (
        ('background' in row['path'] and row['path'].endswith('.intensity'))
        if change == 'background' else row['path'] == 'structure.cell.length_a'
    )]
    assert choices, 'REUSE SETUP: actual original independent scientific field is exposed'
    target = choices[0]
    requested = target['value'] + (1.0 if change == 'background' else 0.001)
    changed = actor.command('manual_value', path=target['path'], value=requested)
    assert not changed['reply']['error'], 'REUSE: real ordinary shared editor commits the edit'
    state = native145_science_settled(actor)
    assert native_parameter(state, target['path'])['value'] == requested and (
        state['context'] != original_context
    ), 'REUSE: genuine changed value is current GUI truth before next original turn'
    assert native_inputs(state) == native_inputs(initial), (
        'REUSE: ordinary parameter/background editing preserves every raw observation/sigma/mask/weight'
    )
    second = reuse269_send(actor, trace, 'Original follow-up uses current scientific GUI truth')
    new_cwd, later = reuse269_thread(trace)
    assert len(starts) == len(later) == 1 and new_cwd == cwd and (
        started_requests(trace)[0]['params']['threadId']
        == started_requests(trace)[1]['params']['threadId']
    ), 'REUSE: ordinary science retains actual backend thread and immutable staging workspace'
    assert second['selected_files'] == selected_before, (
        'REUSE: equal backing bytes keep the original immutable selected IDs/hash authority'
    )
    assert staged.read_bytes() == provider_bytes and selected.read_bytes() == (
        b'Original unchanged disclosure bytes\n'
    ), 'REUSE: follow-up does not overwrite provider staging or silently adopt it into GUI inputs'
    reuse269_account(first, second, trace)
    assert save211_files(owned) == original_files, (
        'REUSE: conversation retention never saves/rewrites the original scientific source tree'
    )


def test_reuse269_native_free_relations_fit_and_undo_retain_original_conversation(
    generic, tmp_path
):
    # Independent original Co2SiO4 fixture: Co1/Co2 Biso=.5. The explicit test user
    # requests their equality; this is not a heuristic that all sites must share ADPs.
    relation = native_call('add_relations', aliases=[
        {'id': 'reuse_co2', 'path': 'structure.atom_sites[Co2].adp_iso'},
    ], constraints=[{'id': 'reuse_adp', 'expression': 'reuse_co2 = original_co1_biso', 'enabled': True}])
    free = native_call('set_free', flags=[
        {'path': 'structure.atom_sites[Co1].adp_iso', 'free': True},
        {'path': 'structure.atom_sites[Co2].adp_iso', 'free': False},
    ])
    turns = json.loads(json.dumps([[native_call('inspect_project')], [free], [free],
                                    [relation], [relation], [native_call('run_fit')],
                                    [native_call('diagnostics')]]))
    # Existing helper consumes its predeclared turn script and connects exactly once.
    def original(g, *args, **kwargs):
        actor, trace = g(*args, **kwargs)
        reuse269_configure(trace)
        return actor, trace
    actor, trace, _source = save211_owner(lambda *a, **k: original(generic, *a, **k),
                                         tmp_path, turns)
    initial = native145_science_settled(actor)
    first = reuse269_send(actor, trace, 'Original native read establishes live conversation',
                          native_count=1)
    cwd, starts = reuse269_thread(trace)
    before_free = first['project']['parameters']
    initial_declarations = first['project']['science_observer']
    freed = reuse269_send(actor, trace, 'Original native free request', native_count=2)
    assert native_parameter(freed, 'structure.atom_sites[Co1].adp_iso')['free'] and not (
        native_parameter(freed, 'structure.atom_sites[Co2].adp_iso')['free']
    ), 'REUSE: the genuine original free command changes its requested flags'
    expected_free = json.loads(json.dumps(before_free))
    for row in expected_free:
        if row['path'] == 'structure.atom_sites[Co2].adp_iso':
            row['free'] = False
    assert freed['project']['parameters'] == expected_free, (
        'REUSE: a genuine free-only edit preserves all values/SUs/unrelated flags and metadata'
    )
    assert actor.command('native_undo')['reply']['was_available'], (
        'REUSE: one normal Undo is genuinely available for the recorded free edit'
    )
    undone = native145_science_settled(actor)
    assert undone['project']['parameters'] == before_free, (
        'REUSE: one ordinary Undo restores all actual pre-free values/flags/SUs'
    )
    assert undone['project']['native_observer']['can_undo'] == first['project']['native_observer']['can_undo'], (
        'REUSE: the complete free batch consumes one record, with no phantom remaining step'
    )
    reuse269_send(actor, trace, 'Original native free reapplication', native_count=3)
    before_relation = actor.last['vm']['project']
    related = reuse269_send(actor, trace, 'Original explicit same-element ADP relation',
                            native_count=4)
    assert any(row['id'] == 'reuse_adp' and row['enabled'] for row in (
        related['project']['science_observer']['constraints']
    )), 'REUSE: actual native relation declaration is observable before Undo'
    assert actor.command('native_undo')['reply']['was_available'], (
        'REUSE: the real recorded relation edit offers one normal Undo'
    )
    undone = native145_science_settled(actor)
    assert undone['project']['parameters'] == before_relation['parameters'] and all(
        undone['project']['science_observer'][key]
        == before_relation['science_observer'][key] for key in ['aliases', 'constraints']
    ), 'REUSE: one Undo restores original declarations/values/free/SUs without retiring conversation'
    assert undone['project']['native_observer']['can_undo'] == before_relation['native_observer']['can_undo'], (
        'REUSE: one relation Undo restores the prior recorded history boundary'
    )
    reuse269_send(actor, trace, 'Original ADP relation reapplication', native_count=5)
    fitted = reuse269_send(actor, trace, 'Original real native fit of current constrained owner',
                           native_count=6)
    replies = native_records(trace, '.native-replies.jsonl')
    fit = json.loads(replies[-1]['response']['result']['contentItems'][0]['text'])
    assert fit['status'] in {'done', 'max_iterations'} and fit['adopted'] is True and (
        fit['iterations'] > 0
    ), 'REUSE: actual native FitJob completes/adopts real iterations, never cached/fictitious success'
    fitted = native145_science_settled(actor)
    report = fitted['project']['native_observer']
    record = report['record']
    chi_square = record['reduced_chi_square']
    assert not report['fit_running'] and record['kind'] and record['iterations'] == fit['iterations'], (
        'REUSE: real completed worker report is adopted into this same current owner'
    )
    assert type(chi_square) in (int, float) and chi_square == chi_square and (
        -float('inf') < chi_square < float('inf')
    ), 'REUSE: actual fitted statistics are finite without a producer-derived optimum/Rwp golden'
    assert all(row in fitted['project']['science_observer']['aliases']
               for row in initial_declarations['aliases']) and all(
        row in fitted['project']['science_observer']['constraints']
        for row in initial_declarations['constraints']
    ), 'REUSE: genuine fit retains every original enabled/disabled declaration'
    assert native_parameter(fitted, 'structure.atom_sites[Co1].adp_iso')['value'] == (
        native_parameter(fitted, 'structure.atom_sites[Co2].adp_iso')['value']
    ), 'REUSE: actual requested ADP relation remains satisfied after real worker publication'
    final = reuse269_send(actor, trace, 'Original current postfit diagnostics', native_count=7)
    assert len(reuse269_thread(trace)[1]) == len(starts) == 1 and (
        reuse269_thread(trace)[0] == cwd
        and len({row['params']['threadId'] for row in started_requests(trace)}) == 1
    ), 'REUSE: own native free/relation/fit/Undo preserve one actual backend conversation/workspace'
    assert native_inputs(final) == native_inputs(initial), (
        'REUSE: genuine fit and declarations preserve all original measured columns/masks/weights'
    )
    assert all(row['response']['result']['success'] for row in native_records(
        trace, '.native-replies.jsonl'
    )), 'REUSE: each genuine normal native operation has its own successful original response'
    reuse269_account(first, final, trace)


@pytest.mark.parametrize('change', ['selected-add', 'selected-remove', 'same-name-bytes',
                                   'owner', 'folder', 'account', 'topology'])
def test_reuse269_real_scope_revocation_requires_new_backend_memory(generic, tmp_path, change):
    actor, trace = generic('fileauth')
    fixture = ROOT / 'tests/fixtures/e04_t1/editable-project'
    assert actor.command('open', path=str(fixture))['reply']['opened'], (
        'REUSE SETUP: original genuine project opens before scope approval'
    )
    selected = tmp_path / 'Original scope bytes.txt'
    selected.write_bytes(b'Original content A\n')
    token = actor.command('selected_begin')['reply']['request_id']
    assert actor.command('selected_add', request_id=token, urls=[selected.as_uri()])[
        'reply'
    ]['accepted'], 'REUSE SETUP: initial selected content is genuinely admitted'
    reuse269_configure(trace)
    connect(actor)
    native145_approve(actor)
    first = reuse269_send(actor, trace, 'Original conversation before genuine scope revocation')
    original_thread = started_requests(trace)[-1]['params']['threadId']
    old_selection = first['selected_files'][0]['id']
    if change in {'selected-remove', 'same-name-bytes'}:
        assert actor.command('selected_remove', id=old_selection)['reply']['accepted'], (
            'REUSE SETUP: genuine settled selected authority is actually removed'
        )
    if change in {'selected-add', 'same-name-bytes'}:
        if change == 'selected-add':
            selected = tmp_path / 'Original added input.txt'
            selected.write_bytes(b'Original independent content B\n')
        else:
            selected.write_bytes(b'Original content B\n')  # Same name/path/byte count, real changed bytes.
        token = actor.command('selected_begin')['reply']['request_id']
        assert actor.command('selected_add', request_id=token, urls=[selected.as_uri()])[
            'reply'
        ]['accepted'], 'REUSE: current new/changed input is actually selected through public intake'
    elif change == 'owner':
        actor.command('close_project')
        assert actor.command('open', path=str(fixture))['reply']['opened'], (
            'REUSE: a real newly loaded owner may have equal metadata/path/science'
        )
    elif change == 'topology':
        removed = actor.command('native_remove_structure', index=0)
        assert removed['reply']['remaining'] == 0, (
            'REUSE SETUP: actual public structure removal changes same-owner structural scope'
        )
    elif change == 'folder':
        chosen = tmp_path / 'Original genuinely chosen capability'
        chosen.mkdir()
        intent = actor.command('working_folder_begin')['reply']['intent']
        assert actor.command('working_folder_complete', intent=intent,
                             directory=str(chosen))['reply']['accepted'], (
            'REUSE: only actual public picker callback authorizes the new writable root'
        )
    elif change == 'account':
        actor.command('sign_out')
        assert not actor.last['vm']['connected'], 'REUSE: explicit account retirement actually disconnects'
        connect(actor)  # Explicit new account admission, never silent repair.
    state = settle(actor, lambda value: value['connected'] and not value['can_cancel'])
    if change in {'selected-add', 'selected-remove', 'same-name-bytes', 'owner', 'topology'}:
        native145_approve(actor)  # Acknowledge only genuinely requested changed-scope disclosure.
    elif change == 'folder':
        assert not state['context_consent_required'], (
            'REUSE: genuine picker already authorized the exact folder, without duplicate grant'
        )
    else:
        native145_approve(actor)
    final = reuse269_send(actor, trace, 'Original new turn after genuine scope admission')
    assert started_requests(trace)[-1]['params']['threadId'] != original_thread, (
        'REUSE: actual input/owner/account/root revocation cannot retain old model memory'
    )
    if change != 'account':
        reuse269_account(first, final, trace)
    if change == 'selected-remove':
        assert not final['selected_files'] and old_selection not in json.dumps(
            started_requests(trace)[-1]['params']['input']
        ), 'REUSE: removed original grant cannot leak into new original turn context'
    if change == 'same-name-bytes':
        assert len(final['selected_files']) == 1 and final['selected_files'][0]['id'] != (
            old_selection
        ), 'REUSE: same-name same-length content replacement receives current authority, not stale ID'
        staged = Path(reuse269_thread(trace)[0]) / 'inputs' / selected.name
        assert staged.read_bytes() == b'Original content B\n', (
            'REUSE: new memory stages independently authored changed bytes, never the old same-name snapshot'
        )
    if change == 'folder':
        folder167_policy(trace, chosen.resolve())
    assert not any(row.get('method') in {'thread/list', 'thread/read', 'thread/archive'}
                   for row in records(trace)), (
        'REUSE: fresh memory uses actual new admission, never scans/rewrites personal sessions'
    )


@pytest.mark.parametrize('selected_input', [False, True], ids=['project-only', 'input-removed'])
def test_reuse269_settled_clear_resets_memory_without_reapproving_remaining_scope(
    generic, tmp_path, selected_input
):
    actor, trace = generic('fileauth')
    assert actor.command('open', path=str(ROOT / 'tests/fixtures/e04_t1/editable-project'))[
        'reply'
    ]['opened'], 'REUSE SETUP: original current owner exists before Clear'
    if selected_input:
        selected = tmp_path / 'Original removed by Clear.txt'
        selected.write_bytes(b'Original selected scope before Clear\n')
        token = actor.command('selected_begin')['reply']['request_id']
        assert actor.command('selected_add', request_id=token, urls=[selected.as_uri()])[
            'reply'
        ]['accepted'], 'REUSE SETUP: real selected grant precedes conversation approval'
    reuse269_configure(trace)
    connect(actor)
    native145_approve(actor)
    first = reuse269_send(actor, trace, 'Original retained history before real settled Clear')
    initial_thread = started_requests(trace)[-1]['params']['threadId']
    actor.command('clear_history')
    cleared = settle(actor, lambda value: value['connected'] and not value['can_cancel']
                     and not value['messages'])
    assert not cleared['context_consent_required'] and not cleared['selected_files'], (
        'REUSE: actual Clear removes selected grants and preserves unchanged remaining approval'
    )
    assert_clear_projection156(cleared)
    assert actor.command('archive')['reply']['rows'] == [], (
        'REUSE: fresh model memory begins only after actual durable empty history settlement'
    )
    assert actor.last['vm']['project'] == first['project'], (
        'REUSE: real Clear leaves current scientific owner/parameters/data/Undo untouched'
    )
    final = reuse269_send(actor, trace, 'Original fresh memory after successful Clear')
    assert started_requests(trace)[-1]['params']['threadId'] != initial_thread and not any(
        row.get('text') == 'Original retained history before real settled Clear'
        for row in final['messages']
    ), 'REUSE: retired conversation is not revived by fresh post-Clear input'
    reuse269_account(first, final, trace)


@pytest.mark.parametrize('retirement', ['clear', 'scope-upgrade'])
def test_reuse269_real_preack_retirement_preserves_once_and_scope_upgrade(
    generic, tmp_path, retirement
):
    actor, trace = generic('clear:pending-ack')
    assert actor.command('open', path=str(ROOT / 'tests/fixtures/e04_t1/editable-project'))[
        'reply'
    ]['opened'], 'REUSE SETUP: original project opens before genuine pre-ACK work'
    selected = tmp_path / 'Original grant before actual pending control.txt'
    selected.write_bytes(b'Original selected content\n')
    token = actor.command('selected_begin')['reply']['request_id']
    assert actor.command('selected_add', request_id=token, urls=[selected.as_uri()])[
        'reply'
    ]['accepted'], 'REUSE SETUP: actual initial selected grant is live'
    reuse269_configure(trace)
    connect(actor)
    native145_approve(actor)
    original = actor.last['vm']
    actor.command('send_text', text='Original real work before settled reuse decision')
    settle(actor, lambda value: value['can_cancel'] and any(
        row.get('payload', {}).get('id') == 'clear-prior-work' for row in value['messages']
    ))
    target = native_parameter(actor.last['vm'])
    changed = actor.command('manual_value', path=target['path'], value=target['value'] + 0.001)
    assert not changed['reply']['error'], 'REUSE: original ordinary edit actually triggers retirement'
    settle(actor, lambda _value: any(
        row['kind'] == 'control-terminal' for row in clear_control_events(trace)
    ))
    events = clear_control_events(trace)
    assert not any(row['kind'] == 'interrupt-ack' for row in events), (
        'REUSE SETUP: actual original terminal reached while original control ACK is still held'
    )
    if retirement == 'clear':
        actor.command('clear_history')
    else:
        assert actor.command('open', path=str(ROOT / 'tests/fixtures/e04_t1/editable-project'))[
            'reply'
        ]['opened'], 'REUSE SETUP: real Session replacement upgrades scope while original ACK is held'
        replacement = native_parameter(actor.last['vm'], target['path'])
        assert replacement['value'] == target['value'] and not actor.last['vm']['selected_files'], (
            'REUSE SETUP: genuine new owner contains original input and has fresh selected authority'
        )
        changed = actor.command('manual_value', path=replacement['path'],
                                value=replacement['value'] + 0.002)
        assert not changed['reply']['error'], (
            'REUSE: a later genuine scientific edit cannot downgrade a prior scope revocation'
        )
    assert not any(row['kind'] == 'interrupt-ack' for row in clear_control_events(trace)), (
        'REUSE SETUP: requested Clear/scope-upgrade is genuinely reached before the same ACK'
    )
    interrupts = [row for row in records(trace) if row.get('method') == 'turn/interrupt']
    active = next(row for row in clear_control_events(trace) if row['kind'] == 'active')
    assert len(interrupts) == 1 and interrupts[0]['params'] == {
        'threadId': active['threadId'], 'turnId': active['turnId']
    }, 'REUSE: repeated retirement channels keep one exact original interrupt obligation'
    final = settle(actor, lambda value: not value['can_cancel'] and any(
        row['kind'] == 'interrupt-ack' for row in clear_control_events(trace)
    ))
    assert len(started_requests(trace)) == 1 and not final['selected_files'], (
        'REUSE: no second turn or retired selected grant crosses unsettled original control'
    )
    if retirement == 'clear':
        assert_clear_projection156(final)
        assert not final['context_consent_required'], (
            'REUSE: deferred successful Clear retains unchanged remaining admitted disclosure'
        )
        assert actor.command('archive')['reply']['rows'] == [], (
            'REUSE: deferred Clear really commits canonical empty retained history'
        )
    else:
        native145_approve(actor)  # Real changed-scope consent only if actually requested.
    assert native_parameter(actor.last['vm'])['value'] == target['value'] + (
        0.001 if retirement == 'clear' else 0.002
    ), 'REUSE: settling old model work cannot overwrite the genuine original manual edit'
    after = reuse269_send(actor, trace, 'Original fresh turn after actual control settlement')
    assert started_requests(trace)[-1]['params']['threadId'] != active['threadId'], (
        'REUSE: Clear or a genuine scope upgrade defeats routine-thread retention permanently'
    )
    reuse269_account(original, after, trace)


def test_reuse269_fresh_turn_rejects_actual_old_native_turn_authority(generic):
    # The old turn ID is the independently predeclared first original native script
    # ID (peer native_start), not an identity inferred from candidate output.
    first = native_call('set_parameters', values=[
        {'path': 'structure.cell.length_a', 'value': 3.911}
    ])
    stale = native_call('set_parameters', values=[
        {'path': 'structure.cell.length_a', 'value': 3.912}
    ])
    stale['turn_id'] = '019a0290-0000-7000-8000-000000000002'
    actor, trace = native_case(generic, [],
        project=ROOT / 'tests/fixtures/e04_t1/editable-project', connect_now=False,
        script={'reuse269': {}})
    assert actor.command('native_science_enable')['reply']['enabled']
    native145_configure(actor, trace, [[first], [stale]])
    original = native145_science_settled(actor)
    reuse269_send(actor, trace, 'Original first turn commits its own valid value', native_count=1)
    settled = native145_science_settled(actor)
    assert native_parameter(settled)['value'] == 3.911, (
        'REUSE SETUP: first original-turn value really committed before stale-ID escape'
    )
    before = settled['project']
    assert not settled['context_consent_required'], (
        'REUSE: original successful own edit does not force unrelated reapproval'
    )
    actor.command('send_text', text='Original fresh turn must not authorize old native turn')
    settle(actor, lambda _value: len(native_records(trace, '.native-emitted.jsonl')) == 2)
    assert len(started_requests(trace)) == 2 and rpc83_context_inputs(
        started_requests(trace)[-1]['params']
    ) == [settled['context']], 'REUSE: stale escape starts only from an actually fresh full GUI context'
    state = actor.command('inspect')['vm']  # Existing ordinary event delivery after real emission.
    emitted = native_records(trace, '.native-emitted.jsonl')
    assert len(emitted) == 2 and emitted[-1]['params']['turnId'] == stale['turn_id'] and (
        emitted[-1]['params']['turnId'] != emitted[-1]['binding']['turnId']
    ), 'REUSE SETUP: exact old turn is actually emitted during a distinct genuine current turn'
    responses = native_records(trace, '.native-replies.jsonl')
    assert 1 <= len(responses) <= 2 and not native_records(trace, '.native-wrong-envelope.jsonl'), (
        'REUSE: stale authority cannot produce duplicate or rebased original responses'
    )
    if len(responses) == 2:
        refused = responses[-1]
        response = refused['response']
        error = response.get('error')
        lawful_failure = response.get('result', {}).get('success') is False or (
            isinstance(error, dict) and type(error.get('code')) is int
            and isinstance(error.get('message'), str) and 'result' not in response
        )
        assert refused['original']['id'] == emitted[-1]['id'] == response['id'] and lawful_failure, (
            'REUSE: any stale refusal is exactly once on its original envelope, never new authority'
        )
    assert state['project']['parameters'] == before['parameters'] and (
        native_inputs(state) == native_inputs(settled)
    ), 'REUSE: even a lawfully unanswered stale call cannot acquire authority or write partial science'
    if state['can_cancel']:
        actor.command('cancel')  # Genuine Stop settles a lawfully unanswered foreign request.
        state = settle(actor, lambda value: not value['can_cancel'])
    assert state['project']['parameters'] == before['parameters'] and (
        native_inputs(state) == native_inputs(settled)
    ), 'REUSE: original Stop/control settlement cannot revive rejected old-turn authority'
    final_responses = native_records(trace, '.native-replies.jsonl')
    assert 1 <= len(final_responses) <= 2 and final_responses[0] == responses[0] and not (
        native_records(trace, '.native-wrong-envelope.jsonl')
    ), 'REUSE: final discard/Stop retains the first reply and permits at most one original stale refusal'
    if len(final_responses) == 2:
        refused = final_responses[-1]
        response = refused['response']
        error = response.get('error')
        lawful_failure = response.get('result', {}).get('success') is False or (
            isinstance(error, dict) and type(error.get('code')) is int
            and isinstance(error.get('message'), str) and 'result' not in response
        )
        assert refused['original']['id'] == emitted[-1]['id'] == response['id'] and lawful_failure, (
            'REUSE: deferred stale refusal remains exact original once-only failure, never scientific success'
        )
    assert actor.command('native_undo')['reply']['was_available'], (
        'REUSE: rejected stale call cannot consume the valid original recorded Undo'
    )
    undone = native145_science_settled(actor)
    assert undone['project']['parameters'] == original['project']['parameters'], (
        'REUSE: one real Undo restores exactly the original pre-first-call scientific state'
    )


def test_reuse280_failed_archive_clear_cannot_claim_fresh_memory(generic):
    actor, trace = generic('fileauth')
    assert actor.command('open', path=str(ROOT / 'tests/fixtures/e04_t1/editable-project'))[
        'reply'
    ]['opened'], 'REUSE SETUP: actual original project loads before failed discard control'
    reuse269_configure(trace)
    connect(actor)
    native145_approve(actor)
    first = reuse269_send(actor, trace, 'Original durable history before real storage refusal')
    # Original input acknowledgement/idle is not final public-history publication.
    # The independent fileauth peer's first response has this exact declared text.
    first = settle(actor, lambda value: (
        value['connected'] and not value['can_cancel'] and not value['last_error']
        and all(row in value['messages'] for row in first['messages'])
        and any(row.get('kind') == 'assistant' and row.get('status') == 'completed'
                and row.get('text') == 'Original fileauth reply 1'
                for row in value['messages'])
    ))
    old_thread = started_requests(trace)[-1]['params']['threadId']
    baseline = actor.command('archive')
    before_rows = baseline['reply']['rows']
    assert baseline['vm']['messages'] == first['messages'] == before_rows, (
        'REUSE SETUP: the complete original response is paired with exactly its durable public archive'
    )
    first = baseline['vm']
    barrier = actor.command('persistence_barrier')
    assert barrier['archive']['is_directory'] and barrier['reply']['preserved_sha256'], (
        'REUSE SETUP: actual QSaveFile target is blocked with original archive bytes preserved'
    )
    actor.command('clear_history')
    state = settle(actor, lambda value: not value['can_cancel'] and bool(value['last_error']))
    assert state['messages'] == first['messages'] and state['project'] == first['project'], (
        'REUSE: refused durable Clear retains original canonical history/science/Undo'
    )
    assert len(started_requests(trace)) == 1 and len(reuse269_thread(trace)[1]) == 1, (
        'REUSE: failed discard cannot manufacture a fresh backend conversation'
    )
    reuse269_account(first, state, trace)
    actor.command('persistence_restore')
    assert actor.command('archive')['reply']['rows'] == before_rows, (
        'REUSE: restored real archive retains exactly the original committed records'
    )
    actor.command('clear_history')
    state = settle(actor, lambda value: not value['can_cancel'] and not value['messages'])
    assert_clear_projection156(state)
    assert actor.command('archive')['reply']['rows'] == [], (
        'REUSE: later genuine successful Clear commits empty history, not inferred success'
    )
    assert not actor.last['vm']['context_consent_required'], (
        'REUSE: successful retry retains only the unchanged preowned remaining project scope'
    )
    final = reuse269_send(actor, trace, 'Original new memory only after actual committed discard')
    assert started_requests(trace)[-1]['params']['threadId'] != old_thread
    reuse269_account(first, final, trace)


# BG285: public declared ordinary/native policy, exact core round-trip invariants,
# and committed independent fixture writer. No producer-generated scientific golden.
def background285_fixture(tmp_path, kind='cw', rows=3, *, arrangement=None, constrained=False,
                          second_bank=False):
    root = tmp_path / 'Original declared background input'
    namespace = {}
    factory = ROOT / 'tests/fixtures/c13_t6_background/project.py'
    exec(compile(factory.read_text(), str(factory), 'exec'), namespace)
    axis = [10.0, 20.0, 30.0, 40.0] if kind != 'tof' else [2000.0, 4000.0, 6000.0, 8000.0]
    namespace['materialize'](root, {'project': 'pd-neut-' + ('tof' if kind == 'tof' else 'cwl'),
                                  'type': 'line-segment'}, axis, [41.0, 43.0, 47.0, 53.0])
    path = root / 'experiments/experiment.edi'
    text = path.read_text()
    prefix, data = text.split('loop_\n_data.', 1)
    prefix = prefix.split('_background.type', 1)[0]
    positions = arrangement or ([12.0, 20.0, 28.0] if kind != 'tof' else [2400.0, 4000.0, 5600.0])
    if rows > 3:
        positions = [axis[0] + (axis[-1] - axis[0]) * (i + 1) / (rows + 1) for i in range(rows)]
    prefix += '_background.type line-segment\nloop_\n_background.id\n_background.position\n_background.intensity\n'
    prefix += ''.join(f'p{i} {position:.17g} {11.25 + i:.17g}(25)\n' for i, position in enumerate(positions))
    prefix += '\nloop_\n_excluded_region.id\n_excluded_region.start\n_excluded_region.end\nmask 21 22\n'
    if kind == 'no-measured-source':
        # Real load path generates a calculation-only grid; it is not a raw null-data hook.
        text = prefix + '\n_data_range.two_theta_min 10\n_data_range.two_theta_max 40\n_data_range.two_theta_step 10\n'
    else:
        data_lines = data.splitlines()
        assert data_lines[:3] == [
            'time_of_flight' if kind == 'tof' else 'two_theta',
            '_data.intensity_meas', '_data.intensity_meas_su',
        ], 'BG SETUP: actual fixture axis/intensity/sigma headers precede every original observation'
        values = [line for line in data_lines[3:] if line]
        assert len(values) == 4, 'BG SETUP: the public fixture writer declares four literal original observations'
        prefix += 'loop_\n_data.' + data.splitlines()[0] + '\n_data.intensity_meas\n_data.intensity_meas_su\n'
        prefix += ''.join(f'{x:.17g} {y:.17g} {s:.17g}\n' for x, y, s in zip(axis, [41, 43, 47, 53], [.5, .75, 1.25, 2], strict=True))
        text = prefix
    path.write_text(text)
    analysis = root / 'analysis/analysis.edi'
    analysis.write_text('_edi.schema_version 3\n_fitting_mode.type single\n_minimizer.max_iterations 3\n'
        + ('\nloop_\n_alias.id\n_alias.parameter_unique_name\nkeep_target experiment.background.p0.intensity\n'
           'loop_\n_constraint.id\n_constraint.expression\n_constraint.enabled\n'
           'keep_value "keep_target = 11.25" true\n' if constrained else ''))
    analysis.write_text(analysis.read_text() + '\nloop_\n_fit_parameter.id\n_fit_parameter.start_value\n_fit_parameter.start_uncertainty\nexperiment.background.p1 10.75 0.125\n')
    if second_bank:
        (root / 'experiments/other.edi').write_text(path.read_text().replace(
            'data_experiment', 'data_other', 1))
    return root


def background285_image(actor):
    return actor.command('inspect')['vm']['project']['background285']


def background285_bank(image, name='experiment'):
    rows = [row for row in image['banks'] if row['id'] == name]
    assert len(rows) == 1, 'BG: exact actual bank identity resolves uniquely, never an implicit bank switch'
    return rows[0]


def background285_without_identity(row):
    return {key: value for key, value in row.items() if key != 'identity'}


def background285_preserved(before, after, bank_id='experiment'):
    assert all(before[key] == after[key] for key in ['owner', 'core', 'mode', 'path', 'selected_index']), (
        'BG: actual current Session/core owner remains the original project'
    )
    old = background285_bank(before, bank_id)
    new = background285_bank(after, bank_id)
    assert {k: v for k, v in old.items() if k != 'anchors'} == {
        k: v for k, v in new.items() if k != 'anchors'
    }, 'BG: complete raw axes/intensity/sigma, every write identity, exclusions, phase links/scale, weight and bank metadata survive'
    unrelated_before = [row for row in before['parameters'] if '.background[' not in row['path']]
    unrelated_after = [row for row in after['parameters'] if '.background[' not in row['path']]
    assert unrelated_before == unrelated_after, (
        'BG: complete unrelated spec/start/SU/free/dependence and composition parameters are preserved'
    )
    assert [row for row in before['banks'] if row['id'] != bank_id] == [
        row for row in after['banks'] if row['id'] != bank_id
    ], 'BG: unrelated banks retain exact membership, source bytes and anchor metadata/identities'


def background285_undo(actor, before, bank_id='experiment'):
    assert actor.command('native_undo')['reply']['was_available'], (
        'BG: the actual common editor retains one genuine recorded Undo'
    )
    restored = background285_image(actor)
    background285_preserved(before, restored, bank_id)
    assert background285_bank(restored, bank_id)['anchors'] == background285_bank(before, bank_id)['anchors'], (
        'BG: ONE actual Undo restores every original ordered owned row identity/ID/value/free/SU/start/dependence/spec'
    )
    assert restored['parameters'] == before['parameters'] and restored['can_undo'] == before['can_undo'], (
        'BG: one structural edit/Undo restores full parameter metadata and the actual prior Undo availability'
    )


@pytest.mark.parametrize('case', ['simulation', 'no-measured-source', 'legacy-owned-key',
                                  'extrapolation', 'duplicate-order', 'above-native-capacity'])
def test_background285_ordinary_policy_and_real_undo(generic, tmp_path, case):
    root = background285_fixture(tmp_path,
        'no-measured-source' if case == 'no-measured-source' else 'cw',
        257 if case == 'above-native-capacity' else 3,
        arrangement=[28.0, 12.0, 12.0] if case == 'duplicate-order' else None)
    actor, trace = native_case(generic, [], project=root, connect_now=False)
    actor.command('native_science_enable')
    assert actor.command('background285_observe')['reply']['enabled'], (
        'BG SETUP: test-only observer reads actual model state without preparing edits'
    )
    bank_id = 'experiment'
    if case == 'simulation':
        result = actor.command('background285_simulation')
        assert result['reply']['created'], 'BG SETUP: genuine public Create Experiment creates a simulation'
        image = background285_image(actor)
        simulations = [row for row in image['banks'] if row['calculation_only']]
        assert len(simulations) == 1, 'BG SETUP: actual new simulation is unique among the measured source bank'
        bank_id = simulations[0]['id']
    if case == 'legacy-owned-key':
        renamed = actor.command('background285_manual', action='rename', row=1, id='legacy\towned')
        assert renamed['reply']['accepted'], 'BG SETUP: existing ordinary rename accepts original owned legacy key bytes'
    before = background285_image(actor)
    original = background285_bank(before, bank_id)['anchors']
    if case == 'no-measured-source':
        assert background285_bank(before)['calculation_only'], (
            'BG SETUP: actual no-measurement source is a genuine calculation-only project, not a fake measured bank'
        )
    if case == 'above-native-capacity':
        assert len(original) == 257, 'BG SETUP: ordinary source genuinely exceeds the native inclusive256 rows'
    if case == 'simulation':
        result = actor.command('background285_manual', action='defined', operation='add', id='manual-first',
                               position=2.5, intensity=7.25, free=True)
        assert result['reply']['applied'] and result['reply']['published'], (
            'BG: ordinary no-observation simulation Add commits through actual shared editor'
        )
        after = background285_image(actor)
        background285_preserved(before, after, bank_id)
        anchors = background285_bank(after, bank_id)['anchors']
        assert len(anchors) == len(original) + 1 and [row['id'] for row in anchors[:-1]] == [row['id'] for row in original] and any(row['id'] == 'manual-first' and row['position'] == 2.5 and row['value'] == 7.25
                   and row['free'] for row in anchors), 'BG: genuine simulation Add publishes exact declared point'
        background285_undo(actor, before, bank_id)
        return
    # Existing row entrance must preserve exact already-owned key bytes, not route
    # them through native text admission. Ordinary finite positions may extrapolate
    # or duplicate an existing one while preserving the original slot/order.
    position = -4.5 if case == 'extrapolation' else original[0]['position']
    result = actor.command('background285_manual', action='position', row=1, position=position)
    assert result['reply']['accepted'], 'BG: genuine ordinary row position admits its broader finite manual policy'
    after = background285_image(actor)
    background285_preserved(before, after, bank_id)
    anchors = background285_bank(after, bank_id)['anchors']
    expected = json.loads(json.dumps(original))
    expected[1]['position'] = position
    assert [background285_without_identity(row) for row in anchors] == [
        background285_without_identity(row) for row in expected
    ], 'BG: manual position changes only its exact existing row, without sorting/clamping/ID normalization'
    assert all(anchors[i]['identity'] == original[i]['identity'] for i in range(len(original)) if i != 1), (
        'BG: every unrelated actual shared anchor identity survives manual update'
    )
    background285_undo(actor, before, bank_id)
    before = background285_image(actor)
    removed = actor.command('background285_manual', action='remove', row=1)
    assert removed['reply']['removed'], 'BG: actual ordinary remove reaches its exact owned row at every capability size'
    after = background285_image(actor)
    background285_preserved(before, after, bank_id)
    assert [row['id'] for row in background285_bank(after, bank_id)['anchors']] == [
        row['id'] for i, row in enumerate(background285_bank(before, bank_id)['anchors']) if i != 1
    ], 'BG: manual removal preserves exact remaining legacy keys and original order'
    background285_undo(actor, before, bank_id)
    # Ordinary staged Add stays outside native capacity/domain policy as well.
    before = background285_image(actor)
    result = actor.command('background285_manual', action='defined', operation='add', id='manual-extra',
                           position=50.5, intensity=8.125, free=False)
    assert result['reply']['applied'] and result['reply']['published'], (
        'BG: ordinary staged Add remains available for no-measurement, legacy, duplicate and above-native-capacity banks'
    )
    after = background285_image(actor)
    background285_preserved(before, after, bank_id)
    actual = background285_bank(after, bank_id)['anchors']
    assert [row['id'] for row in actual] == [row['id'] for row in background285_bank(before, bank_id)['anchors']] + ['manual-extra'], (
        'BG: ordinary Add appends without normalizing original order or imposing native row admission'
    )
    background285_undo(actor, before, bank_id)
    assert not trace.exists(), 'BG: ordinary shared editor never silently starts an assistant/provider process'


@pytest.mark.parametrize('case', ['cw', 'tof', 'outside', 'wrong-bank', 'duplicate-position',
    'existing-id', 'missing-id', 'control-id', 'id-equal', 'id-over', 'count-equal', 'count-over',
    'dependent', 'alias-removal', 'remove-extra-fields', 'wrong-type', 'simulation',
    'repair-unsorted', 'repair-unsorted-add', 'repair-unsorted-update',
    'repair-duplicate', 'repair-extrapolation', 'remove', 'undo-conflict',
    'valid-two-bank-current', 'valid-distinct-update'])
def test_background285_original_native_policy_metadata_and_undo(generic, tmp_path, case):
    root = background285_fixture(tmp_path, 'tof' if case == 'tof' else 'cw',
                                  255 if case == 'count-equal' else 256 if case == 'count-over' else 3,
                                  constrained=case in {'dependent', 'alias-removal'},
                                  arrangement=[28.0, 12.0, 20.0] if case.startswith('repair-unsorted') else
                                  [12.0, 20.0, 20.0] if case == 'repair-duplicate' else
                                  [9.0, 20.0, 28.0] if case == 'repair-extrapolation' else None,
                                  second_bank=case in {'wrong-bank', 'valid-two-bank-current'})
    actor, trace = native_case(generic, [], project=root, connect_now=False)
    actor.command('native_science_enable')
    actor.command('background285_observe')
    if case == 'simulation':
        assert actor.command('background285_simulation')['reply']['created'], (
            'BG SETUP: native refusal observes a real current simulation rather than a fake flag'
        )
    initial = background285_image(actor)
    context = json.loads(actor.last['vm']['native_context'])
    if case == 'simulation':
        bank_id = next(row['id'] for row in initial['banks'] if row['calculation_only'])
    else:
        bank_id = 'experiment'
    bank = background285_bank(initial, bank_id)
    if case != 'simulation':
        original_p1 = next(row for row in bank['anchors'] if row['id'] == 'p1')
        assert original_p1['value'] == 12.25 and original_p1['uncertainty'] == 0.25 and (
            original_p1['start_value'] == 10.75 and original_p1['start_uncertainty'] == 0.125
        ), 'BG SETUP: original nonzero SU and fit-start metadata are literal fixture inputs, not an output-derived golden'
    disclosed = [row for row in context['datasets'] if row['id'] == bank_id]
    assert len(disclosed) == 1, 'BG SETUP: exact current dataset is genuinely disclosed before original native RPC'
    expected_descriptors = [{key: row[key] for key in ['id', 'position', 'free']}
                            | {'intensity': row['value'], 'uncertainty': row['uncertainty'],
                               'dependence': 'constrained' if row['dependence'] == 3 else 'independent'}
                            for row in bank['anchors']]
    assert disclosed[0]['background']['anchors'] == expected_descriptors, (
        'BG: complete ordered public context owns every actual anchor ID/value/SU/free/dependence, never a truncated prefix'
    )
    args = dict(experiment=bank_id, operation='update', id='p1', position=bank['anchors'][1]['position']
                if len(bank['anchors']) > 1 else 1.0, intensity=12.25, free=False)
    good = case in {'cw', 'tof', 'id-equal', 'count-equal', 'repair-unsorted',
                    'repair-unsorted-add', 'repair-unsorted-update',
                    'repair-duplicate', 'repair-extrapolation', 'remove', 'undo-conflict',
                    'valid-two-bank-current', 'valid-distinct-update'}
    if case in {'id-equal', 'id-over', 'count-equal', 'count-over', 'outside', 'existing-id', 'control-id', 'duplicate-position', 'repair-unsorted-add'}:
        args.update(operation='add', id=('測' * 85 + 'x') if case == 'id-equal' else ('測' * 85 + 'xx')
                    if case == 'id-over' else 'bad\tkey' if case == 'control-id' else 'p0' if case == 'existing-id' else 'native-new',
                    position=9.0 if case == 'outside' else bank['anchors'][0]['position'] if case == 'duplicate-position' else 35.0)
    if case == 'wrong-bank':
        other = background285_bank(initial, 'other')
        assert bank['id'] == initial['banks'][initial['selected_index']]['id'] and other['id'] != bank['id'] and (
            not other['calculation_only'] and other['axis'] == bank['axis']
            and [row['id'] for row in other['anchors']] == ['p0', 'p1', 'p2']
        ), 'BG NEGATIVE SETUP: target is a real existing measured NONCURRENT bank with lawful rows, never an unknown name'
        args['experiment'] = other['id']
    if case == 'missing-id':
        args.update(id='no-such-anchor', position=21.5)
        assert all(row['position'] != args['position'] and row['id'] != args['id'] for row in bank['anchors']), (
            'BG NEGATIVE SETUP: missing-ID Update has distinct in-range otherwise-valid position, so an upsert cannot refuse for collision'
        )
    if case == 'dependent': args.update(id='p0', position=bank['anchors'][0]['position'], intensity=21.0)
    if case in {'alias-removal', 'remove-extra-fields', 'remove', 'repair-unsorted', 'repair-duplicate'}:
        args = dict(experiment=bank_id, operation='remove', id='p0' if case in {'alias-removal', 'remove-extra-fields'} else 'p1')
        if case == 'remove-extra-fields': args.update(position=12, intensity=11.25, free=False)
    if case == 'repair-extrapolation': args.update(id='p0', position=12.0, intensity=11.25)
    if case == 'repair-unsorted-update': args.update(position=14.0)
    if case == 'valid-distinct-update': args.update(position=21.5)
    if case == 'valid-two-bank-current':
        other = background285_bank(initial, 'other')
        assert bank['id'] == initial['banks'][initial['selected_index']]['id'] and other['id'] != bank['id'], (
            'BG POSITIVE SETUP: exact same two-bank fixture admits a current-bank edit, isolating noncurrent refusal'
        )
    if case == 'simulation':
        args.update(operation='add', id='simulation-new', position=20.5, intensity=12.25, free=False)
        assert bank['calculation_only'] and bank['axis'] and min(bank['axis']) <= args['position'] <= max(bank['axis']) and all(
            row['id'] != args['id'] and row['position'] != args['position'] for row in bank['anchors']
        ), 'BG NEGATIVE SETUP: measured-only rejection gets a lawful real simulation Add, never an absent-row Update'
    if case == 'wrong-type': args['free'] = 1
    call = native_call('edit_background', **args)
    native145_configure(actor, trace, [[call]])
    before = background285_image(actor)
    old_state = actor.last['vm']
    state, replies = native_send(actor, trace, 1)
    outcome = replies[0]['decoded']
    after = background285_image(actor)
    background285_preserved(before, after, bank_id)
    if good:
        assert replies[0]['response']['result']['success'] and outcome['status'] == 'edited', (
            'BG: genuine native CW/TOF and inclusive exact capacities commit, not applied_unconfirmed/refused'
        )
        anchors = background285_bank(after, bank_id)['anchors']
        if args['operation'] == 'remove':
            expected = sorted([(row['id'], row['position'], row['value'], row['free'])
                               for row in bank['anchors'] if row['id'] != args['id']], key=lambda row: row[1])
        elif args['operation'] == 'add':
            expected = sorted([(row['id'], row['position'], row['value'], row['free']) for row in bank['anchors']]
                              + [(args['id'], args['position'], args['intensity'], args['free'])], key=lambda row: row[1])
        else:
            expected = [(row['id'], args['position'] if row['id'] == args['id'] else row['position'],
                         args['intensity'] if row['id'] == args['id'] else row['value'],
                         args['free'] if row['id'] == args['id'] else row['free']) for row in bank['anchors']]
            expected.sort(key=lambda row: row[1])
        assert [(row['id'], row['position'], row['value'], row['free']) for row in anchors] == expected, (
            'BG: one native edit publishes exactly its independently declared sorted arrangement'
        )
        old = {row['id']: row for row in bank['anchors']}
        for row in anchors:
            if row['id'] in old and row['id'] != args['id']:
                assert row == old[row['id']], 'BG: every untouched native row keeps shared identity and all original metadata'
            elif row['id'] in old:
                assert row['uncertainty'] == old[row['id']]['uncertainty'] and all(
                    row[key] == old[row['id']][key] for key in ['spec_identity', 'start_value', 'start_uncertainty', 'dependence']
                ), 'BG: equal-intensity native update preserves original SU/start/spec/dependence exactly'
        if case == 'undo-conflict':
            target = next(row for row in actor.last['vm']['project']['parameters']
                          if '.background[p1]' in row['path'])
            actual = actor.command('manual_value', path=target['path'], value=target['value'] + 2.0)
            assert not actual['reply']['error'], 'BG SETUP: genuine later ordinary edit changes the actual affected row'
            conflict = background285_image(actor)
            assert actor.command('native_undo')['reply']['was_available'], 'BG SETUP: original structural Undo is still offered before conflict validation'
            refused_undo = background285_image(actor)
            assert {k: v for k, v in refused_undo.items() if k != 'can_undo'} == {
                k: v for k, v in conflict.items() if k != 'can_undo'
            }, 'BG: conflicting Undo never writes its stale recorded background over a later actual manual edit'
        else:
            background285_undo(actor, before, bank_id)
            if case.startswith('repair-'):
                assert background285_bank(background285_image(actor), bank_id)['anchors'] == bank['anchors'], (
                    'BG: native repair ONE Undo restores exact original unsorted/duplicate/extrapolating rows and shared identities'
                )
    else:
        assert not replies[0]['response']['result']['success'] and outcome['status'] in {'refused', 'unavailable'}, (
            'BG: native domain/type/count/text/current-bank/dependence/alias violations honestly refuse before writes'
        )
        assert after == before, 'BG: refused original native work preserves every anchor/spec/raw identity and Undo'
    reuse269_account(old_state, actor.last['vm'], trace)


def test_background285_complete_context_cannot_truncate_over_cap_anchor_collection(generic, tmp_path):
    root = background285_fixture(tmp_path, rows=256)
    original = root / 'experiments/experiment.edi'
    text = original.read_text()
    anchor_lines = text.split('_background.intensity\n', 1)[1].split('\nloop_', 1)[0].splitlines()
    rows = [line.split() for line in anchor_lines if line.strip()]
    assert len(rows) == 256, 'BG RESOURCE SETUP: actual declared per-bank anchor count is exactly the inclusive native limit'
    # Seventeen banks x256 distinct256-byte owned IDs exceeds1MiB just in IDs.
    # Ordinary file sources own these bounded literal inputs before any native call.
    total_id_bytes = 0
    for bank in range(17):
        replacement = []
        for index, row in enumerate(rows):
            identifier = f'owned-{bank:02d}-{index:03d}-' + 'x' * (256 - len(f'owned-{bank:02d}-{index:03d}-'))
            assert len(identifier.encode()) == 256, 'BG RESOURCE SETUP: independent ASCII ID spelling is exactly256 UTF8 bytes'
            total_id_bytes += len(identifier.encode())
            replacement.append(identifier + ' ' + row[1] + ' ' + row[2])
        bank_text = text.replace('data_experiment', 'data_bank_' + str(bank), 1)
        bank_text = bank_text.replace('\n'.join(anchor_lines), '\n'.join(replacement), 1)
        (root / 'experiments' / ('bank_' + str(bank) + '.edi')).write_text(bank_text)
    original.unlink()
    # No fit-start names are retained for a nonexistent renamed original bank.
    (root / 'analysis/analysis.edi').write_text('_edi.schema_version 3\n_fitting_mode.type joint\n')
    assert total_id_bytes == 17 * 256 * 256 and total_id_bytes > 1048576, (
        'BG RESOURCE: mandatory complete descriptor IDs alone exceed the declared inclusive1MiB context capacity'
    )
    actor, trace = native_case(generic, [], project=root, connect_now=False)
    state = actor.last['vm']
    assert len([row for row in state['project']['parameters'] if '.background[' in row['path']]) == 17 * 256, (
        'BG RESOURCE SETUP: actual ordinary source admitted every declared owned anchor before context refusal'
    )
    context = json.loads(state['native_context'])
    assert context.get('error'), (
        'BG RESOURCE: actual complete context refuses honestly instead of returning a silently truncated dataset/anchor prefix'
    )
    assert not trace.exists(), 'BG RESOURCE: capacity refusal never silently starts a provider/account process'


# Pure setup preflight: these literal factory shapes are shared by ordinary,
# native and Main background cases. No Session, native process or app is started.
BACKGROUND291_FIXTURE_SHAPES = [
    pytest.param('cw', 3, None, False, False, id='cw-simulation-base'),
    pytest.param('tof', 3, None, False, False, id='tof'),
    pytest.param('no-measured-source', 3, None, False, False, id='no-measured-source'),
    pytest.param('cw', 3, [28.0, 12.0, 12.0], False, False, id='ordinary-duplicate-order'),
    pytest.param('cw', 3, [28.0, 12.0, 20.0], False, False, id='native-unsorted-repair'),
    pytest.param('cw', 3, [12.0, 20.0, 20.0], False, False, id='native-duplicate-repair'),
    pytest.param('cw', 3, [9.0, 20.0, 28.0], False, False, id='native-extrapolation-repair'),
    pytest.param('cw', 255, None, False, False, id='native-count-equal'),
    pytest.param('cw', 256, None, False, False, id='native-count-over-and-context'),
    pytest.param('cw', 257, None, False, False, id='ordinary-above-native-capacity'),
    pytest.param('cw', 3, None, True, False, id='original-alias-constraint'),
    pytest.param('cw', 3, None, False, True, id='existing-nonselected-bank'),
]


@pytest.mark.parametrize('kind,rows,arrangement,constrained,second_bank',
                         BACKGROUND291_FIXTURE_SHAPES)
def test_background291_fixture_construction_preserves_declared_sections(
        tmp_path, kind, rows, arrangement, constrained, second_bank):
    """Setup-only gate over real committed factory; never a background product pass."""
    root = background285_fixture(tmp_path, kind, rows, arrangement=arrangement,
                                 constrained=constrained, second_bank=second_bank)
    experiment = (root / 'experiments/experiment.edi').read_text()
    if kind == 'no-measured-source':
        assert '_data.' not in experiment and (
            '_data_range.two_theta_min 10\n_data_range.two_theta_max 40\n'
            '_data_range.two_theta_step 10\n' in experiment
        ), 'BG291 SETUP: calculation-only fixture keeps its literal declared range and has no measured data loop'
    else:
        axis_name = 'time_of_flight' if kind == 'tof' else 'two_theta'
        axis = [2000, 4000, 6000, 8000] if kind == 'tof' else [10, 20, 30, 40]
        expected_rows = list(zip(axis, [41, 43, 47, 53], [.5, .75, 1.25, 2], strict=True))
        expected_block = ('loop_\n_data.' + axis_name
            + '\n_data.intensity_meas\n_data.intensity_meas_su\n'
            + ''.join(f'{x:.17g} {y:.17g} {sigma:.17g}\n' for x, y, sigma in expected_rows))
        assert experiment.endswith(expected_block) and experiment.count(expected_block) == 1, (
            'BG291 SETUP: exact axis/intensity/sigma headers precede all four original numeric observations once'
        )
        assert len(expected_rows) == 4 and all(len(row) == 3 and row[2] > 0 for row in expected_rows), (
            'BG291 SETUP: independent original four measured triples retain their literal positive sigmas'
        )
    anchors = experiment.split('_background.intensity\n', 1)[1].split('\nloop_', 1)[0].splitlines()
    anchors = [line for line in anchors if line]
    positions = arrangement if arrangement is not None else (
        [2400.0, 4000.0, 5600.0] if kind == 'tof' else [12.0, 20.0, 28.0])
    if rows > 3:
        positions = [10.0 + 30.0 * (index + 1) / (rows + 1) for index in range(rows)]
    assert anchors == [f'p{index} {position:.17g} {11.25 + index:.17g}(25)'
                       for index, position in enumerate(positions)], (
        'BG291 SETUP: original ordered anchor IDs, positions, literal intensities and nonzero SU remain exact'
    )
    assert '\nmask 21 22\n' in experiment and (
        '\nstructure 0\n' in experiment
    ), 'BG291 SETUP: original exclusion and linked phase scale survive the measured-loop extraction'
    analysis = (root / 'analysis/analysis.edi').read_text()
    assert analysis.endswith('experiment.background.p1 10.75 0.125\n'), (
        'BG291 SETUP: independent original nonzero fit-start value/SU and canonical persistent key survive'
    )
    assert ('keep_target experiment.background.p0.intensity' in analysis) is constrained and (
        ('keep_value "keep_target = 11.25" true' in analysis) is constrained
    ), 'BG291 SETUP: original alias/constraint fixture is present exactly when explicitly requested'
    other = root / 'experiments/other.edi'
    assert other.exists() is second_bank, 'BG291 SETUP: only declared two-bank variants create the nonselected bank'
    if second_bank:
        assert other.read_text() == experiment.replace('data_experiment', 'data_other', 1), (
            'BG291 SETUP: actual second measured bank differs only by its independent original dataset name'
        )

def ux345_default_scattering_project(owned):
    """Owned original scientific bytes, deliberately using the public native default table."""
    original = ROOT / 'tests/fixtures/e04_t1/editable-project'
    before = save211_files(original)
    declaration = (b'loop_\n_scattering_length.type_symbol\n'
                   b'_scattering_length.length_fm\nLa 8.24\n')
    structure = before['structures/lbco.edi']
    assert structure.count(declaration) == 1 and structure.endswith(declaration), (
        'UX345 SETUP: committed original has exactly the known terminal La-only custom declaration'
    )
    expected = dict(before)
    expected['structures/lbco.edi'] = structure[:-len(declaration)]
    assert b'_scattering_length.' not in expected['structures/lbco.edi'], (
        'UX345 SETUP: owned fixture truly omits the custom table and requests the documented default'
    )
    source = owned / 'ux345-default-scattering-project'
    assert not source.exists() and not source.is_symlink(), (
        'UX345 SETUP: scientific input is a fresh owned directory, never shared or reused'
    )
    shutil.copytree(original, source)
    (source / 'structures/lbco.edi').write_bytes(expected['structures/lbco.edi'])
    assert save211_files(source) == expected and save211_files(original) == before, (
        'UX345 SETUP: only the incomplete custom declaration is omitted; every other byte and original fixture stay exact'
    )
    assert expected['structures/lbco.edi'] + declaration == structure, (
        'UX345 SETUP: literal declaration reinsertion reconstructs every original scientific structure byte'
    )
    return source


# Direct public facade ownership is deliberately separate from real Session/account
# authority. Existing target/peer/Generic transport and bounds only.
@pytest.mark.parametrize(('trigger', 'action'), [
    ('response', 'destroy'), ('response', 'recreate'), ('event', 'recreate'),
    ('failed-record', 'restart'), ('failed-eof', 'recreate'),
    ('failed-deadline', 'recreate'), ('before-write', 'recreate'),
])
def test_ux304_public_transport_callback_owns_original_receiver(generic, trigger, action):
    actor, trace = generic('transport304')
    source = ux345_default_scattering_project(trace.parent)
    assert actor.command('open', path=str(source))[
        'reply']['opened'], 'UX304 SETUP: real scientific owner exists outside isolated facade caller'
    actor.command('native_science_enable')
    actor.command('background285_observe')
    original = settle(actor, lambda value: not value['project']['science_observer']['calculating']
                      and all(x['current'] for x in value['project']['science_observer']['calculations']))
    before = json.loads(json.dumps(original))
    config_path = trace.parent / 'peer-input.json'
    config = json.loads(config_path.read_text())
    config['transport304_mode'] = trigger
    config_path.write_text(json.dumps(config))
    original_config = config_path.read_bytes()
    assert actor.command('codex304_start', trigger=trigger, action=action)['reply']['armed'], (
        'UX304 SETUP: existing native target starts only its actual owned public facade'
    )
    for _ in range(40):
        state = actor.last.get('public_transport304', {})
        completed = state.get('boundary_reached') and (action == 'destroy' or any(
            x['signal'] == 'response' and x['label'] == 'B' for x in state.get('events', [])))
        if completed:
            break
        actor.command('inspect')
    state = actor.last.get('public_transport304', {})
    assert state.get('boundary_reached') and not state.get('observer_error') and not state.get(
        'observer_overflow'), 'UX304 SETUP: original real public callback interval is witnessed without synthetic state'
    event = state['events'][state['boundary_event_index']]
    assert event['label'] == 'A' and event['signal'] == (
        'failed' if trigger.startswith('failed-') else trigger
    ) and event['receiver'] == state['original_receiver'] and event['original_alive_at_entry'], (
        'UX304: reached callback belongs to the exact original live public QObject receiver'
    )
    assert event['depth'] >= 1 and state['boundary_in_callback_depth'] >= 1 and event[
        'returned_from_action_in_same_callback'], (
        'UX304: real deletion/restart returned inside original direct callback, never between command frames'
    )
    assert event['original_alive_after_action'] is (action == 'restart'), (
        'UX304: QPointer proves genuine QObject destruction or surviving same-facade process restart'
    )
    assert not any(x['label'] == 'A' for x in state['events'][state['boundary_event_index'] + 1:]), (
        'UX308: disconnected A listener records no later A signal; this alone is not stale-emission proof'
    )
    if action != 'destroy':
        replacement = [x for x in state['events'] if x['label'] == 'B' and x['signal'] == 'response']
        assert len(replacement) == 1 and replacement[0]['request_id'] == state['issued']['B'] and (
            replacement[0]['envelope']['id'] == state['issued']['B']
            and 'error' not in replacement[0]['envelope']
            and replacement[0]['envelope']['result']['userAgent'] == 'original-offline-peer/0.162.1'
        ), 'UX304: new actual process original request/reply settles once, never detached/failed by A cleanup'
        assert state['replacement_start_returned'] and not any(
            x['label'] == 'B' and x['signal'] in {'failed', 'serverRequest'} for x in state['events']
        ), 'UX304: retired original read/fail/finished continuation cannot fail new receiver/process'
    if trigger.startswith('failed-'):
        assert event['explanation'] and len(event['explanation'].encode()) <= 512 and (
            'ORIGINAL_TRANSPORT304_CANARY' not in event['explanation']
        ), 'UX304: original public failure cause is nonempty/bounded and never raw malformed record text'
    if trigger == 'failed-deadline':
        assert state['declared_total_ms'] == state['declared_idle_ms'] == 100 and (
            event['elapsed_operation_ms'] >= 100
        ), 'UX304 SETUP: actual public100ms operation deadline elapsed against a genuinely pending original reply'
    requests = records(trace)
    assert all(x.get('method') == 'initialize' for x in requests), (
        'UX304: isolated facade caller emits only original initialize, never account/provider/native input'
    )
    labels = [x['params']['clientInfo']['name'].removeprefix('independent-public-') for x in requests]
    expected = ([] if trigger == 'before-write' else ['A']) + ([] if action == 'destroy' else ['B'])
    assert labels == expected, 'UX304: retired before-write A is not delivered as B and every genuine request is once-only'
    events = clear_control_events(trace)
    actual_requests = [x for x in events if x['kind'] == 'transport304-request']
    assert [x['label'] for x in actual_requests] == expected and all(
        x['request'] == request for x, request in zip(actual_requests, requests, strict=True)
    ), 'UX304 SETUP: original actual owned peer process/envelope is independently recorded for each delivered request'
    if len(actual_requests) == 2:
        assert actual_requests[0]['pid'] != actual_requests[1]['pid'], (
            'UX304 SETUP: replacement request reaches a new genuine owned OS process'
        )
    # Independently specified fixture packets, joined to ACTUAL outgoing IDs.
    # Expected operands are not copied from any parsed subject signal/envelope.
    declarations = [x for x in events if x['kind'] == 'transport308-packet-declared']
    declared_labels = ([] if trigger in {'before-write', 'failed-eof', 'failed-deadline'} else ['A']) + (
        [] if action == 'destroy' else ['B'])
    assert [x['label'] for x in declarations] == declared_labels, (
        'UX308 SETUP: every response batch is independently declared and closed before its delivery'
    )
    wire_by_label = dict(zip(labels, requests, strict=True))
    peer_by_label = {x['label']: x for x in actual_requests}
    expected_responses = {}
    for label in expected:
        request = wire_by_label[label]
        assert set(request) == {'id', 'method', 'params'} and request['method'] == 'initialize' and (
            request['params'] == {'clientInfo': {'name': 'independent-public-' + label, 'version': '1'},
                                  'capabilities': {'experimentalApi': True}}
            and isinstance(request['id'], str) and request['id']
        ), 'UX308: actual original request is the complete independently declared public initialize envelope'
        assert state['issued'][label] == request['id'], (
            'UX308: facade returned original ID is bonded to its actual independent outgoing wire ID'
        )
        expected_responses[label] = {'id': request['id'], 'result': {
            'userAgent': 'original-offline-peer/0.162.1',
            'codexHome': str(trace.parent / 'peer-unused-profile'),
            'platformFamily': 'unix', 'platformOs': 'linux'}}
    for declared in declarations:
        label = declared['label']
        packet = [expected_responses[label]]
        if label == 'A' and trigger == 'failed-record':
            packet = [{'method': 'original/transport304-before-malformed',
                       'params': {'originalCaller': 'A', 'position': 'before-malformed'}}]
        elif label == 'A':
            packet += [{'method': method, 'params': {'originalCaller': 'A'}} for method in [
                'original/transport304-boundary', 'original/transport304-tail']]
        encoded = ''.join(json.dumps(x, separators=(',', ':')) + '\n' for x in packet).encode()
        if label == 'A' and trigger == 'failed-record':
            encoded += b'{"malformed":"ORIGINAL_TRANSPORT304_CANARY"\n'
        assert declared['records'] == packet and declared['request_id'] == wire_by_label[label]['id'] and (
            declared['pid'] == peer_by_label[label]['pid'] and declared['mode'] == trigger and
            declared['wire_utf8'].encode() == encoded and declared['bytes'] == len(encoded)
            and declared['sha256'] == hashlib.sha256(encoded).hexdigest()
            and 0 < len(encoded) <= declared['pipe_bound']
        ), 'UX308 SETUP: pre-delivery declaration matches the complete independent original atomic fixture packet'
    if trigger in {'response', 'event'}:
        original_responses = [x for x in state['events'] if x['label'] == 'A' and x['signal'] == 'response']
        assert len(original_responses) == 1 and original_responses[0]['method'] == 'initialize' and (
            original_responses[0]['request_id'] == wire_by_label['A']['id']
            and original_responses[0]['envelope'] == expected_responses['A']
        ), 'UX308: actual A response ID/method/complete envelope equals the independently authored original packet'
        if trigger == 'event':
            original_events = [x for x in state['events'][:state['boundary_event_index'] + 1]
                               if x['label'] == 'A' and x['signal'] == 'event']
            assert original_events == [event] and event['method'] == 'original/transport304-boundary' and (
                event['params'] == {'originalCaller': 'A'}
                and state['events'].index(original_responses[0]) < state['boundary_event_index']
            ), 'UX308: actual boundary is the exact first declared A event after its original response, not tail/empty/altered data'
        else:
            assert event == original_responses[0], 'UX308: reached response callback itself is the original full A response'
    if trigger == 'failed-record':
        prefix = [x for x in state['events'][:state['boundary_event_index']]
                  if x['label'] == 'A' and x['signal'] == 'event']
        assert len(prefix) == 1 and prefix[0]['method'] == 'original/transport304-before-malformed' and (
            prefix[0]['params'] == {'originalCaller': 'A', 'position': 'before-malformed'}
        ), 'UX308 SETUP: exact public prefix receipt proves original atomic input delivery before genuine failure callback'
    if action != 'destroy':
        assert replacement[0]['method'] == 'initialize' and replacement[0]['request_id'] == wire_by_label['B']['id'] and (
            replacement[0]['envelope'] == expected_responses['B']
        ), 'UX308: B returned/parsed IDs and COMPLETE reply match actual independent B request and fixture packet exactly'
    if trigger == 'failed-eof':
        assert len([x for x in events if x['kind'] == 'transport304-real-eof']) == 1, (
            'UX304 SETUP: original owning process really exits instead of an injected failure signal'
        )
    if trigger == 'failed-deadline':
        held = [x for x in events if x['kind'] == 'transport304-real-pending']
        assert len(held) == 1 and held[0]['request_id'] == state['issued']['A'], (
            'UX304 SETUP: actual original request is outstanding with no fabricated reply before real deadline'
        )
    if trigger == 'before-write':
        assert state['original_prepared_id'] and event['request_id'] == state['original_prepared_id'], (
            'UX304 SETUP: actual original prepare callback receives its own allocated envelope identity before delivery'
        )
    assert config_path.read_bytes() == original_config, 'UX304: original process inputs stay frozen across genuine restart'
    after = actor.last['vm']
    assert after['project'] == before['project'] and after['selected_files'] == before['selected_files'], (
        'UX304: transport callback/deletion/restart leaves every original parameter/SU/free/raw observation/weight/identity/Undo unchanged'
    )
    assert not after['connected'] and not after['can_cancel'] and after['messages'] == before['messages'] and (
        after['models'] == before['models'] and after['pending_plan'] == before['pending_plan']
        and after['pending_question'] == before['pending_question']
    ), 'UX304: isolated facade lifetime never invents account, ACK, history, worker or native scientific authority'


@pytest.mark.parametrize('action', ['clear', 'replace-project', 'recreate-session'])
def test_ux319_actual_completed_model_callback_keeps_original_authority(generic, action):
    actor, trace = generic('complete')
    config_path = trace.parent / 'peer-input.json'
    config = json.loads(config_path.read_text())
    config['vm319_record_packets'] = True
    config_path.write_text(json.dumps(config))
    original_config = config_path.read_bytes()
    source = ux345_default_scattering_project(trace.parent)
    original_files = save211_files(source)
    assert actor.command('open', path=str(source))['reply']['opened'], (
        'UX319 SETUP: original public Session owns actual committed scientific fixture'
    )
    actor.command('native_science_enable')
    native145_science_settled(actor)
    selected_source = trace.parent / 'Original319 selected source.txt'
    selected_bytes = b'Original319 immutable selected source\n'
    selected_source.write_bytes(selected_bytes)
    intent = actor.command('selected_begin')['reply']['request_id']
    selected_reply = actor.command('selected_add', request_id=intent, urls=[selected_source.as_uri()])
    assert selected_reply['reply']['accepted'], 'UX319 SETUP: genuine picker admits original canonical selected bytes'
    selected = selected_reply['vm']['selected_files']
    assert len(selected) == 1 and selected[0]['id'] and selected[0]['name'] == selected_source.name and (
        selected[0]['bytes'] == len(selected_bytes) and selected[0]['pending'] is True
    ), 'UX319 SETUP: exact actual selected source is pending before any successful acknowledgement'
    connect(actor)
    native145_approve(actor)
    before = actor.last['vm']
    original_pid, original_started = live_original_peer(actor)
    text = 'Original319 admitted user before synchronous ' + action
    arm = actor.command('ux319_arm', trigger='completed-user', action=action, text=text)['reply']
    assert arm['armed'], 'UX319 SETUP: observer arms on original actual messages model before Send'
    submitted = actor.command('ux319_submit', text=text)['reply']
    assert submitted['invoked'] and submitted['row_id'], (
        'UX319 SETUP: public submitDraft truthfully returns actual admitted original row through notification retirement'
    )
    for _ in range(40):
        state = actor.last['vm']
        witness = state.get('callback319', {})
        settled = witness.get('entered') and witness.get('returned_inside_callback')
        if action == 'replace-project':
            settled = settled and not state['can_cancel'] and not (
                state['project']['science_observer']['calculating']
            )
        elif action == 'recreate-session':
            settled = settled and state['connected'] and not state['can_cancel'] and not (
                original_peer_is_live((original_pid, original_started))
            )
        if settled:
            break
        actor.command('inspect')
    witness = actor.last['vm'].get('callback319', {})
    assert witness.get('entered') and witness.get('callbacks') == 1 and not witness.get('overflow') and not witness.get('observer_error'), (
        'UX319 SETUP: one real completed-user data notification reaches exact original synchronous callback'
    )
    assert witness['signal'] == 'messages.dataChanged' and (
        witness['receiver_at_entry'] == arm['receiver'] == witness['original_receiver']
        and witness['session_at_entry'] == arm['session'] == witness['original_session']
        and witness['model_at_entry'] == arm['model'] == witness['original_model']
        and witness['original_alive_at_entry']
        and witness['depth_at_entry'] == witness['depth_after_action'] == 1
        and witness['returned_inside_callback']
        and witness['changed_first'] <= witness['changed_user_index'] <= witness['changed_last']
        and (witness['all_roles_changed'] or 'status' in witness['changed_roles'])
    ), 'UX319: exact completed user belongs to announced original model range/status roles and direct live callback receiver'
    user = witness['user_at_entry']
    assert user['id'] == submitted['row_id'] and user['text'] == text and (
        user['kind'] == 'user' and user['status'] == 'completed'
        and witness['archive_user_at_entry'] == user and witness['archive_sha256_at_entry']
    ), 'UX319: actual original response durably commits exact public completed user before callback retirement'
    descriptor = {'id': selected[0]['id'], 'name': selected_source.name, 'bytes': len(selected_bytes),
                  'textReadable': True, 'format': selected[0]['format']}
    assert user['payload'] == {'type': 'ediInput', 'files': [descriptor]}, (
        'UX319: actual ACK descriptor preserves original admitted selected identity and bounded metadata, never source paths or bytes'
    )
    requests = records(trace)
    starts = [row for row in requests if row.get('method') == 'turn/start']
    assert len(starts) == 1 and sum(row.get('text') == text for row in starts[0]['params']['input']) == 1 and (
        starts[0]['params']['clientUserMessageId'] == submitted['row_id']
        and not starts[0]['params'].get('additionalContext')
        and rpc83_context_inputs(starts[0]['params']) == [before['context']]
    ), (
        'UX319: one exact original text request is actually written, never transferred or repeated for successor'
    )
    deliveries = [json.loads(line) for line in trace.with_suffix('.vm319-requests.jsonl').read_text().splitlines()]
    delivered_starts = [row for row in deliveries if row['request'].get('method') == 'turn/start']
    assert delivered_starts == [{'pid': original_pid, 'request': starts[0]}], (
        'UX319: independent actual receiving process records complete original request once before dispatch'
    )
    packets = [json.loads(line) for line in trace.with_suffix('.vm319-packets.jsonl').read_text().splitlines()]
    expected_reply = {'id': starts[0]['id'], 'result': {'turn': {
        'id': '019a0290-0000-7000-8000-000000000002', 'items': [], 'status': 'inProgress'}}}
    assert packets.count({'pid': original_pid, 'packet': expected_reply}) == 1, (
        'UX319 SETUP: actual original process predeclares exact successful envelope before completed callback delivery'
    )
    state = actor.last['vm']
    if action == 'clear':
        final = settle(actor, lambda value: not value['can_cancel'] and not value['messages'])
        retained = actor.command('archive')['reply']['rows']
        assert retained == [] and final['connected'] and final['project'] == before['project'] and (
            final['models'] == before['models'] and final['selected_model'] == before['selected_model']
            and final['selected_effort'] == before['selected_effort']
            and [row['id'] for row in final['selected_files']] == [selected[0]['id']]
        ), 'UX319: real committed Clear discards memory while retaining original account/science/Undo/canonical source consent'
    elif action == 'replace-project':
        assert witness['replacement_created'] and state['project_present'] and (
            state['project']['host_snapshot']['name'] == 'Original319 B'
            and state['project']['science_observer']['structures'] == []
            and state['project']['host_snapshot']['experiments'] == []
            and state['project']['science_observer']['calculations'] == []
            and state['project']['science_observer']['aliases'] == []
            and state['project']['science_observer']['constraints'] == []
            and not state['project']['science_observer']['calculating']
            and not state['can_cancel'] and not state['selected_files']
            and state['connected'] and state['models'] == before['models']
            and state['selected_model'] == before['selected_model']
            and state['selected_effort'] == before['selected_effort']
        ), 'UX319: new empty owner retains original account/catalog/model/effort without old science/input/work'
    else:
        assert not witness['original_alive_after_action'] and not witness['original_session_alive_after_action'] and (
            witness['replacement_present'] and witness['replacement_signin_returned']
        ), 'UX319: real original weak lifetime retires inside callback and explicit new receiver begins actual bootstrap there'
        final = state
        assert final['connected'] and not final['project_present'] and final['models'] and (
            not final['can_cancel'] and not final['selected_files']
        ), 'UX319: retired old publication cannot detach/fail or lend source/science authority to genuine explicit successor account'
        replacement_pid, _ = live_original_peer(actor)
        assert replacement_pid != original_pid and not original_peer_is_live((original_pid, original_started)), (
            'UX319: old original process really terminates while independent replacement process owns ready account'
        )
        deliveries = [json.loads(line) for line in trace.with_suffix('.vm319-requests.jsonl').read_text().splitlines()]
        original_initializes = [row for row in deliveries if row['request'].get('method') == 'initialize']
        assert [row['pid'] for row in original_initializes] == [original_pid, replacement_pid], (
            'UX319: new explicit Session bootstrap has independent actual process, not stale original continuation identity'
        )
    assert config_path.read_bytes() == original_config and save211_files(source) == original_files and (
        selected_source.read_bytes() == selected_bytes
    ), 'UX319: callback actions never alter original provider configuration/scientific fixture/admitted source bytes'


def test_ux319_actual_final_failure_publication_preserves_factual_cause(generic):
    actor, trace = generic('rpc83:unknown:eof')
    config_path = trace.parent / 'peer-input.json'
    config = json.loads(config_path.read_text())
    config['vm319_record_packets'] = True
    config_path.write_text(json.dumps(config))
    original_config = config_path.read_bytes()
    source = ux345_default_scattering_project(trace.parent)
    original_files = save211_files(source)
    assert actor.command('open', path=str(source))['reply']['opened'], (
        'UX319 SETUP: final-publication callback observes original genuine scientific owner'
    )
    actor.command('native_science_enable')
    native145_science_settled(actor)
    connect(actor)
    native145_approve(actor)
    before = actor.last['vm']
    original_pid, original_started = live_original_peer(actor)
    arm = actor.command('ux319_arm', trigger='failure', action='refused-input')['reply']
    text = 'Original319 submitted request before genuine peer EOF'
    submitted = actor.command('ux319_submit', text=text)['reply']
    assert submitted['invoked'] and submitted['row_id'], (
        'UX319 SETUP: original admitted input exists before owned peer really closes transport without ACK'
    )
    for _ in range(40):
        state = actor.last['vm']
        witness = state.get('callback319', {})
        if witness.get('returned_inside_callback') and witness.get('notices') and (
            not state['connected'] and not state['can_cancel']
            and not state['project']['science_observer']['calculating']
            and not original_peer_is_live((original_pid, original_started))
        ):
            break
        actor.command('inspect')
    state = actor.last['vm']
    witness = state.get('callback319', {})
    assert witness.get('entered') and witness.get('callbacks') == 1 and not witness.get('overflow') and not witness.get('observer_error'), (
        'UX319 SETUP: genuine fatal original transport publishes direct original state callback'
    )
    assert witness['signal'] == 'stateChanged' and witness['receiver_at_entry'] == arm['receiver'] and (
        witness['original_alive_at_entry'] and witness['original_alive_after_action']
        and witness['session_at_entry'] == arm['session']
        and witness['current_session_after_action'] == arm['session']
        and witness['depth_at_entry'] == witness['depth_after_action'] == 1
        and witness['returned_inside_callback']
    ), 'UX319: nested refused input occurs within actual unchanged original fatal-publication receiver'
    cause = witness['error_at_entry']
    assert cause and len(cause.encode()) <= 512 and witness['submit_invoked'] and witness['refused_row'] == '', (
        'UX319: same-owner blocked-account whitespace is truly refused and original transport cause is bounded/nonempty'
    )
    after_notices = [row for row in witness['notices'] if row['sequence'] > witness['entry_sequence']]
    assert after_notices and all(row['receiver'] == arm['receiver'] and row['error'] == cause
                                 for row in after_notices) and state['last_error'] == cause, (
        'UX319: later actual lastError notification/getter retains factual cause after refused input'
    )
    starts = [row for row in records(trace) if row.get('method') == 'turn/start']
    deliveries = [json.loads(line) for line in trace.with_suffix('.vm319-requests.jsonl').read_text().splitlines()]
    assert len(starts) == 1 and sum(row.get('text') == text for row in starts[0]['params']['input']) == 1 and (
        starts[0]['params']['clientUserMessageId'] == submitted['row_id']
        and not starts[0]['params'].get('additionalContext')
        and rpc83_context_inputs(starts[0]['params']) == [before['context']]
    ) and (
        [row for row in deliveries if row['request'].get('method') == 'turn/start']
        == [{'pid': original_pid, 'request': starts[0]}]
    ), 'UX319: only exact original encoded input reaches independent peer, never nested refused draft'
    packets = [json.loads(line) for line in trace.with_suffix('.vm319-packets.jsonl').read_text().splitlines()]
    assert not any(row['pid'] == original_pid and row['packet'].get('id') == starts[0]['id'] for row in packets) and (
        not original_peer_is_live((original_pid, original_started))
    ), 'UX319 SETUP: actual original peer exits after receiving request without any successful ACK response'
    assert not any(row.get('id') == submitted['row_id'] and row.get('status') == 'completed'
                   for row in state['messages']), 'UX319: missing original ACK cannot be fabricated by callback refusal/publication'
    assert not state['connected'] and not state['can_cancel'] and state['project'] == before['project'], (
        'UX319: factual account retirement finishes without modifying original scientific values/Undo/source owner'
    )
    assert config_path.read_bytes() == original_config and save211_files(source) == original_files, (
        'UX319: fatal publication and nested policy refusal preserve original config and every source file byte'
    )




def save359_four_original_anchors(text):
    start = 'loop_\n_background.id\n_background.position\n_background.intensity\n'
    stop = '\nloop_\n_data.two_theta\n'
    assert text.count(start) == text.count(stop) == 1, 'SAVE359 SETUP: original exact background/data sections are unambiguous'
    prefix, rest = text.split(start)
    original, suffix = rest.split(stop)
    rows = [line.split() for line in original.splitlines() if line.strip()]
    assert len(rows) == 14 and rows == [[str(index), position, '0.()'] for index, position in enumerate(
        ['8.', '9.', '10.', '11.', '12.', '15.', '25.', '30.', '50.', '70.', '90.', '110.', '130.', '150.'], 1)], (
        'SAVE359 SETUP: committed ordinary fixture has its exact independently pinned FOURTEEN anchor operands'
    )
    selected = [rows[index] for index in [0, 5, 9, 13]]
    value = prefix + start + '\n'.join(' '.join(row) for row in selected) + '\n' + stop + suffix
    assert value.split(start)[0] == prefix and value.split(stop)[1] == suffix, (
        'SAVE359 SETUP: only owned background rows change; every original measured/calculated section and other scalar stays byte-exact'
    )
    return value


@pytest.mark.parametrize('case', ['fresh', 'current', 'no-grant', 'collision', 'stop', 'close-owner', 'current-ten-refit'])
def test_save349_real_visible_writer_and_reopen(generic, tmp_path, case):  # noqa: PLR0914, PLR0915 -- finite existing Main/ordinary writer/loader receipts
    from tests.system.app.test_e11_t5_assistant_popup import popup171_owned_environment

    source = ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project'
    reference = tmp_path / 'Original349 reference'
    reference.mkdir()
    fixture = reference / 'input'
    shutil.copytree(source, fixture)
    if case == 'current-ten-refit':
        experiment359 = fixture / 'experiments/d20.edi'
        experiment359.write_text(save359_four_original_anchors(experiment359.read_text()))
    analysis = fixture / 'analysis/analysis.edi'
    original_analysis = analysis.read_text()
    assert original_analysis.count('_edi.schema_version 2') == 1, (
        'SAVE349 SETUP: independent committed native input has its original schema'
    )
    # Exactly the existing SAVE211 independently declared enabled/disabled relations.
    analysis.write_text(original_analysis.replace('_edi.schema_version 2', '_edi.schema_version 3') + (
        '\nloop_\n_alias.id\n_alias.parameter_unique_name\n'
        'original_o1_occupancy cosio.atom_site.O1.occupancy\n'
        'original_co1_biso cosio.atom_site.Co1.adp_iso\n'
        'loop_\n_constraint.id\n_constraint.expression\n_constraint.enabled\n'
        'original_oxygen_full "original_o1_occupancy = 1" true\n'
        'original_inactive_co "original_co1_biso = 0.5" false\n'
    ))
    original_source = save211_files(source)
    original_inputs = save211_files(fixture)
    for directory in ['ordinary', 'current', 'selected']:
        (reference / directory).mkdir()
    selected = reference / 'selected'
    sentinel = selected / 'Original unrelated user bytes.txt'
    sentinel.write_bytes(b'Original349 directory grant is not overwrite authority\n')
    leaf = 'Original μ 🧪 saved project'
    collision = selected / leaf
    if case == 'collision':
        collision.mkdir()
        (collision / 'Original existing child.txt').write_bytes(b'Original349 collision remains exact\n')
    selected_before = save211_files(selected)
    call = {'tool': 'save_project', 'call_id': 'save349-' + case, 'arguments': {
        'purpose': 'Save original fitted displayed project through actual visible controls',
        'destination': 'current' if case in {'current', 'current-ten-refit'} else 'fresh',
        **({} if case in {'current', 'current-ten-refit'} else {'name': leaf}),
    }}
    environment = popup171_owned_environment(tmp_path)
    environment['EDI_ACCEPTANCE_REFERENCE'] = str(reference)
    config_path = Path(environment['EDI_TEST_CODEX_PEER_INPUT'])
    config = json.loads(config_path.read_text())
    config.pop('report_page_reply')
    config.update(scenario='native:script', native_turn_calls=[[call]])
    config_path.write_text(json.dumps(config))
    original_config = config_path.read_bytes()
    runner = Path(os.environ['EDI_APP_TEST_RUNNER'])
    assert runner.is_file(), 'SAVE349 SETUP: actual coherent Main consumer is required'
    argv = [str(runner), '-input', str(Path(__file__).with_name('tst_assistant_popup.qml')),
            'AssistantPopup::test_save349_visible_real_save_and_retirement:' + case, '-o', '-,txt']
    try:
        result = subprocess.run(argv, cwd=tmp_path, env=environment, capture_output=True,
                                text=True, timeout=90, check=False)
    except subprocess.TimeoutExpired as error:
        for stream in ['stdout', 'stderr']:
            value = getattr(error, stream) or b''
            raw = value if isinstance(value, bytes) else value.encode('utf-8')
            destination = tmp_path / ('save349-timeout.' + stream + '.log')
            destination.write_bytes(raw)
            error.add_note(str(destination) + '\n' + raw.decode(errors='backslashreplace'))
        raise
    (tmp_path / 'save349.stdout.log').write_text(result.stdout)
    (tmp_path / 'save349.stderr.log').write_text(result.stderr)
    (tmp_path / 'save349-process.json').write_text(json.dumps({'argv': argv, 'returncode': result.returncode,
                                                            'timeout': 90, 'case': case}, indent=2))
    output = result.stdout + result.stderr
    assert result.returncode == 0 and 'FAIL!' not in output and (
        'PASS   : edi_app::AssistantPopup::test_save349_visible_real_save_and_retirement(' + case + ')' in output
    ), 'SAVE349: every real control, currentness, fitted science and truthful outcome premise must execute\n' + output
    assert config_path.read_bytes() == original_config, 'SAVE349: original objective/peer configuration stays exact'
    assert save211_files(source) == original_source and save211_files(fixture) == original_inputs, (
        'SAVE349: original committed and owned scientific inputs remain byte-exact'
    )
    trace = Path(config['trace'])
    requests = records(trace)
    inputs = [row for row in requests if row.get('method') in {'turn/start', 'turn/steer'}]
    assert len(inputs) == 1 and inputs[0]['method'] == 'turn/start' and inputs[0]['params'].get('clientUserMessageId'), (
        'SAVE349: exactly one genuinely admitted original objective, never a steer/retry substitute'
    )
    replies = native_records(trace, '.native-replies.jsonl')
    assert len(replies) == 1 and not native_records(trace, '.native-wrong-envelope.jsonl'), (
        'SAVE349: original reverse RPC replies exactly once, including genuine cancellation/owner close'
    )
    receipt = replies[0]
    original, response = receipt['original'], receipt['response']
    assert original['params']['tool'] == call['tool'] and original['params']['callId'] == call['call_id'] and (
        original['params']['arguments'] == call['arguments'] and response['id'] == original['id'] != call['call_id']
    ), 'SAVE349: complete original purpose/destination/name and actual RPC envelope survive visible staging'
    returned = response['result']
    assert type(returned['success']) is bool and len(returned['contentItems']) == 1 and (
        returned['contentItems'][0]['type'] == 'inputText'
    ), 'SAVE349: actual original native response retains the typed official envelope'
    outcome = json.loads(returned['contentItems'][0]['text'])
    if case in {'fresh', 'current', 'current-ten-refit'}:
        destination = reference / 'current' if case in {'current', 'current-ten-refit'} else selected / leaf
        assert returned['success'] is True and outcome['status'] == 'succeeded' and all(
            outcome.get(key) is True for key in ['committed', 'reopened', 'active', 'presentation_complete']
        ), 'SAVE349: only committed/reopened/active/fully presented actual save is success'
        assert Path(outcome['destination']).resolve() == destination.resolve(), (
            'SAVE349: truthful destination is exactly existing current directory or authorized fresh Unicode basename'
        )
        assert destination.is_dir() and not destination.is_symlink() and (destination / 'project.edi').is_file(), (
            'SAVE349: actual native files must exist; a staged receipt is not disk publication'
        )
        if case == 'current-ten-refit':
            lines359 = [line.split('SAVE359_ORDINARY ', 1)[1] for line in result.stdout.splitlines()
                        if 'SAVE359_ORDINARY ' in line]
            assert len(lines359) == 1, 'SAVE359: one actual pre-Save ordinary-writer reference must be delivered'
            ordinary359 = json.loads(lines359[0])
            documents359 = ordinary359['documents']
            names359 = ['project.edi', 'structures/cosio.edi', 'experiments/d20.edi', 'analysis/analysis.edi']
            assert set(documents359) == set(names359), 'SAVE359: ordinary reference has exact closed independent source document membership'
            # Public ProjectText joins the same ordinary savedFiles as '# path\n' + body,
            # with one newline separator. Verify the complete closure; no EDI parser or
            # scientific re-emitter is introduced. The existing real loader reads it.
            import re
            order359 = re.findall(r'(?m)^# ([^\r\n]+\.edi)\n', ordinary359['completeText'])
            assert len(order359) == len(names359) and set(order359) == set(names359) and ordinary359['completeText'] == (
                '\n'.join('# ' + name + '\n' + documents359[name] for name in order359)
            ), 'SAVE359: captured four ordinary blocks equal the WHOLE actual ordinary Project Text file closure'
            positions362 = {'1': 8, '6': 15, '10': 70, '14': 150, 'save359_9': 9,
                            'save359_12': 12, 'save359_25': 25, 'save359_50': 50, 'save359_90': 90, 'save359_130': 130}
            starts362 = {'1': 5.5, '6': 0, '10': 0, '14': 0, 'save359_9': 10,
                         'save359_12': 12.5, 'save359_25': 15, 'save359_50': 17.5, 'save359_90': 20, 'save359_130': 22.5}
            assert len(ordinary359['initialTen']) == 10 and {
                row[0]: (row[1], row[2], row[3]) for row in ordinary359['initialTen']
            } == {key: (positions362[key], starts362[key], True) for key in positions362}, (
                'SAVE362B: independent literal TEN start operands and all-free flags precede genuine refit; they are not a fitted-output golden'
            )
            fitted362 = ordinary359['postFitBackground']
            assert len(fitted362) == 10 and len({row['id'] for row in fitted362}) == 10 and {
                row['id']: row['position'] for row in fitted362
            } == positions362 and all(row['free'] is True and row['hasUncertainty'] is True and row['uncertainty'] > 0
                                     and float('-inf') < row['intensity'] < float('inf') for row in fitted362), (
                'SAVE362B: observed genuine post-fit physical BG operands contain ALL TEN free identities and positive actual SUs'
            )
            assert any(row['intensity'] != starts362[row['id']] for row in fitted362), (
                'SAVE362B: at least one actual fitted background intensity MOVES; no fixed-intensity/no-step substitution'
            )
            assert ordinary359['dirty'] is True and ordinary359['four'] == 4 and len(ordinary359['ten']) == 10 and (
                ordinary359['refitStarts'] == 1 and ordinary359['fittedIterations'] > 0
                and ordinary359['fittedOutcome'] in {'success', 'maxIterations'}
                and Path(ordinary359['currentPath']).resolve() == destination.resolve()
            ), 'SAVE359: original current-path DIRTY four-to-ten refit facts precede delegated Save, never a pre-saved ten-point substitute'
            for name in names359:
                (reference / 'ordinary' / name).parent.mkdir(parents=True, exist_ok=True)
                (reference / 'ordinary' / name).write_text(documents359[name])
        loader, _ = generic('fileauth')
        assert loader.command('native_science_enable')['reply']['enabled'], (
            'SAVE349: existing independent Session loader exposes full actual native science'
        )
        if case == 'current-ten-refit':
            assert loader.command('background285_observe')['reply']['enabled'], (
                'SAVE359: existing passive full background observer independently reads ALL persisted anchor rows'
            )
        assert loader.command('open', path=str(reference / 'ordinary'))['reply']['opened'], (
            'SAVE349: independent real reader loads pre-Save ordinary fitted writer reference'
        )
        expected = native145_science_settled(loader)
        assert loader.command('open', path=str(destination))['reply']['opened'], (
            'SAVE349: independent real reader loads actual visibly saved native files'
        )
        actual = native145_science_settled(loader)
        save211_compare_model(expected, actual)
        if case == 'current-ten-refit':
            expected359 = positions362
            for state359 in [expected, actual]:
                banks359 = state359['project']['background285']['banks']
                assert len(banks359) == 1 and len(banks359[0]['anchors']) == 10, (
                    'SAVE359: both independently reopened ordinary and delegated files retain exactly ALL TEN anchors'
                )
                rows359 = banks359[0]['anchors']
                assert len({row['id'] for row in rows359}) == 10 and {
                    row['id']: row['position'] for row in rows359
                } == expected359 and all(row['free'] is True and row['uncertainty'] is not None and row['uncertainty'] > 0 for row in rows359), (
                    'SAVE362B: both actual ordinary/delegated readbacks retain every independent anchor identity/position and ALL TEN fitted free flags/positive BG SUs'
                )
                assert any(row['uncertainty'] is not None and row['uncertainty'] > 0
                           for row in state359['project']['parameters']), (
                    'SAVE359: BOTH real reader results retain actual positive fitted uncertainties, never an unfit substitute'
                )
            fields359 = ['id', 'position', 'value', 'free', 'uncertainty', 'start_value', 'start_uncertainty', 'dependence']
            assert [{key: row[key] for key in fields359} for row in actual['project']['background285']['banks'][0]['anchors']] == (
                [{key: row[key] for key in fields359} for row in expected['project']['background285']['banks'][0]['anchors']]
            ), 'SAVE359: ALL persisted background SU/start/dependence/order metadata follows independent ordinary writer/readback exactly'
        title = [shlex.split(line)[1:] for line in (destination / 'project.edi').read_text().splitlines()
                 if line.startswith('_metadata.title ') or line.startswith('_metadata.title\t')]
        assert title == [['Original visible Save ' + case]], (
            'SAVE349: exact public metadata scalar persists the real user title, not merely painted state'
        )
        assert sentinel.read_bytes() == selected_before[sentinel.name], 'SAVE349: unrelated grant bytes remain exact'
        assert sorted(path.name for path in selected.iterdir()) == sorted(
            [sentinel.name] + ([leaf] if case == 'fresh' else [])
        ), 'SAVE349: only the one requested fresh child may be published under the selected grant'
    else:
        assert returned['success'] is False and outcome.get('status') != 'succeeded' and outcome.get('committed') is not True and (
            isinstance(outcome.get('message'), str) and outcome['message']
        ), 'SAVE349: refusal/cancel/retirement cannot manufacture successful commit or suppress its reason'
        assert save211_files(selected) == selected_before, (
            'SAVE349: no-grant/collision/Stop/owner retirement never partially publishes or overwrites user files'
        )
    assert not any(row.get('method') in {'account/login/start', 'account/logout'} for row in requests), (
        'SAVE349: scientific saving never substitutes account login/logout repair'
    )


UX356_GUI_CASES = ('send-click', 'send-keyboard', 'cancel-new-draft')


def ux356_owned_inputs(owned):
    reference = owned / 'Original356 reference'
    reference.mkdir()
    source = ux345_default_scattering_project(reference)
    source.rename(reference / 'project')
    folder = reference / 'files'
    folder.mkdir()
    originals = {
        'Original structure.cif': ROOT / 'tests/fixtures/assistant/reference/easydiffraction-ddlm/lbco.cif',
        'Original measured neutron profile.xye': ROOT / 'tests/fixtures/assistant/reference/easydiffraction-ddlm/hrpt.xye',
    }
    facts = {}
    for name, path in originals.items():
        raw = path.read_bytes()
        (folder / name).write_bytes(raw)
        facts[name] = {'source': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        assert (folder / name).read_bytes() == raw, 'UX356 SETUP: actual selected source is a whole-byte original copy'
    return reference, facts


@pytest.mark.parametrize('case', UX356_GUI_CASES)
def test_ux356_real_send_compact_scope_short_file_presentation(case, tmp_path):
    from tests.system.app.test_e11_t5_assistant_popup import popup171_owned_environment

    original_project = save211_files(ROOT / 'tests/fixtures/e04_t1/editable-project')
    reference, facts = ux356_owned_inputs(tmp_path)
    original_inputs = save211_files(reference)
    environment = popup171_owned_environment(tmp_path)
    environment['EDI_ACCEPTANCE_REFERENCE'] = str(reference)
    config_path = Path(environment['EDI_TEST_CODEX_PEER_INPUT'])
    config = json.loads(config_path.read_text())
    config.pop('report_page_reply')
    config.update(scenario='native:script', native_turn_calls=[[], []], ux289_hold_input=True)
    config_path.write_text(json.dumps(config))
    original_config = config_path.read_bytes()
    runner = Path(os.environ['EDI_APP_TEST_RUNNER'])
    assert runner.is_file(), 'UX356 SETUP: genuinely coherent actual Main consumer is required'
    argv = [str(runner), '-input', str(Path(__file__).with_name('tst_assistant_popup.qml')),
            'AssistantPopup::test_ux356_real_send_compact_scope_and_short_files:' + case, '-o', '-,txt']
    try:
        result = subprocess.run(argv, cwd=tmp_path, env=environment, capture_output=True,
                                text=True, timeout=90, check=False)
    except subprocess.TimeoutExpired as error:
        for stream in ['stdout', 'stderr']:
            value = getattr(error, stream) or b''
            raw = value if isinstance(value, bytes) else value.encode('utf-8')
            destination = tmp_path / ('ux356-timeout.' + stream + '.log')
            destination.write_bytes(raw)
            error.add_note(str(destination) + '\n' + raw.decode(errors='backslashreplace'))
        raise
    (tmp_path / 'ux356.stdout.log').write_text(result.stdout)
    (tmp_path / 'ux356.stderr.log').write_text(result.stderr)
    (tmp_path / 'ux356-process.json').write_text(json.dumps({'argv': argv, 'case': case,
        'timeout': 90, 'returncode': result.returncode}, indent=2))
    output = result.stdout + result.stderr
    assert result.returncode == 0 and 'FAIL!' not in output and (
        'PASS   : edi_app::AssistantPopup::test_ux356_real_send_compact_scope_and_short_files(' + case + ')' in output
    ), 'UX356: actual compact dialog/input/chip/ACK/once/science premises must execute\n' + output
    assert config_path.read_bytes() == original_config and save211_files(reference) == original_inputs and (
        save211_files(ROOT / 'tests/fixtures/e04_t1/editable-project') == original_project
    ), 'UX356: compact presentation/consent/removal preserves original objective and every source/scientific file byte'
    for name, expected in facts.items():
        raw = Path(expected['source']).read_bytes()
        assert len(raw) == expected['bytes'] and hashlib.sha256(raw).hexdigest() == expected['sha256'], (
            'UX356: independently committed selected bytes remain exact outside the owned invocation'
        )
    loaded = json.loads(config_path.with_suffix('.peer-loaded.json').read_text())
    assert loaded['sha256'] == hashlib.sha256(original_config).hexdigest() and loaded['native_turn_calls'] == [[], []], (
        'UX356 SETUP: original peer consumed exact held-input two-turn configuration; no fabricated ACK timer'
    )
    trace = Path(config['trace'])
    requests = records(trace)
    starts = [row for row in requests if row.get('method') in {'turn/start', 'turn/steer'}]
    assert len(starts) == 2 and all(row['method'] == 'turn/start' for row in starts) and (
        len({row['id'] for row in starts}) == 2
        and len({row['params']['clientUserMessageId'] for row in starts}) == 2
    ), 'UX356: actual approval/Cancel/new-draft/no-repeat sends only TWO original distinct inputs, never hidden replay'
    gui_lines358 = [line.split('UX356_IDS ', 1)[1] for line in result.stdout.splitlines() if 'UX356_IDS ' in line]
    assert len(gui_lines358) == 1, 'UX358: one actual bounded original GUI identity receipt must be delivered'
    gui358 = json.loads(gui_lines358[0])
    assert gui358['case'] == case and len(gui358['submissions']) == 2, (
        'UX358: actual receipt belongs to this original case and BOTH exact submitted user inputs'
    )
    assert [row['text'] for row in gui358['submissions']] == ['continue', 'continue again'] and (
        len({row['id'] for row in gui358['submissions']}) == 2 and gui358['first'] == gui358['submissions'][0]['id']
    ), 'UX358: original GUI user identities are unique and bonded to literal independent input order'
    ids = []
    for request, text, submitted358 in zip(starts, ['continue', 'continue again'], gui358['submissions'], strict=True):
        context = rpc83_context_inputs(request['params'])
        assert len(context) == 1, 'UX356: actual original request has one complete current context as data'
        selected = context[0]['selected_files']['files']
        assert submitted358['text'] == text and submitted358['id'] == request['params']['clientUserMessageId'], (
            'UX358: each actual original GUI user-row ID equals its independently received original wire clientUserMessageId'
        )
        fields358 = ('id', 'name', 'bytes', 'textReadable', 'format')
        assert len(submitted358['files']) == 2 and all(set(row) == set(fields358) for row in submitted358['files']), (
            'UX358: each original GUI receipt contains exactly TWO bounded five-field admitted descriptors'
        )
        assert submitted358['files'] == [{key: row[key] for key in fields358} for row in selected], (
            'UX358: BOTH literal input orders disclose the corresponding actual GUI canonical IDs and every descriptor field in order'
        )
        assert len(selected) == 2 and {row['name'] for row in selected} == set(facts), (
            'UX356: original current context discloses only the TWO actual independently selected files'
        )
        assert len({row['id'] for row in selected}) == 2 and all(row['id'] for row in selected) and all(
            row['bytes'] == facts[row['name']]['bytes'] for row in selected
        ), 'UX356: disclosed opaque canonical identities and exact byte sizes are actual source facts'
        assert sum(row.get('type') == 'text' and row.get('text') == text
                   for row in request['params']['input']) == 1, (
            'UX356: exact real user spelling remains its own current input, never a developer instruction'
        )
        ids.append({row['name']: row['id'] for row in selected})
    assert ids[0] == ids[1], 'UX356: ACK/presentation and unchanged-scope followup preserve actual canonical file IDs'
    events = [json.loads(line) for line in trace.with_suffix('.clear-events.jsonl').read_text().splitlines()]
    held = [row for row in events if row['kind'] == 'ux289-original-input-received']
    released = [row for row in events if row['kind'] == 'ux289-original-ack-release']
    assert len(held) == len(released) == 2 and all(
        actual['request_id'] == request['id'] and actual['client_user_message_id'] == request['params']['clientUserMessageId']
        for actual, request in zip(held, starts, strict=True)
    ), 'UX356: real original pending intervals are independently witnessed by exact received wire envelopes'
    reads = {row['id']: row for row in requests if row.get('method') == 'account/rateLimits/read'}
    assert len({row['read_id'] for row in released}) == 2 and all(
        release['request_id'] == request['id'] and release['method'] == 'turn/start'
        and release['read_id'] in reads and release['client_user_message_id'] == request['params']['clientUserMessageId']
        for release, request in zip(released, starts, strict=True)
    ), 'UX356: genuine existing public optional reads release only their independently received original ACKs'
    assert not native_records(trace, '.native-replies.jsonl') and not native_records(trace, '.native-wrong-envelope.jsonl'), (
        'UX356: consent/presentation cannot fabricate a native scientific action or RPC'
    )
    assert not any(row.get('method') in {'account/login/start', 'account/logout'} for row in requests), (
        'UX356: genuine owned healthy-account setup never repairs admission by provider login/logout'
    )
