"""Actions semantics, independently fixed from its expression and concurrency contracts."""

import copy

import pytest

from tests.system.py.ci_execution_contract import concurrency_errors, render, value
from tests.system.py.test_ci_context_boundaries import trigger_control


@pytest.mark.parametrize(
    ('expression', 'expected'),
    [
        ("'' == false", True),
        ("'' != false", False),
        ("'' == 0", True),
        ('false == null', True),
        ("'1' == true", True),
        ("'2.5' == 2.5", True),
        ("'not-a-number' == 0", False),
        ("'00' == 0", True),
        ("'false' == false", False),
        ("github.ref == 'REFS/HEADS/MAIN'", True),
        ("'true' == 'TRUE'", True),
        ('github.event.pull_request.head.repo.fork == false', True),
        ("false && 'unused' || github.run_id", 790),
        ("true && 'fixed-group' || github.run_id", 'fixed-group'),
        ("'' || 'fallback'", 'fallback'),
        ("0 || 'fallback'", 'fallback'),
        ("'false' && 'selected'", 'selected'),
        ("!''", True),
        ("' ' == false", True),
        ("'\t' == null", True),
        ("'01.00' == true", True),
        ("'+1' == true", True),
        ("'.5' == 0.5", True),
        ("'1.' == true", True),
        ("'1e0' == true", True),
    ],
    ids=[
        'value-1',
        'value-2',
        'value-3',
        'value-4',
        'value-5',
        'value-6',
        'value-7',
        'value-8',
        'value-9',
        'value-10',
        'value-11',
        'value-12',
        'value-13',
        'value-14',
        'value-15',
        'value-16',
        'value-17',
        'value-18',
        'value-19',
        'value-20',
        'value-21',
        'value-22',
        'value-23',
        'value-24',
        'value-25',
    ],
)
def test_actions_value_contract_preserves_comparisons_and_selected_operands(expression, expected):
    result = value(
        expression,
        {
            'github.ref': 'refs/heads/main',
            'github.run_id': 790,
            'github.event.pull_request.head.repo.fork': '',
        },
    )
    assert type(result) is type(expected), (
        'CI policy: Actions logical operands retain their value types'
    )
    assert result == expected, (
        'CI policy: Actions comparisons and logical selection retain their declared values'
    )


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ('${{ true }}', 'true'),
        ('${{ false }}', 'false'),
        (True, 'true'),
        (False, 'false'),
        ('${{ null }}', ''),
        (None, ''),
        ('${{ github.run_id }}', '790'),
        ("${{ 'true false github.ref always()' }}", 'true false github.ref always()'),
        ("${{ 'It''s true' }}", "It's true"),
        ("prefix-${{ true && 'GROUP' || 'unused' }}", 'prefix-GROUP'),
    ],
    ids=[
        'render-1',
        'render-2',
        'render-3',
        'render-4',
        'render-5',
        'render-6',
        'render-7',
        'render-8',
        'render-9',
        'render-10',
    ],
)
def test_actions_rendering_preserves_literals_and_lowercase_boolean_results(source, expected):
    assert render(source, {'github.ref': 'refs/heads/main', 'github.run_id': 790}) == expected, (
        'CI policy: Actions rendering preserves literals and lowercase boolean values'
    )


@pytest.mark.parametrize(
    'source',
    [
        "contains(github.ref, 'main')",
        'true == false == false',
        'github.ref and true',
        '[true]',
        '"true"',
        "'0x1' == true",
        "'0o1' == true",
        "'Infinity' == 1",
        "'1e400' == true",
        "'ß' == 'SS'",
        "'\u0131' == 'I'",
    ],
    ids=[
        'unsupported-1',
        'unsupported-2',
        'unsupported-3',
        'unsupported-4',
        'unsupported-5',
        'unsupported-6',
        'unsupported-7',
        'unsupported-8',
        'unsupported-9',
        'unsupported-10',
        'unsupported-11',
    ],
)
def test_actions_unsupported_expression_forms_refuse(source):
    with pytest.raises((ValueError, SyntaxError)):
        value(source, {'github.ref': 'refs/heads/main'})


