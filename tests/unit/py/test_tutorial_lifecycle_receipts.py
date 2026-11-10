"""A retained passing case cannot hide an incomplete or contradictory Qt run."""

from types import SimpleNamespace

import pytest

from tests.fixtures.onboarding.lifecycle import check_observation

REQUESTED = ('isolation:simulation', 'completion:keep')
COMPLETE = """PASS   : app::OnboardingTutorials::initTestCase()
PASS   : app::OnboardingTutorials::test_isolation(simulation)
PASS   : app::OnboardingTutorials::test_completion(keep)
PASS   : app::OnboardingTutorials::cleanupTestCase()
"""


@pytest.mark.parametrize(
    ('changed', 'code'),
    [
        (COMPLETE.replace('cleanupTestCase', 'unrelatedCleanup'), 0),
        (COMPLETE.replace('test_completion(keep)', 'test_completion(discard)'), 0),
        (COMPLETE + 'PASS   : app::OnboardingTutorials::test_isolation(simulation)\n', 0),
        (
            COMPLETE.replace(
                'PASS   : app::OnboardingTutorials::test_isolation',
                'SKIP   : app::OnboardingTutorials::test_isolation',
            ),
            0,
        ),
        (COMPLETE, -11),
        (COMPLETE, 1),
    ],
    ids=['unfinished', 'wrong-tag', 'duplicate', 'skip', 'terminated', 'unexplained-exit'],
)
def test_incomplete_or_conflicting_observer_cannot_certify_a_case(changed, code):
    result = SimpleNamespace(stdout=changed, stderr='', returncode=code)
    with pytest.raises(AssertionError):
        check_observation(result, REQUESTED[0], REQUESTED)


def test_each_complete_case_retains_its_own_outcome():
    check_observation(
        SimpleNamespace(stdout=COMPLETE, stderr='', returncode=0), REQUESTED[0], REQUESTED
    )
    mixed = COMPLETE.replace(
        'PASS   : app::OnboardingTutorials::test_completion',
        'FAIL!  : app::OnboardingTutorials::test_completion',
    )
    result = SimpleNamespace(stdout=mixed, stderr='', returncode=1)
    check_observation(result, REQUESTED[0], REQUESTED)
    with pytest.raises(AssertionError, match='own real UI actions'):
        check_observation(result, REQUESTED[1], REQUESTED)


def test_receipts_remain_bound_to_the_requested_actor_suite():
    output = COMPLETE.replace('OnboardingTutorials', 'HeldEditGuards')
    result = SimpleNamespace(stdout=output, stderr='', returncode=0)
    check_observation(result, REQUESTED[0], REQUESTED, suite='HeldEditGuards')
    with pytest.raises(AssertionError, match='start and finish'):
        check_observation(result, REQUESTED[0], REQUESTED)
