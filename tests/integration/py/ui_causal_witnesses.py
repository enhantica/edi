"""Require causal native observations rather than successful driver labels."""

import json
from pathlib import Path


def need(value, explanation):
    assert value, 'Native UI evidence must prove the causal requirement: ' + explanation


def rows(trace, event):
    return [r for r in trace if r['event'] == event]


def unique(trace, event, **keys):
    found = [r for r in rows(trace, event) if all(r.get(k) == v for k, v in keys.items())]
    need(len(found) == 1, 'one native event per operation: ' + event)
    return found[0]


def exclusions(trace, spans):
    callbacks = rows(trace, 'measurement-enter')
    need(
        len(callbacks) == len(rows(trace, 'measurement-leave')) == len(spans),
        'each excluded span has one actual measurement callback',
    )
    measurement_events = {'tool-begin', 'tool-end', 'measurement-enter', 'measurement-leave'}
    for start, stop, identity in spans:
        enter = unique(trace, 'measurement-enter', id=identity)
        leave = unique(trace, 'measurement-leave', id=identity)
        need(
            enter['callback'] in {'QQuickWindow::grabWindow', 'compare-images'},
            'only grab and comparison callbacks are excluded',
        )
        need(
            enter['callback'] == leave['callback']
            and enter['thread'] == leave['thread']
            and enter['thread'] == unique(trace, 'clock')['gui_thread'],
            'callback ownership is GUI-local',
        )
        need(
            enter['t_ms'] == start and leave['t_ms'] == stop,
            'markers exactly delimit callback entry and return',
        )
        need(
            not any(
                r['event'] not in measurement_events
                and (r.get('thread') or enter['thread']) == enter['thread']
                and start < r['t_ms'] < stop
                for r in trace
            ),
            'application and reentrant work cannot occur inside a measurement exclusion',
        )


def block_interval(trace, ticks, spans):
    start, stop = unique(trace, 'block-begin'), unique(trace, 'block-end')
    covering = [
        (a, b)
        for a, b in zip(ticks, ticks[1:], strict=False)
        if a <= start['t_ms'] < stop['t_ms'] <= b
    ]
    need(len(covering) == 1, 'a real GUI block suppresses ticks until its recovery')
    a, b = covering[0]
    need(b <= unique(trace, 'complete')['t_ms'], 'measurement continues through control recovery')
    excluded = sum(max(0, min(b, y) - max(a, x)) for x, y, _ in spans)
    need(b - a - excluded - 10 > 100, 'the control block itself causes the violating interval')


def actions(trace, scenario, steps):
    begin, complete = unique(trace, 'begin'), unique(trace, 'complete')
    issued = rows(trace, 'action')
    need(
        [r['name'] for r in issued] == steps, 'every requested action is actually issued in order'
    )
    need(len({r['request'] for r in issued}) == len(issued), 'action identities are unique')
    previous = {}
    for action in issued:
        state = unique(trace, 'state', request=action['request'])
        step = unique(trace, 'step', request=action['request'])
        need(
            begin['t_ms'] <= action['t_ms'] <= state['t_ms'] <= step['t_ms'] <= complete['t_ms'],
            'state follows input issuance before its completion label',
        )
        need(
            all(
                begin['t_ms'] <= r['t_ms'] <= complete['t_ms']
                for r in trace
                if r['event'] in {'presented', 'render', 'frame'}
                and r.get('request') == action['request']
            ),
            'the measured interval contains requested presentation and rendered completion',
        )
        need(
            state['input'] == unique(trace, 'input')['identity'],
            'each action observes the loaded scenario input',
        )
        if scenario == 'e58-series':
            busy = action['name'] in {'fit-start', 'fit-running'}
            need(
                state['fitting'] is busy,
                'series actions observe actual running and completed states',
            )
            need(
                (state['completed'] < 100) if busy else (state['completed'] == 100),
                'series state witnesses the entire one hundred point fit',
            )
        if scenario == 'e58-pages':
            need(
                state['page'] == action['name'].removeprefix('page-'),
                'page navigation reaches its requested page',
            )
        if scenario in {'e58-banks', 'e58-pattern'}:
            page, direction, _ = action['name'].split('-')
            need(
                state['page'] == page and state['tab'] == 'pattern',
                'navigation uses the actual requested page and tab',
            )
            delta = 1 if direction == 'next' else -1
            need(
                state['selection'] - action['before_selection'] == delta,
                'actual bank or dataset selection moves with the requested input',
            )
            if page in previous:
                need(
                    action['before_selection'] == previous[page]['selection'],
                    'successive inputs follow the observed selection',
                )
            previous[page] = state
    if scenario == 'e58-pattern':
        for page in ('experiment', 'analysis'):
            series = [r for r in issued if r['name'].startswith(page + '-')]
            need(
                all(
                    0 < b['t_ms'] - a['t_ms'] <= 110
                    for a, b in zip(series, series[1:], strict=False)
                ),
                'rapid navigation uses the 100 ms schedule plus at most one tick of jitter',
            )


