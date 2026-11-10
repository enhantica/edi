"""Accepted fit ownership across assistant edits, publication and saves."""

import hashlib
from pathlib import Path

import pytest

from tests.integration.app.test_assistant_candidate_boundaries import (
    TRIAL_PATH,
    call,
    record_receipts,
)
from tests.integration.app.test_assistant_misfit_workflow import actor_in, replies, send
from tests.integration.app.test_assistant_review_receipts import fit_record
from tests.integration.app.test_assistant_trial_retirement import MANUAL_VALUE, manual_value_edit
from tests.system.py import test_e11_t5_dev_native_integration as native

OTHER_PATH = 'experiments[bank].background[1].coef'


def value(record, path):
    return next(row['value'] for row in record['parameters'] if row['path'] == path)


def parameter_edit(identity, path, amount):
    return call('set_parameters', identity, values=[{'path': path, 'value': amount}])


def submit_held(actor, tools, last_call):
    actor.append_turn(tools)
    native._session_configure(actor, final_gate=str(actor.gate))
    actor.until(lambda _row: native.qml(actor, 'Session.assistant.draftAdmissionReady'))
    assert native.qml(actor, 'Session.assistant.submitDraft("Run this owned trial setup.")'), (
        'Required: the ordinary owner admits the trial on its current conversation.'
    )
    actor.until(lambda row: row['ui']['can_cancel'] and last_call in replies(actor))


def stop(actor):
    actor.command('cancel')
    actor.until(lambda row: not row['ui']['can_cancel'])
    return fit_record(actor)


def disk_science(path):
    return {
        str(file.relative_to(path)): hashlib.sha256(file.read_bytes()).hexdigest()
        for directory in ('analysis', 'experiments', 'structures')
        for file in (path / directory).rglob('*')
        if file.is_file()
    }


def observe_ownership(folder, endpoint):  # noqa: PLR0914 - Keep the complete scenario receipt.
    actor = actor_in(folder, [[call('run_fit', 'fit-a')]])
    try:
        send(actor, 1)
        accepted = fit_record(actor)
        assert replies(actor)['fit-a']['value'].get('adopted') is True, (
            'Required: A is an actual adopted fit before the new trial.'
        )
        project = folder / 'project'
        if endpoint.startswith('save'):
            assert actor.command('save')['reply']['saved'], (
                'Required: ordinary Save records a disk baseline for accepted A.'
            )
            accepted = fit_record(actor)
        before = accepted
        disk_before = disk_science(project)
        undo = []
        if endpoint.startswith('manual'):
            assert manual_value_edit(actor) == MANUAL_VALUE, (
                'Required: the actual ordinary owner accepts the manual edit after fit A.'
            )
            before = fit_record(actor)
        elif endpoint == 'clear':
            actor.append_turn([parameter_edit('pre-clear', TRIAL_PATH, MANUAL_VALUE)])
            send(actor, 2)
            assert value(fit_record(actor), TRIAL_PATH) == MANUAL_VALUE, (
                'Required: the old assistant binding owns a real candidate before Clear.'
            )
            actor.command('clear_history')
            actor.until(lambda row: not row['ui']['messages'] and not row['ui']['can_cancel'])
            before = fit_record(actor)
        elif endpoint == 'publication':
            actor.command('arm_estimate_publication', mode='throw')

        setup = parameter_edit('setup-b', OTHER_PATH, 12.875)
        if endpoint == 'manual-refuse':
            flags = [
                {'path': row['path'], 'free': False} for row in before['parameters'] if row['free']
            ]
            actor.append_turn([
                setup,
                call('set_free', 'no-free', flags=flags),
                call('run_fit', 'refused-fit'),
            ])
            send(actor, 2)
            restored = fit_record(actor)
        elif endpoint.startswith('save'):
            mode = 'current' if endpoint == 'save-current' else 'fresh'
            save = call(
                'save_project',
                'candidate-save',
                **(
                    {'destination': mode}
                    if mode == 'current'
                    else {'destination': mode, 'name': 'candidate-fresh'}
                ),
            )
            submit_held(actor, [setup, save], 'candidate-save')
            restored = stop(actor)
        else:
            submit_held(actor, [setup], 'setup-b')
            restored = stop(actor)
        wire = replies(actor)
        current_path = Path(actor.command('inspect')['ui']['project']['path'])
        disk_after = disk_science(project)
        fresh = folder / 'candidate-fresh'
        fresh_disk = disk_science(fresh)
        fault = actor.command('publication_fault')['reply'] if endpoint == 'publication' else None
        if endpoint.startswith('manual') or endpoint == 'publication':
            for _ in range(4 if endpoint == 'manual-refuse' else 2):
                actor.command('undo')
                undo.append(fit_record(actor))
        return record_receipts(
            actor,
            'trial-ownership.json',
            {
                'accepted': accepted,
                'before': before,
                'restored': restored,
                'wire': wire,
                'undo': undo,
                'fault': fault,
                'disk_before': disk_before,
                'disk_after': disk_after,
                'fresh_disk': fresh_disk,
                'fresh_exists': fresh.exists(),
                'current_path': str(current_path),
                'original_path': str(project),
                'fresh_path': str(fresh),
            },
        )
    finally:
        actor.close()


