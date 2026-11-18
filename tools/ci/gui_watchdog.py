# SPDX-License-Identifier: BSD-3-Clause
"""Check a scenario's GUI-thread gaps in a UI trace (ADR-0096).

  gui_watchdog.py --trace <trace.jsonl> --scenario <name>
                  [--contract <contract.json>] [--control] [--report]

The trace is the app's `ui-probe:` events (app/src/ui_probe.hpp), one JSON object per line,
all on one monotonic millisecond clock: `clock` (tick_ms), `begin` and `complete` around the
scenario, a `tick` at every delivery of the GUI thread's 10 ms timer, `step` per measured step,
`measurement-enter`/`measurement-leave` (matched by `id` and `callback`, on the GUI thread)
around the demo driver's own window grabs and image comparisons, and in a control run
`block-begin`/`block-end` around the injected block. Every event names its `thread`.

Each interval between two ticks that meets the scenario's interval counts as its length, less
the time it shares with the driver's work, less the nominal tick; more than the limit (100 ms)
fails. A measurement span is the driver's work only while the GUI thread did nothing else: any
other event on the GUI thread inside it (a tick included; an event naming no thread counts as
the GUI thread's) leaves it counted. The ticks must bracket the scenario's whole interval. With
a contract (tests/fixtures/ui_responsiveness/contract.json by default, when present) the steps
must be the scenario's listed steps, in order. --control checks a control run: it must hold one
block on the GUI thread inside the measured interval, a gap over the limit must contain that
whole block, and the check then fails on it as on any other.

Exit status: 0 within the limit, 1 a gap over it or a trace that is invalid or incomplete
(only the driver's `QQuickWindow::grabWindow` and `compare-images` callbacks are its own work).
A valid control prints that its block was seen. --report prints and exits 0 whatever it finds,
for a baseline. Every refusal names its cause.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / 'tests/fixtures/ui_responsiveness/contract.json'
CALLBACKS = {'QQuickWindow::grabWindow', 'compare-images'}


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
            or not isinstance(event.get('t_ms'), (int, float))
        ):
            raise InvalidTraceError(f'{path}:{number}: an event needs an event name and t_ms')
        events.append(event)
    return events


def clock(events: list[dict]) -> tuple[float, object]:
    """The nominal tick and the GUI thread's name, from the one clock event."""
    clocks = [e for e in events if e['event'] == 'clock']
    if len(clocks) != 1 or clocks[0].get('clock') != 'monotonic' or clocks[0].get('unit') != 'ms':
        raise InvalidTraceError('the trace needs exactly one monotonic millisecond clock event')
    tick = float(clocks[0].get('tick_ms', 0))
    if tick <= 0:
        raise InvalidTraceError('the clock event names no tick interval')
    return tick, clocks[0].get('gui_thread')


def interval(events: list[dict], scenario: str) -> tuple[float, float]:
    """The scenario's measured interval, from its begin to its complete."""
    if any(b['t_ms'] < a['t_ms'] for a, b in zip(events, events[1:], strict=False)):
        raise InvalidTraceError('the events are not in time order')
    begins = [e for e in events if e['event'] == 'begin' and e.get('scenario') == scenario]
    ends = [e for e in events if e['event'] == 'complete' and e.get('scenario') == scenario]
    if len(begins) != 1 or len(ends) != 1:
        raise InvalidTraceError(f'the trace needs one begin and one complete of {scenario}')
    start, end = begins[0]['t_ms'], ends[0]['t_ms']
    if end < start:
        raise InvalidTraceError('the scenario completes before it begins')
    return start, end


def tool_intervals(events: list[dict], gui: object) -> list[tuple[float, float]]:
    """The driver's own work: matched measurement spans with no other GUI-thread event inside."""
    spans, open_spans = [], {}
    for event in events:
        kind = event['event']
        if kind == 'measurement-enter':
            if open_spans:
                raise InvalidTraceError("the driver's measurement spans overlap")
            if event.get('thread') != gui:
                raise InvalidTraceError('a measurement span is not on the GUI thread')
            if event.get('callback') not in CALLBACKS:
                raise InvalidTraceError(
                    f'a measurement span names no driver callback ({event.get("callback")})'
                )
            open_spans[event.get('id'), event.get('callback')] = event['t_ms']
        elif kind == 'measurement-leave':
            key = (event.get('id'), event.get('callback'))
            if key not in open_spans or event.get('thread') != gui:
                raise InvalidTraceError(
                    f'a measurement-leave without its enter (id {event.get("id")})'
                )
            spans.append((open_spans.pop(key), event['t_ms']))
    if open_spans:
        raise InvalidTraceError('a measurement-enter without its leave')
    excluded = []
    for t0, t1 in spans:
        busy = any(
            t0 < e['t_ms'] < t1
            and e['event'] not in {'measurement-enter', 'measurement-leave'}
            and e.get('thread', gui) == gui
            for e in events
        )
        if not busy:
            excluded.append((t0, t1))
    return excluded


def blocks(
    events: list[dict], span: tuple[float, float], gui: object
) -> list[tuple[float, float]]:
    """The control blocks run on the GUI thread inside the measured interval."""
    start, end = span
    found = []
    for a, b in zip(events, events[1:], strict=False):
        if a['event'] == 'block-begin' and b['event'] == 'block-end':
            inside = start <= a['t_ms'] and b['t_ms'] <= end
            if inside and a.get('thread') == gui and b.get('thread') == gui:
                found.append((a['t_ms'], b['t_ms']))
    return found


def gaps_over(
    events: list[dict], span: tuple[float, float], tick: float, limit: float, gui: object
) -> list[tuple[float, float, str]]:
    """The tick intervals whose counted gap is over the limit: start, end and a description."""
    start, end = span
    tools = tool_intervals(events, gui)
    ticks = [e['t_ms'] for e in events if e['event'] == 'tick']
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
    events: list[dict], scenario: str, steps: list[str] | None, limit: float, *, control: bool
) -> list[str]:
    """The gaps over the limit; raises InvalidTraceError for a trace that cannot be judged."""
    tick, gui = clock(events)
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
        found = blocks(events, span, gui)
        if not found:
            raise InvalidTraceError(
                'the control run holds no block on the GUI thread inside the measured interval'
            )
        if not any(a <= b0 and b1 <= b for b0, b1 in found for a, b, _ in over):
            raise InvalidTraceError('no gap over the limit contains the control block')
    return [text for _, _, text in over]


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
    parser.add_argument('--report', action='store_true', help='print only; exit 0')
    options = parser.parse_args(argv)
    invalid = 0 if options.report else 1
    steps, limit = None, 100.0
    if options.contract.is_file():
        contract = json.loads(options.contract.read_text(encoding='utf-8'))
        if options.scenario not in contract.get('scenarios', {}):
            print(
                f'gui_watchdog: {options.scenario} is not a scenario of {options.contract}',
                file=sys.stderr,
            )
            return invalid
        steps = contract['scenarios'][options.scenario]
        limit = float(contract.get('limit_ms', limit))
    if options.limit is not None:
        limit = options.limit
    try:
        over = check(load(options.trace), options.scenario, steps, limit, control=options.control)
    except (InvalidTraceError, OSError) as error:
        print(f'gui_watchdog: {options.trace}: {error}', file=sys.stderr)
        return invalid
    for line in over:
        print(f'gui_watchdog: {options.scenario}: {line}', file=sys.stderr)
    print(f'gui_watchdog: {options.scenario}: {len(over)} gap(s) over {limit:.0f} ms')
    if options.report:
        return 0
    return 1 if over else 0


if __name__ == '__main__':
    sys.exit(main())
