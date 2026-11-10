"""Loss-prevention state remains truthful inside the release publication itself."""

import pytest

from tests.system.py import test_operation_contracts as operations

tutorial_observer = operations.tutorial_observer


@pytest.mark.parametrize('action', ['release', 'save'])
@pytest.mark.parametrize('dataset', ['powder', 'single-crystal', 'scan'])
def test_every_settlement_listener_sees_the_pending_edit_as_unsaved(
    tutorial_observer, tmp_path, dataset, action
):
    row = operations.operation(tutorial_observer, tmp_path, f'held-guard/{action}', dataset)
    assert row['settlementPublications'] > 0, (
        'The guard query must run inside the actual settlement edited announcement'
    )
    assert row['settlementDirty'], (
        'Every loss-prevention read inside settlement sees the held edit as unsaved '
        'before any save has published it'
    )