def view_types():
    contract = json.loads(
        (Path(__file__).parents[2] / 'fixtures/ui_responsiveness/contract.json').read_text()
    )
    return {v: k for k, v in contract['views'].items()}


def lifecycle(trace, kinds):
    hierarchy = unique(trace, 'hierarchy')
    population = {
        r['view']: r
        for r in hierarchy['objects']
        if r['type'] in view_types() and r['initialized']
    }
    registered = {r['view']: r for r in unique(trace, 'census')['views']}
    need(
        population.keys() == registered.keys(),
        'native hierarchy and registered counters cover identical initialized instances',
    )
    need(
        hierarchy['active_page'] == 'analysis' and hierarchy['active_tab'] == 'pattern',
        'hidden observation runs with Analysis Pattern active',
    )
    before, after = unique(trace, 'hidden-before'), unique(trace, 'hidden-after')
    ends = {r['view']: r for r in after['views']}
    changes = rows(trace, 'data-change')
    need(
        len({r['generation'] for r in changes}) == len(changes) >= 3,
        'real data generations change distinctly',
    )
    need(
        all(r['before_hash'] != r['after_hash'] for r in changes),
        'data-change witnesses observe changed model bytes',
    )
    need(
        all(
            a['after_hash'] == b['before_hash'] for a, b in zip(changes, changes[1:], strict=False)
        ),
        'observed changes form a continuous model history',
    )
    hidden_kinds = set()
    for snapshot in before['views']:
        view = snapshot['view']
        native = population[view]
        effective = (
            native['page'] == 'analysis'
            and native['tab'] in {'pattern', 'sidebar'}
            and all(native['ancestors_shown'])
        )
        need(
            snapshot['shown'] == effective and view_types()[native['type']] == snapshot['kind'],
            'counter visibility follows the actual enclosing page and tab chain',
        )
        if effective:
            continue
        hidden_kinds.add(snapshot['kind'])
        invalidations = [r for r in rows(trace, 'invalidate') if r['view'] == view]
        need(
            [r['generation'] for r in invalidations] == [r['generation'] for r in changes],
            'every hidden instance is invalidated by each distinct actual change',
        )
        need(
            [r['after_hash'] for r in invalidations] == [r['after_hash'] for r in changes],
            'invalidations bind the actual changed model content',
        )
        show = unique(trace, 'shown-before', view=view)
        caught = unique(trace, 'shown-after', view=view)
        need(
            after['t_ms'] < show['t_ms'] < caught['t_ms'],
            'show and catch-up follow the entire hidden interval',
        )
        need(
            (show['refreshes'], show['uploads'])
            == (ends[view]['refreshes'], ends[view]['uploads']),
            'hidden counters cannot rise before showing',
        )
        need(
            all(before['t_ms'] < r['t_ms'] < after['t_ms'] for r in invalidations),
            'invalidations belong to this hide/change/show lifecycle',
        )
        need(
            caught['wanted_generation'] == invalidations[-1]['generation'],
            'show consumes the newest actual invalidation',
        )
    need(set(kinds) <= hidden_kinds, 'every claimed data-view kind has a hidden instance')
    created = rows(trace, 'lazy-created')
    need(
        created and all(r['view'] in population and r['t_ms'] < before['t_ms'] for r in created),
        'previously lazy instances are created before the observed hidden lifecycle',
    )
    need(
        any(r['view'] not in {c['view'] for c in created} for r in population.values()),
        'retained instances are exercised as well as lazy instances',
    )


