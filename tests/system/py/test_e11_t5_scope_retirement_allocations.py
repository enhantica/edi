"""V4: qualify the existing one-shot owner allocator at real replacement identity prep.

Selection uses public identity consumption and an independently reached sealed-library
string allocation control, never whether the expected retirement property failed.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'retirement_protocol', ROOT / 'tests/integration/py/test_e11_t5_assistant_protocol.py'
)
protocol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(protocol)
_spec = importlib.util.spec_from_file_location(
    'retirement_questions', ROOT / 'tests/system/py/test_e11_t5_assistant_questions.py'
)
questions = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(questions)


def actor():
    binary = Path(
        os.environ.get(
            'EDI_ASSISTANT_SCOPE_PROBE',
            ROOT / 'build/assistant-core-tests/assistant_scope_retirement_probe',
        )
    )
    assert binary.is_file(), (
        'I10/V4: exact current core and existing fault vehicle link before behavior'
    )
    value = protocol.Host(binary, reply_timeout=5)
    value.start()
    value.approve()
    asked = value.tool('ask_question', questions.arguments(), call_id='retired-question')
    assert asked['reply']['ok'] and asked['retention']['held'] == 1, (
        'I10/V4: real approved scope and accepted question allowance precede retirement'
    )
    value.provider('turn_finished', **value.binding(), status='completed')
    # Fixed finite warmup makes the actual generated representation exceed this kit's SSO.
    for _ in range(32):
        value.command('identity_probe')
    return value


def identity(value):
    return value.command('identity_probe')['reply']


def last_id(value):
    return max(int(text.rsplit('-', 1)[1]) for text in value.values())


def apply(value, route, *, ordinal=0, length=False):
    if route in {'detach', 'new-attach'}:
        return value.command(
            'fault_attach',
            detach=route == 'detach',
            id='' if route == 'detach' else 'new-project',
            ordinal=ordinal,
            length=length,
        )
    payload = protocol.envelope(
        'connection',
        connection_id=('connection-B' if route == 'changed-ready' else 'connection-A'),
        status={'disconnect': 'disconnected', 'expiry': 'expired'}.get(route, 'ready'),
        capabilities=[
            {
                'id': protocol.MODEL,
                'display_name': 'Offline protocol fixture',
                'efforts': ['high'],
                'attachment_types': [],
            }
        ],
    )
    if route == 'malformed':
        payload['capabilities'] = 'invalid required type'
    return value.command('fault_provider', payload=payload, ordinal=ordinal, length=length)


def qualify(route, length):
    # Calibrate ordinary observer consumption instead of assuming an ID offset.
    calibration = actor()
    try:
        before = identity(calibration)
        base = last_id(identity(calibration)) - last_id(before)
        assert base > 0, 'I3/V4: disarmed real observer has measured positive identity consumption'
    finally:
        calibration.close()
    positive = actor()
    try:
        stable = identity(positive)
        suffix = last_id(stable) + 1
        assert 100 <= suffix < 1000, (
            'I3/V4: every qualified trial has the same finite suffix width'
        )
        control = positive.command(
            'identity_string_control', suffix=suffix, ordinal=0, length=length
        )
        expected = 'conversation-' + str(suffix)
        assert control['reply']['value'] == expected, (
            'I3/V4: independent std::string control constructs the exact '
            'observed reset representation'
        )
        assert len(expected.encode()) > control['reply']['inline_capacity'], (
            'I3/V4: observed representation exceeds this actual sealed '
            'standard-library inline capacity'
        )
        assert control['allocation_fault']['seen'] > 0, (
            'I3/V4: constructing this exact reset representation really '
            'allocates in the sealed kit'
        )
        armed = positive.command(
            'identity_string_control', suffix=suffix, ordinal=1, length=length
        )
        assert armed['reply']['threw'] and armed['allocation_fault']['fired'], (
            'I3/V4: the unchanged existing allocator actually reaches that string construction'
        )
        passed = apply(positive, route)
        bound = int(passed['allocation_fault']['seen'])
        assert passed['reply']['ok'] and 0 < bound <= 256, (
            'I3/V4: a successful identical operation supplies a finite measured allocation bound'
        )
        assert last_id(identity(positive)) - last_id(stable) == base + 1, (
            'I3/V4: validated reset generates exactly one identity beyond calibrated observer work'
        )
    finally:
        positive.close()
    for ordinal in range(1, bound + 1):
        current = actor()
        before = identity(current)
        if before != stable:
            current.close()
            pytest.fail('I3/V4: allocation qualification requires stable identities and schedule')
        failed = apply(current, route, ordinal=ordinal, length=length)
        after = identity(current)  # Arm has already disarmed before this ordinary observation.
        consumed = last_id(after) - last_id(before)
        assert consumed in {base, base + 1}, (
            'I3/V4: no unrelated identity producer may run inside the qualification interval'
        )
        if failed['allocation_fault']['fired'] and consumed == base + 1:
            return current, failed
        current.close()
    pytest.fail('I3/V4: exact pre-retirement identity allocation must be reached, not guessed')


@pytest.mark.parametrize('length', [False, True], ids=['bad_alloc', 'length_error'])
@pytest.mark.parametrize(
    'route', ['disconnect', 'expiry', 'changed-ready', 'detach', 'new-attach']
)
def test_pre_retirement_identity_failure_obeys_observed_scope_ownership(route, length):
    value, failed = qualify(route, length)
    try:
        if failed['reply'].get('returned', True):
            protocol.refused(failed, 'resource_exhausted')
        else:
            assert failed['reply']['exception'] == ('length_error' if length else 'bad_alloc'), (
                'I10/V4: thrown public preparation failure is observed distinctly '
                'from a returned refusal'
            )
        if route == 'new-attach':
            assert failed['retention']['held'] == 1 and failed['state']['pending_question_id'], (
                'I10/V4: rejected preparation for a new project preserves the '
                'still-valid old owner'
            )
        else:
            assert (
                not failed['state']['active_turn_id']
                and not failed['state']['pending_question_id']
            ), (
                'I2/I10/V4: already observed retirement fences old authority '
                'before fallible replacement prep'
            )
            assert failed['retention']['held'] == 0 and failed['retention']['destroyed'] == 1, (
                'I10/V4: retirement releases the original actual lease despite '
                'replacement identity failure'
            )
    finally:
        value.close()


@pytest.mark.parametrize('route', ['disconnect', 'expiry', 'changed-ready', 'detach'])
def test_unarmed_valid_retirement_releases_the_actual_owner(route):
    value = actor()
    try:
        before = value.last['snapshot']
        retired = apply(value, route)
        assert retired['reply']['ok'] and retired['retention']['held'] == 0, (
            'I10/V4: ordinary valid scope retirement releases its accepted question role'
        )
        assert retired['snapshot'] == before, (
            'I8/V4: retirement preserves exact accepted scientific state'
        )
    finally:
        value.close()


@pytest.mark.parametrize('route', ['unchanged-ready', 'malformed'])
def test_unchanged_or_rejected_connection_is_distinct_from_observed_retirement(route):
    value = actor()
    try:
        before = identity(value)
        original = value.last['state']['pending_question_id']
        observed = apply(value, route)
        after = identity(value)
        calibration = last_id(after) - last_id(before)
        meter = actor()
        try:
            first = identity(meter)
            ordinary = last_id(identity(meter)) - last_id(first)
        finally:
            meter.close()
        assert calibration == ordinary, (
            'I3/V4: unchanged/rejected notification generates no replacement identity'
        )
        assert (
            observed['retention']['held'] == 1
            and observed['state']['pending_question_id'] == original
        ), (
            'I10/V4: unchanged-ready and rejected malformed admission '
            'preserve the valid old allowance'
        )
        assert observed['reply']['ok'] == (route == 'unchanged-ready'), (
            'I3/V4: malformed admission refuses rather than impersonating an '
            'observed account retirement'
        )
    finally:
        value.close()
