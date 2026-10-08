"""A view may read every old row inside Qt's structural notifications."""

import pytest

from tests.fixtures.scan_app.accident_inputs import project
from tests.fixtures.scan_app.harness import Harness, files


@pytest.fixture(scope='module')
def row_observer(tmp_path_factory):
    root = tmp_path_factory.mktemp('scan-row-generation')
    return root, Harness(root)


def observe(row_observer, route, change, access):
    root, harness = row_observer
    target = project(root / f'{route}-{change}-{access}', fitted=True)
    names = [path.name for path in files(target)]
    observed = harness.invoke('row-generation', target, route, change, access, deadline=120)
    assert observed.get('checkedContainers'), (
        'Scan row lifetime: the native observer must check logical vector bounds, '
        'including erased elements whose storage remains allocated'
    )
    assert not observed.get('error') and observed['settled'], (
        'Scan row lifetime: the actual save, Undo or template replacement must complete '
        'and settle before final rows are judged'
    )
    assert [row['file'] for row in observed['before']] == names, (
        'Scan row lifetime: the starting table must show all three independently authored files'
    )
    return observed, names


def check_notifications(observed, names, expected):
    for event in observed['notifications']:
        assert len(event['rows']) == event['count'], (
            'Scan row lifetime: the observer must read every valid row during each notification'
        )
        for row in event['rows']:
            index = row['row']
            allowed = {''}
            if index < len(names):
                allowed.add(names[index])
            if index < len(expected):
                allowed.add(expected[index])
            assert row['file'] in allowed, (
                'Scan row lifetime: notification reads must return an identified old/new '
                'file or a defined empty value, never unrelated or destroyed storage'
            )
            assert row['experimentName'] in {'', 'd20'}, (
                'Scan row lifetime: notification reads must use a live template QObject '
                'or a defined empty value'
            )


@pytest.mark.parametrize('route', ['save', 'save-as', 'reset-undo', 'reopen'])
@pytest.mark.parametrize('change', ['shrink', 'empty', 'grow', 'same'])
@pytest.mark.parametrize('access', ['get', 'data'])
def test_relisted_scan_rows_remain_readable_during_notifications(
    row_observer, route, change, access
):
    observed, names = observe(row_observer, route, change, access)
    expected = {
        'shrink': names[:2],
        'empty': ['d20.edi'],
        'grow': [*names, 'zz-added.dat'],
        'same': [*names[:2], 'zz-replacement.dat'],
    }[change]
    check_notifications(observed, names, expected)
    assert [row['file'] for row in observed['after']] == expected, (
        'Scan row lifetime: the final table must reflect the actual new file list; '
        'an empty scan falls back to its one ordinary template experiment'
    )
    assert observed['scan'] == (change != 'empty'), (
        'Scan row lifetime: scan admission must follow whether any files remain'
    )
    events = observed['notifications']
    if change in {'shrink', 'empty'}:
        removals = [event for event in events if event['signal'] == 'removing']
        assert removals and removals[0]['last'] == 2 and removals[0]['count'] == 3, (
            'Scan row lifetime: exercise rowsAboutToBeRemoved while the old last row is valid'
        )
        assert removals[0]['rows'][2]['file'] in {'', names[2]}, (
            'Scan row lifetime: the disappearing last file must read as its old name '
            'or a defined empty value inside rowsAboutToBeRemoved'
        )
    elif change == 'grow':
        assert any(event['signal'] == 'inserted' and event['count'] == 4 for event in events), (
            'Scan row lifetime: growth must exercise reads inside real insertion notifications'
        )
    else:
        assert any(event['signal'] == 'changed' for event in events), (
            'Scan row lifetime: same-sized re-listing must publish and expose the changed file'
        )
    if route == 'reopen':
        assert [row['file'] for row in observed['reopened']] == expected, (
            'Scan row lifetime: reopening must preserve the re-listed table '
            'and its file identities'
        )


@pytest.mark.parametrize('access', ['get', 'data'])
def test_template_replacement_keeps_notification_rows_and_qobjects_readable(row_observer, access):
    observed, names = observe(row_observer, 'replace', 'template', access)
    check_notifications(observed, names, names)
    assert observed['replaced'], (
        'Scan row lifetime: the control must destroy the old template QObject '
        'and install its successor'
    )
    assert observed['notifications'] and [row['file'] for row in observed['after']] == names, (
        'Scan row lifetime: structural template replacement must retain every dataset identity '
        'through its notification reads'
    )
    assert all(row['experimentName'] == 'd20' for row in observed['after']), (
        'Scan row lifetime: final dataset rows must point to the live replacement template'
    )
