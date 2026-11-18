"""Exercise each causal-observation escape reported by the gate review."""

import copy
import json
import operator
from pathlib import Path

import pytest

from tests.integration.py.test_gui_watchdog import SCENARIO, STEPS, checker, trace_for
from tests.integration.py.test_ui_observation_controls import frame_trace, view_trace
from tests.integration.py.ui_causal_witnesses import actions
from tests.integration.py.ui_responsiveness_oracle import (
    first_frames,
    hidden_refreshes,
    timing,
    work_delivery,
)

CONTRACT = json.loads(
    (Path(__file__).parents[2] / 'fixtures/ui_responsiveness/contract.json').read_text()
)


def exclusion_escape(case):
    trace = trace_for(170, ((20, 100),))
    if case == 'missing-callback':
        return [r for r in trace if not r['event'].startswith('measurement-')]
    if case == 'reentrant-builder':
        trace.append({'event': 'build', 't_ms': 50})
    elif case == 'overbroad-transition':
        for i, row in enumerate(r for r in trace if r['event'] == 'step'):
            row['t_ms'] = 50 + i
    elif case == 'wrong-callback':
        next(r for r in trace if r['event'] == 'measurement-enter')['callback'] = 'publish'
    return sorted(trace, key=operator.itemgetter('t_ms'))


@pytest.mark.parametrize(
    'case', ['missing-callback', 'reentrant-builder', 'overbroad-transition', 'wrong-callback']
)
def test_exclusion_semantic_escapes_are_rejected(case):
    with pytest.raises(AssertionError):
        timing(exclusion_escape(case), SCENARIO, STEPS)


@pytest.mark.parametrize(
    'case', ['missing-callback', 'reentrant-builder', 'overbroad-transition', 'wrong-callback']
)
def test_production_checker_rejects_exclusion_semantic_escapes(tmp_path, case):
    assert checker(tmp_path, exclusion_escape(case)) is False, (
        'Exclusions require measurement callbacks without reentrant app work'
    )


def test_control_cannot_borrow_an_unrelated_later_stall():
    trace = trace_for(10)
    trace = [r for r in trace if r['event'] not in {'tick', 'complete'}]
    trace += [{'event': 'tick', 't_ms': t} for t in range(0, 171, 10)]
    trace += [
        {'event': 'block-begin', 'thread': 'gui', 't_ms': 5},
        {'event': 'block-end', 'thread': 'gui', 't_ms': 155},
        {'event': 'tick', 't_ms': 400},
        {'event': 'complete', 'scenario': SCENARIO, 't_ms': 400},
    ]
    with pytest.raises(AssertionError, match='suppresses ticks'):
        timing(sorted(trace, key=operator.itemgetter('t_ms')), SCENARIO, STEPS, control=True)


def action_trace(scenario):
    trace = [{'event': 'input', 'identity': 'fixture'}]
    selection = 10
    for i, name in enumerate(CONTRACT['scenarios'][scenario]):
        delta = -1 if '-previous-' in name else 1
        trace += [
            {
                'event': 'action',
                'name': name,
                'request': i,
                't_ms': i * 100,
                'before_selection': selection,
            },
            {'event': 'step', 'name': name, 'request': i, 't_ms': i * 100 + 2},
            {
                'event': 'state',
                'request': i,
                't_ms': i * 100 + 1,
                'input': 'fixture',
                'page': name.removeprefix('page-')
                if scenario == 'e58-pages'
                else name.split('-')[0],
                'tab': 'pattern',
                'selection': selection + delta,
            },
        ]
        selection += delta
    return trace


@pytest.mark.parametrize('scenario', ['e58-pages', 'e58-banks', 'e58-pattern'])
def test_native_action_positive_transitions(scenario):
    actions(action_trace(scenario), scenario, CONTRACT['scenarios'][scenario])


@pytest.mark.parametrize('scenario', ['e58-pages', 'e58-banks', 'e58-pattern'])
def test_noop_actions_do_not_pass_on_step_labels(scenario):
    trace = action_trace(scenario)
    for row in trace:
        if row['event'] == 'state':
            row['page'], row['selection'] = 'home', 10
    with pytest.raises(AssertionError):
        actions(trace, scenario, CONTRACT['scenarios'][scenario])


