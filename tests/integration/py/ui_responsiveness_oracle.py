"""Independent interval arithmetic and render/refresh invariants for UI traces."""

import math

from tests.integration.py import ui_causal_witnesses as causal


def require(condition, message):
    assert condition, 'UI observation must satisfy the declared requirement: ' + message


def events(trace, name):
    return [row for row in trace if row['event'] == name]


def one(trace, name):
    rows = events(trace, name)
    require(len(rows) == 1, 'one ' + name + ' event is required')
    return rows[0]


def timing(trace, scenario, steps, *, control=False):
    clock = one(trace, 'clock')
    require(
        (clock['clock'], clock['unit'], clock['tick_ms']) == ('monotonic', 'ms', 10),
        'S5 uses monotonic milliseconds and a nominal ten millisecond timer',
    )
    times = [row['t_ms'] for row in trace]
    require(
        all(type(t) in {int, float} and math.isfinite(t) for t in times),
        'timestamps are finite clock values',
    )
    require(times == sorted(times), 'recording preserves monotonic event order')
    begin, end = one(trace, 'begin'), one(trace, 'complete')
    require(begin['scenario'] == end['scenario'] == scenario, 'scenario identity is consistent')
    require(end['t_ms'] > begin['t_ms'], 'the scenario has a nonempty measured interval')
    observed = events(trace, 'step')
    require([row['name'] for row in observed] == steps, 'every ordered scenario step completes')
    require(
        all(begin['t_ms'] <= row['t_ms'] <= end['t_ms'] for row in observed),
        'all scenario steps occur inside the measured interval',
    )
    ticks = [row['t_ms'] for row in events(trace, 'tick')]
    require(len(ticks) >= 3 and ticks == sorted(set(ticks)), 'real timer endpoints are distinct')
    require(
        ticks[0] <= begin['t_ms'] and ticks[-1] >= end['t_ms'],
        'timer endpoints bracket the whole scenario including the end transition',
    )
    spans, pending = [], None
    for row in trace:
        if row['event'] == 'tool-begin':
            require(pending is None, 'measurement markers cannot nest')
            pending = row
        elif row['event'] == 'tool-end':
            require(
                pending is not None and pending['id'] == row['id'],
                'measurement markers pair by identity',
            )
            require(row['t_ms'] >= pending['t_ms'], 'measurement duration is nonnegative')
            spans.append((pending['t_ms'], row['t_ms'], row['id']))
            pending = None
    require(pending is None, 'an unmatched marker cannot hide the rest of the run')
    causal.exclusions(trace, spans)
    gaps = []
    for left, right in zip(ticks, ticks[1:], strict=False):
        if right < begin['t_ms'] or left > end['t_ms']:
            continue
        excluded = sum(max(0, min(right, stop) - max(left, start)) for start, stop, _ in spans)
        gaps.append(max(0, right - left - excluded - 10))
    if control:
        block, release = one(trace, 'block-begin'), one(trace, 'block-end')
        require(
            block['thread'] == release['thread'] == clock['gui_thread'],
            'the deliberate block executes on the GUI thread',
        )
        require(
            begin['t_ms'] <= block['t_ms'] < release['t_ms'] <= end['t_ms'],
            'the complete deliberate block lies inside the scenario',
        )
        require(release['t_ms'] - block['t_ms'] >= 150, 'the control really blocks for 150 ms')
        require(
            all(stop <= block['t_ms'] or start >= release['t_ms'] for start, stop, _ in spans),
            'the block cannot be excluded as measurement-tool work',
        )
    if control:
        causal.block_interval(trace, ticks, spans)
    require(max(gaps) <= 100, 'U8 permits no counted gap strictly over 100 ms')


def indexed(rows):
    result = {row['view']: row for row in rows}
    require(len(result) == len(rows) and bool(result), 'every view instance has a unique identity')
    return result


