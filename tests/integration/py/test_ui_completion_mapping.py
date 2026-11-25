"""Completion admits compatible frame sharing and independent view coalescers."""

import copy
import operator

import pytest

from tests.integration.py.test_ui_causal_controls import CONTRACT
from tests.integration.py.test_ui_completion_and_owner import scenario_trace
from tests.integration.py.ui_causal_witnesses import actions


@pytest.mark.parametrize('scenario', ['e58-pages', 'e58-banks'])
@pytest.mark.parametrize('tokens', ['distinct', 'reused'])
def test_incompatible_native_targets_cannot_alias_one_terminal_frame(scenario, tokens):
    trace = scenario_trace(scenario)
    steps = CONTRACT['scenarios'][scenario]
    if scenario == 'e58-banks':
        # Hold the page fixed so this control specifically exercises bank identity.
        steps = steps[:8]
        trace = [
            r
            for r in trace
            if r['event'] not in {'action', 'state', 'step', 'render', 'transition-publication'}
            or r.get('request', 99) < 8
            or (r['event'] in {'render', 'transition-publication'} and r['frame'] < 8)
        ]
    states = [r for r in trace if r['event'] == 'state']
    publications = [r for r in trace if r['event'] == 'transition-publication']
    final = max((r for r in trace if r['event'] == 'render'), key=operator.itemgetter('t_ms'))
    trace = [r for r in trace if r['event'] != 'render'] + [final]
    for publication in publications:
        publication['frame'] = final['frame']
    if tokens == 'distinct':
        final['transitions'] = [r['transition'] for r in states]
    else:
        token = states[-1]['transition']
        for state in states:
            state['transition'] = token
        trace = [r for r in trace if r['event'] != 'transition-publication'] + [publications[-1]]
        final['transitions'] = [token]
    with pytest.raises(AssertionError, match='incompatible targets'):
        actions(trace, scenario, steps)


@pytest.mark.parametrize('tokens', ['distinct', 'reused'])
def test_compatible_native_states_may_share_rendered_completion(tokens):
    trace = scenario_trace('e58-pages')
    chosen = [r for r in trace if r['event'] == 'action' and r['name'] == 'page-experiment']
    requests = {r['request'] for r in chosen}
    trace = [
        r
        for r in trace
        if r['event'] in {'input', 'clock', 'begin', 'complete'} or r.get('request') in requests
    ]
    states = [r for r in trace if r['event'] == 'state']
    frame = {'event': 'render', 'frame': 90, 't_ms': 850, 'displayed': copy.deepcopy(states[-1])}
    publications = []
    for state in states:
        token = 'shared' if tokens == 'reused' else state['transition']
        state['transition'] = token
        if not any(p['transition'] == token for p in publications):
            publications.append({
                'event': 'transition-publication',
                'transition': token,
                'input': state['input'],
                'frame': 90,
                't_ms': 840,
            })
    frame['transitions'] = [r['transition'] for r in states]
    trace += publications + [frame]
    actions(trace, 'e58-pages', [r['name'] for r in chosen])


def independent_views():
    trace = scenario_trace('e58-series')
    final = [r for r in trace if r['event'] == 'transition-publication'][-1]
    work = final['work']
    trace = [r for r in trace if r['event'] != 'swap']
    final['t_ms'] = 310
    completed_render = next(
        r for r in trace if r['event'] == 'render' and r['frame'] == final['frame']
    )
    completed_render['t_ms'] = 311
    for index, source in enumerate(work):
        source['view'] = 'independent-' + str(index)
        for row in trace:
            if (
                row['event'] in {'request', 'built', 'deliver'}
                and row.get('builder') == source['builder']
            ):
                row['view'] = source['view']
                if row['event'] == 'deliver':
                    row['t_ms'] = 302 + index * 3
        frame = 50 + index
        trace += [
            {
                'event': 'swap',
                'view': source['view'],
                'sources': [dict(source)],
                'frame': frame,
                'thread': 'gui',
                't_ms': 303 + index * 3,
            },
            {'event': 'render', 'frame': frame, 't_ms': 303 + index * 3},
        ]
    return trace


def test_series_views_may_finish_in_separate_frames_before_completion():
    actions(independent_views(), 'e58-series', CONTRACT['scenarios']['e58-series'])


