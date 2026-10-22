"""Published SIWC admission/stream error evidence, no live account traffic.

https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery
https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference
"""

from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path

import pytest

from tests.fixtures.assistant.diagnostic_streams import PRIVATE_MARKER, sse

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'http_diagnostic_native', ROOT / 'tests/system/py/test_e11_t5_assistant_native.py'
)
services = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(services)
transport = services.native
signer = services.signer


def unopened(transport, tools=None):
    request = services.provider_request(transport)
    if tools is not None:
        request['tools'] = tools
    result = transport.command('send', payload=request)
    assert result['reply']['ok'], (
        'I13/D2: a real native request precedes its first admission headers'
    )
    return len(result['requests']) - 1, request


def evidence(result, request):
    # Scope only public diagnostics, never planted request/response/store receipts.
    return {
        'state': {k: v for k, v in result['state'].items() if k.startswith('last_error')},
        'terminal': [
            e
            for e in result['events']
            if e.get('type') == 'turn_finished' and e.get('request_id') == request['request_id']
        ],
    }


def leaves(value):
    if isinstance(value, dict):
        return [leaf for child in value.values() for leaf in leaves(child)]
    if isinstance(value, list):
        return [leaf for child in value for leaf in leaves(child)]
    return [value]


def keys(value):
    if isinstance(value, dict):
        return set(value) | {k for child in value.values() for k in keys(child)}
    if isinstance(value, list):
        return {k for child in value for k in keys(child)}
    return set()


@pytest.mark.parametrize(
    ('status', 'shape', 'code', 'param'),
    [
        (403, 'detail', None, None),
        (429, 'error', 'subscription_sharing_usage_limit_exceeded', None),
        (400, 'error', 'subscription_sharing_unsupported_capability', 'tools[0].type'),
        (503, 'detail', None, None),
    ],
)
def test_http_admission_preserves_safe_status_shape_code_parameter_and_provider_id(
    transport, signer, status, shape, code, param
):
    transport.authenticate(signer)
    index, request = unopened(transport)
    original_records = transport.last['records']
    request_count = len(transport.last['requests'])
    message = 'Independent bounded admission diagnostic — Å'
    provider_id = 'req-independent-admission-' + str(status)
    body = (
        {'detail': message}
        if shape == 'detail'
        else {
            'error': {
                'code': code,
                'message': message,
                'param': param,
                'type': 'invalid_request_error',
            }
        }
    )
    body['private_note'] = PRIVATE_MARKER
    transport.command(
        'headers',
        index=index,
        status=status,
        headers=[
            ['Content-Type', 'application/json'],
            ['X-Request-Id', provider_id],
            ['X-Unknown-Private-Header', PRIVATE_MARKER],
        ],
    )
    after_headers = transport.last
    transport.command(
        'data',
        index=index,
        base64=base64.b64encode(json.dumps(body, ensure_ascii=False).encode()).decode(),
    )
    result = transport.command('finish', index=index, failure=0)
    diagnostic = evidence(result, request)
    values = leaves(diagnostic)
    strings = [v for v in values if isinstance(v, str)]
    checks = {
        'body_can_be_observed_before_settlement': not after_headers['requests'][index][
            'cancelled'
        ],
        'actual_http_status': status in values,
        'actual_body_shape': shape in keys(diagnostic) or shape in values,
        'bounded_actual_reason': any(message in value for value in strings),
        'provider_http_request_id': provider_id in values,
        'no_private_body_or_header_echo': PRIVATE_MARKER not in json.dumps(diagnostic),
        'no_new_inference_or_auth_loop': len(result['requests']) == request_count,
        'no_tools_dispatched': not any(e.get('type') == 'tool_call' for e in result['events']),
    }
    if code is not None:
        checks['exact_provider_error_code'] = code in values
    if param is not None:
        checks['exact_provider_error_parameter'] = param in values
    if status == 503:
        checks['temporary_failure_preserves_verified_credentials'] = (
            result['records'] == original_records and not result['erasures']
        )
    assert all(checks.values()), (
        'I3/I12/I13/D2: actual bounded admission response preserves safe independent '
        'diagnostic facts and recovery scope without semantic dispatch: ' + str(checks)
    )


@pytest.mark.parametrize(
    'code', ['subscription_sharing_usage_limit_exceeded', 'subscription_sharing_usage_unavailable']
)
def test_published_failed_stream_preserves_server_code_and_reason_after_http_success(
    transport, signer, code
):
    transport.authenticate(signer)
    index, request = services.start_inference(transport)
    message = 'Independent server failure after stream admission — Ö'
    services.stream(
        transport,
        index,
        [
            {
                'type': 'response.created',
                'sequence_number': 0,
                'response': {'id': 'safe-failed-response', 'status': 'in_progress', 'output': []},
            },
            {
                'type': 'response.failed',
                'sequence_number': 1,
                'response': {
                    'id': 'safe-failed-response',
                    'status': 'failed',
                    'output': [],
                    'error': {'code': code, 'message': message},
                },
            },
        ],
    )
    diagnostic = evidence(transport.last, request)
    values = leaves(diagnostic)
    assert code in values and any(isinstance(v, str) and message in v for v in values), (
        'I13/D1/D2: published streamed usage failure keeps exact provider code/reason, '
        'distinct from decoder refusal and successful inference'
    )
    assert diagnostic['terminal'] and all(
        t['status'] != 'completed' for t in diagnostic['terminal']
    ), 'I13: a published response.failed can never become a completed inference'


def test_non200_complete_looking_sse_never_enters_semantic_dispatch(transport, signer):
    transport.authenticate(signer)
    index, request = unopened(
        transport,
        tools=[
            {
                'name': 'inspect_project',
                'description': 'Read-only fixture inspection',
                'input_schema': {
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
            }
        ],
    )
    call = {
        'id': 'rejected-function',
        'type': 'function_call',
        'call_id': 'rejected-call',
        'name': 'inspect_project',
        'arguments': '{}',
        'status': 'completed',
    }
    transport.command(
        'headers', index=index, status=403, headers=[['Content-Type', 'text/event-stream']]
    )
    wire = sse([
        {'type': 'response.output_item.done', 'output_index': 0, 'item': call},
        {
            'type': 'response.completed',
            'response': {'id': 'rejected-response', 'status': 'completed', 'output': [call]},
        },
    ])
    transport.command('data', index=index, base64=base64.b64encode(wire).decode())
    result = transport.command('finish', index=index, failure=0)
    terminal = evidence(result, request)['terminal']
    assert terminal and all(e['status'] != 'completed' for e in terminal), (
        'I13/D2: rejected HTTP admission remains unsuccessful despite complete-looking SSE bytes'
    )
    assert not any(e.get('type') == 'tool_call' for e in result['events']), (
        'I2/I13/D2: bounded error-body retention never enables execution from non200 SSE'
    )
