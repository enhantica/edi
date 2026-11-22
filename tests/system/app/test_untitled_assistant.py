"""The real offline assistant can create from unnamed Structure work."""

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
            'Opening Project alone leaves the session empty'
        )
        native.qml(actor, '(function(){AppState.open(AppState.Page.Structure);return true;})()')
        assert native.qml(
            actor, 'Session.project !== null && Session.untitled && Session.needsSaveAs'
        ), 'Opening Structure prepares the same unnamed work the user sees'
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
        actor.request('Create the requested named project with its requested title.')
        # The shown action drives real focus and pointer events. Read its offline
        # reply before querying the GUI for the settled turn.
        native.history_poll(lambda: bool(actor.responses()), seconds=120 if shown else 30)
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
        error = native.qml(actor, 'Session.lastError')
        assert isinstance(error, str) and not error, (
            'Creating from untitled leaves no project-operation error'
        )
        (folder / 'creation.json').write_text(json.dumps(result, indent=2) + '\n')
    finally:
        actor.close()
