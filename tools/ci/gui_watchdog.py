# SPDX-License-Identifier: BSD-3-Clause
"""Check a scenario's GUI-thread gaps in a UI trace (ADR-0102).

  gui_watchdog.py --trace <trace.jsonl> --scenario <name>
                  [--contract <contract.json>] [--control] [--report]

The trace is the app's `ui-probe:` events (app/src/ui_probe.hpp), one JSON object per line,
all on one monotonic millisecond clock: `clock` (tick_ms), `begin` and `complete` around the
scenario, a `tick` at every delivery of the GUI thread's 10 ms timer, `step` per measured step,
the callback witnesses `measurement-enter`/`measurement-leave` (one `id`, on the GUI thread)
around the demo driver's own work with its span markers `tool-begin`/`tool-end`, and in a
control run `block-begin`/`block-end` around the injected block. Every event names its
`thread`. Markers and witnesses pair up one id on one thread, never nested; an unmatched,
mismatched or nested one makes the trace invalid.

The clock is checked before any arithmetic: every t_ms a finite number, the nominal tick the
contract's (10 ms), the GUI thread a nonblank name or a positive number, the ticks on that thread
at strictly increasing times, and the measured interval not empty. Each interval between two ticks
that meets the scenario's interval counts as its length, less the time it shares with the driver's
work, less the nominal tick; more than the limit (100 ms) fails. The driver's work is a span whose
markers (`tool-begin`/`tool-end`) and callback witnesses (`measurement-enter`/`measurement-leave`)
agree: one id, one callback, the GUI thread, the same two instants. A span is excluded only while
the GUI thread did nothing else: any other event on the GUI thread inside it (a tick included; an
event naming no thread counts as the GUI thread's) leaves it counted. The ticks must bracket the
scenario's whole interval. With a contract (tests/fixtures/ui_responsiveness/contract.json by
default, when present) the steps must be the scenario's listed steps, in order. --control checks a
control run: it must hold a block on the GUI thread of at least the contract's control length
(150 ms), outside the driver's work, and a gap over the limit, ending inside the measured interval,
must contain that whole block and the timer's recovery from it; the check then fails on it as on
any other.

Exit status: 0 within the limit, 1 a gap over it or a trace that is invalid or incomplete. Only
a valid control whose block was seen prints `the control block was seen`, so a refusal (also 1)
is never taken for a detected block. --report prints the gaps over the limit and exits 0 on
them; a trace that is invalid or incomplete still exits 1. Every refusal names its cause.
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / 'tests/fixtures/ui_responsiveness/contract.json'
CALLBACKS = {'QQuickWindow::grabWindow', 'compare-images', 'DemoDriver::find'}


class InvalidTraceError(Exception):
    """A trace that cannot be judged: malformed, incomplete or inconsistent."""


def load(path: Path) -> list[dict]:
    events = []
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise InvalidTraceError(f'{path}:{number}: not JSON ({error})') from None
        if (
            not isinstance(event, dict)
            or not isinstance(event.get('event'), str)
            or not finite(event.get('t_ms'))
        ):
            raise InvalidTraceError(
                f'{path}:{number}: an event needs an event name and a finite t_ms'
            )
        events.append(event)
    return events


def finite(value: object) -> bool:
    """A JSON number that is finite (NaN and the infinities would make every comparison false)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def owner(value: object) -> bool:
    """A native thread identity: a nonblank string or a positive integer."""
    if isinstance(value, str):
        return bool(value.strip())
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def clock(events: list[dict], tick_ms: float) -> tuple[float, object]:
    """The nominal tick and the GUI thread's name, from the one clock event."""
    clocks = [e for e in events if e['event'] == 'clock']
    if len(clocks) != 1 or clocks[0].get('clock') != 'monotonic' or clocks[0].get('unit') != 'ms':
        raise InvalidTraceError('the trace needs exactly one monotonic millisecond clock event')
    tick = clocks[0].get('tick_ms')
    if not finite(tick) or tick != tick_ms:
        raise InvalidTraceError(
            f'the clock event names a tick of {tick!r}, not the fixed {tick_ms:g} ms'
        )
    gui = clocks[0].get('gui_thread')
    if not owner(gui):
        raise InvalidTraceError(f'the clock event names no GUI thread ({gui!r})')
    return float(tick), gui


def interval(events: list[dict], scenario: str) -> tuple[float, float]:
    """The scenario's measured interval, from its begin to its complete."""
    if any(b['t_ms'] < a['t_ms'] for a, b in zip(events, events[1:], strict=False)):
        raise InvalidTraceError('the events are not in time order')
    begins = [e for e in events if e['event'] == 'begin' and e.get('scenario') == scenario]
    ends = [e for e in events if e['event'] == 'complete' and e.get('scenario') == scenario]
    if len(begins) != 1 or len(ends) != 1:
        raise InvalidTraceError(f'the trace needs one begin and one complete of {scenario}')
    start, end = begins[0]['t_ms'], ends[0]['t_ms']
    if end <= start:
        raise InvalidTraceError('the scenario completes before it begins, or as it begins')
    return start, end


