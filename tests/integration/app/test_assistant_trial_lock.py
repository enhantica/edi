"""Public write boundaries while the assistant owns a native Fit trial."""

import json

import pytest

from tests.integration.app.test_assistant_candidate_boundaries import (
    TRIAL_PATH,
    call,
    record_receipts,
)
from tests.integration.app.test_assistant_misfit_workflow import actor_in, replies, send
from tests.integration.app.test_assistant_review_receipts import fit_record
from tests.integration.app.test_assistant_trial_ownership import (
    OTHER_PATH,
    disk_science,
    parameter_edit,
    stop,
    submit_held,
    value,
)
from tests.integration.app.test_assistant_trial_retirement import (
    MANUAL_VALUE,
    manual_value_attempt,
    manual_value_expression,
)
from tests.system.py import test_e11_t5_dev_native_integration as native

POST_ACCEPT_VALUE = 19.875

SAVE_ROUTES = {
    'folder-save': ('save', {}),
    'folder-as': ('save_as', {'path': 'folder-as'}),
    'folder-copy': ('save_project_as', {'path': 'folder-copy', 'copy': True}),
    'archive-as': ('save_project_as', {'path': 'archive-as.zip', 'zip': True}),
    'archive-copy': ('save_project_as', {'path': 'archive-copy.zip', 'zip': True, 'copy': True}),
}


def trial_reason(error):
    return isinstance(error, str) and 'assistant is trying a change' in error and 'Stop' in error


def save_attempt(actor, command, **arguments):
    # Seed a different diagnostic so a silent refusal cannot reuse the trial reason.
    assert native.qml(actor, 'Session.saveAs("https://invalid.example/edi")') is False and (
        'only local directories' in native.qml(actor, 'Session.lastError')
    ), 'Required: the non-local control produces its own harmless Save diagnostic.'
    saved = actor.command(command, **arguments)['reply']['saved']
    return {'saved': saved, 'error': native.qml(actor, 'Session.lastError')}


def seed_project_diagnostic(actor):
    assert (
        native.qml(actor, 'Session.project.loadData(0,"https://invalid.example/edi")') is False
    ), 'Required: the non-local control cannot change the open project.'
    assert 'not a local file' in native.qml(actor, 'Session.project.lastError'), (
        'Required: a harmless non-local input gives the next project action a distinct diagnostic.'
    )


def observe_held_writes(folder):
    actor = actor_in(folder, [[call('run_fit', 'fit-a')]])
    try:
        send(actor, 1)
        assert actor.command('save')['reply']['saved'], (
            'Required: the ordinary Save writes accepted A before any trial attempt.'
        )
        accepted = fit_record(actor)
        project = folder / 'project'
        before_disk = disk_science(project)
        submit_held(
            actor,
            [
                parameter_edit('setup', OTHER_PATH, 12.875),
                call('undo_fit', 'assistant-undo'),
                call('save_project', 'assistant-current', destination='current'),
                call(
                    'save_project', 'assistant-fresh', destination='fresh', name='assistant-fresh'
                ),
            ],
            'assistant-fresh',
        )
        prepared = fit_record(actor)
        ordinary_edit = manual_value_attempt(actor)
        seed_project_diagnostic(actor)
        description = native.qml(actor, 'Session.project.description')
        metadata = native.qml(
            actor,
            '(function(){const p=Session.project;p.description="Unowned ordinary edit";'
            'return {value:p.description,error:p.lastError};})()',
        )
        seed_project_diagnostic(actor)
        undo_available = native.qml(actor, 'Session.project.canUndo')
        actor.command('undo')
        ordinary_undo = {
            'before': undo_available,
            'error': native.qml(actor, 'Session.project.lastError'),
            'same': fit_record(actor) == prepared,
        }
        messages = {row['id'] for row in actor.last['ui']['messages']}
        actor.command('clear_history')
        clear = {
            'before': bool(messages),
            'same': messages <= {row['id'] for row in actor.last['ui']['messages']},
            'error': native.qml(actor, 'Session.assistant.lastError'),
        }
        saves = {}
        for route, (command, arguments) in SAVE_ROUTES.items():
            options = dict(arguments)
            if 'path' in options:
                options['path'] = str(folder / options['path'])
            saves[route] = save_attempt(actor, command, **options)
        restored = stop(actor)
        return record_receipts(
            actor,
            'held-writes.json',
            {
                'accepted': accepted,
                'prepared': prepared,
                'restored': restored,
                'wire': replies(actor),
                'edit': ordinary_edit,
                'metadata': metadata | {'before': description},
                'undo': ordinary_undo,
                'clear': clear,
                'saves': saves,
                'before_disk': before_disk,
                'after_disk': disk_science(project),
                'fresh_paths': [
                    arguments['path']
                    for _, arguments in SAVE_ROUTES.values()
                    if 'path' in arguments and (folder / arguments['path']).exists()
                ]
                + (['assistant-fresh'] if (folder / 'assistant-fresh').exists() else []),
                'active': actor.command('inspect')['ui']['project']['path'],
                'project': str(project),
            },
        )
    finally:
        actor.close()