def hidden_refreshes(trace, kinds):
    causal.lifecycle(trace, kinds)
    census = indexed(one(trace, 'census')['views'])
    require(
        set(kinds) <= {row['kind'] for row in census.values()},
        'the census covers every data-view kind in the approved inventory',
    )
    before, after = one(trace, 'hidden-before'), one(trace, 'hidden-after')
    starts, ends = indexed(before['views']), indexed(after['views'])
    require(starts.keys() == ends.keys() == census.keys(), 'no initialized instance is omitted')
    changes = [
        r for r in events(trace, 'data-change') if before['t_ms'] < r['t_ms'] < after['t_ms']
    ]
    require(len(changes) >= 3, 'repeated actual changes exercise dirty coalescing')
    steps = {row['name']: row['t_ms'] for row in events(trace, 'step')}
    require(
        steps['fit-running'] <= before['t_ms'] < after['t_ms'] <= steps['fit-ended'],
        'hidden counters are observed during a genuinely running fit',
    )
    hidden = {key for key, row in starts.items() if row['shown'] is False}
    require(
        bool(hidden) and len(hidden) < len(starts), 'both hidden and visible views are observed'
    )
    require(
        not any(
            row['view'] in hidden and before['t_ms'] < row['t_ms'] < after['t_ms']
            for row in events(trace, 'request')
        ),
        'U5 hidden views do not request builders',
    )
    for key, start in starts.items():
        end = ends[key]
        require(end['shown'] == start['shown'], 'visibility is stable during the hidden interval')
        if key in hidden:
            require(
                (end['refreshes'], end['uploads']) == (start['refreshes'], start['uploads']),
                'U1 hidden builders and uploads perform zero work: ' + key,
            )
        else:
            require(
                end['refreshes'] > start['refreshes'] and end['uploads'] > start['uploads'],
                'positive visible observations reject disabled counters: ' + key,
            )
    shown_before, shown_after = (
        indexed(events(trace, 'shown-before')),
        indexed(events(trace, 'shown-after')),
    )
    require(
        shown_before.keys() == shown_after.keys() == hidden,
        'each retained hidden instance is subsequently shown',
    )
    for key in hidden:
        start, end = shown_before[key], shown_after[key]
        require(start['shown'] is False and end['shown'] is True, 'the real shown chain changes')
        require(
            end['refreshes'] - start['refreshes'] == end['uploads'] - start['uploads'] == 1,
            'U1 showing a dirty view performs exactly one completed catch-up',
        )
        require(
            end['generation'] == end['wanted_generation']
            and end['generation'] >= changes[-1]['generation'],
            'the catch-up uses the newest pending data rather than the first invalidation',
        )
    lazy = events(trace, 'lazy-created')
    require(
        bool(lazy) and any(row['view'] in hidden for row in lazy),
        'a previously lazy view also exercises observed initialization and catch-up',
    )


def work_delivery(trace):
    causal.delivery(trace)


def first_frames(trace):
    causal.rendered_navigation(trace)
    navigations = events(trace, 'step')
    requests = [row['request'] for row in navigations]
    require(
        len(requests) == 40 and len(set(requests)) == 40,
        'ten Next and Previous actions run on both pages',
    )
    renders = events(trace, 'render')
    require(bool(renders), 'actual frameSwapped events independently witness the first frame')
    for nav in navigations:
        frames = [row for row in events(trace, 'frame') if row['request'] == nav['request']]
        first_rows = [row for row in frames if row['phase'] == 'first']
        settled_rows = [row for row in frames if row['phase'] == 'settled']
        require(
            len(first_rows) == len(settled_rows) == 1,
            'each navigation has one first and settled frame',
        )
        first, settled = first_rows[0], settled_rows[0]
        issued = causal.unique(trace, 'action', request=nav['request'])
        following = [row for row in renders if row['t_ms'] >= issued['t_ms']]
        require(
            bool(following) and first['frame'] == following[0]['frame'],
            'U7 observes the first actual swap without a ready predicate or settle timer',
        )
        require(
            first['t_ms'] == following[0]['t_ms'] and settled['t_ms'] >= first['t_ms'],
            'frame observations retain the actual swap clock and ordering',
        )
        require(
            first['witness'] == settled['witness'] == 'afterSynchronizing/frameSwapped',
            'scene-sync geometry belongs to an actual rendered frame',
        )
        for frame in (first, settled):
            require(
                set(frame['panes']) == {'pattern', 'bragg', 'residual'},
                'the complete powder pane set is present',
            )
            require(
                set(frame['axes']) == {'x', 'intensity', 'residual'},
                'every required axis is present',
            )
            require(
                set(frame['geometry'])
                == {'pattern', 'bragg', 'residual', 'x', 'intensity', 'residual-axis'},
                'the geometry observes every pane and axis explicitly',
            )
            require(
                all(
                    len(rect) == 4
                    and all(math.isfinite(x) for x in rect)
                    and rect[2] > 0
                    and rect[3] > 0
                    for rect in frame['geometry'].values()
                ),
                'no missing or zero-size pane can pass by equality',
            )
        require(
            first['geometry'] == settled['geometry'],
            'U7 data arrival preserves the first complete layout',
        )
    for page in ('experiment', 'analysis'):
        page_steps = [row for row in navigations if row['name'].startswith(page + '-')]
        selected = [row['dataset'] for row in page_steps]
        require(
            all(a != b for a, b in zip(selected, selected[1:], strict=False)),
            'every navigation actually changes the selected dataset',
        )
        require(
            all(
                row['direction'] == ('next' if '-next-' in row['name'] else 'previous')
                for row in page_steps
            ),
            'the actual navigation direction matches the requested control',
        )
        require(
            all(
                current['dataset'] - previous['dataset']
                == (1 if current['direction'] == 'next' else -1)
                for previous, current in zip(page_steps, page_steps[1:], strict=False)
            ),
            'Next and Previous move the actual dataset index in their respective directions',
        )
