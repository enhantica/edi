"""Accepted scientific state across native candidate retirement boundaries."""

import json

import pytest

from tests.integration.app.test_assistant_candidate_boundaries import (
    TRIAL_PATH,
    call,
    record_receipts,
    setup_trial,
)
from tests.integration.app.test_assistant_misfit_workflow import actor_in, replies, send
from tests.integration.app.test_assistant_review_receipts import fit_record
from tests.system.py import test_e11_t5_dev_native_integration as native

MANUAL_VALUE = 17.125


def manual_value_expression(amount=MANUAL_VALUE):
    return (
        '(function(){const t=Session.project.parameters;'
        'for(let i=0;i<t.count;i++){if(t.text(i,"path")!=='
        + json.dumps(TRIAL_PATH)
        + ')continue;const row=t.item(i,"parameter");const before=row.value;row.value='
        + str(amount)
        + ';return {before:before,value:row.value,error:row.lastError};}return null;})()'
    )


def manual_value_attempt(actor, amount=MANUAL_VALUE):
    return native.qml(actor, manual_value_expression(amount))


def manual_value_edit(actor):
    return manual_value_attempt(actor)['value']


def hold_after_setup(actor, turn, last_call):
    actor.append_turn(turn)
    native._session_configure(actor, final_gate=str(actor.gate))
    actor.request('Prepare a provisional fit with this exact scientific setup.')
    actor.until(lambda row: row['ui']['can_cancel'] and last_call in replies(actor))


def prepare_shape(project):
    # Replace the default polynomial of one bank with four ordinary anchors
    # and retain the other bank's free polynomial parameters for a genuine fit A.
    bank = project / 'experiments/bank.edi'
    text = bank.read_text(encoding='utf-8')
    start = text.index('_background.type')
    end = text.index('loop_', start)
    parameters = text.index('_background.order', end)
    next_loop = text.index('loop_', parameters)
    anchors = (
        '_background.type line-segment\n_background_estimate.mode manual\n\n'
        'loop_\n_background.id\n_background.position\n'
        '_background.intensity\np0 40 4\np1 50 4\np2 61 4\np3 72 4\n\n'
    )
    bank.write_text(text[:start] + anchors + text[next_loop:], encoding='utf-8')
    analysis = project / 'analysis/analysis.edi'
    original = analysis.read_text(encoding='utf-8')
    before_constraint = original.split('loop_\n_constraint.expression')[0]
    analysis.write_text(
        before_constraint.replace(' bank.background.', ' second.background.'),
        encoding='utf-8',
    )


def setup_shape(endpoint):
    if endpoint == 'exclusion':
        return call('edit_experiment', endpoint, experiment='bank', operation='exclusion_append')
    if endpoint == 'background-term':
        return call('estimate_background', endpoint, experiment='bank')
    return call(
        'edit_background',
        endpoint,
        experiment='bank',
        operation='add',
        id='candidate-anchor',
        position=58,
        intensity=7,
        free=False,
    )


def terminal_fit(actor, endpoint, accepted):
    setup = setup_trial(accepted, 'refusal' if endpoint == 'shown-unavailable' else 'stop')
    actor.append_turn(setup)
    send(actor, 2)
    before = fit_record(actor)
    actor.command('show_actions', enabled=True)
    witness = all(not row['free'] for row in before['parameters'])
    if endpoint == 'widget-refusal':
        native.wait_positive_tab(actor, 'appBar.tab.structure')
        actor.command('click', name='appBar.tab.structure')
        actor.until(
            lambda row: native._unique_input_control(row, 'statusBar.fit.button') is not None
        )
        control = actor.command(
            'ui_property', name='statusBar.fit.button', property='enabled', value=False
        )
        witness = control['reply']['value'] is False and native.qml(
            actor, 'Session.project.fit.available'
        )
    actor.append_turn([call('run_fit', 'terminal-fit')])
    send(actor, 3)
    actor.append_turn([call('inspect_project', 'live-after-attempt')])
    send(actor, 4)
    return before, witness


def observe_trial_endpoint(folder, endpoint):
    actor = actor_in(
        folder,
        [[call('run_fit', 'accepted-fit')]],
        prepare=prepare_shape if endpoint == 'background-point' else None,
    )
    try:
        prior = fit_record(actor)
        send(actor, 1)
        accepted = fit_record(actor)
        witness = True
        manual = None
        released_edit = None
        after_later_stop = None
        after_undo = None
        if endpoint in {'shown-unavailable', 'widget-refusal'}:
            prepared, witness = terminal_fit(actor, endpoint, accepted)
        else:
            turn = setup_trial(accepted, 'stop')
            last_call = 'candidate-relations'
            if endpoint in {'exclusion', 'background-point', 'background-term'}:
                turn.append(setup_shape(endpoint))
                last_call = endpoint
            hold_after_setup(actor, turn, last_call)
            prepared = fit_record(actor)
            if endpoint == 'manual-edit':
                manual = manual_value_attempt(actor)
            actor.command('sign_out' if endpoint == 'disconnect' else 'cancel')
            actor.until(lambda row: not row['ui']['can_cancel'])
        restored = fit_record(actor)
        if endpoint in {'manual-edit', 'disconnect', 'shown-unavailable', 'widget-refusal'}:
            released_edit = manual_value_attempt(actor)
        if endpoint == 'manual-edit':
            later = call(
                'set_parameters',
                'later-setup',
                values=[{'path': 'experiments[bank].background[1].coef', 'value': 12.875}],
            )
            actor.until(lambda _row: native.qml(actor, 'Session.assistant.draftAdmissionReady'))
            hold_after_setup(actor, [later], 'later-setup')
            actor.command('cancel')
            actor.until(lambda row: not row['ui']['can_cancel'])
            after_later_stop = fit_record(actor)
        if endpoint == 'exclusion':
            actor.command('undo')
            after_undo = fit_record(actor)
        return record_receipts(
            actor,
            f'{endpoint}.json',
            {
                'prior': prior,
                'accepted': accepted,
                'prepared': prepared,
                'restored': restored,
                'after_undo': after_undo,
                'witness': witness,
                'manual': manual,
                'released_edit': released_edit,
                'after_later_stop': after_later_stop,
                'wire': replies(actor),
                'connected': actor.last['ui']['connected'],
            },
        )
    finally:
        actor.close()