def observe_archive_save(folder):
    actor = actor_in(folder, [[call('run_fit', 'fit-a')]])
    try:
        archive = folder / 'accepted.zip'
        assert actor.command('save_project_as', path=str(archive), zip=True)['reply']['saved'], (
            'Required: an ordinary Save As puts the live project in its owned archive.'
        )
        send(actor, 1)
        assert actor.command('save')['reply']['saved'], (
            'Required: ordinary current Save publishes fit A into the actual archive.'
        )
        before = archive.read_bytes()
        accepted = fit_record(actor)
        working_path = actor.last['ui']['project']['path']
        submit_held(actor, [parameter_edit('archive-setup', OTHER_PATH, 12.875)], 'archive-setup')
        prepared = fit_record(actor)
        attempts = {
            'archive-save': save_attempt(actor, 'save'),
            'archive-replace': save_attempt(actor, 'save_project_as', path=str(archive), zip=True),
        }
        restored = stop(actor)
        return record_receipts(
            actor,
            'archive-save.json',
            {
                'attempts': attempts,
                'accepted': accepted,
                'prepared': prepared,
                'restored': restored,
                'same_archive': archive.read_bytes() == before,
                'same_owner': actor.last['ui']['project']['path'] == working_path,
                'wire': replies(actor),
            },
        )
    finally:
        actor.close()


def observe_fit_undo(folder):
    actor = actor_in(folder, [[call('run_fit', 'fit-a')]])
    try:
        send(actor, 1)
        manual = manual_value_attempt(actor)
        actor.append_turn([
            parameter_edit('prepare-b', OTHER_PATH, 12.875),
            call('run_fit', 'fit-b'),
        ])
        send(actor, 2)
        actor.append_turn([call('undo_fit', 'undo-b')])
        send(actor, 3)
        undone = fit_record(actor)
        submit_held(actor, [parameter_edit('prepare-c', OTHER_PATH, 21.75)], 'prepare-c')
        restored = stop(actor)
        return record_receipts(
            actor,
            'undo-baseline.json',
            {'manual': manual, 'undone': undone, 'restored': restored, 'wire': replies(actor)},
        )
    finally:
        actor.close()


def observe_presentation(folder):
    actor = actor_in(folder, [[call('run_fit', 'fit-a')]])
    try:
        send(actor, 1)
        watch = 'e11.lock.presentation'
        owner = native.control_expression(watch)
        assert native.qml(
            actor,
            '(function(){const w=Qt.createQmlObject('
            + json.dumps(
                'import QtQuick; Item {objectName:"' + watch + '";'
                'property int hits:0;property var attempt:null;property bool running:true}'
            )
            + ',contentItem);const fit=Session.project.fit;fit.finished.connect(function(){'
            'w.hits++;w.running=fit.running;w.attempt='
            + manual_value_expression()
            + ';});return true;})()',
        ), 'Required: the witness observes the actual Fit presentation signal.'
        actor.append_turn([
            parameter_edit('prepare-b', OTHER_PATH, 12.875),
            call('run_fit', 'fit-b'),
        ])
        send(actor, 2)
        presentation = native.qml(
            actor,
            '(function(){const w=' + owner + ';return {hits:w.hits,running:w.running,'
            'attempt:w.attempt};})()',
        )
        accepted = fit_record(actor)
        release = manual_value_attempt(actor, POST_ACCEPT_VALUE)
        return record_receipts(
            actor,
            'presentation-edit.json',
            {
                'presentation': presentation,
                'accepted': accepted,
                'release': release,
                'wire': replies(actor),
            },
        )
    finally:
        actor.close()


@pytest.fixture(scope='module')
def lock_evidence(tmp_path_factory):
    root = tmp_path_factory.mktemp('trial-lock')
    return {
        'held': observe_held_writes(root / 'held'),
        'archive': observe_archive_save(root / 'archive'),
        'undo': observe_fit_undo(root / 'undo'),
        'presentation': observe_presentation(root / 'presentation'),
    }


