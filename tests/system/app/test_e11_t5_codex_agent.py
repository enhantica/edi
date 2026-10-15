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

    def create(scenario='complete', *, override='peer'):
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
        actor = Generic(Path(os.environ['EDI_ASSISTANT_WORKFLOW_VM_PROBE']))
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
