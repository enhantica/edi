"""Untitled autosave and recovery through the real Session storage boundaries."""

import pytest

from tests.system.py import test_project_transactions as transactions

source_qualified_observer = transactions.observer


@pytest.fixture(scope='module')
def recovery(source_qualified_observer, tmp_path_factory):
    return transactions.observe(
        source_qualified_observer,
        'untitled-recovery',
        tmp_path_factory.mktemp('untitled-recovery'),
    )[0]


def test_untitled_edits_reach_autosave(recovery):
    assert recovery['untitled'] and recovery['needsSaveAs'], (
        'Opening Project begins with genuine untitled work before autosave'
    )
    assert recovery.get('writesRecovery') and recovery.get('snapshotExists'), (
        'The normal edit timer writes a complete snapshot before the first named Save'
    )
    assert recovery.get('key'), 'Untitled recovery has a nonempty independently addressable key'


def test_untitled_recovery_restores_science_and_save_state(recovery):
    assert recovery['untitled'] and recovery.get('readsRecovery'), (
        'Untitled work is loadable through the actual recovery entrance'
    )
    assert recovery['after'] == recovery['before'], (
        'Recovery preserves the complete scientific state captured before autosave'
    )
    assert recovery['title'] == 'Unsaved neutron work', 'Recovery keeps the unsaved project title'
    assert recovery['modified'] and recovery['stillUntitled'], (
        'Recovering untitled work keeps dirty state and still asks for its first named Save'
    )
