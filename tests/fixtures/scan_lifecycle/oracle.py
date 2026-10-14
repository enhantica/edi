"""Terminal-state invariants from the input file list and the public Qt fit surface."""

import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATE = (
    'running',
    'scanning',
    'scanProcessed',
    'scanFitted',
    'scanTotal',
    'scanProgress',
    'elapsed',
    'iterations',
    'status',
    'outcome',
    'scanText',
    'eta',
)


def signals():
    header = (ROOT / 'app/src/fit_view_model.hpp').read_text()
    block = header.split('   signals:', 1)[1].split('   private:', 1)[0]
    return sorted(re.findall(r'void\s+(\w+)\s*\(', block))


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def assert_settled(observation, names, project, quiet_ms):
    assert Path(observation['project']).resolve() == Path(project).resolve(), (
        'The normal-app observation must belong to the independently staged scan'
    )
    assert observation['mode'] == 'sequential', 'The actual run must use sequential fitting'
    assert observation['files'] == names, (
        'The app must discover exactly the authored scan file list'
    )
    assert sorted(observation['signals_watched']) == signals(), (
        'The observer must retain every signal declared by the public fit view model'
    )
    events = observation['events']
    assert len(events) >= 5, 'A real fit must expose its start, progress, end and quiet samples'
    times = [event['ms'] for event in events]
    assert all(finite(value) and value >= 0 for value in times), (
        'Event timestamps must be finite nonnegative monotonic-clock observations'
    )
    assert times == sorted(times), 'Fit events and samples must preserve their arrival order'
    count = len(names)
    for event in events:
        assert all(key in event for key in STATE), (
            'Every event must read the complete live fit state'
        )
        assert type(event['running']) is bool and type(event['scanning']) is bool, (
            'Fit state samples must preserve boolean running and scanning properties'
        )
        assert event['kind'] in {'signal', 'sample'}, (
            'Each record must be an actual signal or live sample'
        )
        for key in ('scanProcessed', 'scanFitted', 'scanTotal'):
            assert type(event[key]) is int, 'Scan counters must be integer live property readings'
        assert 0 <= event['scanFitted'] <= event['scanProcessed'] <= count, (
            'The fit counter must never run beyond the independently counted scan files'
        )
        assert event['scanTotal'] in {0, count}, (
            'The scan total must resolve to the input file count'
        )
        progress = event['scanProgress']
        expected = event['scanProcessed'] / count if event['scanTotal'] else 0
        assert finite(progress) and abs(progress - expected) <= 1e-12, (
            'The progress fraction must agree with the actual processed and total counters'
        )
        if event['kind'] == 'signal':
            assert event['signal'] in signals(), (
                'Signal records must identify a real fit-model signal'
            )
    assert any(event['running'] and event['kind'] == 'signal' for event in events), (
        'The normal app must actually enter a running fit before it reports an end'
    )
    assert any(event['scanProcessed'] > 0 and event['kind'] == 'signal' for event in events), (
        'The normal app must publish actual file progress, not only an idle snapshot'
    )
    ends = [
        i
        for i, event in enumerate(events)
        if event['kind'] == 'signal' and event['signal'] == 'scanFinished'
    ]
    assert len(ends) == 1, 'One started sequential scan must emit exactly one terminal scan signal'
    end = events[ends[0]]
    assert not end['running'] and not end['scanning'], (
        'The terminal scan signal must read a cleared running and scanning state'
    )
    assert end['scanProcessed'] == end['scanFitted'] == end['scanTotal'] == count, (
        'A completed positive-input scan must stop its counter at the file count'
    )
    assert end['scanProgress'] == 1, 'A fully processed scan must stop its progress at one'
    after = events[ends[0] + 1 :]
    assert len(after) >= 2 and all(event['kind'] == 'sample' for event in after), (
        'No fit-model signal may arrive after the terminal scan signal'
    )
    assert after[-1]['ms'] - end['ms'] >= quiet_ms, (
        'The app must keep its event loop alive beyond the progress timer period after ending'
    )
    assert all(all(event[key] == end[key] for key in STATE) for event in after), (
        'Stopped state, counters and elapsed/iteration text must remain unchanged after ending'
    )
