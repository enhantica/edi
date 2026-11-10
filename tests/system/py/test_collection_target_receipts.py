"""A fetch receipt belongs to the original objects and declarations, never their shared ID."""

import hashlib

import pytest

from tests.system.py import test_operation_contracts as operations

tutorial_observer = operations.tutorial_observer
CASES = [
    ('pre-existing', 'success', 'none'),
    ('pre-existing', 'failure', 'none'),
    ('retry', 'success', 'none'),
    ('added', 'success', 'none'),
    ('different', 'success', 'none'),
    ('different', 'partial', 'none'),
    ('different', 'failure', 'none'),
    ('reindex', 'success', 'none'),
    ('stop', 'success', 'none'),
] + [
    ('pre-existing', 'success', mutation + '-' + boundary)
    for mutation in ('remove', 'entry', 'digest')
    for boundary in ('publish', 'callback')
]


@pytest.mark.parametrize('case', CASES, ids=['-'.join(row) for row in CASES])
@pytest.mark.parametrize('producer', ['fetch', 'download', 'fit'])
@pytest.mark.parametrize('order', ['forward', 'reverse'])
def test_each_terminal_receipt_requires_its_original_exact_targets(
    tutorial_observer, tmp_path, monkeypatch, case, producer, order
):
    scenario, outcome, mutation = case
    monkeypatch.setenv('XDG_CACHE_HOME', str(tmp_path / 'independent-cache'))
    row = operations.operation(
        tutorial_observer,
        tmp_path,
        f'exact-collection-owner/{scenario}/{producer}/{outcome}/{order}/{mutation}',
        'powder',
    )
    assert row['supported'], 'The target witness reaches the actual collection request boundary'
    assert row['distinctObjects'], (
        'Separate target receipts retain distinct actual experiment objects even when IDs agree'
    )
    assert row['settled'] and len(row['reports']) == (3 if scenario == 'retry' else 2), (
        'Every actually admitted current request reaches its bounded terminal outcome'
    )
    expected_x = [[17.5, 4, 0.5], [18, 9, 1.25], [18.5, 16, 2.5]]
    expected_y = [[17.5, 25, 0.5], [18, 36, 1.25], [18.5, 49, 2.5]]
    for report in row['reports']:
        assert report['calls'] <= 1, 'An exact request never receives its terminal result twice'
        if report['stillCurrent']:
            assert report['calls'] == 1, (
                'Every current exact-target request reaches its terminal transport outcome'
            )
        elif not report['calls']:
            assert row['mutationAccepted'], (
                'Only an actually invalidated target set may retire without a later report'
            )
        assert not report['falseSuccess'], (
            'Success requires every originally requested object, declaration, digest and authored '
            'row, even after publication or an earlier callback changed the project'
        )
        if not report['error']:
            assert all(
                target['present']
                and target['sameDeclaration']
                and target['rows'] == target['expected']
                for target in report['targets']
            ), 'A successful receipt proves every separate original target at completion itself'
            for target in report['targets']:
                is_y = scenario == 'different' and target['label'] == 'second_target'
                payload = (
                    b'17.5 25 .5\n18 36 1.25\n18.5 49 2.5\n'
                    if is_y
                    else (b'17.5 4 .5\n18 9 1.25\n18.5 16 2.5\n')
                )
                assert target['rows'] == (expected_y if is_y else expected_x), (
                    'Each successful original object retains its independent authored row oracle'
                )
                assert (target['entry'], target['digest']) == (
                    'owned-Y' if is_y else 'owned-X',
                    hashlib.sha256(payload).hexdigest(),
                ), (
                    'The successful object still declares its independently authored '
                    'entry and digest'
                )
    if outcome == 'success' and mutation == 'none' and scenario != 'retry':
        assert all(
            not report['error'] or report['refusedWhileBusy'] for report in row['reports']
        ), 'A valid unchanged request succeeds or is explicitly declined during admission'
        assert all(
            target['present']
            and target['sameDeclaration']
            and target['rows'] == target['expected']
            for target in row['finalTargets']
        ), 'Each admitted current object receives exactly its authored measured rows'
    if scenario in {'added', 'different'}:
        assert row['added'] or row['admissionRefused'], (
            'A new target is admitted or explicitly refused during the active operation'
        )
    if scenario == 'reindex':
        assert row['reindexed'] or row['reindexRefused'], (
            'The index-shifting edit reaches the real project or receives an explicit refusal'
        )
    if scenario in {'pre-existing', 'retry'}:
        assert all(report['wantedCount'] == 2 for report in row['reports'][:2]), (
            'Both existing equal-ID objects belong to each request before the first transport'
        )
    if scenario == 'retry':
        assert row['retryIssued'] and len(row['partialTargets']) == 2, (
            'The retry begins only after an actual terminal partial completion of two originals'
        )
        expected_x = [[17.5, 4, 0.5], [18, 9, 1.25], [18.5, 16, 2.5]]
        assert [target['rows'] for target in row['partialTargets']] == [expected_x, []], (
            'Partial completion observes the filled first object '
            'and the still-empty same-ID second'
        )
        assert all(report['error'] for report in row['reports'][:2]), (
            'One filled equal-ID object cannot satisfy either original two-object request'
        )
        assert row['reports'][-1]['wantedCount'] == 1 and not row['reports'][-1]['error'], (
            'A later real request retries the unfilled original object and reports its own result'
        )
        assert [target['rows'] for target in row['finalTargets']] == [expected_x, expected_x], (
            'Retry fills both original objects with independently authored rows, '
            'never a substitute'
        )
    if mutation != 'none':
        assert row['mutationEntered'], (
            'The exact-target accident reaches an actual publication or prior-waiter callback'
        )
        assert row['mutationAccepted'] or row['mutationRefused'], (
            'A fenced mutation is explicitly refused; an admitted mutation changes the original '
            'target rather than only an unrelated selected experiment'
        )
    assert row['fitStartsMissing'] == 0, (
        'The real fit producer cannot start from an unsatisfied or rebound exact target set'
    )
    assert row['fitStartsAfterStop'] == 0, (
        'A stopped fit cannot start later from a successful shared data-fetch completion'
    )
    assert row['staleReports'] == 0, 'Retired exact-target operations publish no terminal report'
    if outcome == 'failure':
        assert all(report['error'] for report in row['reports']), (
            'A failed exact-target transport never becomes successful through retry or selection'
        )


