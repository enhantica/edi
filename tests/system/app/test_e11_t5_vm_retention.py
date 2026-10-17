"""Real Session/VM resource ownership, provider cards and public control regressions.

No Main QML loads in this additional component. Existing full-Main coverage remains.
Expectations are approved R4/S6/model policy and independently encoded fixture events.
"""

from __future__ import annotations

import base64
import importlib.util
import json
import os
import shutil
from pathlib import Path

import pytest

from tests.fixtures.assistant.response_events import message_complete, message_start, text_fragment

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'vm_native_fixture', ROOT / 'tests/system/py/test_e11_t5_assistant_native.py'
)
native = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(native)
signer = native.signer
UI_BYTES, UI_SLOTS, MESSAGE_BYTES = 2097152, 512, 1048576  # Approved packet R4.


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()


class Component(native.Native):
    def __init__(self, binary):
        super().__init__(binary, reply_timeout=5)
        self.opened = set()

    def ready(self):
        return self.last['vm']['connected']

    def batch_callbacks(self, callbacks):
        for offset in range(0, len(callbacks), 16):
            self.command('callback_batch', callbacks=callbacks[offset : offset + 16])
        return self.last


@pytest.fixture
def vm(monkeypatch):
    binary = Path(
        os.environ.get(
            'EDI_ASSISTANT_VM_PROBE', ROOT / 'build/assistant-vm-tests/assistant_vm_resource_probe'
        )
    )
    assert binary.is_file(), (
        'I12/I16/S6: this new component must link the actual Session/VM/controller/native graph'
    )
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    actor = Component(binary)
    actor.command('inspect')
    try:
        yield actor
    finally:
        actor.close()


def seed(vm, *, count=8, size=None):
    rows = [
        {
            'id': 'seed-' + str(i),
            'kind': 'assistant',
            'text': 'Å fixture ' + str(i),
            'status': 'completed',
            'payload': {},
        }
        for i in range(count)
    ]
    if size is not None:
        remaining = size - len(compact(rows))
        assert remaining >= 0, 'I3/S6: independent legal archive encoding fits the requested seed'
        for index in range(count):
            share = remaining // (count - index)
            rows[index]['text'] += 'x' * share
            remaining -= share
        assert len(compact(rows)) == size, (
            'I3/S6: seed byte cost is exact UTF-8 complete-array size'
        )
    vm.command('destroy')
    vm.command('archive_seed', rows=rows)
    vm.command('recreate')
    assert vm.last['vm']['messages'] == rows, (
        'I3/S6: only legitimate isolated persisted rows initialize the real VM archive'
    )
    return rows


def authenticate(vm, signer):
    vm.authenticate(signer)
    assert vm.ready(), 'I12/S6: genuine signed offline flow connects the actual Session-owned VM'
    return vm.last


def responses(vm):
    return [
        (i, row)
        for i, row in enumerate(vm.last['requests'])
        if row['url'] == native.API + '/responses'
    ]


def begin(vm, text='Inspect this actual conversation'):
    before = len(responses(vm))
    vm.command('send_text', text=text)
    after = responses(vm)
    assert len(after) == before + 1, 'I13/S6: one public send admits exactly one physical request'
    return after[-1][0]


def headers(vm, index):
    if index not in vm.opened:
        vm.command(
            'headers', index=index, status=200, headers=[['Content-Type', 'text/event-stream']]
        )
        vm.opened.add(index)


def events(vm, index, values, *, finish=True):
    headers(vm, index)
    wire = b''.join(b'data: ' + compact(value) + b'\n\n' for value in values)
    vm.batch_callbacks([
        {
            'op': 'data',
            'index': index,
            'base64': base64.b64encode(wire[offset : offset + 65536]).decode(),
        }
        for offset in range(0, len(wire), 65536)
    ])
    if finish:
        vm.command('finish', index=index, failure=0)
    return vm.last


