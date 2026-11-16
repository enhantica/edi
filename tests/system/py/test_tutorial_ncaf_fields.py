"""One real Analysis project shared by its field predecessor and pointer assertions."""

import pytest

from tests.system.py.test_tutorial_navigation import (
    ALL_CASES,
    actor_for_cases,
    analysis_field_case,
)

CASES = [case for case in ALL_CASES if analysis_field_case(case, 'pd-neut-tof_ncaf-wish')]


@pytest.fixture(scope='module')
def navigation_actor(request, tmp_path_factory):
    yield from actor_for_cases(request, tmp_path_factory, CASES)


@pytest.mark.parametrize('case', CASES)
def test_written_tutorial_navigation(case, navigation_actor):
    navigation_actor.run('TutorialNavigation::test_' + case)
