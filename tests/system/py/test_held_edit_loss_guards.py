"""Held edits remain dirty to guards while downstream notifications wait."""

import pytest

from tests.system.py import test_operation_contracts as operations

tutorial_observer = operations.tutorial_observer


@pytest.mark.parametrize('dataset', ['powder', 'single-crystal', 'scan'])
@pytest.mark.parametrize(
    'action', ['release', 'save', 'aside', 'browser-open', 'browser-stored', 'browser-recovery']
)
def test_held_edit_stays_visible_to_every_native_guard_query(
    tutorial_observer, tmp_path, dataset, action
):
    row = operations.operation(tutorial_observer, tmp_path, 'held-guard/' + action, dataset)
    assert row['heldProjectSignals'] == 0, (
        'No ordinary project signal invokes a listener while the value is held; '
        'only calculation and adjusting-control signals are permitted'
    )
    assert row['heldDirty'], (
        'An initially clean project reports its real unsaved held edit before release'
    )
    assert (row['heldFields'], row['heldModified'], row['heldEdited']) == (0, 0, 0), (
        'Reading truthful held dirty state never restores per-step change notifications'
    )
    assert row['preserved'], (
        'A delayed browser open cannot replace the owner edited during its held value'
    )
    assert row['oneUndo'], 'One Undo still reverses the complete held operation'
    if action == 'aside':
        assert row['asideDirty'], 'Loss prevention also sees the held edit of a set-aside project'
    if action == 'save':
        assert row['saved'] and row['reopened'], (
            'Saving during a hold persists the independently authored final value 10.3'
        )
        assert not row['releasedDirty'], (
            'Release does not invent another edit after saving the hold'
        )
    else:
        assert row['releasedDirty'], 'An unsaved held value remains dirty after release'