@pytest.mark.parametrize(
    'control', ['first-only', 'second-only', 'removed', 'replacement', 'entry', 'digest']
)
def test_target_observer_cannot_substitute_a_matching_id_for_an_original_object(
    tutorial_observer, tmp_path, monkeypatch, control
):
    monkeypatch.setenv('XDG_CACHE_HOME', str(tmp_path / 'observer-control-cache'))
    row = operations.operation(
        tutorial_observer,
        tmp_path,
        f'exact-collection-owner/observer/fetch/success/forward/{control}',
        'powder',
    )
    assert row['supported'] and row['distinctObjects'], (
        'The observer control constructs two independent original objects with the same ID'
    )
    records = row['observer']
    assert [item['label'] for item in records] == ['first_target', 'second_target'], (
        'The observer retains every original object in order without a resource-keyed overwrite'
    )
    assert [item['present'] for item in records] == [
        control not in {'removed', 'replacement'},
        True,
    ], 'A matching-ID replacement never stands in for an original object that left the project'
    assert [item['sameDeclaration'] for item in records] == [
        control not in {'removed', 'replacement', 'entry', 'digest'},
        True,
    ], 'Each original target retains its own admitted entry and digest'
    expected = [[17.5, 4, 0.5], [18, 9, 1.25], [18.5, 16, 2.5]]
    assert records[0]['rows'] == (
        expected if control in {'first-only', 'entry', 'digest'} else []
    ), 'The first object is observed directly, including removal and declaration changes'
    assert records[1]['rows'] == (expected if control == 'second-only' else []), (
        'Hydrating only one same-ID object cannot manufacture rows on its independent neighbor'
    )
