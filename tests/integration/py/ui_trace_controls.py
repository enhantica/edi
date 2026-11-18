"""Construct complete causal traces for independent gate escape exercises."""

import json
import operator
from pathlib import Path


def enrich_frames(trace):
    for step in [r for r in trace if r['event'] == 'step']:
        request, t = step['request'], step['t_ms']
        trace.append({'event': 'action', 'request': request, 't_ms': t, 'name': step['name']})
        trace.append({
            'event': 'presented',
            'request': request,
            't_ms': t + 1.5,
            'dataset': step['dataset'],
            'generation': request,
        })
        for r in trace:
            if r['event'] == 'render' and r['frame'] in {request * 2, request * 2 + 1}:
                r['request'] = request
                r['generation'] = request
                r['dataset'] = step['dataset']
            if r['event'] == 'frame' and r['request'] == request:
                r['visible'] = dict.fromkeys(r['geometry'], True)
                r['generation'] = request
    return sorted(trace, key=operator.itemgetter('t_ms'))


def enrich_views(trace):
    census = next(r for r in trace if r['event'] == 'census')['views']
    trace.append({
        'event': 'hierarchy',
        'active_page': 'analysis',
        'active_tab': 'pattern',
        'objects': [
            {
                'view': r['view'],
                'type': 'PatternChart',
                'initialized': True,
                'page': 'analysis' if r['view'] == 'visible' else 'experiment',
                'tab': 'pattern',
                'ancestors_shown': [True],
            }
            for r in census
        ],
    })
    for r in trace:
        if r['event'] == 'data-change':
            r['before_hash'] = str(r['generation'] - 1)
            r['after_hash'] = str(r['generation'])
        if r['event'] == 'shown-before':
            r['t_ms'] = 7
        if r['event'] == 'shown-after':
            r['t_ms'] = 8
        if r['event'] == 'lazy-created':
            r['t_ms'] = 0
        if r['event'] == 'model-change':
            r['changed_range'] = [2, 3]
    trace.extend(
        {
            'event': 'invalidate',
            'view': 'hidden',
            't_ms': i + 2,
            'generation': i + 1,
            'after_hash': str(i + 1),
        }
        for i in range(3)
    )
    trace = [
        r for r in trace if r['event'] not in {'build', 'supersede', 'deliver', 'swap', 'render'}
    ]
    builders = json.loads(
        (Path(__file__).parents[2] / 'fixtures/ui_responsiveness/contract.json').read_text()
    )['builders']
    for i, builder in enumerate(builders):
        key = {'view': 'visible', 'builder': builder}
        for gen, requested, started, done in ((1, 10, 11, 17), (2, 12, 13, 14)):
            trace.extend([
                {'event': 'request', **key, 'generation': gen, 't_ms': requested},
                {
                    'event': 'build',
                    **key,
                    'generation': gen,
                    't_ms': started,
                    'thread': 'worker',
                    'scales': True,
                },
                {'event': 'built', **key, 'generation': gen, 't_ms': done, 'thread': 'worker'},
            ])
        trace.extend([
            {'event': 'supersede', **key, 'generation': 1, 'replacement': 2, 't_ms': 12},
            {'event': 'discard', **key, 'generation': 1, 't_ms': 18},
            {'event': 'deliver', **key, 'generation': 2, 'shown': True, 't_ms': 15},
            {'event': 'swap', **key, 'generation': 2, 'frame': i, 'thread': 'gui', 't_ms': 16},
            {'event': 'render', 'frame': i, 't_ms': 16},
        ])
    # Each builder is a distinct observed snapshot target.
    for row in trace:
        if 'builder' in row:
            row['view'] = row['builder']
    return trace