MARKERS = {'tool-begin', 'tool-end', 'measurement-enter', 'measurement-leave'}


def paired(events: list[dict], begin: str, end: str) -> list[tuple[dict, dict]]:
    """Begin and end events of one kind: never nested, each pair on one thread with one id."""
    stack, pairs = [], []
    for event in events:
        if event['event'] == begin:
            if stack:
                raise InvalidTraceError(f'a {begin} (id {event.get("id")}) opens inside another')
            stack.append(event)
        elif event['event'] == end:
            if not stack:
                raise InvalidTraceError(f'a {end} without its {begin} (id {event.get("id")})')
            opened = stack.pop()
            if opened.get('id') != event.get('id') or opened.get('thread') != event.get('thread'):
                raise InvalidTraceError(
                    f'a {end} (id {event.get("id")}) does not close the innermost open {begin} '
                    f'(id {opened.get("id")})'
                )
            pairs.append((opened, event))
    if stack:
        raise InvalidTraceError(f'a {begin} without its {end} (id {stack[-1].get("id")})')
    return pairs


def tool_intervals(events: list[dict], gui: object) -> list[tuple[float, float]]:
    """The driver's own work, as merged intervals.

    Each span's markers and its callback witnesses must agree, one to one: the same id, callback,
    GUI thread and the same two instants. A span is excluded only with no other GUI-thread event
    inside it.
    """
    markers = {}
    for begin, end in paired(events, 'tool-begin', 'tool-end'):
        if begin.get('id') in markers:
            raise InvalidTraceError(f'two driver spans share the id {begin.get("id")}')
        markers[begin.get('id')] = (begin, end)
    excluded, witnessed = [], set()
    for enter, leave in paired(events, 'measurement-enter', 'measurement-leave'):
        callback = enter.get('callback')
        if callback not in CALLBACKS or leave.get('callback') != callback:
            raise InvalidTraceError(f'a measurement span names no driver callback ({callback})')
        if enter.get('thread') != gui:
            raise InvalidTraceError('a measurement span is not on the GUI thread')
        marked = markers.get(enter.get('id'))
        if marked is None or enter.get('id') in witnessed:
            raise InvalidTraceError(
                f'a measurement span (id {enter.get("id")}) has no driver span of its own'
            )
        begin, end = marked
        if (
            begin['t_ms'] != enter['t_ms']
            or end['t_ms'] != leave['t_ms']
            or begin.get('thread') != gui
            or begin.get('callback', callback) != callback
        ):
            raise InvalidTraceError(
                f"a measurement span (id {enter.get('id')}) does not match its driver span's "
                'callback, thread and instants'
            )
        witnessed.add(enter.get('id'))
        t0, t1 = enter['t_ms'], leave['t_ms']
        busy = any(
            t0 < e['t_ms'] < t1 and e['event'] not in MARKERS and e.get('thread', gui) == gui
            for e in events
        )
        if not busy:
            excluded.append((t0, t1))
    if set(markers) != witnessed:
        raise InvalidTraceError('a driver span has no callback witness')
    merged = []
    for t0, t1 in sorted(excluded):
        if merged and t0 <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], t1))
        else:
            merged.append((t0, t1))
    return merged


def blocks(
    events: list[dict], span: tuple[float, float], gui: object, length: float
) -> list[tuple[float, float]]:
    """The control blocks run on the GUI thread inside the measured interval.

    Each is at least `length` long and outside the driver's work. Begin and end pair up by kind,
    whatever other threads write between them.
    """
    start, end = span
    tools = tool_intervals(events, gui)
    found = []
    for a, b in paired(
        [e for e in events if e['event'] in {'block-begin', 'block-end'}],
        'block-begin',
        'block-end',
    ):
        if a.get('thread') != gui or b.get('thread') != gui:
            raise InvalidTraceError('a control block is not on the GUI thread')
        inside = start <= a['t_ms'] and b['t_ms'] <= end
        long_enough = b['t_ms'] - a['t_ms'] >= length
        apart = all(b['t_ms'] <= t0 or t1 <= a['t_ms'] for t0, t1 in tools)
        if inside and long_enough and apart:
            found.append((a['t_ms'], b['t_ms']))
    return found


