"""The service-query count, row, identity-list and paging paths retain their owner."""

import pytest

from tests.system.py import test_operation_contracts as operations

tutorial_observer = operations.tutorial_observer
STAGES = ('count', 'rows', 'list', 'first-chunk', 'more')


@pytest.mark.parametrize('stage', STAGES)
@pytest.mark.parametrize('retirement', ['cancel', 'reset', 'kind', 'source', 'disabled'])
@pytest.mark.parametrize('ending', ['success', 'failure'])
def test_cancelled_cod_stage_cannot_publish_or_start_another_fetch(
    tutorial_observer, tmp_path, stage, retirement, ending
):
    row = operations.operation(
        tutorial_observer, tmp_path, f'cod-owner/{stage}/{retirement}/{ending}/old-first', 'powder'
    )
    assert row['reports'] == 0 and row['stateUnchanged'], (
        'A cancelled service-query continuation publishes no old rows, paging state or error'
    )
    assert row['newFetches'] == 0, (
        'An old count, list or page cannot start another transport after its request is cancelled'
    )


@pytest.mark.parametrize('stage', STAGES)
@pytest.mark.parametrize('order', ['old-first', 'new-first'])
@pytest.mark.parametrize('ending', ['success', 'failure'])
def test_new_cod_query_survives_every_older_service_stage(
    tutorial_observer, tmp_path, stage, order, ending
):
    row = operations.operation(
        tutorial_observer, tmp_path, f'cod-owner/{stage}/newer/{ending}/{order}', 'powder'
    )
    assert row['searched'] and row['ids'] == [], (
        'The newer query completes its independently empty result without any older identity'
    )
    assert row['currentStable'] and row['neverOld'], (
        'An older count, row, list or page success or error cannot disturb the current query'
    )


@pytest.mark.parametrize('stage', STAGES)
def test_current_cod_stage_still_completes_its_real_protocol(tutorial_observer, tmp_path, stage):
    row = operations.operation(
        tutorial_observer, tmp_path, f'cod-owner/{stage}/none/success/old-first', 'powder'
    )
    count = 200 if stage == 'more' else 100 if stage in {'list', 'first-chunk'} else 2
    assert row['ids'] == [str(9100000 + at) for at in range(count)], (
        'Every current service-query stage retains exactly the independently authored '
        'identity order'
    )
