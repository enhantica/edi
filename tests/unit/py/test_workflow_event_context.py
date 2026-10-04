"""Official Actions event context and loose equality are the independent oracle.

https://docs.github.com/en/actions/reference/workflows-and-actions/expressions
Absent properties are empty strings, and unlike Python '' equals false after
numeric coercion. Fork and copied-repository controls must never gain authority.
"""

import pytest

from tests.fixtures.e09_t75_workflow import active


@pytest.mark.parametrize(
    ('event', 'repository', 'fork', 'expected'),
    [
        ('push', 'enhantica/edi', False, True),
        ('schedule', 'enhantica/edi', False, True),
        ('workflow_dispatch', 'enhantica/edi', False, True),
        ('pull_request', 'enhantica/edi', False, True),
        ('pull_request', 'enhantica/edi', True, False),
        ('workflow_dispatch', 'outside/edi', False, False),
        ('workflow_dispatch', 'enhantica/edi-public', False, False),
    ],
)
def test_canonical_update_guard_uses_actual_event_context(event, repository, fork, expected):
    guard = {
        'if': "github.repository == 'enhantica/edi' && "
        'github.event.pull_request.head.repo.fork == false'
    }
    assert active(guard, event, repository=repository, fork=fork) is expected, (
        'Updater replay must admit canonical non-fork events '
        'and refuse forks and other repositories'
    )


@pytest.mark.parametrize(
    ('condition', 'expected'),
    [
        ("'' == false", True),
        ("'' != false", False),
        ("'false' == false", False),
        ("'0' == false", True),
        ("'TRUE' == 'true'", True),
        ("'abc' == 0", False),
    ],
)
def test_actions_equality_matches_documented_coercion(condition, expected):
    assert active({'if': condition}, 'workflow_dispatch') is expected, (
        'Workflow simulation must use Actions equality, including numeric and case coercion'
    )


def test_unknown_condition_cannot_invent_reachability():
    with pytest.raises(AssertionError, match='must be resolved'):
        active({'if': 'github.unproven == false'}, 'workflow_dispatch')
