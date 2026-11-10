"""Publication reentry cannot let an old request use or report its successor."""

import pytest

from tests.system.py import test_operation_contracts as operations
from tests.system.py.test_sealed_publication_contract import ROUTES as CARRIED_ROUTES

tutorial_observer = operations.tutorial_observer
ROUTES = tuple(dict.fromkeys(('save', 'unsaved-folder', *CARRIED_ROUTES)))


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('signal', ['edited', 'modified'])
@pytest.mark.parametrize('action', ['close', 'replace'])
def test_every_save_retains_and_rechecks_its_owner_across_held_settlement(
    tutorial_observer, tmp_path, route, signal, action
):
    row = operations.operation(
        tutorial_observer, tmp_path, f'owner-settlement/{route}/{signal}/{action}'
    )
    assert row['entered'], 'Each save must exercise the actual held-settlement publication stack'
    assert row['aliveInCallback'], (
        'The old owner stays alive until its entire active publication stack has unwound'
    )
    if not row['retired']:
        assert row['refusalVisible'] and row['ownerPreservedAtRefusal'], (
            'A fenced retirement request is explicitly refused while preserving its current owner'
        )
        return
    assert row['writesAfterRetirement'] == 0, (
        'A request retired during settlement cannot write any private or user output afterwards'
    )
    assert row['reportsAfterRetirement'] == 0, (
        'A stale save cannot publish a question or model report for its successor'
    )
    assert row['userTreesIntact'], (
        'The cancelled request cannot change original, destination or successor user files'
    )