def function(name, arguments, *, call='vm-call', completed=True):
    item = {
        'id': 'function-' + call,
        'type': 'function_call',
        'call_id': call,
        'name': name,
        'arguments': compact(arguments).decode(),
        'status': 'completed',
    }
    result = [
        {
            'type': 'response.output_item.added',
            'output_index': 0,
            'item': {**item, 'arguments': '', 'status': 'in_progress'},
        },
        {
            'type': 'response.function_call_arguments.done',
            'output_index': 0,
            'item_id': item['id'],
            'arguments': item['arguments'],
        },
        {'type': 'response.output_item.done', 'output_index': 0, 'item': item},
    ]
    if completed:
        result.append({
            'type': 'response.completed',
            'response': {'id': 'response-' + call, 'status': 'completed', 'output': [item]},
        })
    return result


def question():
    return {
        'text': 'Choose a public check — Å',
        'options': [
            {'id': 'inspect', 'label': 'Inspect', 'description': 'Read only'},
            {'id': 'wait', 'label': 'Wait', 'description': 'Leave unchanged'},
        ],
        'recommended': 'inspect',
        'allow_free_text': True,
    }


def ask(vm, *, complete=True):
    index = begin(vm)
    events(
        vm,
        index,
        function('ask_question', question(), call='vm-question', completed=complete),
        finish=complete,
    )
    return index


def visible_terminals(vm, call):
    return [
        row
        for row in vm.last['vm']['messages']
        if row['payload'].get('type') == 'tool_result'
        and row['payload'].get('call_id') == call
        and row['payload'].get('pending') is False
    ]


def assert_bound(terminal, original):
    assert terminal['call_id'] == original['call_id'], (
        'I3/S6: full terminal preserves the independently planted invocation identity'
    )
    for name in ('connection_id', 'turn_id', 'request_id', 'project_id', 'revision'):
        assert terminal[name] == original[name], (
            'I3/S6: actual terminal retains every captured original activity binding field'
        )


@pytest.mark.parametrize('dimension', ['bytes', 'slots'])
@pytest.mark.parametrize('admit', [False, True], ids=['capacity-refusal', 'capacity-control'])
def test_complete_question_capacity_is_reserved_before_activity_or_work(
    vm, signer, dimension, admit
):
    if dimension == 'slots':
        seed(vm, count=UI_SLOTS - (8 if admit else 1))
    else:
        seed(vm, size=UI_BYTES - MESSAGE_BYTES + (-65536 if admit else 32768))
    authenticate(vm, signer)
    original = vm.last['vm']['project']
    ask(vm)
    shown = vm.last['vm']
    if admit:
        assert shown['pending_question'], (
            'I10/S6: sufficient complete bytes and slots admit a real question'
        )
        assert len(shown['messages']) <= UI_SLOTS, (
            'I3/S6: accepted activity uses bounded whole-row slots'
        )
    else:
        assert not shown['pending_question'], (
            'I10/S6: capacity refusal precedes question publication and human-work admission'
        )
        assert not any(row['payload'].get('pending') is True for row in shown['messages']), (
            'I3/S6: rejected reservation cannot leave a public pending receipt'
        )
    assert len(compact(shown['messages'])) <= UI_BYTES and shown['project'] == original, (
        'I3/I8/S6: complete metadata-bearing rows stay bounded and preserve accepted science'
    )


@pytest.mark.parametrize('dimension', ['bytes', 'slots'])
def test_inclusive_archive_cap_is_loadable_but_no_new_user_io_fits(vm, signer, dimension):
    original = seed(vm, size=UI_BYTES) if dimension == 'bytes' else seed(vm, count=UI_SLOTS)
    authenticate(vm, signer)
    count = len(responses(vm))
    vm.command('send_text', text='No room for this complete new user wrapper')
    assert len(responses(vm)) == count and vm.last['vm']['messages'] == original, (
        'I3/S6: exact-cap persisted history is supported but new user admission refuses before I/O'
    )


