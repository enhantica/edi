"""Accept approved execution models and reject the remaining causal escapes."""

import copy
import operator

import pytest

from tests.integration.py.test_gui_watchdog import SCENARIO, STEPS, checker, trace_for
from tests.integration.py.test_ui_causal_controls import CONTRACT, action_trace
from tests.integration.py.test_ui_observation_controls import frame_trace, view_trace
from tests.integration.py.ui_causal_witnesses import actions
from tests.integration.py.ui_responsiveness_oracle import first_frames, timing, work_delivery

EVENTS = [
    'build',
    'built',
    'presented',
    'discard',
    'deliver',
    'swap',
    'cancel',
    'result-arrival',
    'future-event',
]


@pytest.mark.parametrize('event', EVENTS)
def test_worker_concurrency_is_not_excluded_gui_work(event):
    trace = trace_for(170, ((20, 100),))
    trace.append({'event': event, 'thread': 'worker', 't_ms': 50})
    timing(sorted(trace, key=operator.itemgetter('t_ms')), SCENARIO, STEPS)


@pytest.mark.parametrize('event', EVENTS)
def test_every_gui_application_event_invalidates_an_exclusion(event):
    trace = trace_for(170, ((20, 100),))
    trace.append({'event': event, 'thread': 'gui', 't_ms': 50})
    with pytest.raises(AssertionError, match='reentrant work'):
        timing(sorted(trace, key=operator.itemgetter('t_ms')), SCENARIO, STEPS)


@pytest.mark.parametrize('event', ['presented', 'discard', 'future-event'])
@pytest.mark.parametrize('thread', ['gui', 'worker'])
def test_common_checker_rejects_gui_reentrancy(tmp_path, event, thread):
    trace = trace_for(170, ((20, 100),))
    trace.append({'event': event, 'thread': thread, 't_ms': 50})
    assert checker(tmp_path, sorted(trace, key=operator.itemgetter('t_ms'))) is (
        thread != 'gui'
    ), 'The common watchdog refuses GUI application work inside measurement exclusions'


@pytest.mark.parametrize('scenario', ['e58-pages', 'e58-banks', 'e58-pattern', 'e58-series'])
@pytest.mark.parametrize('edge', ['late-begin', 'early-end'])
def test_measured_interval_contains_every_native_action_and_state(scenario, edge):
    trace = action_trace(scenario)
    if scenario == 'e58-series':
        for r in trace:
            if r['event'] == 'state':
                r.update(fitting=r['request'] < 2, completed=0 if r['request'] < 2 else 100)
    if edge == 'late-begin':
        next(r for r in trace if r['event'] == 'begin')['t_ms'] = 1.5
    else:
        next(r for r in trace if r['event'] == 'complete')['t_ms'] = 0.5
    with pytest.raises(AssertionError):
        actions(trace, scenario, CONTRACT['scenarios'][scenario])


def test_measurement_cannot_end_before_the_requested_render():
    trace = action_trace('e58-pattern')
    trace.append({'event': 'render', 'request': 0, 't_ms': 10000})
    with pytest.raises(AssertionError, match='rendered completion'):
        actions(trace, 'e58-pattern', CONTRACT['scenarios']['e58-pattern'])


def test_fake_supersession_census_cannot_replace_real_relations():
    trace = view_trace()
    trace = [r for r in trace if not (r.get('generation') == 1 and 'builder' in r)]
    for r in copy.deepcopy(trace):
        if r['event'] == 'request':
            trace.append({
                'event': 'supersede',
                'view': r['view'],
                'builder': r['builder'],
                'generation': 900,
                'replacement': r['generation'],
                't_ms': 12,
            })
    with pytest.raises(AssertionError, match='real request'):
        work_delivery(trace)


def test_serial_worker_may_finish_stale_work_before_starting_replacement():
    trace = view_trace()
    for r in trace:
        if r['event'] == 'built' and r['generation'] == 1:
            r['t_ms'] = 11.5
        if r['event'] in {'build', 'built'}:
            r['thread'] = 'serial-' + r['builder']
        if r['event'] == 'deliver':
            r['t_ms'] = 19
        if r['event'] in {'swap', 'render'}:
            r['t_ms'] = 20
    work_delivery(trace)


