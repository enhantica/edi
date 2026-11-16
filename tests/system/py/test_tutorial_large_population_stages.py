"""Full native relation-graph eligibility for the large single-crystal tutorial."""

import pytest

from tests.integration.py import test_tutorial_fit_stages as stages

tutorial_models = stages.tutorial_models
tutorial_model = stages.tutorial_model


@pytest.mark.parametrize('case', sorted(stages.LARGE_POPULATION_CASES))
def test_app_tutorial_teaches_the_same_fitting_groups_cycles_and_constraints(
    case, tutorial_model, tutorial_models
):
    stages.test_app_tutorial_teaches_the_same_fitting_groups_cycles_and_constraints(
        case, tutorial_model, tutorial_models
    )


@pytest.mark.parametrize('case', sorted(stages.LARGE_POPULATION_CASES))
def test_app_docs_teach_the_same_fit_stages_as_the_executable_tutorial(
    case, tutorial_model, tutorial_models
):
    stages.test_app_docs_teach_the_same_fit_stages_as_the_executable_tutorial(
        case, tutorial_model, tutorial_models
    )


@pytest.mark.parametrize('case', sorted(stages.LARGE_SOURCE_CASES))
def test_notebook_and_script_teach_the_same_exact_stage_sequence(case, tutorial_model):
    stages.test_notebook_and_script_teach_the_same_exact_stage_sequence(case, tutorial_model)
