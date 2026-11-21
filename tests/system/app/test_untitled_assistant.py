"""The offline assistant creates a fresh project after protecting unnamed work."""

import json
import os
from pathlib import Path

import pytest

from tests.integration.app.test_assistant_misfit_workflow import replies
from tests.system.py import test_e11_t5_dev_native_integration as native

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('shown', [False, True], ids=['ordinary', 'shown'])
def test_assistant_create_from_untitled(tmp_path, shown):
    binary = Path(
        os.environ.get(
            'EDI_ASSISTANT_UI_PROBE',
            ROOT / 'build/app/assistant-ui-probe/assistant_real_owner_probe',
        )
    )
    folder = tmp_path / 'owner'
    folder.mkdir()
    call_id = 'untitled-create'
    actor = native.MainActor(
        binary,
        folder,
        {
            'turns': [
                [
                    native.tool_call(
                        'create_project',
                        call_id,
                        name='untitled_assistant_7',
                        title='Neutron study from an untitled window',
                    )
                ]
            ],
        },
        shown,
    )
    try:
        native.qml(actor, '(function(){AppState.open(AppState.Page.Project);return true;})()')
        assert native.qml(actor, 'Session.project === null'), (
            'Opening Project creates neither a project nor an invisible work container'
        )
        native.qml(actor, '(function(){AppState.open(AppState.Page.Structure);return true;})()')
        assert native.qml(actor, 'Session.project !== null && Session.untitled'), (
            'Opening Structure supplies the invisible work container before assistant Create'
        )
        title = native.qml(actor, 'Session.project.title')
        assert isinstance(title, str), 'The work container exposes its title as text'
        assert not title, (
            'The work container has no invented project title'
        )
        assert native.qml(
            actor,
            '(function(){const p=Session.project;if(!p.createStructure())return false;'
            'p.currentStructure.cell.length_a.value=7.125;return p.modified;})()',
        ), 'The assistant starts with actual unsaved scientific work to protect'
        assert (
            native.qml(actor, native.control_expression('statusBar.project') + '.valueText')
            == 'Undefined'
        ), 'The status bar hides the unnamed work before assistant creation'
        parent = tmp_path / 'chosen-parent'
        parent.mkdir()
        control = native.control_expression('createProject.dialog')
        assert native.qml(
            actor,
            '(function(){const d=' + control + ';'
            'if(!d)return false;d.projectParentDirectory='
            + json.dumps(parent.as_uri())
            + ';return true;})()',
        ), 'Assistant Create uses the ordinary form with a private remembered parent'
        actor.command('accept_context')
        actor.until(lambda row: row['ui']['connected'])
        actor.connect()
        actor.until(lambda _row: native.qml(actor, 'Session.assistant.draftAdmissionReady'))
        assert native.qml(
            actor, 'Session.assistant.submitDraft("Create the requested project.")'
        ), 'The ordinary assistant admits the deterministic create request'
        question = native.control_expression('unsavedChanges')
        actor.until(lambda _row: native.qml(actor, question + '.opened'))
        assert (
            native.qml(actor, 'Session.project.currentStructure.cell.length_a.value') == 7.125
        ), 'Assistant Create protects the existing scientific edit until the user answers'
        actor.command('click', name='unsavedChanges.discard')
        native._session_completed(actor, 1)
        result = replies(actor).get(call_id)
        assert result is not None and result['success'], (
            'The genuine create_project call succeeds from untitled in either presentation mode'
        )
        assert native.qml(actor, 'Session.project.name') == 'untitled_assistant_7', (
            'The assistant retains the literal requested short name'
        )
        assert (
            native.qml(actor, 'Session.project.title') == 'Neutron study from an untitled window'
        ), 'Assistant creation retains the requested project title'
        assert native.qml(actor, 'Session.project.structures.count') == 0, (
            'Assistant Create makes a new project rather than adopting the unnamed work'
        )
        assert native.qml(actor, '!Session.untitled && !Session.needsSaveAs'), (
            'Assistant Create saves the named desktop project immediately'
        )
        assert (parent / 'untitled_assistant_7' / 'project.edi').is_file(), (
            'Assistant creation writes the new project at the chosen location'
        )
        error = native.qml(actor, 'Session.lastError')
        assert isinstance(error, str) and not error, (
            'Creating from untitled leaves no project-operation error'
        )
        (folder / 'creation.json').write_text(json.dumps(result, indent=2) + '\n')
    finally:
        actor.close()