@pytest.mark.parametrize('route', ['edit', 'metadata', 'undo', 'clear', 'assistant-undo'])
def test_held_trial_refuses_other_edits_undo_and_clear_with_a_reason(lock_evidence, route):
    held = lock_evidence['held']
    assert held['wire']['fit-a']['value']['adopted'] and held['wire']['setup']['success'], (
        'Required: an actual accepted fit and a subsequent write own the held trial.'
    )
    if route == 'assistant-undo':
        response = held['wire'][route]
        assert not response['success'] and trial_reason(response['value'].get('message', '')), (
            'Required: assistant Undo refuses because of the trial and names how to release it.'
        )
        return
    row = held[route]
    untouched = (
        row['before'] == row['value']
        if route in {'edit', 'metadata'}
        else row['before'] and row['same']
    )
    assert untouched and trial_reason(row['error']), (
        f'Required: {route} leaves the held owner intact and explains how to release the trial.'
    )


@pytest.mark.parametrize('route', [*SAVE_ROUTES, 'assistant-current', 'assistant-fresh'])
def test_held_trial_refuses_saving_and_stop_leaves_only_accepted_files(lock_evidence, route):
    held = lock_evidence['held']
    assert held['wire']['setup']['success'] and value(held['prepared'], OTHER_PATH) == 12.875, (
        'Required: each Save is attempted after a real provisional scientific edit.'
    )
    if route.startswith('assistant-'):
        result = held['wire'][route]
        attempt = {'saved': result['success'], 'error': result['value'].get('message', '')}
    else:
        attempt = held['saves'][route]
    assert not attempt['saved'] and trial_reason(attempt['error']), (
        f'Required: {route} refuses with the trial reason before publishing.'
    )
    assert held['before_disk'] == held['after_disk'] and not held['fresh_paths'], (
        'Required: no held Save leaves rejected science on disk or publishes a new destination.'
    )
    assert held['restored'] == held['accepted'] and held['active'] == held['project'], (
        'Required: Stop restores accepted science with its original folder still active.'
    )


@pytest.mark.parametrize('route', ['archive-save', 'archive-replace'])
def test_held_archive_save_refuses_before_writing_and_stop_restores_live_state(
    lock_evidence, route
):
    evidence = lock_evidence['archive']
    assert (
        evidence['wire']['archive-setup']['success']
        and evidence['prepared'] != evidence['accepted']
    ), 'Required: archive writes are attempted during an actual scientific trial.'
    attempt = evidence['attempts'][route]
    assert not attempt['saved'] and trial_reason(attempt['error']), (
        f'Required: {route} refuses with the trial reason before touching the archive.'
    )
    assert (
        evidence['same_archive']
        and evidence['same_owner']
        and evidence['restored'] == evidence['accepted']
    ), 'Required: Stop keeps the original archive bytes and restores the matching live project.'


def test_manual_correction_survives_later_fit_undo_and_stop(lock_evidence):
    observed = lock_evidence['undo']
    wire = observed['wire']
    assert observed['manual']['value'] == MANUAL_VALUE and wire['fit-b']['value'].get('adopted'), (
        'Required: the ordinary correction and the later Fit B both really apply.'
    )
    assert wire['undo-b']['success'] and value(observed['undone'], TRIAL_PATH) == MANUAL_VALUE, (
        'Required: assistant Undo of B reinstates the pre-B ordinary correction.'
    )
    assert (
        wire['prepare-c']['success'] and value(observed['restored'], TRIAL_PATH) == MANUAL_VALUE
    ), 'Required: a new assistant setup and Stop preserve the correction restored by Undo.'


def test_fit_presentation_refuses_observer_edit_until_acceptance_settles(lock_evidence):
    observed = lock_evidence['presentation']
    witness = observed['presentation']
    assert observed['wire']['fit-b']['value'].get('adopted') and witness['hits'] == 1, (
        'Required: the original presentation observer runs exactly once on a genuinely adopted B.'
    )
    attempt = witness['attempt']
    assert not witness['running'] and attempt['before'] == attempt['value'] != MANUAL_VALUE, (
        'Required: the presentation observer cannot edit after running ends but before acceptance.'
    )
    assert trial_reason(attempt['error']), (
        'Required: the observer write is refused with the same actionable trial reason.'
    )
    assert value(observed['accepted'], TRIAL_PATH) == attempt['before'], (
        'Required: the accepted project contains the actual Fit value.'
    )


def test_trial_lock_releases_after_acceptance(lock_evidence):
    observed = lock_evidence['presentation']
    assert observed['wire']['fit-b']['value'].get('adopted'), (
        'Required: Fit B really adopts before the later ordinary edit.'
    )
    release = observed['release']
    assert release['before'] != POST_ACCEPT_VALUE and release['value'] == POST_ACCEPT_VALUE, (
        'Required: an ordinary edit changes the value once acceptance has settled.'
    )
