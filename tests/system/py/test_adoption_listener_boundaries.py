"""A listener reentering adoption cannot create a lost edit or redirect a completed save."""

import pytest

from tests.fixtures.project_save.reference import six_digits
from tests.system.py import test_operation_contracts as operations

tutorial_observer = operations.tutorial_observer
ROUTES = (
    'save',
    'save-as',
    'fresh-folder',
    'fresh-zip',
    'save-archive',
    'web-save',
    'web-folder',
    'web-zip',
    'web-save-zip',
    'web-save-browser',
    'web-browser',
    'assistant-folder',
    'assistant-zip',
)


@pytest.mark.parametrize(
    ('route', 'signal'),
    [(route, 'clean') for route in ROUTES]
    + [
        (route, 'path')
        for route in ('save-as', 'fresh-folder', 'fresh-zip', 'assistant-folder', 'assistant-zip')
    ],
)
@pytest.mark.parametrize('action', ['edit', 'replace'])
def test_adoption_listener_cannot_lose_an_edit_or_redirect_the_saved_snapshot(
    tutorial_observer, tmp_path, route, signal, action
):
    row = operations.operation(
        tutorial_observer, tmp_path, f'adoption-boundary/{route}/{signal}/{action}', 'powder'
    )
    assert row['durableValue'] == six_digits(row['plannedValue']), (
        'The outer save writes exactly its original scientific value under the declared save rule'
    )
    assert row['durableDescription'] == 'An independently authored dirty state before adoption', (
        'The actual output includes the dirty metadata that belonged to the planned owner'
    )
    assert row['replacementOwnerRetained'], (
        'An old save preserves the actual replacement owner '
        'and every location and save-state announcement'
    )
    assert row['entered'], 'The listener enters the real adoption or dirty-clear notification'
    assert row['successorIntact'], 'The old save never writes into an unrelated replacement input'
    if action == 'replace':
        assert row['replaced'] or (row['current'] and row['explicitRefusal']), (
            'Replacement is admitted after safe completion or explicitly refused while held'
        )
    elif row['editAccepted']:
        assert row['current'] and row['modified'] and row['finalValue'] == row['requested'], (
            'An admitted listener edit remains dirty and retains its exact nontrivial value'
        )
        assert row['undoAvailable'] and row['afterUndo'] == row['durableValue'], (
            'One ordinary Undo restores the admitted listener edit to the saved scientific value'
        )
        assert row['durableValue'] != row['requested'], (
            'The completed outer save cannot certify a later listener edit as already written'
        )
    else:
        assert row['current'] and row['explicitRefusal'], (
            'An edit fenced by the save hold receives an actual visible refusal'
        )
        assert not row['modified'] and row['finalValue'] == row['durableValue'], (
            'A successfully adopted unchanged model equals the actual durable scientific snapshot'
        )
