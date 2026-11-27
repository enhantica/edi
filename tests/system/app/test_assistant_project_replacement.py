"""A tool request alone does not authorize closing a populated saved project."""

from pathlib import Path

import pytest

from tests.system.py import test_e11_t5_dev_native_integration as native

main_actor = native.main_actor


def asks_about_replacement(ui):
    if ui['pending_question']:
        lines = [ui['pending_question']['text']]
    else:
        lines = [row['display'] for row in ui['texts'] if row['visible']]
    return any(
        'project' in line.casefold()
        and any(word in line.casefold() for word in ('replace', 'close'))
        and ('?' in line or 'confirm' in line.casefold())
        for line in lines
    )


@pytest.mark.parametrize('show_actions', [False, True], ids=['quiet', 'shown'])
def test_saved_project_awaits_user_confirmation(main_actor, tmp_path, show_actions):
    actor = main_actor(
        [[native.tool_call('create_project', 'new-project', name='replacement_review')]],
        show_actions=show_actions,
    )
    original = native.copied_estimate_project(tmp_path, overrides=False)
    assert actor.command('open', path=str(original))['reply']['opened'], (
        'The replacement check starts from a genuinely saved project'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    assert native.qml(
        actor, '!Session.project.modified && Session.project.structures.count > 0'
    ), 'The open project must be clean and populated, so unsaved edits cannot trigger the guard'
    before = {path: path.read_bytes() for path in original.rglob('*.edi')}
    actor.connect()
    actor.request('Please create a new project called replacement_review.')
    state = actor.until(
        lambda row: (
            asks_about_replacement(row['ui'])
            or not row['ui']['project']
            or Path(row['ui']['project']['path']).resolve() != original
            or bool(actor.responses())
        ),
        visible_progress=show_actions,
    )['ui']
    assert state['project'] and Path(state['project']['path']).resolve() == original, (
        'The populated saved project must remain open until the user confirms closing it'
    )
    assert asks_about_replacement(state), (
        'User confirmation is required before replacing the populated saved project'
    )
    assert not actor.responses(), (
        'Assistant Create remains pending while the user decides whether to close the project'
    )
    assert before == {path: path.read_bytes() for path in before}, (
        'The saved project files stay intact while the replacement decision is pending'
    )
    choice = 'close' if show_actions else 'cancel'
    actor.command('click', name='unsavedChanges.' + choice)
    actor.until(
        lambda row: bool(actor.responses()) and row['ui']['state'] == 'idle',
        visible_progress=show_actions,
    )
    outcome = actor.responses()[0]['result']
    actual = actor.last['ui']['project']
    if show_actions:
        assert outcome['success'] and actual['name'] == 'replacement_review', (
            'An explicit user Close choice allows the shown assistant to adopt the new project'
        )
    else:
        assert not outcome['success'] and Path(actual['path']).resolve() == original, (
            'Cancel leaves the original project current and refuses the proposed new project'
        )
    assert before == {path: path.read_bytes() for path in before}, (
        'Closing or canceling a clean original project preserves its saved files'
    )
