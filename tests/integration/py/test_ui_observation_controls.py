"""Attempt escapes against the first-frame and hidden-work observation gates."""

import copy
import operator

import pytest

from tests.integration.py.ui_responsiveness_oracle import (
    first_frames,
    hidden_refreshes,
    work_delivery,
)
from tests.integration.py.ui_trace_controls import enrich_frames, enrich_views


def frame_trace():
    geometry = {
        key: [0, i * 20, 200, 20]
        for i, key in enumerate((
            'pattern',
            'bragg',
            'residual',
            'x',
            'intensity',
            'residual-axis',
        ))
    }
    rows = []
    for page_index, page in enumerate(('experiment', 'analysis')):
        for i in range(20):
            request = page_index * 20 + i
            t = request * 100
            rows.extend([
                {
                    'event': 'step',
                    'name': f'{page}-'
                    + ('next-' + str(i) if i < 10 else 'previous-' + str(i - 10)),
                    'request': request,
                    't_ms': t,
                    'dataset': i + 1 if i < 10 else 19 - i,
                    'direction': 'next' if i < 10 else 'previous',
                },
                {'event': 'render', 't_ms': t + 1, 'frame': request * 2},
                {'event': 'render', 't_ms': t + 2, 'frame': request * 2 + 1},
            ])
            for phase, offset in (('first', 0), ('settled', 1)):
                rows.append({
                    'event': 'frame',
                    'request': request,
                    'frame': request * 2 + offset,
                    'phase': phase,
                    't_ms': t + 1 + offset,
                    'witness': 'afterSynchronizing/frameSwapped',
                    'panes': ['pattern', 'bragg', 'residual'],
                    'axes': ['x', 'intensity', 'residual'],
                    'geometry': copy.deepcopy(geometry),
                })
    return enrich_frames(sorted(rows, key=operator.itemgetter('t_ms')))


def test_complete_first_frame_control_is_admitted():
    first_frames(frame_trace())


@pytest.mark.parametrize(
    'escape',
    [
        'no-pane',
        'no-axis',
        'zero-rect',
        'late-first',
        'timer-witness',
        'moving-layout',
        'unchanged-selection',
        'no-render',
        'missing-navigation',
    ],
)
def test_first_frame_gate_refuses_each_observation_escape(escape):
    rows = frame_trace()
    first = next(row for row in rows if row['event'] == 'frame')
    if escape == 'no-pane':
        first['panes'].remove('bragg')
    elif escape == 'no-axis':
        first['axes'].remove('residual')
    elif escape == 'zero-rect':
        first['geometry']['bragg'][3] = 0
    elif escape == 'late-first':
        first['frame'] += 1
    elif escape == 'timer-witness':
        first['witness'] = 'singleShot'
    elif escape == 'moving-layout':
        first['geometry']['bragg'][1] += 1
    elif escape == 'unchanged-selection':
        for row in rows:
            if row['event'] == 'step':
                row['dataset'] = 0
    elif escape == 'no-render':
        rows = [row for row in rows if row['event'] != 'render']
    elif escape == 'missing-navigation':
        rows.pop(0)
    with pytest.raises(AssertionError):
        first_frames(rows)


def view_trace():
    def snapshot(view, shown, count, generation):
        return {
            'view': view,
            'kind': 'V1',
            'shown': shown,
            'refreshes': count,
            'uploads': count,
            'generation': generation,
        }

    return enrich_views([
        {'event': 'clock', 'gui_thread': 'gui'},
        {'event': 'step', 'name': 'fit-running', 't_ms': 0},
        {
            'event': 'census',
            'views': [{'view': 'hidden', 'kind': 'V1'}, {'view': 'visible', 'kind': 'V1'}],
        },
        {
            'event': 'hidden-before',
            't_ms': 1,
            'views': [snapshot('hidden', False, 0, 0), snapshot('visible', True, 1, 0)],
        },
        *[{'event': 'data-change', 't_ms': i + 2, 'generation': i + 1} for i in range(3)],
        {
            'event': 'hidden-after',
            't_ms': 5,
            'views': [snapshot('hidden', False, 0, 0), snapshot('visible', True, 4, 3)],
        },
        {'event': 'step', 'name': 'fit-ended', 't_ms': 6},
        {'event': 'shown-before', **snapshot('hidden', False, 0, 0)},
        {'event': 'shown-after', **snapshot('hidden', True, 1, 3), 'wanted_generation': 3},
        {'event': 'lazy-created', 'view': 'hidden'},
        {'event': 'build', 'view': 'visible', 'scales': True, 'thread': 'worker'},
        {'event': 'supersede', 'view': 'visible', 't_ms': 2, 'generation': 1, 'replacement': 3},
        {'event': 'deliver', 'view': 'visible', 't_ms': 3, 'generation': 3, 'shown': True},
        {
            'event': 'swap',
            'view': 'visible',
            't_ms': 4,
            'generation': 3,
            'frame': 1,
            'thread': 'gui',
        },
        {'event': 'render', 'frame': 1},
        {
            'event': 'model-change',
            'view': 'visible',
            'incremental': True,
            'operation': 'dataChanged',
            'first': 2,
            'last': 3,
            'rows': 10,
        },
    ])


def test_complete_hidden_and_delivery_control_is_admitted():
    hidden_refreshes(view_trace(), ['V1'])
    work_delivery(view_trace())


@pytest.mark.parametrize(
    'escape',
    [
        'hidden-rebuild',
        'disabled-counters',
        'double-catchup',
        'stale-catchup',
        'missing-instance',
        'hidden-request',
        'gui-builder',
        'stale-swap',
        'double-swap',
        'unrendered-swap',
        'late-delivery',
        'model-reset',
        'full-range',
    ],
)
def test_hidden_and_delivery_gates_refuse_each_observation_escape(escape):
    rows = view_trace()

    def event(name):
        return next(row for row in rows if row['event'] == name)

    if escape in {'hidden-rebuild', 'disabled-counters'}:
        index = 0 if escape == 'hidden-rebuild' else 1
        event('hidden-after')['views'][index]['refreshes'] = 1
    elif escape == 'double-catchup':
        event('shown-after')['refreshes'] = 2
    elif escape == 'stale-catchup':
        event('shown-after')['generation'] = 1
    elif escape == 'missing-instance':
        event('hidden-after')['views'].pop()
    elif escape == 'hidden-request':
        rows.append({'event': 'request', 'view': 'hidden', 't_ms': 3})
    elif escape == 'gui-builder':
        event('build')['thread'] = 'gui'
    elif escape == 'stale-swap':
        event('swap')['generation'] = 1
    elif escape == 'double-swap':
        rows.append(copy.deepcopy(event('swap')))
    elif escape == 'unrendered-swap':
        event('swap')['frame'] = 99
    elif escape == 'late-delivery':
        event('swap')['t_ms'] = 104
    elif escape == 'model-reset':
        event('model-change')['operation'] = 'reset'
    elif escape == 'full-range':
        event('model-change').update(first=0, last=9)
    with pytest.raises(AssertionError):
        check_view_trace(rows)


def check_view_trace(rows):
    hidden_refreshes(rows, ['V1'])
    work_delivery(rows)