@pytest.mark.parametrize('view', ['independent-0', 'independent-1'])
@pytest.mark.parametrize('escape', ['missing-render', 'late-render', 'premature-completion'])
def test_each_independent_view_must_finish_inside_measurement(view, escape):
    trace = independent_views()
    swap = next(r for r in trace if r['event'] == 'swap' and r['view'] == view)
    rendered = next(r for r in trace if r['event'] == 'render' and r['frame'] == swap['frame'])
    if escape == 'missing-render':
        trace.remove(rendered)
    elif escape == 'late-render':
        swap['t_ms'] = rendered['t_ms'] = 1000
    else:
        final = [r for r in trace if r['event'] == 'transition-publication'][-1]
        completion = next(
            r for r in trace if r['event'] == 'render' and r['frame'] == final['frame']
        )
        completion['t_ms'] = swap['t_ms'] - 0.5
        final['t_ms'] = completion['t_ms'] - 0.5
    with pytest.raises(AssertionError):
        actions(trace, 'e58-series', CONTRACT['scenarios']['e58-series'])


@pytest.mark.parametrize('tokens', ['distinct', 'reused'])
def test_compatible_bank_targets_can_share_a_frame_across_another_target(tokens):
    trace = scenario_trace('e58-banks')
    trace = [
        r
        for r in trace
        if r['event'] in {'clock', 'input', 'begin', 'complete'}
        or (r['event'] in {'action', 'state', 'step'} and r['request'] < 3)
    ]
    names = ['experiment-next-0', 'experiment-previous-0', 'experiment-next-1']
    for row in trace:
        request = row.get('request')
        if request is None:
            continue
        if row['event'] in {'action', 'step'}:
            row['name'] = names[request]
        if row['event'] == 'action':
            row['before_selection'] = [10, 11, 10][request]
        if row['event'] == 'state':
            row['selection'] = [11, 10, 11][request]
            row['transition'] = (
                'bank11' if tokens == 'reused' and request != 1 else 'bank-' + str(request)
            )
    states = [r for r in trace if r['event'] == 'state']
    publications = []
    for row in states:
        frame, time = (10, 104) if row['request'] == 1 else (11, 204)
        if not any(r['transition'] == row['transition'] for r in publications):
            publications.append({
                'event': 'transition-publication',
                'transition': row['transition'],
                'input': row['input'],
                'frame': frame,
                't_ms': time - 1,
            })
    trace += publications
    trace += [
        {
            'event': 'render',
            'frame': 10,
            't_ms': 104,
            'displayed': dict(states[1]),
            'transitions': [states[1]['transition']],
        },
        {
            'event': 'render',
            'frame': 11,
            't_ms': 204,
            'displayed': dict(states[2]),
            'transitions': [states[0]['transition'], states[2]['transition']],
        },
    ]
    actions(trace, 'e58-banks', names)


@pytest.mark.parametrize('field', ['input', 'page', 'tab', 'selection'])
def test_bank_completion_requires_each_actual_displayed_state_field(field):
    trace = scenario_trace('e58-banks')
    next(r for r in trace if r['event'] == 'render')['displayed'].pop(field)
    with pytest.raises(AssertionError, match='incompatible targets'):
        actions(trace, 'e58-banks', CONTRACT['scenarios']['e58-banks'])


def test_same_page_with_incompatible_tabs_cannot_share_completion():
    trace = scenario_trace('e58-pages')
    visits = [r for r in trace if r['event'] == 'state' and r['page'] == 'experiment']
    earlier, later = visits
    earlier['tab'] = 'stacked'
    publication = next(
        r
        for r in trace
        if r['event'] == 'transition-publication' and r['transition'] == earlier['transition']
    )
    old_frame = publication['frame']
    publication['frame'] = later['request']
    trace = [r for r in trace if not (r['event'] == 'render' and r['frame'] == old_frame)]
    actual = next(r for r in trace if r['event'] == 'render' and r['frame'] == later['request'])
    actual['transitions'].append(earlier['transition'])
    with pytest.raises(AssertionError, match='incompatible targets'):
        actions(trace, 'e58-pages', CONTRACT['scenarios']['e58-pages'])
