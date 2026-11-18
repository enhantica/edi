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
    forbidden = {
        'action',
        'state',
        'step',
        'request',
        'build',
        'deliver',
        'swap',
        'model-change',
        'data-change',
        'begin',
        'complete',
        'tick',
    }
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
            not any(r['event'] in forbidden and start < r['t_ms'] < stop for r in trace),
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
    excluded = sum(max(0, min(b, y) - max(a, x)) for x, y, _ in spans)
    need(b - a - excluded - 10 > 100, 'the control block itself causes the violating interval')


def actions(trace, scenario, steps):
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
            action['t_ms'] <= state['t_ms'] <= step['t_ms'],
            'state follows input issuance before its completion label',
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


def delivery(trace):
    contract = json.loads(
        (Path(__file__).parents[2] / 'fixtures/ui_responsiveness/contract.json').read_text()
    )
    expected = set(contract['builders'])
    requested = rows(trace, 'request')
    need(
        {r['builder'] for r in requested} == expected,
        'requests cover every known data-sized builder',
    )
    gui = unique(trace, 'clock')['gui_thread']
    keys = [(r['view'], r['builder'], r['generation']) for r in requested]
    need(len(keys) == len(set(keys)), 'builder request identities are unique')
    for event in ('build', 'built', 'deliver', 'discard', 'swap'):
        need(
            all((r['view'], r['builder'], r['generation']) in keys for r in rows(trace, event)),
            'all work belongs to a real requested generation',
        )
    for request in requested:
        key = {k: request[k] for k in ('view', 'builder', 'generation')}
        start, done = unique(trace, 'build', **key), unique(trace, 'built', **key)
        need(
            request['t_ms'] <= start['t_ms'] < done['t_ms'],
            'each request binds its actual execution and completion',
        )
        need(
            start['thread'] == done['thread'] and start['thread'] != gui and bool(start['thread']),
            'every known data-sized builder executes off GUI regardless of its scaling label',
        )
        superseded = [
            r for r in rows(trace, 'supersede') if all(r[k] == v for k, v in key.items())
        ]
        if superseded:
            newer = unique(
                trace,
                'request',
                view=request['view'],
                builder=request['builder'],
                generation=superseded[0]['replacement'],
            )
            latest = unique(
                trace,
                'built',
                view=newer['view'],
                builder=newer['builder'],
                generation=newer['generation'],
            )
            discard = unique(trace, 'discard', **key)
            need(
                newer['generation'] > request['generation']
                and newer['t_ms'] == superseded[0]['t_ms']
                and latest['t_ms'] < done['t_ms'] <= discard['t_ms'],
                'a genuinely late old completion is discarded after the newer result',
            )
            need(
                not any(
                    all(r[k] == v for k, v in key.items())
                    for r in rows(trace, 'swap') + rows(trace, 'deliver')
                ),
                'stale results never deliver or swap',
            )
        else:
            delivered = unique(trace, 'deliver', **key)
            swapped = unique(trace, 'swap', **key)
            rendered = unique(trace, 'render', frame=swapped['frame'])
            need(
                done['t_ms'] <= delivered['t_ms'] <= swapped['t_ms'] <= delivered['t_ms'] + 100,
                'each current completion delivers and swaps within its bound',
            )
            need(
                swapped['t_ms'] == rendered['t_ms'] and swapped['thread'] == gui,
                'each snapshot swap binds its actual render clock and owner',
            )
    need(
        {r['builder'] for r in rows(trace, 'supersede')} == expected,
        'out-of-order completion is exercised for every affected builder',
    )
    for edit in rows(trace, 'model-change'):
        if edit['incremental']:
            need(
                edit['operation'] in {'dataChanged', 'insert', 'remove'}
                and 0 <= edit['first'] <= edit['last'] < edit['rows'],
                'every incremental model edit has valid bounds without a reset',
            )
            need(
                [edit['first'], edit['last']] == edit['changed_range'],
                'every emitted range matches actual changes, including the last row',
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
        publication = unique(trace, 'presented', request=step['request'])
        displayed = unique(trace, 'render', frame=settled['frame'])
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