def test_incomplete_native_tool_stream_does_not_fabricate_a_ui_allowance(vm, signer):
    # The real native adapter buffers calls until the actual semantic terminal.
    seed(vm, size=UI_BYTES - MESSAGE_BYTES - 65536)
    authenticate(vm, signer)
    index = ask(vm, complete=False)
    assert not vm.last['vm']['pending_question'], (
        'I13/S6: an incomplete provider item does not yet own a genuine UI question allowance'
    )
    item = function('ask_question', question(), call='vm-question')[-1]
    events(vm, index, [item])
    assert vm.last['vm']['pending_question'], (
        'I10/S6: only actual semantic completion admits the real pending question'
    )


def test_complete_question_terminal_is_object_correlated_unique_and_persisted(vm, signer):
    authenticate(vm, signer)
    ask(vm)
    pending = vm.last['vm']['pending_question']
    assert pending, 'I3/S6: actual question is visible before its trusted answer'
    original = {**pending, 'call_id': 'vm-question'}
    vm.command('answer', id=pending['question_id'], answer='inspect')
    terminal = visible_terminals(vm, 'vm-question')
    assert len(terminal) == 1, (
        'I3/S6: actual answer replaces pending state with one complete terminal row'
    )
    payload = terminal[0]['payload']
    assert_bound(payload, original)
    assert payload['result'] == {
        'question_id': pending['question_id'],
        'answer': 'inspect',
        'selected_option_id': 'inspect',
    }, (
        'I3/S6: retained answer is the full actual bound object, never a '
        'serialized string or acknowledgement'
    )
    before = vm.last['vm']['messages']
    saved = vm.command('archive')['reply']['rows']
    assert saved == before, (
        'I3/S6: actual persisted archive contains the complete original visible rows'
    )
    vm.command('destroy')
    vm.command('recreate')
    assert vm.last['vm']['messages'] == saved, (
        'I3/S6: a real replacement Session reloads exact terminal metadata'
    )