@pytest.mark.parametrize('scope', ['workflow', 'job'])
@pytest.mark.parametrize('damage', ['cancel', 'replace'])
@pytest.mark.parametrize('event', ['pull_request', 'push', 'schedule', 'workflow_dispatch'])
@pytest.mark.parametrize('comparison', ['loose', 'case'])
def test_actions_comparisons_cannot_hide_cancellation_or_replacement(
    scope, damage, event, comparison
):
    workflow = trigger_control()
    # This is edi's existing independent fork guard; absent non-PR fields remain absent.
    workflow['jobs']['full']['if'] = 'github.event.pull_request.head.repo.fork == false'
    assert not concurrency_errors([workflow]), (
        'CI policy: the existing edi fork guard admits valid PR and non-PR runs'
    )
    owner = workflow if scope == 'workflow' else workflow['jobs']['full']
    condition = (
        "github.event_name == '" + event + "' && github.event.pull_request.head.repo.fork == 0"
        if comparison == 'loose'
        else "github.ref == '"
        + ('REFS/PULL/79/MERGE' if event == 'pull_request' else 'REFS/HEADS/MAIN')
        + "'"
    )
    if damage == 'cancel':
        owner['concurrency']['cancel-in-progress'] = '${{ ' + condition + ' }}'
    else:
        owner['concurrency']['group'] = (
            scope + '-${{ github.ref }}-${{ ' + condition + " && 'fixed' || github.run_id }}"
        )
    assert concurrency_errors([workflow]), (
        'CI policy: Actions comparisons expose cancellation and queued replacement'
    )


@pytest.mark.parametrize('scope', ['workflow', 'job'])
@pytest.mark.parametrize('same_name', [False, True])
def test_actions_concurrency_groups_collide_without_case_even_with_repeated_job_names(
    scope, same_name
):
    workflow = trigger_control()
    if scope == 'workflow':
        workflows = [copy.deepcopy(workflow) for _ in range(3)]
        for index, item in enumerate(workflows):
            item['name'] = 'workflow-' + str(index)
            item['concurrency']['group'] = (
                'owner-' + str(index) + '-${{ github.ref }}-${{ github.run_id }}'
            )
            del item['jobs']['full']['concurrency']
        assert not concurrency_errors(workflows), (
            'CI policy: independent run-qualified workflow identities admit before case collision'
        )
        workflows[1]['concurrency']['group'] = workflows[0]['concurrency']['group'].replace(
            'owner', 'OWNER'
        )
        workflows[2]['concurrency']['group'] = workflows[0]['concurrency']['group'].replace(
            'owner', 'Owner'
        )
    else:
        del workflow['concurrency']
        workflow['jobs'] = {
            key: {
                'runs-on': 'ubuntu-latest',
                'name': 'same' if same_name else key,
                'concurrency': {
                    'group': key + '-${{ github.ref }}-${{ github.run_id }}',
                    'cancel-in-progress': False,
                },
            }
            for key in ('first', 'second', 'third')
        }
        workflows = [workflow]
        assert not concurrency_errors(workflows), (
            'CI policy: independent run-qualified job identities admit before case collision'
        )
        workflow['jobs']['second']['concurrency']['group'] = workflow['jobs']['first'][
            'concurrency'
        ]['group'].replace('first', 'FIRST')
        workflow['jobs']['third']['concurrency']['group'] = workflow['jobs']['first'][
            'concurrency'
        ]['group'].replace('first', 'First')
    assert concurrency_errors(workflows), (
        'CI policy: differently cased groups share one concurrency identity for distinct owners'
    )


@pytest.mark.parametrize('scope', ['workflow', 'job'])
def test_actions_case_only_successor_identity_changes_still_replace_queued_work(scope):
    workflow = trigger_control()
    assert not concurrency_errors([workflow]), (
        'CI policy: unique successor identities admit before a case-only spelling change'
    )
    owner = workflow if scope == 'workflow' else workflow['jobs']['full']
    owner['concurrency']['group'] = (
        scope + "-${{ github.ref }}-${{ github.run_id == 790 && 'pending' || 'PENDING' }}"
    )
    assert concurrency_errors([workflow]), (
        'CI policy: group letter case cannot preserve an earlier queued run'
    )


def test_actions_matrix_jobs_remain_distinct_owners_when_names_and_group_case_coincide():
    workflow = trigger_control()
    job = workflow['jobs']['full']
    job['name'] = 'same display name'
    job['strategy'] = {'matrix': {'lane': ['first', 'second', 'third']}}
    job['concurrency']['group'] = 'job-${{ matrix.lane }}-${{ github.ref }}-${{ github.run_id }}'
    assert not concurrency_errors([workflow]), (
        'CI policy: distinct matrix job identities admit before group collision'
    )
    job['concurrency']['group'] = (
        "job-${{ matrix.lane == 'first' && 'pending' || 'PENDING' }}"
        '-${{ github.ref }}-${{ github.run_id }}'
    )
    assert concurrency_errors([workflow]), (
        'CI policy: matrix jobs cannot share a case-equivalent group through a shared name'
    )


@pytest.mark.parametrize('scope', ['workflow', 'job'])
def test_actions_non_ascii_concurrency_identity_refuses(scope):
    workflow = trigger_control()
    assert not concurrency_errors([workflow]), (
        'CI policy: the supported ASCII concurrency identity admits before unsupported damage'
    )
    owner = workflow if scope == 'workflow' else workflow['jobs']['full']
    owner['concurrency']['group'] = '\u0131-${{ github.run_id }}'
    with pytest.raises(ValueError, match='non-ASCII'):
        concurrency_errors([workflow])
