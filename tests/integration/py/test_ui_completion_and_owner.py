"""Close missing completion and GUI-owner admissions without changing worker models."""

import pytest

from tests.integration.py.test_gui_watchdog import SCENARIO, STEPS, trace_for
from tests.integration.py.test_ui_causal_controls import CONTRACT, action_trace
from tests.integration.py.test_ui_observation_controls import view_trace
from tests.integration.py.ui_causal_witnesses import actions, exclusions, snapshots
from tests.integration.py.ui_responsiveness_oracle import timing, work_delivery


def scenario_trace(scenario):
    trace = action_trace(scenario)
    if scenario == 'e58-series':
        for row in trace:
            if row['event'] == 'state':
                row.update(fitting=row['request'] < 2, completed=0 if row['request'] < 2 else 100)
    return trace


@pytest.mark.parametrize('scenario', CONTRACT['scenarios'])
def test_real_transition_publication_and_render_complete_inside_measurement(scenario):
    actions(scenario_trace(scenario), scenario, CONTRACT['scenarios'][scenario])


@pytest.mark.parametrize('scenario', CONTRACT['scenarios'])
@pytest.mark.parametrize(
    'escape', ['missing', 'missing-render', 'unmatched', 'post-window', 'wrong-frame']
)
def test_required_completion_witness_cannot_be_absent_unmatched_or_late(scenario, escape):
    trace = scenario_trace(scenario)
    publication = [r for r in trace if r['event'] == 'transition-publication'][-1]
    render = next(
        r for r in trace if r['event'] == 'render' and r['frame'] == publication['frame']
    )
    if escape == 'missing':
        trace.remove(publication)
    elif escape == 'missing-render':
        trace.remove(render)
    elif escape == 'unmatched':
        publication['transition'] = 'unrelated-transition'
    elif escape == 'post-window':
        render['t_ms'] = next(r for r in trace if r['event'] == 'complete')['t_ms'] + 1000
    else:
        render['transitions'] = ['another-native-transition']
    with pytest.raises(AssertionError):
        actions(trace, scenario, CONTRACT['scenarios'][scenario])


@pytest.mark.parametrize(
    'escape',
    [
        'missing-work',
        'unmatched-work',
        'wrong-run',
        'late-delivery',
        'late-publication',
        'late-fit',
    ],
)
def test_series_completion_binds_actual_run_work_not_navigation_tags(escape):
    trace = scenario_trace('e58-series')
    publication = [r for r in trace if r['event'] == 'transition-publication'][-1]
    delivered = next(r for r in trace if r['event'] == 'deliver')
    end = next(r for r in trace if r['event'] == 'complete')['t_ms']
    if escape == 'missing-work':
        publication.pop('work')
    elif escape == 'unmatched-work':
        publication['work'] = [{'view': 'foreign', 'builder': 'results-index', 'generation': 99}]
    elif escape == 'wrong-run':
        delivered['run'] = 'previous-run'
    elif escape == 'late-delivery':
        delivered['t_ms'] = end + 1000
    elif escape == 'late-publication':
        publication['t_ms'] = end + 1000
    else:
        next(r for r in trace if r['event'] == 'fit-finished')['t_ms'] = end + 1000
    with pytest.raises(AssertionError):
        actions(trace, 'e58-series', CONTRACT['scenarios']['e58-series'])


def test_unrelated_setup_and_background_events_may_lie_outside_the_window():
    trace = scenario_trace('e58-series')
    trace += [
        {'event': 'render', 'frame': 'unrelated', 'transitions': ['background'], 't_ms': 99999},
        {
            'event': 'built',
            'view': 'other',
            'builder': 'unrelated',
            'generation': 1,
            't_ms': -1000,
        },
    ]
    actions(trace, 'e58-series', CONTRACT['scenarios']['e58-series'])


@pytest.mark.parametrize('identity', [None, '', '  ', 0, False, 'absent'])
def test_missing_gui_and_equally_missing_swap_identity_do_not_prove_ownership(identity):
    trace = view_trace()
    clock = next(r for r in trace if r['event'] == 'clock')
    if identity == 'absent':
        clock.pop('gui_thread')
    else:
        clock['gui_thread'] = identity
    for swap in (r for r in trace if r['event'] == 'swap'):
        if identity == 'absent':
            swap.pop('thread')
        else:
            swap['thread'] = identity
    with pytest.raises(AssertionError, match='native GUI thread identity'):
        work_delivery(trace)


@pytest.mark.parametrize('identity', [None, '', '  ', 'absent'])
def test_timing_requires_gui_identity_even_without_excluded_spans(identity):
    trace = trace_for(10)
    clock = next(r for r in trace if r['event'] == 'clock')
    if identity == 'absent':
        clock.pop('gui_thread')
    else:
        clock['gui_thread'] = identity
    with pytest.raises(AssertionError, match='native GUI thread identity'):
        timing(trace, SCENARIO, STEPS)


@pytest.mark.parametrize('identity', [None, '', 'absent', 'worker'])
def test_swap_must_belong_to_the_validated_gui_owner(identity):
    trace = view_trace()
    swap = next(r for r in trace if r['event'] == 'swap')
    if identity == 'absent':
        swap.pop('thread')
    else:
        swap['thread'] = identity
    with pytest.raises(AssertionError, match='GUI owner'):
        work_delivery(trace)


def test_native_numeric_gui_identity_is_supported():
    trace = view_trace()
    next(r for r in trace if r['event'] == 'clock')['gui_thread'] = 42
    for swap in (r for r in trace if r['event'] == 'swap'):
        swap['thread'] = 42
    work_delivery(trace)


def test_exclusion_owner_validation_is_not_conditional_on_a_callback():
    trace = [{'event': 'clock', 'gui_thread': None}]
    with pytest.raises(AssertionError, match='native GUI thread identity'):
        exclusions(trace, [])


def test_shared_snapshot_entry_requires_an_actual_gui_identity():
    trace = [{'event': 'clock', 'gui_thread': ''}]
    with pytest.raises(AssertionError, match='native GUI thread identity'):
        snapshots(trace, {}, {})


@pytest.mark.parametrize('escape', ['missing-swap', 'unmatched-sources', 'late-swap'])
def test_series_work_keyed_swap_cannot_escape_the_window(escape):
    trace = scenario_trace('e58-series')
    swap = next(r for r in trace if r['event'] == 'swap')
    if escape == 'missing-swap':
        trace.remove(swap)
    elif escape == 'unmatched-sources':
        swap['sources'] = [{'view': 'other', 'builder': 'results-index', 'generation': 99}]
    else:
        swap['t_ms'] = 10000
    with pytest.raises(AssertionError):
        actions(trace, 'e58-series', CONTRACT['scenarios']['e58-series'])
