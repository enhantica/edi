"""Every joined collection request retains its admitted dependencies and owner."""

import pytest

from tests.system.py import test_operation_contracts as operations

tutorial_observer = operations.tutorial_observer
PRODUCERS = ('fetch', 'download', 'fit')
X = [[17.5, 4, 0.5], [18, 9, 1.25], [18.5, 16, 2.5]]
Y = [[17.5, 25, 0.5], [18, 36, 1.25], [18.5, 49, 2.5]]


def observe(binary, tmp_path, monkeypatch, producers, join, outcome, retirement):
    first, second = producers
    monkeypatch.setenv('XDG_CACHE_HOME', str(tmp_path / 'isolated-cache'))
    row = operations.operation(
        binary,
        tmp_path,
        f'collection-owner/{first}/{second}/{join}/{outcome}/{retirement}',
        'powder',
    )
    assert row['supported'], 'The collection operation reaches its actual request producer'
    return row


@pytest.mark.parametrize('first', PRODUCERS)
@pytest.mark.parametrize('second', PRODUCERS)
@pytest.mark.parametrize('join', ['same', 'added', 'selected', 'replace'])
@pytest.mark.parametrize('outcome', ['success', 'partial', 'failure'])
def test_each_fetch_waiter_requires_its_own_complete_admitted_input_set(
    tutorial_observer, tmp_path, monkeypatch, first, second, join, outcome
):
    row = observe(tutorial_observer, tmp_path, monkeypatch, (first, second), join, outcome, 'none')
    assert row['settled'], (
        'The bounded admitted requests all reach their terminal transport outcomes'
    )
    assert len(row['reports']) == 2, (
        'Both actual request admissions retain separate terminal witnesses'
    )
    for index, report in enumerate(row['reports']):
        assert report['calls'] <= 1, 'A coalesced request never delivers a terminal result twice'
        if not row['xRemoved'] or index != 0:
            assert report['calls'] == 1, (
                'Every current terminal waiter settles rather than waiting forever'
            )
        assert not report['successMissing'], (
            'A successful waiter has every dependency admitted by that request, '
            'including later additions'
        )
    if outcome == 'success':
        final = row['reports'][-1]
        assert final['calls'] == 1, (
            'Every current or explicitly refused request has a terminal receipt'
        )
        if final['error']:
            assert final['refusedWhileBusy'], (
                'Only an explicit immediate refusal during an active operation '
                'may decline a valid join'
            )
        else:
            label = 'Y' if row['yAdmitted'] else 'X'
            assert [target['rows'] for target in row['data'] if target['label'] == label] == [
                Y if row['yAdmitted'] else X
            ], 'An accepted waiter publishes its own independently authored measured rows'
    if not row['xRemoved'] and outcome != 'failure':
        assert [target['rows'] for target in row['data'] if target['label'] == 'X'] == [X], (
            'Partial completion retains the exact successful X rows'
        )
    if outcome == 'failure':
        assert row['reports'][-1]['error'], (
            'A refused transport cannot be reported as a successful fetch'
        )


@pytest.mark.parametrize('signal', ['pattern', 'missing', 'error'])
@pytest.mark.parametrize('retirement', ['close', 'replace'])
@pytest.mark.parametrize('producer', ['download', 'fit'])
@pytest.mark.parametrize('partial', [False, True], ids=['one-dependency', 'partial-dependencies'])
def test_complete_fetch_publication_stack_retains_and_rechecks_its_owner(
    tutorial_observer, tmp_path, monkeypatch, signal, retirement, producer, partial
):
    outcome = 'failure' if signal == 'error' else 'partial' if partial else 'success'
    row = observe(
        tutorial_observer,
        tmp_path,
        monkeypatch,
        (producer, 'fetch'),
        'added' if partial else 'same',
        outcome,
        retirement + '-' + signal,
    )
    assert row['publicationEntered'], (
        'Retirement must occur inside the real data, chart or error publication stack'
    )
    if row['retirementRefused']:
        assert row['refusalVisible'] and row['settled'], (
            'A fenced retirement is explicitly refused and its valid fetch still settles'
        )
        assert all(r['calls'] == 1 and not r['successMissing'] for r in row['reports']), (
            'Refusing retirement preserves truthful terminal delivery to every current waiter'
        )
    if signal == 'pattern':
        assert row['aliveInside'], (
            'The multi-step data publisher retains its exact owner through subscriber reentry'
        )
    assert row['lateReports'] == 0, (
        'A retired fetch reports nothing to a later waiter or successor'
    )
    assert row['successorIntact'], 'A stale hydration or preview cannot change the successor files'


@pytest.mark.parametrize(
    ('first', 'second'),
    [('fit', 'download'), ('download', 'fit'), ('fit', 'fit'), ('fetch', 'fit'), ('fit', 'fetch')],
)
@pytest.mark.parametrize('join', ['same', 'added'])
def test_stop_cancels_only_its_fit_wait_while_other_fetch_requests_finish(
    tutorial_observer, tmp_path, monkeypatch, first, second, join
):
    row = observe(
        tutorial_observer, tmp_path, monkeypatch, (first, second), join, 'success', 'stop'
    )
    assert row['startsAfterStop'] == 0, 'A stopped fit never starts from a later download callback'
    assert row['settled'] and all(r['calls'] == 1 for r in row['reports']), (
        'Stopping a fit preserves the terminal delivery of every other admitted fetch request'
    )
    assert all(not r['successMissing'] for r in row['reports']), (
        'Stop cannot make a shared request falsely succeed with missing data'
    )
