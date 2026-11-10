"""A real fit's final publication and every Save share one operation boundary."""

import pytest

from tests.system.py import test_operation_contracts as operations

tutorial_observer = operations.tutorial_observer
ENTRIES = [
    ('ordinary', 'running-false'),
    ('native', 'running-false'),
    ('native', 'native-result'),
    ('visible-native', 'running-false'),
    ('visible-native', 'native-result'),
]


@pytest.mark.parametrize(('entry', 'moment'), ENTRIES)
@pytest.mark.parametrize('ending', ['success', 'error', 'stop'])
@pytest.mark.parametrize(
    'route', ['save', 'save-archive', 'web-save-browser', 'assistant-folder', 'assistant-zip']
)
def test_a_fit_final_write_cannot_follow_an_admitted_save_snapshot(
    tutorial_observer, tmp_path, entry, moment, ending, route
):
    row = operations.operation(
        tutorial_observer, tmp_path, f'fit-ending/{entry}/{moment}/{ending}/{route}', 'powder'
    )
    assert row['reached'] and row['polls'] >= 1, (
        'The witness reaches both the actual optimizer poll and its original terminal notification'
    )
    assert row[{'success': 'success', 'error': 'error', 'stop': 'cancelled'}[ending]], (
        'The actual optimizer delivers the independently requested success, error or Stop outcome'
    )
    if ending == 'stop':
        assert row['stopped'], (
            'Stop is delivered to the original real fit before cancellation is polled'
        )
    if ending == 'error':
        assert 'Independently requested worker failure' in row['terminalError'], (
            'Failure is the real worker report from the injected public seam'
        )
    if row['firstCompleted']:
        assert row['firstClean'] and row['firstDurable'] == row['afterWrite'], (
            'The first actual publication leaves a clean live model '
            'matching its durable scientific data'
        )
        assert row['firstDescription'] == row['firstLiveDescription'], (
            'No final fit continuation overwrites metadata after the first save publishes it'
        )
        assert row['parametersAtPlan'] == row['afterTerminal'] == row['afterWrite'], (
            'After Save plans and publishes, no fit continuation can rewrite '
            'values, uncertainties or flags'
        )
    else:
        assert (
            row['explicitRefusal'] and row['jobsAtTerminal'] == 0 and row['stagesAtTerminal'] == 0
        ), 'A Save fenced during terminal publication refuses visibly before staging or transport'
    assert row['retry'], (
        'Every terminal outcome releases its hold so a later real Save can complete'
    )
    assert row['final'] == row['durable'] and not row['modified'], (
        'The actual post-terminal Save adopts exactly the independently '
        'reopened scientific snapshot'
    )
    assert row['durableDescription'] == 'Independently authored fit-ending save state', (
        'The completed post-terminal Save retains the original authored metadata'
    )
