"""Published returning OAuth callback rule, only independently signed offline accounts.

https://developers.openai.com/siwc/token-sharing-open-source/sign-in#3-handle-the-callback-and-exchange-the-code
No owner callback URL, credential, account or provider request is read.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'reauthorization_native', ROOT / 'tests/system/py/test_e11_t5_assistant_native.py'
)
services = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(services)
transport = services.native
signer = services.signer


def exchanges(actor):
    return [
        row
        for row in actor.last['requests']
        if row['url'] == services.AUTH + '/api/accounts/oauth/token'
        and parse_qs(row['body']).get('grant_type') == ['authorization_code']
    ]


def mappings(actor):
    return {
        row['key']: json.loads(row['bytes'])
        for row in actor.last['records']
        if row['key'].startswith('1:')
    }


def returning(actor, signer):
    original = actor.authenticate(signer)
    assert actor.ready(), (
        'I12: real issued-client registration succeeds before returning callback tests'
    )
    selected = mappings(actor)
    mapping_count = len(selected)
    assert mapping_count == 1, (
        'I12: returning flow selects one genuinely registered fixture account'
    )
    actor.command('sign_out')
    actor.automatic()
    pending = [
        (i, row)
        for i, row in enumerate(actor.last['requests'])
        if i not in actor.handled and row['url'] == services.AUTH + '/independent-revoke'
    ]
    assert len(pending) == 1, (
        'I12: ordinary prior-account sign-out reaches its actual revocation callback'
    )
    actor.respond(pending[0][0], None)
    actor.handled.add(pending[0][0])
    same_mapping = mappings(actor) == selected
    assert same_mapping, 'I12: sign-out retains the exact nonsecret issued-account mapping'
    actor.command('connect_saved', id=next(iter(selected))[2:])
    actor.automatic()
    query = {
        key: values[0]
        for key, values in parse_qs(urlsplit(actor.last['browsers'][-1]).query).items()
    }
    assert (
        query['client_id'] == services.CLIENT
        and query['ext_agent_host_id'] == original['ext_agent_host_id']
    ), 'I12: pending returning attempt uses the selected issued client and original stable host'
    assert query['state'] != original['state'] and query['nonce'] != original['nonce'], (
        'I12: returning attempt has independent fresh state and nonce before callback delivery'
    )
    return query, selected


def prepare_token(actor, signer, query, patch=None):
    sign, actor.jwks = signer
    actor.jwt = sign({
        'iss': services.AUTH,
        'aud': services.CLIENT,
        'sub': services.SUBJECT,
        'nonce': query['nonce'],
        'iat': services.WALL,
        'exp': services.WALL + 3600,
        'email': 'synthetic@example.invalid',
        **(patch or {}),
    })
    actor.scope = services.SCOPES


@pytest.mark.parametrize('provided', [False, True], ids=['omitted', 'matching'])
def test_returning_callback_uses_exact_pending_issued_client_when_optional_id_is_omitted(
    transport, signer, provided
):
    query, selected = returning(transport, signer)
    prepare_token(transport, signer, query)
    count = len(exchanges(transport))
    callback = {'code': 'independent-returning-code', 'state': query['state']}
    if provided:
        callback['client_id'] = services.CLIENT
    transport.command('callback', query=callback)
    transport.automatic()
    after = exchanges(transport)[count:]
    checks = {
        'actual_code_exchange_once': len(after) == 1,
        'verified_returning_readiness': transport.ready(),
        'same_selected_account_mapping': mappings(transport) == selected,
    }
    if after:
        fields = {key: values[0] for key, values in parse_qs(after[0]['body']).items()}
        checks.update({
            'exact_pending_client_not_placeholder': fields['client_id'] == services.CLIENT,
            'same_callback_uri_and_resource': fields['redirect_uri'] == query['redirect_uri']
            and fields['resource'] == 'https://api.openai.com/v1',
            'actual_authorization_code': fields['code'] == callback['code'],
            'fresh_pkce_bound_to_this_pending_attempt': services.b64(
                hashlib.sha256(fields['code_verifier'].encode()).digest()
            )
            == query['code_challenge'],
        })
    assert all(checks.values()), (
        'I12: published optional returning client_id preserves the exact pending verified '
        'registration, code, account and PKCE binding: ' + str(checks)
    )


@pytest.mark.parametrize(
    'supplied',
    ['', 'oaiapp-independent-wrong-client', 'dynamic_agent_client'],
    ids=['empty', 'different', 'placeholder'],
)
def test_supplied_invalid_returning_client_never_replaces_selected_registration(
    transport, signer, supplied
):
    query, selected = returning(transport, signer)
    prepare_token(transport, signer, query)
    count = len(exchanges(transport))
    transport.command(
        'callback',
        query={
            'code': 'independent-rejected-code',
            'state': query['state'],
            'client_id': supplied,
        },
    )
    transport.automatic()
    exchange_count = len(exchanges(transport))
    assert not transport.ready() and exchange_count == count, (
        'I12: explicit empty/different/placeholder returning client is rejected '
        'before token exchange'
    )
    same_mapping = mappings(transport) == selected
    assert same_mapping, (
        'I12: a supplied invalid callback client cannot overwrite the selected account mapping'
    )


@pytest.mark.parametrize(
    'supplied', [None, 'dynamic_agent_client'], ids=['missing', 'placeholder']
)
def test_new_dynamic_registration_requires_an_issued_callback_client(transport, signer, supplied):
    query = transport.begin()
    assert query['client_id'] == 'dynamic_agent_client', (
        'I12: this negative control is actual initial registration, not a '
        'fabricated returning state'
    )
    prepare_token(transport, signer, query)
    count = len(exchanges(transport))
    callback = {'code': 'independent-initial-code', 'state': query['state']}
    if supplied is not None:
        callback['client_id'] = supplied
    transport.command('callback', query=callback)
    transport.automatic()
    exchange_count = len(exchanges(transport))
    assert not transport.ready() and exchange_count == count, (
        'I12: initial dynamic registration never substitutes a missing/placeholder issued client'
    )
    mapping_count = len(mappings(transport))
    assert mapping_count == 0, (
        'I12: incomplete new registration never fabricates an account mapping'
    )


def test_new_dynamic_registration_with_issued_client_remains_a_positive_control(transport, signer):
    transport.authenticate(signer)
    mapping_count = len(mappings(transport))
    assert transport.ready() and mapping_count == 1, (
        'I12: genuine issued callback client, verified JWT and granted scopes '
        'establish initial readiness'
    )


@pytest.mark.parametrize('fault', ['wrong-state', 'missing-code'])
def test_returning_omitted_client_does_not_relax_state_or_authorization_code_guards(
    transport, signer, fault
):
    query, selected = returning(transport, signer)
    prepare_token(transport, signer, query)
    count = len(exchanges(transport))
    callback = {'state': query['state'], 'code': 'independent-guarded-code'}
    if fault == 'wrong-state':
        callback['state'] = 'independent-wrong-state'
    else:
        del callback['code']
    transport.command('callback', query=callback)
    transport.automatic()
    exchange_count = len(exchanges(transport))
    same_mapping = mappings(transport) == selected
    assert not transport.ready() and exchange_count == count and same_mapping, (
        'I12: omitted optional client never bypasses actual state/code validation '
        'or changes the account'
    )


@pytest.mark.parametrize('claim', ['nonce', 'aud', 'sub'])
def test_returning_omitted_client_still_verifies_pending_nonce_client_and_selected_account(
    transport, signer, claim
):
    query, selected = returning(transport, signer)
    patch = {
        'nonce': 'independent-wrong-nonce',
        'aud': 'oaiapp-independent-wrong-audience',
        'sub': 'independent-different-subject',
    }
    prepare_token(transport, signer, query, {claim: patch[claim]})
    count = len(exchanges(transport))
    transport.command(
        'callback', query={'state': query['state'], 'code': 'independent-identity-code'}
    )
    transport.automatic()
    exchange_count = len(exchanges(transport))
    assert exchange_count == count + 1, (
        'I12: omitted-client returning flow actually reaches JWT verification '
        'before identity refusal'
    )
    same_mapping = mappings(transport) == selected
    assert not transport.ready() and same_mapping, (
        'I12: valid signature cannot bypass the pending nonce, issued-client '
        'audience or selected account'
    )
