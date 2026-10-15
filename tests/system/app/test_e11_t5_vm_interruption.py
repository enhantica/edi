"""B1-B3 real dispatched-owner interruption and visible-history preservation.

B4 deferred allocation preparation and B3's exact precommit interval remain explicit
qualification holes; ordinary transport/file observations are never relabelled as them.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'interrupted_vm', ROOT / 'tests/system/app/test_e11_t5_vm_retention.py'
)
component = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(component)
vm = component.vm
signer = component.signer


def active_stream(vm, *, text='Original bounded partial — Å', headers=True):
    index = component.begin(vm, 'Original human before interruption')
    if headers:
        component.headers(vm, index)
    if text is not None:
        component.events(
            vm,
            index,
            [
                *component.message_start(item_id='original-stream'),
                component.text_fragment(text, item_id='original-stream'),
            ],
            finish=False,
        )
    return index


def cards(vm):
    return [
        row
        for row in vm.last['vm']['messages']
        if row['payload'].get('type') == 'provider_failure'
    ]


def body(vm, index):
    return json.loads(vm.last['requests'][index]['body'])


def input_texts(value):
    # Official Responses input messages support plain string or typed content arrays.
    result = []
    for item in value.get('input', []):
        if item.get('role') != 'user':
            continue
        content = item.get('content', [])
        if isinstance(content, str):
            result.append(content)
        else:
            result.extend(part['text'] for part in content if part.get('type') == 'input_text')
    return result


def opened(vm, signer, tmp_path):
    destination = tmp_path / 'real-project'
    shutil.copytree(ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project', destination)
    assert vm.command('open', path=str(destination))['reply']['opened'], (
        'I8/B1: ordinary manual interruption uses the actual open supported project'
    )
    component.authenticate(vm, signer)


def late_complete(vm, index):
    component.events(
        vm,
        index,
        component.message_complete('Original bounded partial — Å', item_id='original-stream'),
    )


@pytest.mark.parametrize('stage', ['before-headers', 'after-headers', 'after-text'])
def test_real_stop_retains_original_interruption_and_fences_late_completion(vm, signer, stage):
    component.authenticate(vm, signer)
    index = active_stream(
        vm,
        text='Original bounded partial — Å' if stage == 'after-text' else None,
        headers=stage != 'before-headers',
    )
    original = vm.last['vm']['project']
    partial = [row for row in vm.last['vm']['messages'] if row['kind'] == 'assistant']
    vm.command('cancel')
    stopped = vm.last
    retained = cards(vm)
    before_late = vm.last['vm']['messages']
    late_complete(vm, index)
    unchanged = vm.last['vm']['messages'] == before_late
    checks = {
        'original_transport_cancelled': stopped['requests'][index]['cancelled'],
        'accepted_state_preserved': vm.last['vm']['project'] == original,
        'one_durable_interruption': len(retained) == 1 and retained[0]['status'] == 'interrupted',
        'late_original_completion_inert': unchanged,
        'ordinary_stop_settled': not vm.last['vm']['can_cancel'],
    }
    if retained:
        payload = retained[0]['payload']
        checks['complete_original_scope'] = (
            all(payload.get(k) for k in ('connection_id', 'turn_id', 'request_id', 'code'))
            and payload['status'] == 'interrupted'
        )
        if partial:
            checks['same_original_public_binding'] = all(
                payload[k] == partial[0]['payload'][k]
                for k in ('connection_id', 'turn_id', 'request_id')
            )
    checks['archive_matches_complete_public_rows'] = (
        vm.command('archive')['reply']['rows'] == vm.last['vm']['messages']
    )
    assert all(checks.values()), (
        'I3/I10/I13/B2: Stop settles actual original transport and durably retains matching '
        'interruption while late completion remains nonexecuting: ' + str(checks)
    )


@pytest.mark.parametrize('reason', ['manual-value', 'ui-output-capacity'])
def test_dispatched_scope_revocation_cancels_original_native_and_allows_new_send(
    vm, signer, tmp_path, reason
):
    if reason == 'manual-value':
        opened(vm, signer, tmp_path)
    else:
        component.seed(vm, size=component.UI_BYTES - 400000)
        component.authenticate(vm, signer)
    index = active_stream(vm, text=None)
    original = vm.last['vm']['project']
    if reason == 'manual-value':
        parameter = next(
            row for row in original['parameters'] if row['path'] == 'structure.cell.length_a'
        )
        desired = parameter['value'] + 0.001
        edited = vm.command('manual_value', path=parameter['path'], value=desired)
        assert not edited['reply']['error'], (
            'I8/B1: actual public manual edit reaches a successful live scalar change'
        )
        expected = {
            **original,
            'parameters': [
                {**row, 'value': desired} if row['path'] == parameter['path'] else row
                for row in original['parameters']
            ],
        }
    else:
        expected = original
        component.events(
            vm,
            index,
            [
                *component.message_start(item_id='capacity-stream'),
                component.text_fragment('q' * 524288, item_id='capacity-stream'),
            ],
            finish=False,
        )
    revoked = vm.last
    vm.command('cancel')
    cancelled = vm.last
    # Explicit Clear is a separate owner action, not an excuse to keep inference orphaned.
    vm.command('clear_history')
    if reason == 'manual-value':
        vm.command('sign_in')  # Existing public re-consent after the actual context edit.
    count = len(component.responses(vm))
    vm.command('send_text', text='Unique new human after old owner retirement')
    checks = {
        'original_operation_cancelled': revoked['requests'][index]['cancelled'],
        'accepted_live_state_exact': cancelled['vm']['project'] == expected,
        'stop_can_reach_original_operation': cancelled['requests'][index]['cancelled'],
        'one_recovered_physical_send': len(component.responses(vm)) == count + 1,
        'one_recovered_public_user': sum(
            row['kind'] == 'user' and row['text'] == 'Unique new human after old owner retirement'
            for row in vm.last['vm']['messages']
        )
        == 1,
    }
    assert all(checks.values()), (
        'I2/I3/I8/I10/B1: observed core revocation cancels the original physical owner, '
        'preserves accepted edits and leaves usable explicit recovery: ' + str(checks)
    )


def test_approved_elapsed_budget_retires_dispatched_continuation_transport(vm, signer, tmp_path):
    opened(vm, signer, tmp_path)
    first = component.begin(vm)
    component.events(
        vm,
        first,
        component.function(
            'propose_plan',
            {
                'summary': 'Independent finite elapsed-budget witness',
                'groups': [{'id': 'workflow', 'paths': ['structure.cell.length_a']}],
                'budget': {'max_trials': 2, 'max_iterations': 20, 'max_elapsed_ms': 200},
                'objective': {'absolute_tolerance': 0.0, 'relative_tolerance': 0.0},
            },
            call='budget-plan',
        ),
    )
    plan = vm.last['vm']['pending_plan']
    assert plan, 'I2/B1: real approved-plan budget is admitted before elapsed retirement'
    vm.command('approve', id=plan['plan_id'])
    index = component.responses(vm)[-1][0]
    assert index != first and not vm.last['requests'][index]['cancelled'], (
        'I10/B1: real continuation is physically dispatched before its ordinary elapsed deadline'
    )
    original = vm.last['vm']['project']
    for _ in range(16):
        vm.command('inspect')  # Existing ordinary owner delivery; no injected core clock or sleep.
        if vm.last['requests'][index]['cancelled']:
            break
    assert not vm.last['vm']['can_cancel'], (
        'I10/B1: the actual core deadline has retired its live approval/turn before transport proof'
    )
    assert vm.last['requests'][index]['cancelled'] and vm.last['vm']['project'] == original, (
        'I8/I10/B1: actual elapsed core budget revokes the matching native continuation '
        'without changing accepted state'
    )


@pytest.mark.parametrize('terminal', ['failed', 'incomplete', 'refused', 'interrupted'])
def test_pending_failed_card_survives_automatic_expiry_until_real_storage_recovery(
    vm, signer, terminal
):
    component.authenticate(vm, signer)
    index = component.begin(vm, 'Original user with pending durable failure')
    vm.command('persistence_barrier')
    if terminal == 'interrupted':
        component.headers(vm, index)
        vm.command('finish', index=index, failure=1)
    elif terminal == 'refused':
        component.events(
            vm,
            index,
            [
                *component.message_start(channel='refusal'),
                component.text_fragment('Original bounded refusal', channel='refusal'),
                *component.message_complete('Original bounded refusal', channel='refusal'),
            ],
        )
    else:
        component.events(
            vm,
            index,
            [
                {
                    'type': 'response.' + terminal,
                    'response': {
                        'id': 'pending-' + terminal,
                        'status': terminal,
                        'output': [],
                        'error': {'message': 'Original bounded ' + terminal},
                        'incomplete_details': {'reason': 'max_output_tokens'},
                    },
                }
            ],
        )
    failed = vm.last
    vm.command('advance', seconds=3601, milliseconds=0)
    for _ in range(8):
        if not vm.last['vm']['connected']:
            break
        vm.command('inspect')
    expired = vm.last
    vm.command('persistence_restore')
    count = len(component.responses(vm))
    vm.command('send_text', text='Recovery cannot silently discard the pending original')
    recovered = cards(vm)
    saved = vm.command('archive')['reply']['rows']
    checks = {
        'real_storage_failure_visible': bool(failed['vm']['last_error']),
        'automatic_expiry_observed': not expired['vm']['connected'],
        'no_unconnected_physical_send': len(component.responses(vm)) == count,
        'one_original_complete_card': len(recovered) == 1 and recovered[0]['status'] == terminal,
        'complete_public_archive_preserved': saved == vm.last['vm']['messages'],
    }
    if recovered:
        checks['original_bound_failure'] = all(
            recovered[0]['payload'].get(k)
            for k in ('connection_id', 'turn_id', 'request_id', 'code')
        )
    vm.command('clear_history')
    checks['explicit_clear_distinct'] = not vm.last['vm']['messages']
    assert all(checks.values()), (
        'I3/I10/I13/B2: actual unpersisted original failure survives automatic expiry, '
        'flushes completely when storage returns and retires only on explicit Clear: '
        + str(checks)
    )


@pytest.mark.parametrize('retry', ['same-text', 'different-text'])
def test_real_dispatch_refusal_retry_never_replays_invisible_or_duplicate_user(vm, signer, retry):
    component.authenticate(vm, signer)
    attempt = 'Distinct original attempted human prompt — Å'
    vm.command('fail', value='request-null')
    vm.command('send_text', text=attempt)
    refused = vm.last
    vm.command('fail', value='')
    text = attempt if retry == 'same-text' else 'Distinct subsequent human prompt — Ö'
    count = len(component.responses(vm))
    vm.command('send_text', text=text)
    requests = component.responses(vm)
    checks = {
        'ordinary_dispatch_refusal_visible': bool(refused['vm']['last_error']),
        'one_physical_retry': len(requests) == count + 1,
    }
    if len(requests) == count + 1:
        sent = input_texts(body(vm, requests[-1][0]))
        visible = [row['text'] for row in vm.last['vm']['messages'] if row['kind'] == 'user']
        for original in {attempt, text}:
            checks['no_invisible_or_duplicate_' + original] = sent.count(
                original
            ) <= visible.count(original)
        checks['actual_new_prompt_once'] = sent.count(text) == (
            2 if retry == 'same-text' and visible.count(text) == 2 else 1
        )
    checks['full_visible_history_persisted'] = (
        vm.command('archive')['reply']['rows'] == vm.last['vm']['messages']
    )
    assert all(checks.values()), (
        'I3/I13/B3: actual outgoing retry history has a visible, unique admitted human '
        'row for every attempted prompt or an explicit retired conversation: ' + str(checks)
    )


def test_uninterrupted_live_stream_is_a_real_transport_and_persistence_control(vm, signer):
    component.authenticate(vm, signer)
    index = active_stream(vm)
    assert not vm.last['requests'][index]['cancelled'] and vm.last['vm']['can_cancel'], (
        'I10/B1: an ordinary real in-flight stream remains owned until completion or revocation'
    )
    late_complete(vm, index)
    assert vm.command('archive')['reply']['rows'] == vm.last['vm']['messages'], (
        'I3/B2: ordinary successful completion keeps complete public and persisted rows identical'
    )
