"""Real trigger payloads must reach concurrency and execution refusals."""

import copy

import pytest

from tests.system.py.ci_execution_contract import concurrency_errors, contexts


def trigger_control():
    return {
        'name': 'payload control',
        'on': {
            'pull_request': None,
            'push': {'branches': ['main', 'slot-*']},
            'schedule': [{'cron': '17 2 * * *'}, {'cron': '41 5 * * 2'}],
            'workflow_dispatch': None,
        },
        'concurrency': {
            'group': 'workflow-${{ github.ref }}-${{ github.run_id }}',
            'cancel-in-progress': False,
        },
        'jobs': {
            'full': {
                'runs-on': 'ubuntu-latest',
                'concurrency': {
                    'group': 'job-${{ github.ref }}-${{ github.run_id }}',
                    'cancel-in-progress': False,
                },
            }
        },
    }


@pytest.mark.parametrize('scope', ['workflow', 'job'])
@pytest.mark.parametrize('damage', ['cancel', 'replace'])
@pytest.mark.parametrize('cron', ['17 2 * * *', '41 5 * * 2'], ids=['cron-a', 'cron-b'])
def test_declared_crons_reach_both_concurrency_boundaries(scope, damage, cron):
    workflow = trigger_control()
    assert not concurrency_errors([workflow]), (
        'CI policy: every declared cron admits with unique non-cancelling run identities'
    )
    owner = workflow if scope == 'workflow' else workflow['jobs']['full']
    condition = "github.event.schedule == '" + cron + "'"
    if damage == 'cancel':
        owner['concurrency']['cancel-in-progress'] = '${{ ' + condition + ' }}'
    else:
        owner['concurrency']['group'] = (
            scope + '-${{ github.ref }}-${{ ' + condition + ' && 0 || github.run_id }}'
        )
        # Use a truthy constant: Actions' ternary idiom does not select numeric zero.
        owner['concurrency']['group'] = owner['concurrency']['group'].replace('&& 0', '&& 1')
    assert concurrency_errors([workflow]), (
        'CI policy: cancellation or queued replacement on either actual cron must refuse'
    )


@pytest.mark.parametrize('scope', ['workflow', 'job'])
@pytest.mark.parametrize('damage', ['cancel', 'replace'])
@pytest.mark.parametrize('event', ['push', 'schedule', 'workflow_dispatch'])
@pytest.mark.parametrize('field', ['number', 'head.sha', 'head.repo.fork'])
def test_absent_pr_fields_reach_non_pr_concurrency_boundaries(scope, damage, event, field):
    workflow = trigger_control()
    assert not concurrency_errors([workflow]), (
        'CI policy: event-appropriate payloads admit before non-PR cancellation damage'
    )
    owner = workflow if scope == 'workflow' else workflow['jobs']['full']
    condition = (
        "github.event_name == '" + event + "' && github.event.pull_request." + field + " == ''"
    )
    if damage == 'cancel':
        owner['concurrency']['cancel-in-progress'] = '${{ ' + condition + ' }}'
    else:
        owner['concurrency']['group'] = (
            scope + '-${{ github.ref }}-${{ ' + condition + ' && 1 || github.run_id }}'
        )
    assert concurrency_errors([workflow]), (
        'CI policy: missing PR properties on non-PR events cannot suppress a concurrency refusal'
    )


@pytest.mark.parametrize('scope', ['workflow', 'job'])
@pytest.mark.parametrize(
    'trigger',
    [
        {'push': {'branches': ['release/**']}},
        {'push': {'branches': ['main', 'release/**']}},
        {'push': {'branches-ignore': ['*']}},
        {'pull_request': {'branches': ['release/**']}},
        {'schedule': []},
        {'schedule': [{'cron': ''}]},
    ],
)
def test_unrepresented_trigger_forms_refuse_instead_of_certifying_an_empty_loop(scope, trigger):
    workflow = trigger_control()
    assert not concurrency_errors([workflow]), (
        'CI policy: supported trigger representatives admit before an unproved form is planted'
    )
    workflow['on'] = copy.deepcopy(trigger)
    owner = workflow if scope == 'workflow' else workflow['jobs']['full']
    owner['concurrency']['cancel-in-progress'] = True
    with pytest.raises((ValueError, TypeError)):
        concurrency_errors([workflow])


@pytest.mark.parametrize('event', ['pull_request', 'push', 'schedule', 'workflow_dispatch'])
def test_payload_controls_preserve_only_event_appropriate_pr_and_schedule_fields(event):
    rows = list(
        contexts(trigger_control(), event, 'slot-a' if event == 'pull_request' else 'main')
    )
    assert rows, 'CI policy: each supported event produces concrete contexts'
    assert {ctx['github.event.schedule'] for _, _, ctx, _ in rows} == (
        {'17 2 * * *', '41 5 * * 2'} if event == 'schedule' else {''}
    ), 'CI policy: scheduled contexts use every declared cron and other events have none'
    for _, _, ctx, _ in rows:
        assert ctx['github.event.pull_request.number'] == (
            79 if event == 'pull_request' else ''
        ), 'CI policy: a PR number exists only in a pull-request payload'
        assert ctx['github.event.pull_request.head.sha'] == (
            '79' * 20 if event == 'pull_request' else ''
        ), 'CI policy: a PR head exists only in a pull-request payload'
        assert ctx['github.event.pull_request.head.repo.fork'] == (
            False if event == 'pull_request' else ''
        ), 'CI policy: non-PR payloads do not invent a pull-request fork flag'
