"""Real fit termination after transport retirement and presentation failure."""

import json

import pytest

from tests.integration.app.test_assistant_candidate_boundaries import call, record_receipts
from tests.integration.app.test_assistant_misfit_workflow import actor_in, replies, send
from tests.integration.app.test_assistant_review_receipts import fit_record
from tests.integration.app.test_assistant_trial_ownership import OTHER_PATH, parameter_edit
from tests.system.py import test_e11_t5_dev_native_integration as native


def observe_fit_fault(folder, endpoint):
    actor = actor_in(folder, [[call('run_fit', 'fit-a')]])
    try:
        send(actor, 1)
        accepted = fit_record(actor)
        actor.append_turn([parameter_edit('setup-b', OTHER_PATH, 12.875)])
        send(actor, 2)
        candidate = fit_record(actor)
        actor.command('arm_fit_boundary_fault', mode=endpoint)
        actor.append_turn([call('run_fit', 'fit-b')])
        assert native.qml(actor, 'Session.assistant.submitDraft("Fit the provisional setup.")'), (
            'Required: the ordinary assistant owner accepts fit B.'
        )
        actor.until(
            lambda row: (
                not row['ui']['can_cancel']
                and actor.command('fit_boundary_fault')['reply']['ended'] == 1
            ),
            seconds=20,
        )
        fault = actor.command('fit_boundary_fault')['reply']
        sent = map(json.loads, actor.trace.with_suffix('.sent.jsonl').read_text().splitlines())
        (identity,) = (row['id'] for row in sent if row.get('params', {}).get('callId') == 'fit-b')
        receipt_count = sum(response.get('id') == identity for response in actor.responses())
        return record_receipts(
            actor,
            'fit-settlement.json',
            {
                'accepted': accepted,
                'candidate': candidate,
                'restored': fit_record(actor),
                'fault': fault,
                'receipt_count': receipt_count,
                'wire': replies(actor),
                'connected': actor.last['ui']['connected'],
            },
        )
    finally:
        actor.close()


@pytest.fixture(scope='module')
def faults(tmp_path_factory):
    root = tmp_path_factory.mktemp('fit-settlement')
    return {name: observe_fit_fault(root / name, name) for name in ('disconnect', 'presentation')}


@pytest.mark.parametrize('endpoint', ['disconnect', 'presentation'])
def test_fit_callback_preserves_accepted_state_across_a_real_failure(faults, endpoint):
    result = faults[endpoint]
    fault = result['fault']
    assert (
        result['wire']['fit-a']['value']['adopted'] and result['candidate'] != result['accepted']
    ), 'Required: fit A was adopted and B had a distinct scientific setup.'
    assert (fault['started'], fault['ended']) == (1, 1), (
        'Required: the same admitted Fit owner reaches a single terminal transition.'
    )
    assert result['receipt_count'] <= 1, (
        'Required: retirement or presentation failure cannot settle the provider call twice.'
    )
    if endpoint == 'disconnect':
        assert fault['transport_failure'] and fault['running_after_transport_fault'], (
            'Required: the owned transport fails while the native Fit is still running.'
        )
        assert not result['connected'], 'Required: the actual assistant connection retires.'
    else:
        assert fault['finished'] == 1, (
            'Required: the presentation fault is delivered after actual fit adoption.'
        )
        assert not result['wire']['fit-b']['success'], (
            'Required: failed presentation is not reported as a successful B.'
        )
    assert result['restored'] == result['accepted'], (
        'Required: the failed B leaves A as the complete accepted scientific state.'
    )
