"""Real multi-fit GUI recipe journeys run at the declared nightly system cadence."""

import pytest

from tests.fixtures.tutorial_recipe.reference import boundary_contracts, state_errors
from tests.system.py.test_tutorial_recipe_preservation import RECIPES, observe_states


@pytest.fixture(scope='module')
def states(tmp_path_factory, request):
    wanted = {
        item.callspec.params['case']
        for item in request.session.items
        if item.originalname == 'test_builtin_pre_fit_state_equals_the_declared_docs_recipe'
    }
    return observe_states(tmp_path_factory, wanted)


@pytest.mark.parametrize('case', RECIPES)
def test_builtin_pre_fit_state_equals_the_declared_docs_recipe(case, states):
    expected = boundary_contracts(RECIPES[case])
    records = [r for r in states['records'] if r['id'] == case]
    problems = []
    run = states['native_runs'][case]
    if run['returncode'] != 0:
        problems.append((
            'native completion',
            [run.get('first_failure'), run['reason'], run['log']],
        ))
    if case in states['transport_errors']:
        problems.append(('strict transport', [states['transport_errors'][case]]))
    for boundary in expected:
        found = [row for row in records if row['stage'] == boundary['stage']]
        if len(found) != 1:
            problems.append((boundary['stage'], ['missing or duplicate actual boundary']))
            continue
        errors = state_errors(boundary, found[0])
        if case == 'pd-neut-tof_si-sepd' and not found[0]['fileAlternativeSeen']:
            errors.append('From file alternative not shown')
        if errors:
            problems.append((boundary['stage'], errors))
    if len(records) != len(expected):
        problems.append(('count', [len(records), len(expected)]))
    assert not problems, 'Actual pre-fit state matches the independent docs recipe: ' + repr(
        problems
    )


def test_recipe_observer_has_a_real_positive_control(states):
    assert states['native_runs']['controls']['returncode'] == 0, (
        'Every independent native clock, fit grammar, menu and model control completes normally'
    )
    assert 'controls' not in states['transport_errors'], (
        'Native model-control JSON remains strict rather than replacing malformed data'
    )
    assert states['data_menu_controls'] == [{'closed': 0, 'opened': 1, 'closed_after': 0}], (
        'The From file observer sees the genuine original menu before measured data exists'
    )
    assert states['clock_controls'] == [{'delta': 156, 'monotonic': True}], (
        'Native boundary observations require the independently exercised '
        'monotonic animation clock'
    )
    assert states['menu_controls'] == [{'closed': 0, 'opened': 1, 'closed_after': 0}], (
        'The original-menu observer must pass its genuine closed/opened/Escape control '
        'before its native state observations are qualified'
    )
    found = [row for row in states['records'] if row['id'] == 'observer-control']
    assert len(found) == 1, (
        'The boundary observer reaches an independently authored real app model'
    )
    assert found[0]['values']['lbco.cell.length_a'] == pytest.approx(3.89), (
        'The passive observer reads the independent onboarding structure cell, without changing it'
    )
    assert found[0]['experiments'], (
        'The passive observer reads the actual experiment text and settings'
    )
