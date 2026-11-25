"""Build content-model and render-consumer inputs, independently of the app."""

import hashlib

from tests.fixtures.ui_responsiveness.content_contract import (
    content_expectations,
    required_content,
)
from tests.fixtures.ui_responsiveness.tab_inventory import tab_targets


def activate(trace, state, expectations, active, publications):
    wanted = {
        area: (state['page'], area, key)
        for area, key in required_content({'area': 'page', 'page': state['page']}, state)
    }
    for area, current in list(active.items()):
        if current['key'] != wanted.get(area):
            trace.append({
                'event': 'content-hidden',
                't_ms': state['t_ms'],
                'root': current['root'],
                'visit': current['visit'],
                'thread': 'gui',
            })
            del active[area]
    state['content_sources'] = {}
    state['model_bindings'] = {}
    for area, key in wanted.items():
        spec = expectations[state['page']][area][key[2]]
        root = '/'.join(key)
        source = {
            'input': state['input'],
            'data': 'native-model/' + spec['binding'],
            'generation': 1,
            'stage': spec['stage'],
        }
        if area not in active:
            active[area] = {
                'root': root,
                'key': key,
                'visit': root + '/visit-' + str(state['request']),
            }
            trace.append({
                'event': 'content-shown',
                't_ms': state['t_ms'],
                'root': root,
                'visit': active[area]['visit'],
                'thread': 'gui',
            })
        state['content_sources'][area] = dict(source)
        state['model_bindings'][spec['binding']] = {
            field: source[field] for field in ('data', 'generation')
        }
        if root not in publications:
            publications[root] = {
                'event': 'content-publication',
                't_ms': state['t_ms'] + 0.2,
                'id': 'payload/' + root,
                'root': root,
                'source': dict(source),
                'kind': spec['kind'],
                'mode': spec['mode'],
                'unit': spec['unit'],
                'count': 0 if spec['mode'] == 'empty' else 2,
                'digest': hashlib.sha256(root.encode()).hexdigest(),
                'reason': spec.get('reason', ''),
                'thread': 'gui',
                'loaded': 4000,
                'covered': 4000,
                'failed': 0,
            }
            trace.append(publications[root])


def populate_frame(trace, state, target, inventory, expectations, active, publications):
    frame = next(r for r in trace if r['event'] == 'render' and r['frame'] == state['request'])
    frame['contents'] = []
    for area, current in active.items():
        key = current['key'][2]
        spec = expectations[state['page']][area][key]
        if (area, key) in required_content(target, state):
            trace.append({
                'event': 'content-selected',
                't_ms': state['t_ms'] + 0.1,
                'request': state['request'],
                'area': area,
                'key': key,
                'root': current['root'],
                'visit': current['visit'],
                'kind': spec['kind'],
                'object': spec.get('object', ''),
                'tab_object': next(
                    (
                        t['object']
                        for t in inventory[state['page']].get(area, [])
                        if t['key'] == key
                    ),
                    '',
                ),
                'source': state['content_sources'][area],
                'tab_enabled': True,
                'tab_visible': True,
                'witness': 'native-selected-content',
                'thread': 'gui',
            })
        published = publications[current['root']]
        frame['contents'].append({
            'root': current['root'],
            'visit': current['visit'],
            'publication': published['id'],
            'source': dict(published['source']),
            'kind': spec['kind'],
            'mode': published['mode'],
            'unit': published['unit'],
            'count': published['count'],
            'digest': published['digest'],
            'reason': published['reason'],
            'visible': True,
            'geometry': [0, 0, 300, 200],
            'loading': 0,
            'pending': 0,
            'visual_count': 1,
            'loaded': 4000,
            'covered': 4000,
            'failed': 0,
            'witness': 'native-render-consumer',
        })
    publication = next(
        r
        for r in trace
        if r['event'] == 'transition-publication' and r['transition'] == state['transition']
    )
    publication['content_publications'] = [item['publication'] for item in frame['contents']]


def with_content(trace, inventory):
    expectations = content_expectations(inventory)
    targets = tab_targets(inventory)
    next(r for r in trace if r['event'] == 'input')['patterns'] = 4000
    active, publications = {}, {}
    for state in [r for r in trace if r['event'] == 'state']:
        activate(trace, state, expectations, active, publications)
        populate_frame(
            trace, state, targets[state['request']], inventory, expectations, active, publications
        )
    return trace