def test_queued_superseded_work_can_cancel_without_execution():
    trace = view_trace()
    # Keep one running serial job's delayed owner callback as the rejection control.
    cancelled = set(CONTRACT['builders'][1:])
    trace = [
        r
        for r in trace
        if not (
            r.get('builder') in cancelled
            and r.get('generation') == 1
            and r['event'] in {'build', 'built', 'discard', 'result-arrival'}
        )
    ]
    for builder in cancelled:
        trace.append({
            'event': 'cancel',
            'view': builder,
            'builder': builder,
            'generation': 1,
            't_ms': 12,
        })
    work_delivery(trace)


def test_serial_rejection_before_replacement_completion_is_allowed():
    trace = view_trace()
    for r in trace:
        if r.get('generation') == 1 and 'builder' in r:
            if r['event'] == 'built':
                r['t_ms'] = 11.5
            if (
                r['event'] in {'result-arrival', 'discard'}
                and r['builder'] != CONTRACT['builders'][0]
            ):
                r['t_ms'] = 12.5
    work_delivery(trace)


def test_multiple_builder_stages_feed_one_snapshot_swap():
    trace = view_trace()
    swaps = [r for r in trace if r['event'] == 'swap']
    sources = [{k: r[k] for k in ('builder', 'generation')} | {'view': 'shared'} for r in swaps]
    trace = [r for r in trace if r['event'] not in {'swap', 'render'}]
    for r in trace:
        if 'builder' in r:
            r['view'] = 'shared'
    trace += [
        {
            'event': 'swap',
            'view': 'shared',
            'sources': sources,
            'thread': 'gui',
            'frame': 42,
            't_ms': 16,
        },
        {'event': 'render', 'frame': 42, 't_ms': 16},
    ]
    work_delivery(trace)


@pytest.mark.parametrize('rows', [1, 10])
def test_whole_model_changes_are_valid_beside_a_partial_edit(rows):
    trace = view_trace()
    trace.append({
        'event': 'model-change',
        'incremental': True,
        'operation': 'dataChanged',
        'rows': rows,
        'first': 0,
        'last': rows - 1,
        'changed_range': [0, rows - 1],
    })
    work_delivery(trace)


def test_a_stale_result_cannot_contribute_to_a_shared_snapshot():
    trace = view_trace()
    swap = next(r for r in trace if r['event'] == 'swap')
    swap['sources'] = [{'view': swap['view'], 'builder': swap['builder'], 'generation': 1}]
    with pytest.raises(AssertionError, match='current output'):
        work_delivery(trace)


def test_render_stream_cannot_be_consistently_offset_from_native_selection():
    trace = frame_trace()
    for r in trace:
        if r['event'] in {'step', 'presented', 'render'} and 'dataset' in r:
            r['dataset'] += 100
    with pytest.raises(AssertionError, match='actual selected dataset'):
        first_frames(trace)


def test_rendered_navigation_must_use_the_selected_input():
    trace = frame_trace()
    next(r for r in trace if r['event'] == 'state')['input'] = 'another-project'
    with pytest.raises(AssertionError, match='actual selected dataset'):
        first_frames(trace)


def test_matching_indices_cannot_hide_wrong_rendered_pattern_content():
    trace = frame_trace()
    displayed = next(r for r in trace if r['event'] == 'render' and r['frame'] == 1)
    displayed['data_identity'] = 'other-pattern'
    with pytest.raises(AssertionError, match='pattern content'):
        first_frames(trace)


@pytest.mark.parametrize('identity', ['', None])
def test_absent_pattern_identity_cannot_pass_by_equality(identity):
    trace = frame_trace()
    for r in trace:
        if 'data_identity' in r:
            r['data_identity'] = identity
    with pytest.raises(AssertionError, match='pattern content'):
        first_frames(trace)
