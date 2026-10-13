"""Real app choices must govern worker fills and survive machine-setting reloads."""

import copy

import pytest

from tests.fixtures.app_environment.observations import Observations
from tests.fixtures.thread_selector.build import ESCAPES
from tests.fixtures.thread_selector.harness import COUNTS, observation


@pytest.fixture(scope='module')
def selectors(tmp_path_factory):
    root = tmp_path_factory.mktemp('thread-selector')
    return Observations(
        lambda backend: {
            control: observation(backend, root / backend / (control or 'normal'), control)
            for control in (None, *ESCAPES)
        }
    )


def complete(item):
    assert not item.get('error'), (
        'ADR-0084: selector observations must complete a real calculation and complete fit'
    )
    assert item['calculated'] and item['scientific']['values'], (
        'ADR-0084: real numeric work must accompany every worker-participation observation'
    )
    assert item['scientific']['converged'], (
        'ADR-0084: byte comparisons must follow a complete converged scientific fit'
    )


def participates(item, count):
    assert count > 0, 'I17: exact team participation applies only to an explicit positive count'
    expected = count
    groups = [item['calculationFills'], item['fitFills']]
    assert all(groups), 'ADR-0084: both real calculation and Jacobian fills must be observed'
    return all(
        any(fill['items'] >= expected and fill['chunks'] >= expected for fill in group)
        and all(
            fill['workers'] == expected
            for fill in group
            if fill['items'] >= expected and fill['chunks'] >= expected
        )
        for group in groups
    )


def auto_policy(item):
    assert item['environment'] == '2' and item['reportedWorkers'] == 2, (
        'I17: Auto retains the caller environment and the shipped admitted team'
    )
    groups = [item['calculationFills'], item['fitFills']]
    assert all(groups), 'I17: Auto must reach actual calculation and Jacobian fills'
    for group in groups:
        assert any(fill['items'] >= 2 and fill['chunks'] >= 2 for fill in group), (
            'I17: Auto admission is exercised on work with multiple available chunks'
        )
        assert all(1 <= fill['workers'] <= 2 for fill in group if fill['items']), (
            'I17: dynamic Auto claiming retains a nonempty bounded team without requiring '
            'every admitted worker to claim each fill'
        )


@pytest.mark.parametrize('backend', ['desktop', 'browser'])
@pytest.mark.parametrize('count', COUNTS)
@pytest.mark.parametrize('phase', ['selected', 'reopened'])
def test_real_selector_controls_worker_identities_after_restart(selectors, backend, count, phase):
    item = selectors[backend][None]['results'][str(count)][phase]
    complete(item)
    assert item['selectorUsable'], 'ADR-0084: the actual Develop selector must be usable'
    assert item['selectedIndex'] == count and item['setting'] == count, (
        'ADR-0084: the real selected machine preference must apply before each worker fill'
    )
    if phase == 'reopened':
        assert item['initialSetting'] == count, (
            'ADR-0084: desktop restart and browser reload must restore the saved count at startup'
        )
    assert item['environment'] == '2', (
        'ADR-0084: explicit counts must be tested against a conflicting caller environment'
    )
    if count:
        participating = participates(item, count)
        assert participating, (
            'ADR-0084: the explicit chosen number must participate through actual '
            'thread identities inside fills'
        )
    else:
        auto_policy(item)
    assert item['reportedWorkers'] == (count or 2), (
        'I17: reported workers retain the explicit team or shipped Auto admission policy'
    )
    if backend == 'browser':
        assert selectors[backend][None]['isolated'], (
            'ADR-0084: browser worker evidence must run in the actual isolated pthread host'
        )
        assert count != 9 or count > selectors[backend][None]['preallocated'], (
            'ADR-0084: browser selection must grow beyond the preallocated worker pool'
        )


@pytest.mark.parametrize('backend', ['desktop', 'browser'])
def test_auto_restores_caller_policy_after_an_explicit_choice(selectors, backend):
    item = selectors[backend][None]['results']['restore']['selected']
    complete(item)
    assert item['beforeAuto'] == 3 and item['setting'] == 0, (
        'ADR-0084: selecting Auto must reset a previously applied explicit count'
    )
    auto_policy(item)


@pytest.mark.parametrize('backend', ['desktop', 'browser'])
@pytest.mark.parametrize('defect', ['environment', 'reportedWorkers', 'overfull-fill'])
def test_auto_contract_refuses_wrong_admission_without_requiring_full_participation(
    selectors, backend, defect
):
    actual = selectors[backend][None]['results']['0']['selected']
    complete(actual)
    auto_policy(actual)
    altered = copy.deepcopy(actual)
    if defect == 'overfull-fill':
        active = next(fill for fill in altered['calculationFills'] if fill['items'] >= 2)
        active['workers'] = 3
    else:
        altered[defect] = '9' if defect == 'environment' else 3
    with pytest.raises(AssertionError, match='I17:'):
        auto_policy(altered)


@pytest.mark.parametrize('backend', ['desktop', 'browser'])
def test_calculation_and_complete_fit_are_byte_identical_across_choices(selectors, backend):
    results = selectors[backend][None]['results']
    expected = results['1']['selected']
    complete(expected)
    for case in results.values():
        for item in case.values():
            complete(item)
            assert item['calculated'] == expected['calculated'], (
                'ADR-0084: every selected and persisted team must retain exact calculation bytes'
            )
            assert item['scientific'] == expected['scientific'], (
                'ADR-0084: complete fitted values, uncertainties and status retain exact bytes'
            )


@pytest.mark.parametrize('backend', ['desktop', 'browser'])
@pytest.mark.parametrize('escape', ESCAPES)
def test_selector_contract_refuses_actual_engine_and_persistence_escapes(
    selectors, backend, escape
):
    baseline = selectors[backend][None]['results']['3']
    control = selectors[backend][escape]['results']['3']
    phase = 'reopened' if escape == 'ignored-persistence' else 'selected'
    complete(baseline[phase])
    complete(control[phase])
    baseline_participates = participates(baseline[phase], 3)
    assert baseline_participates, (
        'ADR-0084: each escaped property must first pass through the real working selector'
    )
    assert control[phase]['scientific'] == baseline[phase]['scientific'], (
        'ADR-0084: escapes must reach valid numeric work rather than unrelated build errors'
    )
    valid = control[phase]['setting'] == 3 and participates(control[phase], 3)
    if escape == 'ignored-persistence':
        valid = valid and control[phase]['initialSetting'] == 3
    assert not valid, (
        'ADR-0084: ignored setters, caller-local choices, lost settings and serial fills must fail'
    )
