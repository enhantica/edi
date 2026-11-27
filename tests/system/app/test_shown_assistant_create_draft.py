"""A shown assistant Create starts with the current project's clean form."""

import os
from pathlib import Path

import pytest

from tests.system.py import test_e11_t5_dev_native_integration as native

DRAFT = {
    'createProject.name': 'OldUnsubmittedDraft',
    'createProject.title': 'Private previous title',
    'createProject.authors': 'Private previous authors',
    'createProject.description': 'Private previous description',
}
NEW_NAME = 'shown_new_project'


@pytest.fixture(scope='module')
def shown_create(tmp_path_factory):
    root = tmp_path_factory.mktemp('shown-assistant-create')
    old = native.copied_estimate_project(root, overrides=False)
    replacement = root / 'empty-project'
    replacement.mkdir()
    (replacement / 'project.edi').write_text(
        '_edi.schema_version 2\n_metadata.name empty_project\n', encoding='utf-8'
    )
    binary = Path(
        os.environ.get(
            'EDI_ASSISTANT_UI_PROBE',
            native.ROOT
            / 'build/app/assistant-ui-probe'
            / (
                'assistant_real_owner_probe.exe'
                if os.name == 'nt'
                else 'assistant_real_owner_probe'
            ),
        )
    )
    folder = root / 'owner'
    folder.mkdir()
    actor = native.MainActor(
        binary,
        folder,
        {'turns': [[native.tool_call('create_project', 'create', name=NEW_NAME)]]},
        True,
    )
    try:
        actor.connect()
        if native.qml(actor, 'assistantPanelVisible'):
            actor.command('click', name='assistant.toggle')
            actor.until(lambda _: not native.qml(actor, 'assistantPanelVisible'))
        assert actor.command('open', path=str(old))['reply']['opened'], (
            'Open the saved project that owns the unpublished Create draft'
        )
        native.wait_positive_tab(actor, 'appBar.tab.project')
        actor.command('click', name='appBar.tab.project')
        actor.until(lambda row: native._unique_input_control(row, 'project.create') is not None)
        actor.command('click', name='project.create')
        actor.until(
            lambda row: any(
                item['name'] == 'createProject.name' and item['visible']
                for item in row['ui']['controls']
            )
        )
        for field, value in DRAFT.items():
            actual = actor.command('ui_property', name=field, property='text', value=value)[
                'reply'
            ]
            assert actual['value'] == value, (
                f'The previous project receives the unpublished draft in {field}'
            )
        actor.command('manual_key', key='escape')
        actor.until(
            lambda row: (
                not any(
                    item['name'] == 'createProject.name' and item['visible']
                    for item in row['ui']['controls']
                )
            )
        )
        assert actor.command('open', path=str(replacement))['reply']['opened'], (
            'Replace the old project with a different saved project before the assistant acts'
        )
        assert Path(actor.last['ui']['project']['path']).resolve() == replacement, (
            'The next user request starts with the replacement project as the current owner'
        )
        if not native.qml(actor, 'assistantPanelVisible'):
            native.wait_positive_tab(actor, 'assistant.toggle')
            actor.command('click', name='assistant.toggle')
        actor.command('clear_ui_sequence')
        actor.request(f'Create a new project named {NEW_NAME}.')
        actor.until(
            lambda row: bool(actor.responses()) and row['ui']['state'] == 'idle',
            visible_progress=True,
        )
        yield actor
    finally:
        actor.close()


def test_shown_create_leaves_previous_project_draft_behind(shown_create):
    actor = shown_create
    assert actor.responses()[0]['result']['success'], (
        'The shown assistant successfully completes the distinct new project request'
    )
    assert any(event.get('confirm_contains_press') for event in actor.last['ui']['ui_sequence']), (
        'The assistant uses a real press on the original visible Create form'
    )
    project = actor.last['ui']['project']
    assert project['name'] == NEW_NAME, 'The adopted project keeps the explicit requested name'
    saved = (Path(project['path']) / 'project.edi').read_text(encoding='utf-8')
    carried = [field for field, value in DRAFT.items() if value in saved]
    assert not carried, (
        f'The shown assistant Create must leave previous draft fields behind: {carried}'
    )
