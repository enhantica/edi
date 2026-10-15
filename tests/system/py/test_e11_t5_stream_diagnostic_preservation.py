"""Preserve actual public parser diagnostics through real native and VM owners.

These are lossless-public-diagnostic invariants, not producer-generated error wording pins.
The prior compiled VM lacks cards; its failures cannot qualify the uncompiled new VM.
"""

from __future__ import annotations

import base64
import importlib.util
import os
from pathlib import Path

import pytest

from tests.fixtures.assistant.diagnostic_streams import PRIVATE_MARKER, diagnostic_wire

ROOT = Path(__file__).resolve().parents[3]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


protocol = load('diagnostic_protocol', 'tests/integration/py/test_e11_t5_assistant_protocol.py')
services = load('diagnostic_native', 'tests/system/py/test_e11_t5_assistant_native.py')
component = load('diagnostic_vm', 'tests/system/app/test_e11_t5_vm_retention.py')
transport = services.native
signer = services.signer
vm = component.vm
CASES = ['malformed-json', 'changed-completed-item', 'truncated']
ERROR_BYTES = 512  # Approved public Limits::error_bytes, packet R4.


def parser_refusal(case):
    binary = Path(
        os.environ.get(
            'EDI_ASSISTANT_CORE_PROBE', ROOT / 'build/app/core/assistant_contract_probe'
        )
    )
    assert binary.is_file(), (
        'I13: real public parser consumer must exist before diagnostic comparison'
    )
    host = protocol.Host(binary)
    try:
        host.command('stream_start')
        result = host.command('stream_feed', bytes=list(diagnostic_wire(case)))['reply']
        if case == 'truncated':
            assert result['ok'], 'I13: valid unfinished event prefix reaches actual finish refusal'
            result = host.command('stream_finish')['reply']
        assert not result['ok'] and result['code'] and result['value']['message'], (
            'I13: the original actual parser refusal has a concrete code and safe public reason'
        )
        message = result['value']['message']
        assert len(message.encode()) <= ERROR_BYTES and PRIVATE_MARKER not in message, (
            'I3/I13: parser diagnostic is bounded and does not echo unrecognized/private input'
        )
        return result['code'], message
    finally:
        host.close()


def deliver(actor, index, case):
    actor.command('data', index=index, base64=base64.b64encode(diagnostic_wire(case)).decode())
    if case == 'truncated':
        actor.command('finish', index=index, failure=0)
    return actor.last


@pytest.mark.parametrize('case', CASES)
def test_actual_native_preserves_first_parser_feed_or_finish_reason_and_code(
    transport, signer, case
):
    code, message = parser_refusal(case)
    transport.authenticate(signer)
    index, request = services.start_inference(transport)
    result = deliver(transport, index, case)
    terminal = [
        event
        for event in result['events']
        if event.get('type') == 'turn_finished'
        and event.get('request_id') == request['request_id']
    ]
    checks = {
        'one_original_noncompleted_terminal': len(terminal) == 1
        and terminal[0]['status'] != 'completed',
        'actual_reason_preserved': result['state'].get('last_error') == message,
        'actual_code_preserved': result['state'].get('last_error_code') == code,
        'original_operation_cancelled': result['requests'][index]['cancelled'],
    }
    if terminal:
        checks['terminal_reason_preserved'] = terminal[0].get('message') == message
        # Code travels through the declared native state; terminal JSON needs no new field.
        checks['original_full_binding'] = all(
            terminal[0].get(key) == request[key]
            for key in ('connection_id', 'turn_id', 'request_id')
        )
    assert all(checks.values()), (
        'I3/I13: actual feed/finish refusal keeps its original safe bounded code/reason '
        'through native state and matching failure terminal: ' + str(checks)
    )


@pytest.mark.parametrize('case', CASES)
def test_real_vm_failure_card_preserves_parser_diagnostic_without_replacing_its_code(
    vm, signer, case
):
    code, message = parser_refusal(case)
    component.authenticate(vm, signer)
    index = component.begin(vm, 'Independent safe diagnostic card check')
    component.headers(vm, index)
    original = vm.last['vm']['project']
    deliver(vm, index, case)
    found = [
        row
        for row in vm.last['vm']['messages']
        if row['payload'].get('type') == 'provider_failure'
    ]
    checks = {
        'one_visible_failure_card': len(found) == 1,
        'accepted_project_preserved': vm.last['vm']['project'] == original,
    }
    if found:
        payload = found[0]['payload']
        checks.update({
            'original_safe_message': payload.get('message') == message,
            'original_code_not_replaced_by_interrupted': payload.get('code') == code,
            'not_a_success': found[0]['status'] != 'completed',
            'bounded_public_reason': len(payload.get('message', '').encode()) <= ERROR_BYTES,
            'no_private_input_echo': PRIVATE_MARKER not in str(found[0]),
            'full_original_scope_present': all(
                payload.get(k) for k in ('connection_id', 'turn_id', 'request_id')
            ),
        })
    checks['complete_visible_failure_persisted'] = (
        vm.command('archive')['reply']['rows'] == vm.last['vm']['messages']
    )
    assert all(checks.values()), (
        'I3/I13: actual original-bound parser failure survives the real VM/archive card '
        'without generic code/message substitution or private payload disclosure: ' + str(checks)
    )
