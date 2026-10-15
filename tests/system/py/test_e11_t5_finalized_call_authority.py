"""Reviewed item.done authority, independent originals and actual native finish.

Private candidate only until the conductor grants tracked application. Packet
 d5dec42b4 is the omission policy; official item/response schemas supply shapes.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from tests.system.app import test_e11_t5_workflow_vm as workflow

# Destination is tests/system/py; no private cache/path supplies a production API.
_spec = importlib.util.spec_from_file_location(
    'finalized_native', Path(__file__).with_name('test_e11_t5_native_completion_authority.py')
)
authority = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(authority)
originals = authority.originals
native = authority.native
signer = authority.signer
host = originals.host


def call(identity, *, absent=False):
    value = originals.original('function_call', identity)
    if absent:
        del value['status']
    return value


def calls(result):
    return [event for event in result['stream_events'] if event.get('type') == 'tool_call']


@pytest.mark.parametrize('layout', ['one', 'two', 'mixed'])
@pytest.mark.parametrize('status', ['absent', 'completed'])
def test_finalized_original_calls_survive_explicit_empty_or_compact_final_array(
    host, layout, status
):
    host.command('stream_start')
    values = [call('omitted-A', absent=status == 'absent')]
    if layout == 'two':
        values.append(call('omitted-B', absent=status == 'absent'))
    elif layout == 'mixed':
        values = [
            originals.original('reasoning', 'opaque-before'),
            values[0],
            originals.original('message', 'public-after'),
        ]
    prefix = originals.wire(
        host, [originals.item_event(value, index) for index, value in enumerate(values)]
    )
    assert prefix['reply']['ok'] and not calls(prefix), (
        'S-R3: genuine immutable done originals alone stage, never publish executable work'
    )
    final = [values[-1]] if layout == 'mixed' else []
    ended = originals.wire(host, [originals.complete(final)])
    expected = [value for value in values if value['type'] == 'function_call']
    assert ended['reply']['ok'] and [value['call_id'] for value in calls(ended)] == [
        value['call_id'] for value in expected
    ], (
        'S-R3: successful explicit compact summary retains exact genuinely '
        'finalized original calls in original positions'
    )
    finished = host.command('stream_finish')
    assert finished['reply']['ok'] and host.command('stream_output')['reply'] == values, (
        'S-R3: complete immutable original evidence is retained exactly once in original order'
    )


@pytest.mark.parametrize('entry', ['added', 'arguments-done'])
def test_unfinalized_parseable_call_does_not_qualify_for_omission(host, entry):
    host.command('stream_start')
    value = call('unfinalized-A')
    events = [originals.item_event(value, done=False)]
    if entry == 'arguments-done':
        events.append({
            'type': 'response.function_call_arguments.done',
            'item_id': value['id'],
            'output_index': 0,
            'arguments': '{}',
        })
    ended = originals.wire(host, [*events, originals.complete([])])
    assert not ended['reply']['ok'] and not calls(ended), (
        'S-R3: added/arguments.done parseability never substitutes for genuine item.done authority'
    )
    assert not host.command('stream_finish')['reply']['ok'], (
        'S-R3: unfinalized omission remains refused after physical EOF'
    )


@pytest.mark.parametrize('status', ['in_progress', 'incomplete', 'failed', None, 17])
def test_explicit_noncomplete_or_wrong_status_is_not_optional_absence(host, status):
    host.command('stream_start')
    value = call('wrong-status-A')
    value['status'] = status
    ended = originals.wire(host, [originals.item_event(value), originals.complete([])])
    assert not ended['reply']['ok'] and not calls(ended), (
        'S-R3: semantic partial/failed/null/wrong-type originals do not qualify omitted execution'
    )


@pytest.mark.parametrize('fault', ['call-id', 'arguments', 'duplicate-slot', 'malformed-message'])
def test_omitted_valid_prefix_cannot_mask_later_contradiction_or_bad_companion(host, fault):
    host.command('stream_start')
    first = call('valid-omitted-A')
    second = call('second-present-B')
    events = [originals.item_event(first), originals.item_event(second, 1)]
    final = copy.deepcopy(second)
    if fault == 'call-id':
        final['call_id'] = 'contradictory-original-correlation'
    elif fault == 'arguments':
        final['arguments'] = '{"changed":true}'
    elif fault == 'duplicate-slot':
        events.append(originals.item_event(call('replacement-slot-C'), 0))
    else:
        final = originals.original('message', 'malformed-message-C')
        del final['role']
        events.append(originals.item_event(final, 2))
    ended = originals.wire(host, [*events, originals.complete([final])])
    assert not ended['reply']['ok'] and not calls(ended), (
        'S-R3: whole-group validation contains a later contradiction/invalid '
        'companion before any executable prefix'
    )


@pytest.mark.parametrize('status', ['absent', 'completed'])
def test_native_omitted_done_call_waits_for_finish_and_pairs_actual_next_wire(
    native, signer, status
):
    native.authenticate(signer)
    index, request = authority.services.start_inference(native, tools=authority.TOOLS)
    value = call('native-omitted-paired-A', absent=status == 'absent')
    before = authority.feed(native, index, [originals.item_event(value), originals.complete([])])
    assert not authority.bound(before, request, 'tool_call'), (
        'S-R3: logical omitted-call success cannot release physical native work before finish'
    )
    settled = native.command('finish', index=index, failure=0)
    delivered = authority.bound(settled, request, 'tool_call')
    assert len(delivered) == 1 and delivered[0]['call_id'] == value['call_id'], (
        'S-R3: one genuinely finalized original crosses successful physical finish exactly once'
    )
    terminal = authority.bound(settled, request, 'turn_finished')
    assert len(terminal) == 1 and terminal[0]['status'] == 'completed', (
        'S-R3: actual native exchange completes without a fabricated interrupted result'
    )
    history = [
        *request['history'],
        {'type': 'tool_call', 'call_id': value['call_id'], 'name': value['name'], 'arguments': {}},
        {
            'type': 'tool_result',
            'call_id': value['call_id'],
            'ok': True,
            'code': '',
            'result': {'original': 'trusted read-only fixture outcome'},
        },
    ]
    continuation = authority.services.provider_request(
        native, request_id='omitted-next-paired', history=history
    )
    sent = native.command('send', payload=continuation)
    assert sent['reply']['ok'], 'S-R3: actual correlated trusted outcome permits continuation'
    outgoing = json.loads(sent['requests'][-1]['body'])['input']
    assert [item for item in outgoing if item.get('type') == 'function_call'] == [value], (
        'S-R3: native subsequent wire retains exact original once, never a '
        'summary-generated replacement'
    )
    results = [item for item in outgoing if item.get('type') == 'function_call_output']
    assert len(results) == 1 and results[0]['call_id'] == value['call_id'], (
        'S-R3: actual outgoing wire pairs one original call with one matching result'
    )


@pytest.mark.parametrize(
    'failure', ['transport', 'late-malformed', 'failed', 'incomplete', 'cancel', 'sign-out']
)
def test_native_omitted_call_never_bypasses_whole_failure_or_retirement(native, signer, failure):
    native.authenticate(signer)
    index, request = authority.services.start_inference(native, tools=authority.TOOLS)
    value = call('native-omission-fenced-A')
    terminal = originals.complete([])
    if failure in {'failed', 'incomplete'}:
        terminal['type'] = 'response.' + failure
        terminal['response']['status'] = failure
        if failure == 'failed':
            terminal['response']['error'] = {
                'code': 'subscription_sharing_usage_limit_exceeded',
                'message': 'Original offline quota fixture',
            }
    prefix = authority.feed(native, index, [originals.item_event(value), terminal])
    assert not authority.bound(prefix, request, 'tool_call'), (
        'S-R3: even a genuinely finalized omitted call stays buffered until whole physical success'
    )
    if failure == 'late-malformed':
        native.command(
            'data',
            index=index,
            base64=authority.base64.b64encode(b'data: {not-json}\n\n').decode(),
        )
    elif failure == 'cancel':
        native.command('cancel', turn_id=request['turn_id'])
    elif failure == 'sign-out':
        native.command('sign_out')
    ended = native.command('finish', index=index, failure=1 if failure == 'transport' else 0)
    assert not authority.bound(ended, request, 'tool_call'), (
        'S-R3: failure, late invalid bytes or actual operation/account retirement '
        'cannot release omitted work'
    )
    assert not any(
        event['status'] == 'completed'
        for event in authority.bound(ended, request, 'turn_finished')
    ), 'S-R3: unsuccessful/retired original does not publish false successful completion'


# Existing real Session component closes the native-release vs scientific-approval seam.

workflow_vm = workflow.workflow_vm


@pytest.mark.parametrize('decision', ['approve', 'stop', 'manual-revision'])
def test_omitted_proposal_still_requires_actual_current_ui_approval(workflow_vm, signer, decision):
    vm = workflow_vm
    workflow.connect(vm, signer)
    workflow.acknowledge(vm)
    before = vm.last['vm']['project']
    index = workflow.prior.begin(vm, 'Original proposal requiring genuine approval')
    proposal = {
        'summary': 'Original scoped omission proposal',
        'groups': [{'id': 'workflow', 'paths': ['structure.cell.length_a']}],
        'budget': {'max_trials': 2, 'max_iterations': 20, 'max_elapsed_ms': 5000},
        'objective': {'absolute_tolerance': 0.0, 'relative_tolerance': 0.0},
    }
    stream = workflow.prior.function('propose_plan', proposal, call='omitted-proposal-A')
    stream[-1]['response']['output'] = []
    workflow.prior.events(vm, index, stream, finish=False)
    assert not vm.last['vm']['pending_plan'], (
        'S-R3: logical stream completion cannot publish a proposal before physical finish'
    )
    vm.command('finish', index=index, failure=0)
    plan = vm.last['vm']['pending_plan']
    assert plan and vm.last['vm']['project'] == before, (
        'S-R3: genuine finalized omitted proposal reaches actual UI approval '
        'without scientific writes'
    )
    requests_before = len(workflow.prior.responses(vm))
    if decision == 'approve':
        vm.command('approve', id=plan['plan_id'])
        assert len(workflow.prior.responses(vm)) == requests_before + 1, (
            'S-R3: only actual trusted approval resumes the bound proposal once'
        )
        assert vm.last['vm']['project'] == before, (
            'S-R3: approval alone never fabricates a fit or live scientific result'
        )
    elif decision == 'stop':
        vm.command('cancel')
        vm.command('approve', id=plan['plan_id'])
        assert len(workflow.prior.responses(vm)) == requests_before, (
            'S-R3: ordinary Stop revokes omitted proposal approval authority'
        )
    else:
        vm.command('manual_value', path='structure.cell.length_a', value=6.25)
        actual_manual = vm.last['vm']['project']
        vm.command('approve', id=plan['plan_id'])
        assert len(workflow.prior.responses(vm)) == requests_before, (
            'S-R3: genuine manual revision cannot approve the captured older proposal'
        )
        assert vm.last['vm']['project'] == actual_manual, (
            'S-R3: stale approval preserves the actual independently requested manual edit'
        )


# FC1/FC2: published supplied identity and initial argument declaration are
# independent prior inputs, never values reconstructed from decoder projection.
def argument_event(value, ending, arguments):
    return {
        'type': 'response.function_call_arguments.' + ending,
        'item_id': value['id'],
        'output_index': 0,
        'delta' if ending == 'delta' else 'arguments': arguments,
    }


@pytest.mark.parametrize('identity', ['absent', 'consistent'])
def test_supplied_response_identity_is_optional_but_consistent_when_present(host, identity):
    host.command('stream_start')
    value = call('identity-positive-A')
    done, terminal = originals.item_event(value), originals.complete([value])
    if identity == 'absent':
        del terminal['response']['id']
    else:
        done['response_id'] = terminal['response']['id']
    observed = originals.wire(host, [done, terminal])
    assert observed['reply']['ok'] and len(calls(observed)) == 1, (
        'FC1: genuine optional absence and consistent supplied response identity remain valid'
    )


@pytest.mark.parametrize(
    'door', ['created', 'added', 'delta', 'arguments-done', 'item-done', 'terminal']
)
def test_conflicting_supplied_response_identity_refuses_before_callable_publication(host, door):
    host.command('stream_start')
    value = call('identity-conflict-A')
    events = []
    if door == 'created':
        events.append({
            'type': 'response.created',
            'response': {'id': 'response-A', 'status': 'in_progress', 'output': []},
        })
    added = originals.item_event({**value, 'status': 'in_progress', 'arguments': ''}, done=False)
    delta = argument_event(value, 'delta', '{}')
    arguments_done = argument_event(value, 'done', '{}')
    done = originals.item_event(value)
    for label, event in [
        ('added', added),
        ('delta', delta),
        ('arguments-done', arguments_done),
        ('item-done', done),
    ]:
        if door == label:
            event['response_id'] = 'response-A'
    terminal = originals.complete([value])
    terminal['response']['id'] = 'response-B'
    if door == 'terminal':
        done['response_id'] = 'response-A'
        terminal['response_id'] = 'response-A'
    observed = originals.wire(host, [*events, added, delta, arguments_done, done, terminal])
    assert not observed['reply']['ok'] and not calls(observed), (
        'FC1: contradictory supplied event/response identities cannot authorize '
        'any callable prefix'
    )
    assert not host.command('stream_finish')['reply']['ok'], (
        'FC1: identity contradiction stays refused after EOF without repaired authority'
    )


@pytest.mark.parametrize('door', ['event', 'terminal'])
@pytest.mark.parametrize(
    'value', [None, 17, ['response-A'], 'r' * 257], ids=['null', 'number', 'array', 'over-id-cap']
)
def test_supplied_response_identity_checks_type_and_existing_byte_capacity(host, door, value):
    host.command('stream_start')
    original = call('identity-type-A')
    done, terminal = originals.item_event(original), originals.complete([original])
    if door == 'event':
        done['response_id'] = value
    else:
        terminal['response']['id'] = value
    observed = originals.wire(host, [done, terminal])
    assert not observed['reply']['ok'] and not calls(observed), (
        'FC1: supplied response IDs obey existing typed bounded identity contract '
        'before publication'
    )


@pytest.mark.parametrize(
    ('initial', 'flow', 'repeat'),
    [
        ('', 'direct', True),
        ('{"x":1}', 'direct', False),
        ('{"x":', 'delta', True),
        ('{"x":', 'arguments-done', False),
    ],
)
def test_initial_arguments_empty_complete_and_progressive_declarations_agree(
    host, initial, flow, repeat
):
    host.command('stream_start')
    value = call('initial-compatible-A')
    value['arguments'] = '{"x":1}'
    added = originals.item_event(
        {**value, 'status': 'in_progress', 'arguments': initial}, done=False
    )
    events = [added]
    if flow == 'delta':
        events.append(argument_event(value, 'delta', '1}'))
    elif flow == 'arguments-done':
        events.append(argument_event(value, 'done', value['arguments']))
    events.extend([originals.item_event(value), originals.complete([value] if repeat else [])])
    observed = originals.wire(host, events)
    assert observed['reply']['ok'] and len(calls(observed)) == 1, (
        'FC2: compatible initial declarations retain valid direct and progressive finalization'
    )
    assert calls(observed)[0]['arguments'] == {'x': 1}, (
        'FC2: complete arguments preserve the independently planted original object'
    )


@pytest.mark.parametrize(
    ('fault', 'flow', 'repeat'),
    [
        ('null', 'direct', True),
        ('object', 'direct', False),
        ('number', 'delta', True),
        ('contradictory', 'direct', False),
        ('contradictory', 'delta', True),
        ('contradictory', 'arguments-done', False),
        ('prefix-conflict', 'delta', False),
    ],
)
def test_initial_argument_type_capacity_and_declaration_cannot_be_overwritten(
    host, fault, flow, repeat
):
    host.command('stream_start')
    value = call('initial-refused-A')
    value['arguments'] = '{"x":2}'
    initial = {
        'null': None,
        'object': {'x': 1},
        'number': 17,
        'contradictory': '{"x":1}',
        'prefix-conflict': '{"y":',
    }[fault]
    added = originals.item_event(
        {**value, 'status': 'in_progress', 'arguments': initial}, done=False
    )
    events = [added]
    if flow == 'delta':
        events.append(argument_event(value, 'delta', '2}'))
    elif flow == 'arguments-done':
        events.append(argument_event(value, 'done', value['arguments']))
    events.extend([originals.item_event(value), originals.complete([value] if repeat else [])])
    observed = originals.wire(host, events)
    assert not observed['reply']['ok'] and not calls(observed), (
        'FC2: initial wrong type/oversize/contradiction cannot disappear into a '
        'later valid done original'
    )


def test_supplied_content_event_response_identity_cannot_rebind_later_call(host):
    host.command('stream_start')
    message = originals.original('message', 'identity-content-A')
    value = call('identity-content-call-B')
    text = message['content'][0]['text']
    prefix = originals.wire(
        host,
        [
            originals.item_event({**message, 'status': 'in_progress', 'content': []}, done=False),
            {
                'type': 'response.content_part.added',
                'item_id': message['id'],
                'output_index': 0,
                'content_index': 0,
                'part': {'type': 'output_text', 'text': '', 'annotations': []},
            },
            {
                'type': 'response.output_text.delta',
                'item_id': message['id'],
                'output_index': 0,
                'content_index': 0,
                'delta': text,
                'response_id': 'response-content-A',
            },
            originals.item_event(message),
            originals.item_event(value, 1),
        ],
    )
    assert prefix['reply']['ok'] and not calls(prefix), (
        'FC1: genuine live content and finalized callable prefix reach staging coherently'
    )
    terminal = originals.complete([message, value])
    terminal['response']['id'] = 'response-content-B'
    refused = originals.wire(host, [terminal])
    assert not refused['reply']['ok'] and not calls(refused), (
        'FC1: supplied content-event response identity binds the whole later callable group'
    )
