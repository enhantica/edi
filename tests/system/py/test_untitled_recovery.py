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
    assert recovery['projectPageEmpty'], 'Opening Project alone creates no work container'
    assert recovery['untitled'] and recovery['needsSaveAs'], (
        'Opening Structure begins genuine unnamed work before autosave'
    )
    assert isinstance(recovery['defaultTitle'], str), 'The default project title remains text'
    assert not recovery['defaultTitle'], 'Unnamed work has no invented project title'
    assert recovery['before']['structures'] == 1 and recovery['before']['cells'][0][0] == 7.125, (
        'Autosave starts from the actual nontrivial cell edit in the untitled structure'
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
        'Recovery preserves the authored cell values and structure/experiment inventory'
    )
    assert recovery['title'] == 'Unsaved neutron work', 'Recovery keeps the unsaved project title'
    assert recovery['modified'] and recovery['stillUntitled'], (
        'Recovering untitled work keeps dirty state and still asks for its first named Save'
    )
