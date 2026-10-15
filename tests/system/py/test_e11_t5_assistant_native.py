"""Offline SIWC conformance through the real native connection, never live entitlement proof.

References: official OpenAI SIWC sign-in, accounts/sessions, token-reference and models/inference
pages acquired 2026-10-14; hashes in tests/fixtures/assistant/provider-contracts.json. Synthetic
RSA keys and tokens are created in pytest scratch only. No default credential store is read.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import select
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[3]
AUTH = 'https://auth.openai.com'
API = 'https://api.openai.com/v1'
WALL = 1_800_000_000
CLIENT = 'oaiapp_independent_fixture'
SUBJECT = 'independent-subject'
SCOPES = 'openid profile email offline_access resource.invoke chatgpt.tokens.use.direct'


def b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode()


@pytest.fixture(scope='module')
def signer(tmp_path_factory):
    folder = tmp_path_factory.mktemp('synthetic-rsa')
    private = folder / 'private.pem'
    openssl = Path(sys.executable).with_name('openssl')
    assert openssl.is_file(), (
        'I12: the locked interpreter environment supplies its independent OpenSSL signer'
    )
    result = subprocess.run(
        [
            str(openssl),
            'genpkey',
            '-algorithm',
            'RSA',
            '-pkeyopt',
            'rsa_keygen_bits:2048',
            '-pkeyopt',
            'rsa_keygen_pubexp:65537',
            '-out',
            str(private),
        ],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, (
        'I12: the independent OpenSSL signer is available for real JWT verification'
    )
    modulus = (
        subprocess
        .run(
            [str(openssl), 'rsa', '-in', str(private), '-noout', '-modulus'],
            capture_output=True,
            timeout=2,
            check=True,
        )
        .stdout.decode()
        .strip()
        .split('=', 1)[1]
    )
    jwks = {
        'keys': [
            {
                'kty': 'RSA',
                'kid': 'independent-key',
                'alg': 'RS256',
                'use': 'sig',
                'n': b64(bytes.fromhex(modulus)),
                'e': b64((65537).to_bytes(3, 'big')),
            }
        ]
    }

    def sign(claims):
        header = {'alg': 'RS256', 'kid': 'independent-key', 'typ': 'JWT'}
        unsigned = (
            b64(json.dumps(header, separators=(',', ':')).encode())
            + '.'
            + b64(json.dumps(claims, separators=(',', ':')).encode())
        ).encode()
        signed = subprocess.run(
            [str(openssl), 'dgst', '-sha256', '-sign', str(private)],
            input=unsigned,
            capture_output=True,
            timeout=2,
            check=True,
        ).stdout
        return unsigned.decode() + '.' + b64(signed)

    return sign, jwks


class Native:
    def __init__(self, binary, reply_timeout=1.0):
        self.process = subprocess.Popen(
            [str(binary)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
        )
        self.reply_timeout = reply_timeout
        self.last = None
        self.handled = set()
        self.jwt = None
        self.jwks = None
        self.scope = SCOPES
        self.catalog = {
            'models': [
                {
                    'slug': 'gpt-6.1-sol',
                    'display_name': 'Offline fixture',
                    'visibility': 'list',
                }
            ]
        }

    def command(self, op, **fields):
        self.process.stdin.write(json.dumps({'op': op, **fields}, ensure_ascii=False) + '\n')
        self.process.stdin.flush()
        readable, _, _ = select.select([self.process.stdout], [], [], self.reply_timeout)
        assert readable, (
            'I12/I13: real native service actions return bounded replies on the event-loop owner'
        )
        line = self.process.stdout.readline()
        assert line, (
            'I12/I13: the real native connection survives each adversarial service callback'
        )
        self.last = json.loads(line)
        assert 'host_error' not in self.last, (
            'I12/I13: dependency failures are caught by the production native boundary'
        )
        return self.last

    def respond(self, index, body, *, status=200):
        self.command(
            'headers', index=index, status=status, headers=[['Content-Type', 'application/json']]
        )
        if body is not None:
            raw = json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode()
            self.command('data', index=index, base64=base64.b64encode(raw).decode())
        return self.command('finish', index=index, failure=0)

    def automatic(self):
        for _ in range(16):
            pending = [
                (i, r) for i, r in enumerate(self.last['requests']) if i not in self.handled
            ]
            if not pending:
                return self.last
            index, request = pending[0]
            self.handled.add(index)
            url = request['url']
            if url == AUTH + '/.well-known/openid-configuration':
                self.respond(
                    index,
                    {
                        'issuer': AUTH,
                        'authorization_endpoint': AUTH + '/api/accounts/authorize',
                        'token_endpoint': AUTH + '/api/accounts/oauth/token',
                        'jwks_uri': AUTH + '/independent-jwks',
                        'revocation_endpoint': AUTH + '/independent-revoke',
                    },
                )
            elif url == AUTH + '/independent-jwks':
                self.respond(index, self.jwks)
            elif url == AUTH + '/api/accounts/oauth/token' and self.jwt:
                self.respond(
                    index,
                    {
                        'access_token': 'synthetic-access-v1',
                        'refresh_token': 'synthetic-refresh-v1',
                        'id_token': self.jwt,
                        'token_type': 'Bearer',
                        'expires_in': 3600,
                        'earliest_refresh_at': WALL + 3500,
                        'scope': self.scope,
                    },
                )
            elif url == API + '/models':
                self.respond(index, self.catalog)
            else:
                self.handled.remove(index)
                return self.last
        pytest.fail(
            'I12: a finite canonical sign-in does not recurse into unbounded native requests'
        )

    def begin(self):
        self.command('sign_in')
        self.automatic()
        assert self.last['browsers'], (
            'I12: real sign-in opens the canonical authorization URL '
            'through its browser dependency'
        )
        url = urlsplit(self.last['browsers'][-1])
        assert (
            url.scheme == 'https'
            and url.netloc == 'auth.openai.com'
            and url.path == '/api/accounts/authorize'
        ), 'I12: sign-in chooses only the official canonical authorization endpoint'
        return {key: values[0] for key, values in parse_qs(url.query).items()}

    def authenticate(self, signer, *, claims_patch=None, scopes=SCOPES, corrupt=False):
        sign, self.jwks = signer
        query = self.begin()
        claims = {
            'iss': AUTH,
            'aud': CLIENT,
            'sub': SUBJECT,
            'nonce': query['nonce'],
            'iat': WALL,
            'exp': WALL + 3600,
            'email': 'synthetic@example.invalid',
            **(claims_patch or {}),
        }
        self.jwt = sign(claims)
        if corrupt:
            pieces = self.jwt.split('.')
            signature = bytearray(
                base64.urlsafe_b64decode(pieces[2] + '=' * (-len(pieces[2]) % 4))
            )
            signature[0] ^= 1
            self.jwt = '.'.join([*pieces[:2], b64(signature)])
        self.scope = scopes
        self.command(
            'callback',
            query={'code': 'synthetic-code', 'state': query['state'], 'client_id': CLIENT},
        )
        self.automatic()
        return query

    def ready(self):
        return any(
            event.get('type') == 'connection' and event.get('status') == 'ready'
            for event in self.last['events']
        )

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.process.stdout.close()
        self.process.stderr.close()


@pytest.fixture
def native():
    value = os.environ.get('EDI_ASSISTANT_NATIVE_PROBE')
    binary = (
        Path(value)
        if value
        else ROOT / 'build/assistant-native-tests/assistant_native_contract_probe'
    )
    assert binary.is_file(), (
        'I12/I13: the approved real native dependency constructor/probe must build '
        'before offline behavior is measurable'
    )
    actor = Native(binary)
    actor.command('inspect')
    try:
        yield actor
    finally:
        actor.close()


def test_real_loopback_pkce_verified_jwt_and_catalog_establish_only_synthetic_readiness(
    native, signer
):
    query = native.authenticate(signer)
    assert native.ready(), (
        'I12/I13: a real signed validated identity and direct-use scope '
        'produce a ready native connection'
    )
    assert query['client_id'] == 'dynamic_agent_client', (
        'I12: first registration starts through the provider dynamic-client entrypoint'
    )
    assert query['resource'] == API and query['code_challenge_method'] == 'S256', (
        'I12: authorization binds the official resource and SHA-256 PKCE'
    )
    callback = urlsplit(query['redirect_uri'])
    assert (
        callback.scheme == 'http'
        and callback.hostname == '127.0.0.1'
        and callback.path == '/auth/callback'
    ), 'I12: the real callback listener uses literal loopback with the registered callback path'
    token = next(
        r for r in native.last['requests'] if r['url'] == AUTH + '/api/accounts/oauth/token'
    )
    form = {k: v[0] for k, v in parse_qs(token['body']).items()}
    assert form['client_id'] == CLIENT and form['redirect_uri'] == query['redirect_uri'], (
        'I12: code exchange uses the issued client and exact attempt callback URI'
    )
    assert (
        b64(hashlib.sha256(form['code_verifier'].encode()).digest()) == query['code_challenge']
    ), 'I12: the exchanged PKCE verifier matches the independently hashed browser challenge'
    assert not any(
        secret in json.dumps(native.last['state']) + json.dumps(native.last['events'])
        for secret in ['synthetic-access-v1', 'synthetic-refresh-v1', native.jwt]
    ), 'I12: public native state/events expose no fixture credential material'


@pytest.mark.parametrize(
    'patch',
    [
        {'iss': 'https://wrong.invalid'},
        {'aud': 'other-client'},
        {'nonce': 'wrong-nonce'},
        {'exp': WALL - 1},
        {'sub': ''},
    ],
    ids=['issuer', 'audience', 'nonce', 'expiry', 'subject'],
)
def test_real_verifier_rejects_invalid_identity_claims_without_saving_grant(native, signer, patch):
    native.authenticate(signer, claims_patch=patch)
    assert not native.ready(), (
        'I12: a signed token with invalid bound identity claims never establishes readiness'
    )
    assert not any(r['key'].startswith('2:') for r in native.last['records']), (
        'I12: invalid identity claims persist no credential record'
    )


@pytest.mark.parametrize('failure', ['signature', 'scope'])
def test_real_signature_and_direct_use_scope_are_both_required(native, signer, failure):
    native.authenticate(
        signer,
        corrupt=failure == 'signature',
        scopes='openid profile email' if failure == 'scope' else SCOPES,
    )
    assert not native.ready(), (
        'I12/I13: invalid signature or absent direct-use grant cannot authorize model access'
    )
    assert not any(r['url'] == API + '/models' for r in native.last['requests']), (
        'I12/I13: denied identity/grant sends no model access request'
    )


@pytest.mark.parametrize(
    'patch',
    [{'state': 'foreign-state'}, {'client_id': ''}, {'error': 'access_denied'}],
    ids=['state', 'missing-issued-client', 'denied'],
)
def test_callback_refusal_never_exchanges_a_code(native, patch):
    query = native.begin()
    native.command(
        'callback',
        query={'state': query['state'], 'code': 'synthetic-code', 'client_id': CLIENT, **patch},
    )
    assert not any(
        r['url'] == AUTH + '/api/accounts/oauth/token' for r in native.last['requests']
    ), 'I12: callback state/client/error refusal exchanges no authorization code'
    assert not native.ready(), (
        'I12: browser callback success alone never establishes a native connection'
    )


@pytest.mark.parametrize(
    'failure',
    [
        'request-null',
        'request-throw',
        'browser',
        'browser-throw',
        'read',
        'read-throw',
        'write',
        'write-throw',
        'list',
        'list-throw',
    ],
)
def test_service_failure_is_caught_and_does_not_fabricate_a_connection(native, signer, failure):
    native.command('fail', value=failure)
    observed = len(native.last['services'])
    if failure.startswith(('read', 'list')):
        native.command('recreate')
    if failure.startswith('write'):
        native.authenticate(signer)
    else:
        native.command('sign_in')
        native.automatic()
    result = native.last
    service = failure.split('-', 1)[0]
    assert service in result['services'][observed:], (
        'I12: each dependency fault control actually reaches its named real native service'
    )
    assert not native.ready(), 'I12: dependency refusal/exception never fabricates readiness'
    assert result['state'].get('last_error') or result['reply'].get('ok') is False, (
        'I12: a reached dependency failure remains a visible refusal rather than silent success'
    )
    assert 'synthetic-sensitive-service-body' not in json.dumps(result['state']) + json.dumps(
        result['events']
    ), 'I12: dependency exceptions are sanitized before public projection'


def pending_request(native):
    query = native.begin()
    native.command(
        'callback', query={'code': 'synthetic-code', 'state': query['state'], 'client_id': CLIENT}
    )
    pending = [i for i in range(len(native.last['requests'])) if i not in native.handled]
    assert pending, 'I12: a valid callback begins a real canonical HTTP exchange'
    return pending[-1]


@pytest.mark.parametrize(
    'sequence',
    [
        'data-before-headers',
        'repeated-headers',
        'oversize-body',
        'oversize-headers',
        'header-count',
    ],
)
def test_native_transport_enforces_order_and_aggregate_bounds(native, sequence):
    index = pending_request(native)
    if sequence != 'data-before-headers':
        headers = [['Content-Type', 'application/json']]
        if sequence == 'oversize-headers':
            headers.append(['X-Witness', 'x' * 16384])
        if sequence == 'header-count':
            headers.extend([['X-' + str(i), 'v'] for i in range(64)])
        native.command('headers', index=index, status=200, headers=headers)
    if sequence == 'repeated-headers':
        native.command('headers', index=index, status=200, headers=[])
    elif sequence == 'data-before-headers':
        native.command('data', index=index, base64=base64.b64encode(b'{').decode())
    elif sequence == 'oversize-body':
        assert native.last['requests'][index]['body_limit'] == 1048576, (
            'I12: authentication JSON operations declare the approved one-MiB receive limit'
        )
        prefix = b'{"padding":"' + b'x' * (65536 - len(b'{"padding":"'))
        native.command('data', index=index, base64=base64.b64encode(prefix).decode())
        for _ in range(15):
            native.command('data', index=index, base64=base64.b64encode(b'x' * 65536).decode())
        assert not native.last['requests'][index]['cancelled'], (
            'I12: an incomplete valid JSON prefix at the inclusive body cap '
            'awaits more input instead of premature parsing'
        )
        native.command('data', index=index, base64=base64.b64encode(b'x').decode())
    result = native.command('inspect')
    assert result['requests'][index]['cancelled'], (
        'I12/I13: malformed or over-budget HTTP input cancels its owning operation before EOF'
    )
    assert not native.ready(), (
        'I12: invalid HTTP callback phases or quotas cannot authenticate a connection'
    )
    assert result['state'].get('last_error'), (
        'I12/I13: native transport refusal is visible through its sanitized bounded state error'
    )


@pytest.mark.parametrize('ending', ['sign-out', 'destroy'])
def test_late_http_callbacks_after_teardown_cannot_touch_records_or_reconnect(native, ending):
    index = pending_request(native)
    native.command('sign_out' if ending == 'sign-out' else 'destroy')
    records = native.last['records']
    events = native.last['events']
    native.respond(index, {'issuer': AUTH, 'jwks_uri': AUTH + '/independent-jwks'})
    assert native.last['records'] == records and native.last['events'] == events, (
        'I12/I13: stale operation callbacks after revocation/destruction are inert'
    )


def test_native_http_and_sign_in_deadlines_use_injected_monotonic_clock(native):
    index = pending_request(native)
    result = native.command('advance', seconds=0, milliseconds=30000)
    assert result['requests'][index]['cancelled'], (
        'I12: the inclusive HTTP deadline cancels outstanding authentication work'
    )
    assert not native.ready() and result['state'].get('last_error'), (
        'I12: deadline expiry is a visible refusal rather than successful sign-in'
    )


@pytest.mark.parametrize('failure', ['network', 'erase'])
def test_signout_preserves_mapping_and_reports_unconfirmed_remote_or_local_erasure(
    native, signer, failure
):
    native.authenticate(signer)
    assert native.ready(), 'I12: sign-out fixture first reaches real verified readiness'
    registration = [r for r in native.last['records'] if r['key'].startswith('1:')]
    if failure == 'erase':
        native.command('fail', value='erase')
    native.command('sign_out')
    native.automatic()
    pending = [(i, r) for i, r in enumerate(native.last['requests']) if i not in native.handled]
    assert pending and pending[-1][1]['url'] == AUTH + '/independent-revoke', (
        'I12: sign-out attempts the validated metadata revocation endpoint'
    )
    index, request = pending[-1]
    form = parse_qs(request['body'])
    assert form.get('token') == ['synthetic-refresh-v1'] and form.get('client_id') == [CLIENT], (
        'I12: revocation binds the renewable token to its issued client registration'
    )
    if failure == 'network':
        native.command('finish', index=index, failure=4)
    else:
        native.respond(index, None)
    if failure == 'network':
        native.command('advance', seconds=0, milliseconds=10000)
    assert [r for r in native.last['records'] if r['key'].startswith('1:')] == registration, (
        'I12: sign-out preserves the nonsecret account/client registration'
    )
    assert native.last['state'].get('last_error'), (
        'I12: unconfirmed revocation or failed local erasure is disclosed '
        'instead of claiming complete teardown'
    )


def provider_request(native, *, request_id='request-one', history=None):
    ready = [
        e
        for e in native.last['events']
        if e.get('type') == 'connection' and e.get('status') == 'ready'
    ][-1]
    return {
        'schema': 'edi.assistant/1',
        'type': 'request',
        'connection_id': ready['connection_id'],
        'turn_id': 'turn-one',
        'request_id': request_id,
        'model': 'gpt-6.1-sol',
        'text': 'Inspect PbSO₄ — Ångström 🧪',
        'attachments': [],
        'context': {
            'schema': 'edi.assistant.context/1',
            'project': {
                'id': 'project-one',
                'revision': '1',
                'name': 'Displayed source',
                'fitting_mode': 'single',
            },
            'parameters': [],
            'diagnostics': [],
        },
        'history': history
        or [{'type': 'message', 'role': 'user', 'text': 'Inspect PbSO₄ — Ångström 🧪'}],
        'tools': [
            {
                'name': 'inspect_project',
                'description': 'Inspect displayed source',
                'input_schema': {
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
            }
        ],
    }


def start_inference(native, *, tools=None):
    request = provider_request(native)
    if tools is not None:
        request['tools'] = tools
    sent = native.command('send', payload=request)
    assert sent['reply']['ok'], (
        'I13: verified offline readiness admits a real native inference request'
    )
    index = len(sent['requests']) - 1
    outgoing = sent['requests'][index]
    assert outgoing['url'] == API + '/responses' and outgoing['method'] == 'POST', (
        'I13: subscription inference uses the official Responses API endpoint'
    )
    body = json.loads(outgoing['body'])
    assert body.get('store') is False and body.get('stream') is True, (
        'I13: each subscription inference is explicitly stateless and streamed'
    )
    native.command(
        'headers', index=index, status=200, headers=[['Content-Type', 'text/event-stream']]
    )
    return index, request


def stream(native, index, events, *, width=65536):
    wire = ''.join(
        'data: ' + json.dumps(event, ensure_ascii=False, separators=(',', ':')) + '\n\n'
        for event in events
    ).encode()
    for offset in range(0, len(wire), width):
        native.command(
            'data', index=index, base64=base64.b64encode(wire[offset : offset + width]).decode()
        )
    return native.command('finish', index=index, failure=0)


def objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)


@pytest.mark.parametrize('status', ['failed', 'incomplete'])
def test_successful_http_with_streamed_failure_is_visible_and_never_completed(
    native, signer, status
):
    native.authenticate(signer)
    assert native.ready(), (
        'I13: streamed failure control begins from a verified synthetic connection'
    )
    index, request = start_inference(native)
    result = stream(
        native,
        index,
        [
            {'type': 'response.output_text.delta', 'delta': 'Public partial answer Å'},
            {
                'type': 'response.' + status,
                'response': {
                    'id': 'response-one',
                    'status': status,
                    'error': {
                        'code': 'subscription_sharing_usage_limit_exceeded',
                        'message': 'Fixture limit reached',
                    },
                },
            },
        ],
        width=3,
    )
    terminal = [
        e
        for e in result['events']
        if e.get('type') == 'turn_finished' and e.get('request_id') == request['request_id']
    ]
    assert terminal and terminal[-1]['status'] != 'completed', (
        'I13: successful transport cannot relabel a provider failed/incomplete '
        'terminal as completed'
    )
    assert result['state'].get('last_error'), (
        'I13: a streamed usage/refusal failure remains visible after HTTP success'
    )


def test_stateless_continuation_preserves_original_encrypted_reasoning_and_arguments(
    native, signer
):
    native.authenticate(signer)
    assert native.ready(), 'I13: stateless replay control begins from verified synthetic readiness'
    index, request = start_inference(
        native,
        tools=[
            {
                'name': 'set_parameters',
                'description': 'Set explicitly approved scientific scalar values',
                'input_schema': {
                    'type': 'object',
                    'properties': {
                        'plan_id': {'type': 'string'},
                        'values': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'path': {'type': 'string'},
                                    'value': {'type': 'number'},
                                },
                                'required': ['path', 'value'],
                                'additionalProperties': False,
                            },
                        },
                    },
                    'required': ['plan_id', 'values'],
                    'additionalProperties': False,
                },
            }
        ],
    )
    original_arguments = (
        '{ "plan_id" : "opaque-plan-Å🧪", "values" : '
        '[{"path":"structure.cell.length_a","value":4.37}] }'
    )
    reasoning = {
        'id': 'reasoning-one',
        'type': 'reasoning',
        'summary': [],
        'encrypted_content': 'opaque-encrypted-fixture',
    }
    call = {
        'id': 'function-one',
        'type': 'function_call',
        'call_id': 'provider-call-one',
        'name': 'set_parameters',
        'arguments': original_arguments,
        'status': 'completed',
    }
    stream(
        native,
        index,
        [
            {
                'type': 'response.output_item.added',
                'output_index': 0,
                'item': {**reasoning, 'status': 'in_progress'},
            },
            {'type': 'response.output_item.done', 'output_index': 0, 'item': reasoning},
            {
                'type': 'response.output_item.added',
                'output_index': 1,
                'item': {**call, 'arguments': '', 'status': 'in_progress'},
            },
            {
                'type': 'response.function_call_arguments.done',
                'output_index': 1,
                'item_id': call['id'],
                'arguments': original_arguments,
            },
            {'type': 'response.output_item.done', 'output_index': 1, 'item': call},
            {
                'type': 'response.completed',
                'response': {
                    'id': 'response-one',
                    'status': 'completed',
                    'output': [reasoning, call],
                },
            },
        ],
        width=7,
    )
    # Model the documented core domain projection after an unapproved-tool refusal.
    # Native replay must retain provider items even when core denies the operation.
    history = [
        *request['history'],
        {
            'type': 'tool_call',
            'call_id': call['call_id'],
            'name': call['name'],
            'arguments': {'values': [{'path': 'structure.cell.length_a', 'value': 4.37}]},
        },
        {
            'type': 'tool_result',
            'call_id': call['call_id'],
            'ok': False,
            'code': 'edi.assistant.approval_required',
            'result': {'message': 'No approved plan grants this scalar operation'},
        },
    ]
    sent = native.command(
        'send', payload=provider_request(native, request_id='request-two', history=history)
    )
    assert sent['reply']['ok'], (
        'I13: a correlated refused tool result can continue a stateless native conversation'
    )
    body = json.loads(sent['requests'][-1]['body'])
    retained = list(objects(body.get('input')))
    assert any(
        v.get('type') == 'reasoning'
        and v.get('encrypted_content') == reasoning['encrypted_content']
        for v in retained
    ), 'I13: stateless continuation retains the original opaque encrypted reasoning item'
    assert any(
        v.get('type') == 'function_call'
        and v.get('arguments') == original_arguments
        and v.get('call_id') == call['call_id']
        for v in retained
    ), (
        'I3/I13: wire continuation preserves the exact original function '
        'arguments including plan ID and Unicode'
    )
    assert any(
        v.get('type') == 'function_call_output' and v.get('call_id') == call['call_id']
        for v in retained
    ), (
        'I13: original provider items and the real correlated tool output '
        'coexist in the next request'
    )


def test_signout_then_reauthorization_reuses_issued_client_and_stable_host(native, signer):
    first = native.authenticate(signer)
    assert native.ready(), (
        'I12: registration reuse control begins from verified synthetic readiness'
    )
    native.command('sign_out')
    native.automatic()
    pending = [i for i in range(len(native.last['requests'])) if i not in native.handled]
    assert pending, 'I12: sign-out starts renewal-session revocation before credential erasure'
    native.respond(pending[-1], None)
    native.handled.add(pending[-1])
    registrations = [
        r['key'].split(':', 1)[1] for r in native.last['records'] if r['key'].startswith('1:')
    ]
    assert len(registrations) == 1, (
        'I12: completed sign-out retains the issued account/client mapping'
    )
    native.command('connect_saved', id=registrations[0])
    native.automatic()
    query = {k: v[0] for k, v in parse_qs(urlsplit(native.last['browsers'][-1]).query).items()}
    assert (
        query['client_id'] == CLIENT and query['ext_agent_host_id'] == first['ext_agent_host_id']
    ), 'I12: reauthorization preserves issued client identity and stable host after sign-out'
    assert 'agent_name_hint' not in query and 'id_token_hint' not in query, (
        'I12: returning registration omits first-registration metadata and erased token hints'
    )


def test_refresh_is_serial_and_late_rotation_cannot_resurrect_signed_out_account(native, signer):
    native.authenticate(signer)
    assert native.ready(), 'I12: refresh control begins from verified synthetic readiness'
    before = len(native.last['requests'])
    native.command('advance', seconds=3600, milliseconds=3600000)
    request = provider_request(native)
    native.command('send', payload=request)
    native.command('send', payload={**request, 'request_id': 'request-two'})
    refreshes = [
        (i, r)
        for i, r in enumerate(native.last['requests'][before:], start=before)
        if r['url'] == AUTH + '/api/accounts/oauth/token'
        and parse_qs(r['body']).get('grant_type') == ['refresh_token']
    ]
    assert len(refreshes) == 1, (
        'I12: concurrent inference/renewal demand owns only one rotating refresh '
        'request per session'
    )
    index, request = refreshes[0]
    form = parse_qs(request['body'])
    assert (
        form.get('client_id') == [CLIENT]
        and form.get('refresh_token') == ['synthetic-refresh-v1']
        and 'scope' not in form
    ), 'I12: renewal uses the issued client/latest refresh grant without silently changing scope'
    native.command('sign_out')
    protected = native.last['records']
    event_count = len(native.last['events'])
    native.respond(
        index,
        {
            'access_token': 'synthetic-access-v2',
            'refresh_token': 'synthetic-refresh-v2',
            'token_type': 'Bearer',
            'expires_in': 3600,
            'scope': SCOPES,
        },
    )
    assert native.last['records'] == protected, (
        'I12: a superseded rotating refresh completion cannot rewrite signed-out credentials'
    )
    assert not any(e.get('status') == 'ready' for e in native.last['events'][event_count:]), (
        'I12: late credential rotation cannot reconnect a torn-down account'
    )


def test_fragmented_model_refusal_is_public_and_never_an_empty_success(native, signer):
    native.authenticate(signer)
    assert native.ready(), 'I13: refusal control begins from verified synthetic readiness'
    index, _ = start_inference(native)
    refusal = 'I cannot perform this requested action — PbSO₄ 🧪'
    result = stream(
        native,
        index,
        [
            {
                'type': 'response.refusal.delta',
                'item_id': 'message-one',
                'output_index': 0,
                'content_index': 0,
                'delta': refusal,
                'sequence_number': 1,
            },
            {
                'type': 'response.refusal.done',
                'item_id': 'message-one',
                'output_index': 0,
                'content_index': 0,
                'refusal': refusal,
                'sequence_number': 2,
            },
            {
                'type': 'response.completed',
                'response': {
                    'id': 'response-one',
                    'status': 'completed',
                    'output': [
                        {
                            'type': 'message',
                            'id': 'message-one',
                            'role': 'assistant',
                            'status': 'completed',
                            'content': [{'type': 'refusal', 'refusal': refusal}],
                        }
                    ],
                },
            },
        ],
        width=1,
    )
    public = json.dumps(result['events'], ensure_ascii=False) + json.dumps(
        result['state'], ensure_ascii=False
    )
    assert refusal in public, (
        'I13: a real provider refusal remains visible public content or an '
        'explicit refusal outcome after arbitrary UTF-8 fragmentation'
    )


@pytest.mark.parametrize('index', range(8))
def test_missing_native_dependency_refuses_before_any_external_service(native, index):
    result = native.command('missing_dependency', index=index)
    assert result['reply']['rejected'], (
        'I12: every required native service function is validated at construction'
    )
    assert result['reply']['service_calls'] == 0, (
        'I12: invalid native dependency bundles cause no '
        'browser/store/network/clock I/O or default fallback'
    )


def test_catalog_intersects_account_order_with_exact_reviewed_capabilities(native, signer):
    native.catalog = {
        'models': [
            {'slug': 'future-unknown', 'display_name': 'Future', 'visibility': 'list'},
            {
                'slug': 'gpt-6.1-sol',
                'display_name': 'Sol',
                'visibility': 'list',
                'supported_reasoning_efforts': [
                    {'reasoning_effort': 'invented', 'display_name': '<b>bad</b>'}
                ],
            },
            {'slug': 'gpt-6-sol', 'display_name': 'Earlier Sol', 'visibility': 'list'},
            {
                'slug': 'gpt-6.1-sol-snapshot',
                'display_name': 'Unknown snapshot',
                'visibility': 'list',
            },
            {'slug': 'hidden', 'display_name': 'Hidden', 'visibility': 'hidden'},
        ]
    }
    native.authenticate(signer)
    assert native.ready(), 'I13: eligible catalog entries establish synthetic verified readiness'
    models = native.last['state']['models']
    assert [model['id'] for model in models] == [
        'future-unknown',
        'gpt-6.1-sol',
        'gpt-6-sol',
        'gpt-6.1-sol-snapshot',
    ], 'I13: visible account order is preserved without inventing snapshot capabilities'
    assert [model['available'] for model in models] == [False, True, True, False], (
        'I13: only exact reviewed model IDs are available for actual inference'
    )
    assert models[1]['efforts'] == ['low', 'medium', 'high', 'xhigh', 'max'], (
        'I13: undocumented provider effort metadata cannot override the reviewed Sol mapping'
    )
    assert models[2]['efforts'] == ['none', 'low', 'medium', 'high', 'xhigh', 'max'], (
        'I13: explicit none remains distinct from provider-default omission'
    )
    assert all(not model['efforts'] for model in (models[0], models[3])), (
        'I13: unknown visible IDs remain explanatory unavailable entries with no guessed efforts'
    )


@pytest.mark.parametrize('kind', ['unknown-only', 'duplicate', 'malformed', 'over-cap'])
def test_no_eligible_or_malformed_catalog_never_silently_becomes_ready(native, signer, kind):
    model = {'slug': 'gpt-6.1-sol', 'display_name': 'Sol', 'visibility': 'list'}
    catalogs = {
        'unknown-only': {'models': [{**model, 'slug': 'gpt-6.1-sol-unknown'}]},
        'duplicate': {'models': [model, model]},
        'malformed': {'models': [{**model, 'slug': 7}]},
        'over-cap': {
            'models': [model]
            + [
                {'slug': 'hidden-' + str(index), 'display_name': 'Hidden', 'visibility': 'hidden'}
                for index in range(128)
            ]
        },
    }
    native.catalog = catalogs[kind]
    native.authenticate(signer)
    assert not native.ready() and native.last['state'].get('last_error'), (
        'I13: missing capabilities, malformed identity and aggregate catalog overflow '
        'fail closed with a visible prerequisite rather than a fabricated default'
    )