def gaps_over(
    events: list[dict], span: tuple[float, float], tick: float, limit: float, gui: object
) -> list[tuple[float, float, str]]:
    """The tick intervals whose counted gap is over the limit: start, end and a description."""
    start, end = span
    tools = tool_intervals(events, gui)
    ticks = [e['t_ms'] for e in events if e['event'] == 'tick']
    if any(e.get('thread') != gui for e in events if e['event'] == 'tick'):
        raise InvalidTraceError('a tick is not delivered on the GUI thread')
    if any(b <= a for a, b in zip(ticks, ticks[1:], strict=False)):
        raise InvalidTraceError('two ticks share an instant or go back in time')
    if not ticks or ticks[0] > start or ticks[-1] < end:
        raise InvalidTraceError(
            'the ticks do not bracket the scenario from its begin to its complete'
        )
    over = []
    for a, b in zip(ticks, ticks[1:], strict=False):
        if b < start or a > end:
            continue
        shared = sum(max(0.0, min(b, t1) - max(a, t0)) for t0, t1 in tools)
        counted = (b - a) - shared - tick
        if counted > limit:
            text = (
                f'a gap of {counted:.0f} ms ending at {b:.0f} ({b - a:.0f} ms between ticks, '
                f'{shared:.0f} ms driver work)'
            )
            over.append((a, b, text))
    return over


def check(
    events: list[dict],
    scenario: str,
    steps: list[str] | None,
    limit: float,
    *,
    control: bool,
    tick_ms: float = 10.0,
    control_ms: float = 150.0,
) -> list[str]:
    """The gaps over the limit; raises InvalidTraceError for a trace that cannot be judged."""
    tick, gui = clock(events, tick_ms)
    span = interval(events, scenario)
    if steps is not None:
        shown = [
            e.get('name')
            for e in events
            if e['event'] == 'step' and span[0] <= e['t_ms'] <= span[1]
        ]
        if shown != steps:
            raise InvalidTraceError(
                f"the steps are not {scenario}'s listed steps in order: {shown}"
            )
    over = gaps_over(events, span, tick, limit, gui)
    if control:
        found = blocks(events, span, gui, control_ms)
        if not found:
            raise InvalidTraceError(
                f'the control run holds no GUI-thread block of {control_ms:g} ms inside the '
                "measured interval and outside the driver's work"
            )
        # The gap holds the whole block and ends with the timer's first delivery after it, inside
        # the measured interval: the recovery is measured too.
        if not any(a <= b0 and b1 <= b <= span[1] for b0, b1 in found for a, b, _ in over):
            raise InvalidTraceError(
                'no gap over the limit holds the control block and its recovery'
            )
    return [text for _, _, text in over]


def scenario_steps(contract: dict, scenario: str) -> list[str]:
    """A scenario's steps, as the contract lists them.

    A dynamic scenario (the every-tab one) takes them from the module the contract names, which
    reads them from the app's declared pages and tabs.
    """
    if scenario in contract.get('scenarios', {}):
        return contract['scenarios'][scenario]
    module = contract.get('dynamic_scenarios', {})[scenario]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    return importlib.import_module(module).scenario_steps(ROOT)[scenario]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    parser.add_argument('--trace', type=Path, required=True)
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--contract', type=Path, default=CONTRACT)
    parser.add_argument(
        '--limit',
        type=float,
        default=None,
        help='milliseconds a counted gap may reach (default: 100)',
    )
    parser.add_argument(
        '--control', action='store_true', help='check a control run with one injected GUI block'
    )
    parser.add_argument(
        '--report', action='store_true', help='print the gaps; fail only on an invalid trace'
    )
    options = parser.parse_args(argv)
    steps, limit, tick_ms, control_ms = None, 100.0, 10.0, 150.0
    if options.contract.is_file():
        contract = json.loads(options.contract.read_text(encoding='utf-8'))
        try:
            steps = scenario_steps(contract, options.scenario)
        except (KeyError, ImportError, ValueError) as error:
            print(
                f'gui_watchdog: {options.scenario} is not a scenario of {options.contract} '
                f'({error})',
                file=sys.stderr,
            )
            return 1
        limit = float(contract.get('limit_ms', limit))
        tick_ms = float(contract.get('tick_ms', tick_ms))
        control_ms = float(contract.get('control_ms', control_ms))
    if options.limit is not None:
        limit = options.limit
    try:
        over = check(
            load(options.trace),
            options.scenario,
            steps,
            limit,
            control=options.control,
            tick_ms=tick_ms,
            control_ms=control_ms,
        )
    except (InvalidTraceError, OSError) as error:
        print(f'gui_watchdog: {options.trace}: {error}', file=sys.stderr)
        return 1
    for line in over:
        print(f'gui_watchdog: {options.scenario}: {line}', file=sys.stderr)
    print(f'gui_watchdog: {options.scenario}: {len(over)} gap(s) over {limit:.0f} ms')
    if options.control:
        print(f'gui_watchdog: {options.scenario}: the control block was seen')
    if options.report:
        return 0
    return 1 if over else 0


if __name__ == '__main__':
    sys.exit(main())
