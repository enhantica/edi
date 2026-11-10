"""Project-file and single/batch web producers cannot outlive their request owners."""

import pytest

from tests.system.py import test_operation_contracts as operations

tutorial_observer = operations.tutorial_observer
PRODUCERS = (
    'example',
    'example-aside',
    'structure',
    'experiment',
    'data',
    'new-data',
    'batch-data',
)
CASES = [(producer, retirement) for producer in PRODUCERS for retirement in ('close', 'replace')]
CASES += [(producer, 'cancel') for producer in PRODUCERS if not producer.startswith('example')]
CASES += [('data', 'target-removed'), ('batch-data', 'target-removed')]


@pytest.mark.parametrize(('producer', 'retirement'), CASES)
@pytest.mark.parametrize('ending', ['success', 'failure'])
def test_every_file_fetch_stops_before_stale_materialization_or_reporting(
    tutorial_observer, tmp_path, producer, retirement, ending
):
    row = operations.operation(
        tutorial_observer, tmp_path, f'network-owner/{producer}/{retirement}/{ending}', 'powder'
    )
    assert row['entered'] and row['settled'], (
        'Each public fetch reaches and finishes the actual held transport continuation'
    )
    if retirement in {'close', 'replace'}:
        assert row['aliveInside'], (
            'The request remains on a real active publication stack during owner retirement'
        )
    if not row['retired']:
        assert row['refusalVisible'] and row['ownerPreservedAtRefusal'], (
            'A fenced close, replacement or removal is explicitly refused and retains its owner'
        )
        if ending == 'success':
            assert row['delivered'] > 0, (
                'Refusing retirement preserves successful delivery to the still-current request'
            )
        else:
            assert row['reports'] > 0, (
                'The still-current request reports its own transport refusal'
            )
        assert row['userFilesIntact'], (
            'A refused lifecycle request preserves original and successor user files'
        )
        return
    assert row['writes'] == 0, (
        'A stale project-file or web-load request never materializes bytes '
        'before a late consumer guard'
    )
    assert row['reports'] == 0, (
        'A cancelled request cannot publish a file, error or terminal UI report'
    )
    assert row['userFilesIntact'], (
        'Late fetch completion preserves original and successor user files'
    )


@pytest.mark.parametrize('producer', PRODUCERS)
def test_each_current_file_fetch_still_delivers_its_checked_input(
    tutorial_observer, tmp_path, producer
):
    row = operations.operation(
        tutorial_observer, tmp_path, f'network-owner/{producer}/none/success', 'powder'
    )
    assert row['settled'] and row['delivered'] > 0, (
        'An active request is admitted and delivers its actual checked input '
    )