def test_slow_pattern_actions_are_not_rapid_navigation():
    trace = action_trace('e58-pattern')
    for row in trace:
        if 't_ms' in row:
            row['t_ms'] *= 10
    with pytest.raises(AssertionError, match='rapid navigation'):
        actions(trace, 'e58-pattern', CONTRACT['scenarios']['e58-pattern'])


@pytest.mark.parametrize(
    'case',
    [
        'consistent-omission',
        'wrong-visibility',
        'between-snapshots',
        'show-before-hide',
        'duplicate-generation',
        'unrelated-lazy',
    ],
)
def test_hidden_instance_and_lifecycle_escapes(case):
    trace = view_trace()

    def event(name):
        return next(r for r in trace if r['event'] == name)

    if case == 'consistent-omission':
        for name in ('census', 'hidden-before', 'hidden-after'):
            event(name)['views'] = [r for r in event(name)['views'] if r['view'] != 'hidden']
    elif case == 'wrong-visibility':
        event('hierarchy')['objects'][0]['page'] = 'analysis'
    elif case == 'between-snapshots':
        event('shown-before')['refreshes'] = 2
        event('shown-after')['refreshes'] = 3
    elif case == 'show-before-hide':
        event('shown-before')['t_ms'] = 0
    elif case == 'duplicate-generation':
        event('data-change')['generation'] = 2
    elif case == 'unrelated-lazy':
        event('lazy-created')['view'] = 'omitted'
    with pytest.raises(AssertionError):
        hidden_refreshes(trace, ['V1'])


@pytest.mark.parametrize(
    'case',
    [
        'omitted-builder',
        'false-scaling',
        'inorder-only',
        'invented-supersede',
        'render-clock',
        'mixed-full-range',
    ],
)
def test_complete_causal_work_escapes(case):
    trace = view_trace()

    def event(name):
        return next(r for r in trace if r['event'] == name)

    if case == 'omitted-builder':
        trace = [r for r in trace if r.get('builder') != CONTRACT['builders'][-1]]
    elif case == 'false-scaling':
        event('build').update(scales=False, thread='gui')
    elif case == 'inorder-only':
        event('built')['t_ms'] = 13.5
    elif case == 'invented-supersede':
        event('supersede')['generation'] = 9
    elif case == 'render-clock':
        event('render')['t_ms'] = 999
    elif case == 'mixed-full-range':
        bad = copy.deepcopy(event('model-change'))
        bad.update(first=0, last=9)
        trace.append(bad)
    with pytest.raises(AssertionError):
        work_delivery(trace)


def test_changed_last_row_is_a_valid_strict_incremental_range():
    trace = view_trace()
    event = next(r for r in trace if r['event'] == 'model-change')
    event.update(first=9, last=9, changed_range=[9, 9])
    work_delivery(trace)


@pytest.mark.parametrize(
    'case',
    [
        'unrendered-settled',
        'premature-settled',
        'invisible-pane',
        'late-layout',
        'delayed-action-boundary',
    ],
)
def test_both_frames_are_bound_to_actual_rendered_data(case):
    trace = frame_trace()
    first = next(r for r in trace if r['event'] == 'frame' and r['phase'] == 'first')
    settled = next(r for r in trace if r['event'] == 'frame' and r['phase'] == 'settled')
    if case == 'unrendered-settled':
        settled['frame'] = 9999
    elif case == 'premature-settled':
        next(r for r in trace if r['event'] == 'presented')['t_ms'] = 99
    elif case == 'invisible-pane':
        settled['visible']['bragg'] = False
    elif case == 'late-layout':
        settled['geometry']['bragg'][1] += 5
    elif case == 'delayed-action-boundary':
        next(r for r in trace if r['event'] == 'action')['t_ms'] = -5
        trace.insert(0, {'event': 'render', 'frame': 999, 't_ms': -1, 'request': first['request']})
    with pytest.raises(AssertionError):
        first_frames(trace)