def work_key(row):
    return tuple(row[k] for k in ('view', 'builder', 'generation'))


def delivery(trace):
    contract = json.loads(
        (Path(__file__).parents[2] / 'fixtures/ui_responsiveness/contract.json').read_text()
    )
    requests = {work_key(r): r for r in rows(trace, 'request')}
    need(len(requests) == len(rows(trace, 'request')), 'requests have distinct causal identities')
    need(
        {r['builder'] for r in requests.values()} == set(contract['builders']),
        'all known data-sized builders are exercised',
    )
    for name in ('build', 'built', 'deliver', 'discard', 'cancel', 'supersede', 'result-arrival'):
        need(
            all(work_key(r) in requests for r in rows(trace, name)),
            'every causal work event names a real request',
        )
    relations = {}
    for relation in rows(trace, 'supersede'):
        key = work_key(relation)
        replacement = (*key[:2], relation['replacement'])
        need(
            key not in relations and replacement in requests and key[2] < replacement[2],
            'supersession connects distinct real ordered generations',
        )
        need(
            requests[key]['t_ms'] < relation['t_ms'] == requests[replacement]['t_ms'],
            'supersession occurs when the replacement is requested',
        )
        relations[key] = replacement
    need(
        {key[1] for key in relations} == set(contract['builders']),
        'each known builder exercises supersession',
    )
    for key, request in requests.items():
        execution(trace, request, key in relations)
    snapshots(trace, requests, relations)
    late = []
    for key, replacement in relations.items():
        arrivals = [r for r in rows(trace, 'result-arrival') if work_key(r) == key]
        newer = [r for r in rows(trace, 'built') if work_key(r) == replacement]
        if arrivals and newer and arrivals[0]['t_ms'] > newer[0]['t_ms']:
            late.append(key)
    need(bool(late), 'a controlled stale arrival after replacement completion exercises rejection')
    edits = [r for r in rows(trace, 'model-change') if r['incremental']]
    need(bool(edits), 'real incremental changes are exercised')
    for edit in edits:
        need(
            edit['operation'] in {'dataChanged', 'insert', 'remove'}
            and 0 <= edit['first'] <= edit['last'] < edit['rows'],
            'incremental edits retain valid bounds without model reset',
        )
        need(
            [edit['first'], edit['last']] == edit['changed_range'],
            'every range matches the actual change including full and one-row models',
        )
    need(
        any(r['last'] - r['first'] + 1 < r['rows'] for r in edits),
        'a partial edit witnesses strict subrange invalidation',
    )


def execution(trace, request, stale):
    key = work_key(request)
    records = {
        name: [r for r in rows(trace, name) if work_key(r) == key]
        for name in ('build', 'built', 'cancel', 'discard', 'deliver', 'result-arrival')
    }
    if not records['build']:
        need(
            stale and len(records['cancel']) == 1,
            'a superseded queued request can cancel before execution',
        )
        need(
            not any(records[n] for n in ('built', 'discard', 'deliver', 'result-arrival')),
            'queued cancellation does not fabricate execution or output',
        )
        replacement = unique(trace, 'supersede', view=key[0], builder=key[1], generation=key[2])
        need(
            records['cancel'][0]['t_ms'] >= replacement['t_ms'],
            'queued cancellation follows supersession',
        )
        return
    need(
        len(records['build']) == len(records['built']) == 1,
        'executed work has exactly one start and completion',
    )
    start, done = records['build'][0], records['built'][0]
    gui = unique(trace, 'clock')['gui_thread']
    need(request['t_ms'] <= start['t_ms'] < done['t_ms'], 'execution follows its actual request')
    need(
        bool(start['thread']) and start['thread'] == done['thread'] != gui,
        'data-sized work executes off the GUI thread',
    )
    if stale:
        need(
            len(records['discard']) == len(records['result-arrival']) == 1
            and not records['deliver'],
            'stale results are observed arriving and rejected before view delivery',
        )
        relation = unique(trace, 'supersede', view=key[0], builder=key[1], generation=key[2])
        need(
            done['t_ms'] <= records['result-arrival'][0]['t_ms'] <= records['discard'][0]['t_ms']
            and relation['t_ms'] <= records['discard'][0]['t_ms'],
            'stale rejection follows real completion, arrival and supersession',
        )
    else:
        need(
            len(records['deliver']) == 1 and not records['discard'] and not records['cancel'],
            'current completed work delivers exactly once',
        )
        need(done['t_ms'] <= records['deliver'][0]['t_ms'], 'delivery follows completed execution')


