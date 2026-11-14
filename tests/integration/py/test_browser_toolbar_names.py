"""Browser actors retain the published project-toolbar identity contract."""

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PUBLISHED = 'b16f9867ef1de464dfed731796848eb5ba60e739'
LEGACY = (
    'Save current state of the project',
    'Reset to initial state without project, model and data',
)
CAPTIONS = (
    'Save the project',
    'Undo the last change',
    'Redo the last undone change',
    'Clear: close the project and start again',
)


def require_current_actor_names(directory):
    actors = sorted(directory.glob('*.mjs'))
    assert actors, 'The browser actor inventory must not be empty'
    for path in actors:
        text = path.read_text()
        assert not any(caption in text for caption in LEGACY), (
            'A browser actor retains a retired project toolbar caption: ' + path.name
        )


def test_browser_actor_inventory_keeps_the_published_toolbar_contract():
    source = subprocess.check_output(
        ['git', 'show', PUBLISHED + ':app/qml/Main.qml'], cwd=ROOT, text=True
    )
    for caption in CAPTIONS:
        assert 'qsTr("' + caption + '")' in source, (
            'The caption contract comes from the published app, not a new browser observation'
        )
    actors = ROOT / 'tests/system/manual'
    require_current_actor_names(actors)
    main = (actors / 'e04_t11_browser.mjs').read_text()
    assert all(caption in main for caption in CAPTIONS)
    assert 'assert.equal(toolbar.length,4' in main
    assert 'assert.deepEqual(toolbar.map(button=>button.name),toolbarNames' in main


@pytest.mark.parametrize('caption', LEGACY)
def test_a_stale_caption_in_any_browser_actor_refuses(tmp_path, caption):
    actor = tmp_path / 'other_actor.mjs'
    actor.write_text('const caption = "Save the project";\n')
    require_current_actor_names(tmp_path)
    actor.write_text('const caption = ' + repr(caption) + ';\n')
    with pytest.raises(AssertionError, match='retired project toolbar caption'):
        require_current_actor_names(tmp_path)


def test_empty_browser_actor_inventory_cannot_pass(tmp_path):
    with pytest.raises(AssertionError, match='must not be empty'):
        require_current_actor_names(tmp_path)


@pytest.mark.parametrize(
    'actor', ['e04_t11_browser.mjs', 'project_archive_browser.mjs', 'project_browser_storage.mjs']
)
def test_published_stale_actor_preimage_is_rejected(tmp_path, actor):
    previous = subprocess.check_output(
        ['git', 'show', PUBLISHED + ':tests/system/manual/' + actor], cwd=ROOT, text=True
    )
    assert any(caption in previous for caption in LEGACY)
    (tmp_path / actor).write_text(previous)
    with pytest.raises(AssertionError, match='retired project toolbar caption'):
        require_current_actor_names(tmp_path)