@pytest.fixture(scope='module')
def trial_observations(tmp_path_factory):
    root = tmp_path_factory.mktemp('trial-endpoints')
    return {
        endpoint: observe_trial_endpoint(root / endpoint, endpoint)
        for endpoint in (
            'shown-unavailable',
            'widget-refusal',
            'manual-edit',
            'disconnect',
            'exclusion',
            'background-point',
            'background-term',
        )
    }


def assert_admitted_a(observed):
    assert observed['wire']['accepted-fit']['value'].get('adopted'), (
        'Required: fit A really adopted before provisional setup.'
    )
    assert observed['prepared'] != observed['accepted'], (
        'Required: the provisional setup changed the live scientific project.'
    )


@pytest.mark.parametrize('endpoint', ['shown-unavailable', 'widget-refusal', 'disconnect'])
def test_fit_retirement_restores_accepted_state(trial_observations, endpoint):
    observed = trial_observations[endpoint]
    assert_admitted_a(observed)
    if endpoint == 'disconnect':
        assert not observed['connected'], 'Required: the actual provider connection retired.'
    else:
        assert observed['witness'] and not observed['wire']['terminal-fit']['success'], (
            'Required: the selected native or shown-control refusal was genuinely reached.'
        )
    assert observed['restored'] == observed['accepted'], (
        'Required: a terminal refusal or disconnect leaves the complete accepted fit intact.'
    )


def test_manual_value_edit_survives_stopping_an_assistant_candidate(trial_observations):
    observed = trial_observations['manual-edit']
    assert_admitted_a(observed)
    blocked = observed['manual']
    assert blocked['before'] == blocked['value'] != MANUAL_VALUE, (
        'Required: the real ordinary parameter owner refuses an edit during the trial.'
    )
    assert 'assistant is trying a change' in blocked['error'] and 'Stop' in blocked['error'], (
        'Required: the parameter control names the trial and how to release it.'
    )
    assert observed['restored'] == observed['accepted'], (
        'Required: Stop settles the held trial before admitting the manual edit.'
    )
    assert observed['released_edit']['value'] == MANUAL_VALUE, (
        'Required: the same ordinary parameter edit applies after Stop.'
    )
    assert observed['wire']['later-setup']['success'], (
        'Required: a later assistant turn makes a genuine setup edit before another Stop.'
    )
    current = {row['path']: row['value'] for row in observed['after_later_stop']['parameters']}
    assert current[TRIAL_PATH] == MANUAL_VALUE, (
        'Required: a later assistant rollback cannot erase an edit made after the lock released.'
    )


@pytest.mark.parametrize('endpoint', ['shown-unavailable', 'widget-refusal', 'disconnect'])
def test_trial_lock_releases_after_refusal_or_sign_out(trial_observations, endpoint):
    released = trial_observations[endpoint]['released_edit']
    assert released['before'] != MANUAL_VALUE and released['value'] == MANUAL_VALUE, (
        'Required: the same ordinary edit can write after the native refusal or sign-out settles.'
    )


@pytest.mark.parametrize('endpoint', ['exclusion', 'background-point', 'background-term'])
def test_candidate_shape_change_is_refused_or_restored_atomically(trial_observations, endpoint):
    observed = trial_observations[endpoint]
    assert_admitted_a(observed)
    before, prepared = observed['accepted'], observed['prepared']
    changed = '_excluded_region.' in prepared['files']['experiments/bank.edi']
    if endpoint == 'exclusion':
        assert '_excluded_region.' in prepared['files']['experiments/bank.edi'] or (
            not observed['wire'][endpoint]['success']
        ), 'Required: the actual exclusion edit was applied or expressly refused.'
    else:
        bank_before = next(row for row in before['backgrounds'] if row['id'] == 'bank')
        bank_after = next(row for row in prepared['backgrounds'] if row['id'] == 'bank')
        changed = bank_after != bank_before
    outcome = observed['wire'][endpoint]
    assert changed is outcome['success'], (
        'Required: an admitted edit changes its scientific shape and a refusal leaves it intact.'
    )
    assert observed['restored'] == before, (
        'Required: rejected trial shape and accepted scientific fit are restored together.'
    )


def test_ordinary_undo_cannot_split_rejected_exclusion_trial(trial_observations):
    observed = trial_observations['exclusion']
    assert_admitted_a(observed)
    allowed = (observed['accepted'], observed['prior'])
    assert observed['after_undo'] in allowed, (
        'Required: ordinary Undo cannot reintroduce a fragment of the rejected trial.'
    )


def test_refused_fit_receipt_is_distinct_from_accepted_live_fit(trial_observations):
    observed = trial_observations['widget-refusal']
    wire = observed['wire']
    attempt = wire['terminal-fit']
    live = wire['live-after-attempt']
    assert not attempt['success'] and not attempt['value'].get('adopted'), (
        'Required: the refused attempt cannot borrow adoption from the live accepted fit.'
    )
    assert live['success'] and live['value']['native_state'].get('fit_result_current') is True, (
        'Required: the independent provider inspection reports the actual accepted fit as current.'
    )
    assert observed['restored'] == observed['accepted'], (
        'Required: currentness belongs to the actual complete accepted state.'
    )