def fit_start(vm, signer, tmp_path):
    project = tmp_path / 'supported-project'
    shutil.copytree(ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project', project)
    assert vm.command('open', path=str(project))['reply']['opened'], (
        'I8/S6: genuine supported project opens before real candidate work'
    )
    authenticate(vm, signer)
    index = begin(vm)
    proposal = {
        'summary': 'Independent actual candidate',
        'groups': [{'id': 'workflow', 'paths': ['structure.cell.length_a']}],
        'budget': {'max_trials': 2, 'max_iterations': 20, 'max_elapsed_ms': 5000},
        'objective': {'absolute_tolerance': 0.0, 'relative_tolerance': 0.0},
    }
    events(vm, index, function('propose_plan', proposal, call='vm-plan'))
    plan = vm.last['vm']['pending_plan']
    assert plan, 'I2/S6: real scoped approval precedes asynchronous candidate setup'
    vm.command('approve', id=plan['plan_id'])
    events(
        vm,
        responses(vm)[-1][0],
        function(
            'begin_trial', {'group_id': 'workflow', 'plan_id': plan['plan_id']}, call='vm-begin'
        ),
    )
    begun = visible_terminals(vm, 'vm-begin')
    assert len(begun) == 1, (
        'I8/S6: actual begin-trial result exposes its generated candidate identity'
    )
    trial = begun[0]['payload']['result']['trial_id']
    events(
        vm,
        responses(vm)[-1][0],
        function(
            'set_free',
            {
                'flags': [{'path': 'structure.cell.length_a', 'free': True}],
                'plan_id': plan['plan_id'],
            },
            call='vm-free',
        ),
    )
    original = vm.last['vm']['project']
    events(
        vm,
        responses(vm)[-1][0],
        function('fit_trial', {'trial_id': trial, 'plan_id': plan['plan_id']}, call='vm-fit'),
    )
    return original


def fit_settle(vm):
    for _ in range(16):
        if visible_terminals(vm, 'vm-fit'):
            return vm.last
        vm.command('inspect')
    pytest.fail(
        'I8/I10/S6: genuine worker returns a complete terminal in bounded actual-owner delivery'
    )


def test_real_fit_activity_retains_full_terminal_and_coalesces_progress(vm, signer, tmp_path):
    original = fit_start(vm, signer, tmp_path)
    fit_settle(vm)
    terminal = visible_terminals(vm, 'vm-fit')
    assert len(terminal) == 1 and isinstance(terminal[0]['payload']['result'], dict), (
        'I8/S6: real optimizer retains one complete object terminal rather '
        'than progress or pending data'
    )
    result = terminal[0]['payload']['result']
    assert result['status'] in {'done', 'max_iter', 'no_step'} and isinstance(
        result['diagnostics'], list
    ), 'I8/S6: actual supported optimizer status and full diagnostics survive VM publication'
    assert vm.last['vm']['project'] == original, (
        'I8/S6: candidate activity never mutates live accepted state'
    )
    progress = [row for row in vm.last['vm']['messages'] if row['kind'] == 'progress']
    assert len(progress) <= 1, (
        'I3/S6: progress coalesces into bounded state instead of new archive rows'
    )
    assert vm.command('archive')['reply']['rows'] == vm.last['vm']['messages'], (
        'I3/S6: actual fit terminal persists with full metadata and no silent archive loss'
    )


@pytest.mark.parametrize('retirement', ['clear', 'project', 'account', 'session'])
@pytest.mark.parametrize('operation', ['question', 'fit'])
def test_stop_settles_actual_work_and_explicit_owner_retirement_fences_late_callbacks(
    vm, signer, tmp_path, operation, retirement
):
    if operation == 'fit':
        fit_start(vm, signer, tmp_path)
    else:
        authenticate(vm, signer)
        ask(vm)
    index = responses(vm)[-1][0]
    before = vm.last['vm']['project']
    vm.command('cancel')
    if operation == 'fit':
        fit_settle(vm)
    assert vm.last['vm']['project'] == before, (
        'I8/S6: ordinary Stop preserves accepted scientific state'
    )
    old = vm.last['vm']['messages']
    vm.command(
        'queued_callbacks_retire',
        retirement=retirement,
        callbacks=[
            {
                'op': 'data',
                'index': index,
                'base64': base64.b64encode(
                    b'data: {"type":"response.completed","response":'
                    b'{"id":"old","status":"completed","output":[]}}\n\n'
                ).decode(),
            },
            {'op': 'finish', 'index': index, 'failure': 0},
        ],
    )
    if retirement == 'session':
        assert not vm.last['vm']['alive'], (
            'I10/S6: late transport callback cannot resurrect a destroyed real Session'
        )
    else:
        assert not vm.last['vm']['pending_question'] and not vm.last['vm']['active_job'], (
            'I10/S6: explicit real-owner retirement cannot retain dead asynchronous authority'
        )
        if retirement == 'clear':
            assert vm.last['vm']['messages'] == [], (
                'I3/S6: explicit Clear releases its owned archive after actual settlement'
            )
        else:
            assert vm.last['vm']['messages'] == old, (
                'I3/S6: late retired callbacks cannot append or replace original visible outcomes'
            )


def failed_response(vm, status):
    index = begin(vm, 'Original user before provider failure')
    if status == 'interrupted':
        headers(vm, index)
        vm.command('finish', index=index, failure=1)
    elif status == 'refused':
        events(
            vm,
            index,
            [
                *message_start(channel='refusal'),
                text_fragment('Ordinary provider refusal', channel='refusal'),
                *message_complete('Ordinary provider refusal', channel='refusal'),
            ],
        )
    else:
        events(
            vm,
            index,
            [
                {
                    'type': 'response.' + status,
                    'response': {
                        'id': 'provider-' + status,
                        'status': status,
                        'output': [],
                        'error': {'message': 'Ordinary fixture ' + status},
                        'incomplete_details': {'reason': 'max_output_tokens'},
                    },
                }
            ],
        )
    return index


@pytest.mark.parametrize('status', ['failed', 'incomplete', 'refused', 'interrupted'])
def test_provider_terminal_card_is_durable_and_same_chat_retry_keeps_its_user(vm, signer, status):
    authenticate(vm, signer)
    failed_response(vm, status)
    cards = [row for row in vm.last['vm']['messages'] if row['status'] == status]
    before = vm.last['vm']['messages']
    text = 'Unique admitted Retry after ' + status
    count = len(responses(vm))
    vm.command('send_text', text=text)
    assert len(responses(vm)) == count + 1, (
        'I13/A2: same-chat valid Retry dispatches exactly one physical request'
    )
    user = [
        row for row in vm.last['vm']['messages'] if row['kind'] == 'user' and row['text'] == text
    ]
    assert len(user) == 1, (
        'I13/A2: prior provider error cannot suppress an actually admitted new user row'
    )
    assert vm.last['vm']['messages'][: len(before)] == before, (
        'I3/A2: Retry preserves all prior conversation/card rows'
    )
    assert vm.command('archive')['reply']['rows'] == vm.last['vm']['messages'], (
        'I3/A2: Retry admission persists its complete user row exactly once'
    )
    assert cards and all(row['text'] for row in cards), (
        'I13/S6/A2: actual provider terminal leaves a durable visible typed failure/refusal card'
    )


def test_persistence_refusal_precedes_new_user_row_and_provider_io(vm, signer):
    seed(vm, count=2)
    authenticate(vm, signer)
    before = vm.last['vm']['messages']
    count = len(responses(vm))
    vm.command('persistence_barrier')
    vm.command('send_text', text='Must not leave before durable admission')
    assert len(responses(vm)) == count and vm.last['vm']['messages'] == before, (
        'I3/S6/A2: genuine isolated persistence refusal precedes user '
        'admission and physical provider I/O'
    )
    assert vm.last['vm']['last_error'], (
        'I13/S6: real persistence refusal is visible and recoverable'
    )


def test_native_start_refusal_then_retry_keeps_admitted_user_and_unique_send(vm, signer):
    authenticate(vm, signer)
    count = len(responses(vm))
    vm.command('fail', value='request')
    vm.command('send_text', text='Actual start dependency refusal')
    assert len(responses(vm)) == count, (
        'I13/A2: refused native transport start performs no physical HTTP'
    )
    vm.command('fail', value='')
    text = 'Recovered public Retry'
    vm.command('send_text', text=text)
    assert len(responses(vm)) == count + 1, (
        'I13/A2: recovered actual native start dispatches one Retry'
    )
    assert (
        len([
            row
            for row in vm.last['vm']['messages']
            if row['kind'] == 'user' and row['text'] == text
        ])
        == 1
    ), 'I3/A2: recovered Retry cannot silently omit or duplicate its admitted user row'


@pytest.mark.parametrize('stop', [False, True], ids=['live-control', 'revoked'])
@pytest.mark.parametrize('origin', ['initial', 'continuation'])
def test_queued_physical_request_rechecks_actual_owner_authority(vm, signer, stop, origin):
    authenticate(vm, signer)
    if origin == 'initial':
        count = len(responses(vm))
        vm.command('send_then_stop', text='Queued actual user input', stop=stop)
        assert vm.last['reply']['before_stop']['can_cancel'], (
            'I13/A1: actual public user admission precedes Stop and queued dispatch'
        )
    else:
        ask(vm)
        pending = vm.last['vm']['pending_question']
        assert pending, (
            'I3/A1: a genuine completed question precedes queued trusted-answer continuation'
        )
        count = len(responses(vm))
        vm.command('answer_then_stop', id=pending['question_id'], answer='inspect', stop=stop)
    assert len(responses(vm)) == count + int(not stop), (
        'I2/I13/A1: live owner sends once; Stop before queued dispatch forbids later physical I/O'
    )


def two_models(vm):
    vm.catalog['models'].append({
        'slug': 'gpt-6-luna',
        'display_name': 'Mapped alternate',
        'visibility': 'list',
    })


def test_provider_default_and_incompatible_model_reset_remain_visible(vm, signer):
    two_models(vm)
    authenticate(vm, signer)
    vm.command('select_model', id='gpt-6-luna')
    vm.command('select_effort', id='none')
    assert vm.last['vm']['selected_effort'] == 'none', (
        'I13/A3: reviewed compatible canonical effort remains selectable'
    )
    vm.command('select_model', id='gpt-6.1-sol')
    assert not vm.last['vm']['selected_effort'], (
        'I13/A3: incompatible selection resets visibly to Provider default'
    )
    vm.command('select_effort', id='')
    index = begin(vm)
    body = json.loads(vm.last['requests'][index]['body'])
    assert 'effort' not in body.get('reasoning', {}), (
        'I13/A3: Provider default omits canonical reasoning effort on actual wire'
    )


def test_busy_public_setters_refuse_selection_drift(vm, signer):
    two_models(vm)
    authenticate(vm, signer)
    vm.command('select_effort', id='high')
    begin(vm)
    before = (vm.last['vm']['selected_model'], vm.last['vm']['selected_effort'])
    count = len(responses(vm))
    vm.command('select_model', id='gpt-6-luna')
    vm.command('select_effort', id='low')
    assert (vm.last['vm']['selected_model'], vm.last['vm']['selected_effort']) == before, (
        'I2/I13/A3: both real public setters refuse busy model/effort drift'
    )
    assert len(responses(vm)) == count, (
        'I13/A3: refused busy selection never silently restarts a request'
    )


def test_pending_browser_signin_can_stop_and_late_valid_callback_cannot_connect(vm, signer):
    sign, vm.jwks = signer
    query = vm.begin()
    before = vm.last['vm']['can_cancel']
    vm.command('cancel')
    vm.jwt = sign({
        'iss': native.AUTH,
        'aud': native.CLIENT,
        'sub': native.SUBJECT,
        'nonce': query['nonce'],
        'iat': native.WALL,
        'exp': native.WALL + 3600,
        'email': 'synthetic@example.invalid',
    })
    vm.command(
        'callback',
        query={'code': 'synthetic-code', 'state': query['state'], 'client_id': native.CLIENT},
    )
    vm.automatic()
    checks = {'pending_auth_cancellable': before, 'late_callback_fenced': not vm.ready()}
    assert all(checks.values()), (
        'I12/A4: actual pending browser auth is cancellable and late valid callback stays fenced'
    )


@pytest.mark.parametrize('recovery', ['clear', 'restore-and-retry'])
def test_real_question_failed_persistence_preserves_settlement_until_explicit_recovery(
    vm, signer, recovery
):
    authenticate(vm, signer)
    ask(vm)
    pending = vm.last['vm']['pending_question']
    assert pending, (
        'I10/S6: a genuine writable-archive question is admitted before settlement refusal'
    )
    original = vm.last['vm']['project']
    count = len(responses(vm))
    vm.command('persistence_barrier')
    vm.command('answer', id=pending['question_id'], answer='inspect')
    failed = vm.last
    vm.command('cancel')
    stopped = vm.last
    checks = {
        'no_complete_public_terminal': not visible_terminals(vm, 'vm-question'),
        'no_continuation': len(responses(vm)) == count,
        'accepted_state_preserved': vm.last['vm']['project'] == original,
        'failed_settlement_visible': bool(failed['vm']['last_error']),
        'stop_preserves_recovery': stopped['vm']['can_cancel'],
    }
    if recovery == 'clear':
        vm.command('clear_history')
        checks['explicit_clear_retires'] = (
            not vm.last['vm']['can_cancel'] and not vm.last['vm']['pending_question']
        )
    else:
        vm.command('persistence_restore')
        vm.command('answer', id=pending['question_id'], answer='inspect')
        terminal = visible_terminals(vm, 'vm-question')
        expected = {
            'question_id': pending['question_id'],
            'answer': 'inspect',
            'selected_option_id': 'inspect',
        }
        checks['original_complete_answer_survives'] = (
            len(terminal) == 1 and terminal[0]['payload']['result'] == expected
        )
        checks['recovery_is_settled'] = not vm.last['vm']['can_cancel']
        checks['complete_outcome_is_persisted'] = (
            vm.command('archive')['reply']['rows'] == vm.last['vm']['messages']
        )
    assert all(checks.values()), (
        'I3/I10/S6: real failed host settlement preserves actual question/answer, blocks '
        'publication/continuation through Stop and permits explicit owner recovery: ' + str(checks)
    )