def snapshots(trace, requests, relations):
    consumed = set()
    swaps = rows(trace, 'swap')
    need(bool(swaps), 'current builder outputs reach a rendered snapshot')
    identities = [(r['view'], r['frame']) for r in swaps]
    need(len(identities) == len(set(identities)), 'each view swaps at most once per actual frame')
    for swap in swaps:
        render = unique(trace, 'render', frame=swap['frame'])
        need(
            swap['t_ms'] == render['t_ms']
            and swap['thread'] == unique(trace, 'clock')['gui_thread'],
            'view swaps bind the actual render clock and GUI owner',
        )
        sources = swap.get('sources', [swap])
        need(bool(sources), 'a view snapshot names its actual contributing builder outputs')
        for source in sources:
            key = work_key(source)
            need(
                key in requests
                and key not in relations
                and key not in consumed
                and key[0] == swap['view'],
                'only current output contributes once to its target view',
            )
            need(
                not any(
                    other[:2] == key[:2] and other[2] > key[2] and r['t_ms'] <= swap['t_ms']
                    for other, r in requests.items()
                ),
                'no superseded generation can reach a view even without a supersede label',
            )
            output = unique(trace, 'deliver', view=key[0], builder=key[1], generation=key[2])
            need(
                output['t_ms'] <= swap['t_ms'] <= output['t_ms'] + 100,
                'a shown completed output reaches its view within the coalescing bound',
            )
            consumed.add(key)
    need(
        consumed == set(requests) - set(relations),
        'every current builder output contributes to a final view snapshot',
    )


def rendered_navigation(trace):
    for step in rows(trace, 'step'):
        action = unique(trace, 'action', request=step['request'])
        render = [r for r in rows(trace, 'render') if r['t_ms'] >= action['t_ms']]
        first = unique(trace, 'frame', request=step['request'], phase='first')
        settled = unique(trace, 'frame', request=step['request'], phase='settled')
        need(
            bool(render) and first['frame'] == render[0]['frame'],
            'first frame is measured from issuance, not a delayed completion label',
        )
        state = unique(trace, 'state', request=step['request'])
        need(
            state['input'] == unique(trace, 'input')['identity']
            and state['selection'] == step['dataset'],
            'the rendered request uses the actual selected dataset and loaded input',
        )
        publication = unique(trace, 'presented', request=step['request'])
        displayed = unique(trace, 'render', frame=settled['frame'])
        need(
            bool(state['data_identity'])
            and bool(state['input'])
            and all(
                r['input'] == state['input'] and r['data_identity'] == state['data_identity']
                for r in (publication, displayed)
            ),
            'rendered pattern content and project identity match native selection',
        )
        need(
            displayed['generation'] == publication['generation']
            and displayed['dataset'] == step['dataset'],
            'settled render contains the requested published data',
        )
        need(
            publication['dataset'] == step['dataset'] and publication['t_ms'] >= action['t_ms'],
            'settling follows presentation of the requested actual dataset',
        )
        for frame in (first, settled):
            swap = unique(trace, 'render', frame=frame['frame'])
            need(
                frame['t_ms'] == swap['t_ms'] and swap['request'] == step['request'],
                'both geometry observations bind synchronized and swapped frames for this request',
            )
            need(
                set(frame['visible']) == set(frame['geometry']) and all(frame['visible'].values()),
                'every required positive-size pane and axis is effectively shown',
            )
        need(
            settled['t_ms'] >= publication['t_ms']
            and settled['generation'] == publication['generation'],
            'settled geometry belongs to the rendered new-data generation',
        )