@pytest.fixture(scope='module')
def ownership(tmp_path_factory):
    root = tmp_path_factory.mktemp('trial-ownership')
    return {
        case: observe_ownership(root / case, case)
        for case in (
            'manual-stop',
            'manual-refuse',
            'clear',
            'publication',
            'save-current',
            'save-fresh',
        )
    }


@pytest.mark.parametrize('endpoint', ['manual-stop', 'manual-refuse'])
def test_later_assistant_setup_preserves_an_intervening_manual_edit_and_undo(ownership, endpoint):
    result = ownership[endpoint]
    assert result['wire']['setup-b']['success'], (
        'Required: a later actual assistant setup edit applies.'
    )
    if endpoint == 'manual-refuse':
        assert not result['wire']['refused-fit']['success'], (
            'Required: the actual attempted Fit refuses after later setup.'
        )
    assert value(result['restored'], TRIAL_PATH) == MANUAL_VALUE, (
        'Required: the ordinary manual edit survives the later assistant trial termination.'
    )
    assert any(
        value(state, TRIAL_PATH) == value(result['accepted'], TRIAL_PATH)
        for state in result['undo']
    ), 'Required: ordinary Undo can still reverse the manual edit.'


def test_clear_cannot_rebind_an_older_fit_snapshot(ownership):
    result = ownership['clear']
    assert result['wire']['setup-b']['success'], (
        'Required: a real setup edit applies on the conversation after Clear.'
    )
    assert value(result['restored'], TRIAL_PATH) == value(result['before'], TRIAL_PATH), (
        'Required: Stop on the new conversation preserves the value observed after Clear.'
    )


def test_failed_publication_preserves_undo_when_stop_cannot_restore(ownership):
    result = ownership['publication']
    assert result['fault']['hits'] and result['fault']['undo_seen'], (
        'Required: the injected postwrite failure reaches an already-owned Undo record.'
    )
    assert value(result['restored'], OTHER_PATH) == 12.875, (
        'Required: this stopped restore was refused after the real candidate write.'
    )
    assert value(result['undo'][0], OTHER_PATH) == value(result['before'], OTHER_PATH), (
        'Required: the first ordinary Undo still recovers the prewrite parameter value.'
    )


@pytest.mark.parametrize('endpoint', ['save-current', 'save-fresh'])
def test_stopping_a_candidate_preserves_consistent_saved_science_and_location(ownership, endpoint):
    result = ownership[endpoint]
    assert result['wire']['setup-b']['success'], (
        'Required: Save is attempted during an actual trial.'
    )
    assert result['disk_after'] == result['disk_before'], (
        'Required: the accepted folder contains no rejected trial values or results after Stop.'
    )
    if result['fresh_exists']:
        assert (
            result['current_path'] == result['fresh_path']
            and result['fresh_disk'] == result['disk_before']
        ), 'Required: Save As contains accepted science matching the live project.'
    else:
        assert result['current_path'] == result['original_path'], (
            'Required: when no fresh save is published, the accepted project retains its folder.'
        )
