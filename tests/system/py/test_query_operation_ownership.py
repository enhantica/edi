"""Index preparation, search and supersession retain their query generation."""

import pytest

from tests.system.py import test_operation_contracts as operations

tutorial_observer = operations.tutorial_observer


@pytest.mark.parametrize('entry', ['prepare', 'search'])
@pytest.mark.parametrize('retirement', ['cancel', 'reset'])
@pytest.mark.parametrize('ending', ['success', 'failure'])
def test_cancelled_query_cannot_publish_from_its_index_continuation(
    tutorial_observer, tmp_path, entry, retirement, ending
):
    row = operations.operation(
        tutorial_observer,
        tmp_path,
        f'query-owner/{entry}/{retirement}/old-first/{ending}',
        'powder',
    )
    assert row['reports'] == 0 and row['stateUnchanged'], (
        'A cancelled preparation or search emits no late query UI publication'
    )
    assert row['writes'] == 0, 'A cancelled index continuation writes no request-owned files'


@pytest.mark.parametrize('order', ['old-first', 'new-first'])
@pytest.mark.parametrize('ending', ['success', 'failure'])
def test_older_index_reply_cannot_replace_the_current_query(
    tutorial_observer, tmp_path, order, ending
):
    row = operations.operation(
        tutorial_observer, tmp_path, f'query-owner/search/newer/{order}/{ending}', 'powder'
    )
    assert row['searched'] and row['rows'] == 0, (
        'The current impossible-name query completes with its independently empty result set'
    )
    assert row['neverPublishedOlderRows'] and row['currentStayedStable'], (
        'An earlier index success or error cannot publish the old rows '
        'or disturb the current result'
    )
