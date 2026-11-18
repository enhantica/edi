# UI responsiveness inputs and observations

The scan files are small, unchanged members of the owner's external `44k.zip`.
`scan-source.json` records the archive identity and each extracted member's SHA256.
The archive and generated scans stay outside git. `generate.py <empty-directory>`
stages the same two structures, linked powder experiment, report settings and
analysis settings with 4000 patterns on the original grid. Noise is seeded; it
does not claim scientific correctness. The original template is unchanged.

The other independent inputs are the committed CLI NCAF five-bank start-5
project and `tests.fixtures.joint_series.ncaf.prepare(..., points=100,
descent='fast_descent')` with all five banks. No fitted output is a timing oracle.
The nightly page scenario uses `run.py --archive <44k.zip>` in place of
`--scan`. It verifies and extracts the whole archive and never substitutes the
reduced input. Run `tests/system/slow/ui_responsiveness.py` explicitly against
that separate evidence directory in the nightly app job. Asset publication is an operator dependency.

## Producer interface

`python -m tests.fixtures.ui_responsiveness.run --app <current-app> --output <empty-directory> --scan <project>
--series <100-point-project>` runs each scenario and its blocking control. It
does not compile an app. Run this preparation in the app CI job, including PRs,
then run `tests/system/app/test_ui_responsiveness.py` with
`EDI_UI_EVIDENCE=<output>`. The watchdog checker is
`python tools/ci/gui_watchdog.py --trace <trace.jsonl> --scenario <name>`; success
is status 0, any invalid/incomplete/over-budget trace is nonzero. `--control`
requires a real injected block and still fails on its observed over-budget gap.
The checker may initially be report-only in the separate baseline CI step.

The driver runs `--demo-only <name>` for names in `contract.json`. It opens the
supplied `EDI_DEMO_SCAN_PROJECT` for pages, Pattern navigation and series cases;
banks opens NCAF start-5. `EDI_UI_TRACE=1` enables one JSON object per
`ui-probe: ` log line. The control additionally sets `EDI_UI_BLOCK_MS=150`:
queue a real GUI-thread block while that scenario is being measured, outside
driver measurement markers. This seam is absent in normal runs. The producer
uses separate fresh app processes and settings stores for all runs.

## Trace conventions

All timestamps are `t_ms` on one monotonic millisecond clock, recorded at the
event rather than inferred from log arrival. Required events are:

* `clock`: `clock="monotonic"`, `unit="ms"`, `tick_ms=10`, `gui_thread`.
* `begin`: `scenario`; `tick`: every real GUI timer delivery, not just stalls;
  `step`: `name` from the ordered contract list; `complete`: `scenario`.
  Tick endpoints bracket the complete measured interval, including its end.
* `tool-begin` / `tool-end`: matched nonoverlapping `id` around only the driver's
  own image grab/compare work. Subtract their intersection with each tick
  interval, then subtract the nominal 10 ms. A partially overlapping interval
  retains all app time outside the marker. Strictly more than 100 ms fails.
* `block-begin` / `block-end`: actual control execution, `thread=gui_thread`.
  The measured interval must include the whole block and the timer's recovery.

The series scenario also records these passive work observations. Counters
increment at completed builders/uploads, not at invalidations or a driver's
request to refresh. Use stable per-instance `view` identities and the inventory
`kind` in contract.json. Multiple instances of a kind remain distinct.

* `census`: `views` list of `{view, kind}` for every initialized data view,
  including retained hidden pages/tabs and tables. Visit them before fitting.
* `hidden-before` / `hidden-after`: `views` list containing `view`, `kind`,
  `shown`, `refreshes`, `uploads`, `generation`. Both snapshots surround at
  least three actual `data-change` events while Analysis Pattern is shown.
* `shown-before` / `shown-after`: same fields for one formerly hidden view;
  `wanted_generation` is the newest invalidation at show. Exactly one completed
  refresh and upload must consume it. Include every hidden instance, including
  an initialized hidden view and a previously lazy view. Emit `lazy-created`
  for the latter. The visible Analysis Pattern must refresh during fitting.
* `build`: `view`, `thread`, `scales` (true for data-sized builders);
  `request` / `deliver`: `view`, `generation`; a `supersede` event records the
  old generation and its newer `replacement`. Exercise an out-of-order result.
* `swap`: `view`, `frame`, `generation`, `thread`. `frame` is the real rendered
  frame sequence, not a timer tick; at most one swap per view in a frame.
* `model-change`: `view`, `operation`, `first`, `last`, `rows`, `incremental`.
  An incremental edit exercises a strict subrange, with no model reset.

For `e58-pattern`, every navigation `step` also has `request`, `direction` and
`dataset` from the actual selected model. Its first and settled frames emit
`frame`: `request`, `frame`, `phase` (`first` or `settled`), `event="frame"`,
`witness="afterSynchronizing/frameSwapped"`, `panes`, `axes`, `geometry`.
The observer connects before navigation and records the first swap after it,
without a ready predicate. The linked measured powder fixture requires panes
`pattern`, `bragg`, `residual` and axes `x`, `intensity`, `residual`.
`geometry` maps `pattern`, `bragg`, `residual`, `x`, `intensity`, `residual-axis` to a positive `[x,y,width,height]`
rectangle sampled at synchronization and associated with that actual swap.
Emit `render` for every swap so the first-frame claim is independently checked.
The first frame must have the complete layout and equal the settled geometry.
The dataset observation must change in each navigation direction.

These names are the producer/checker interface; the hidden assertions and
negative controls stay in the hidden tiers. The producer must observe real
callbacks; a precomputed successful trace is not a substitute.

## Causal witness requirements

The callbacks are passive observations at native operations, not driver-issued
success labels. The driver installs observers before input. Each `step` carries
its issued `request`; a separate `action` records the issuance clock, name and
`before_selection`. A `state` with that request samples the actual active page,
tab, selected bank/dataset (`selection`), and loaded `input` identity. Series
states also sample `fitting` and `completed`. Ordinary and control runs must use
the same content identity. Pattern input issuance follows the 100 ms schedule,
allowing at most one nominal timer tick of jitter; completion labels cannot
start the first-frame clock. The producer does not set `EDI_DEMO_DELAY_MS`,
which belongs to the existing blocking helper rather than the action timer.

Exclusion spans match `measurement-enter` and `measurement-leave` from the
actual `QQuickWindow::grabWindow` or `compare-images` callback. Both carry the
same `id`, `callback`, GUI `thread` and exact endpoint timestamps as the markers.
A GUI-thread application event of any kind, including future event types,
or a GUI timer delivery inside them invalidates the exclusion. Concurrent
worker events are permitted. Events carry their native thread identity; an
event without one is conservatively treated as GUI work. The control's violating timer interval must contain the actual
GUI block and its recovery; an unrelated later stall does not qualify.

A separate `hierarchy` walks initialized native/QML view objects and includes
`active_page`, `active_tab`, and `objects` with `view`, normalized metaobject
`type`, `initialized`, enclosing `page`, `tab`, and `ancestors_shown`. Normalize
the QML generated type suffix through its metaobject ancestry. The known view
types are the values in `contract.json`; do not select objects by counter
registration. Reconcile this enumeration with registered counters and both
snapshots. Every claimed kind needs a hidden instance; Analysis Pattern and its
sidebar may be shown. Creation of previously lazy instances precedes the hide
snapshot; retained instances are included too. Every hidden instance receives
an `invalidate` for each real `data-change`, carrying the generation and
`after_hash` of the actual changed model content. Changes record `before_hash`
and `after_hash`, forming a continuous, nonidentical content history. Counter
values at show equal their final hidden values; timestamps order hide, changes,
show and catch-up. The positive catch-up consumes the newest invalidation.

`contract.json` names the data-sized `builders` from the approved inventory.
Request/build/completion/delivery/discard/supersede/cancel/result-arrival events
carry `builder`, target `view`, `generation` and actual clock. Each supersession
binds real old and replacement requests at the replacement issuance time.
A queued superseded request may `cancel` without running (ADR-0096). A running
one may complete and discard serially before its replacement starts (ADR-0020),
or arrive late; its raw worker callback is `result-arrival`, distinct from a
`deliver` accepted by the view. Stale output must never reach a view snapshot.

The controlled rejection seam defers at least one stale owner arrival until
after replacement computation, then observes rejection; it does not require
reversed completion on every production worker. Native execution may remain
serial and owner deliveries ordered. A `swap` may combine multiple builder
outputs in a `sources` list of `{view,builder,generation}`. Every current output
contributes exactly once to a final snapshot, with no stale source and at most
one swap per view per frame. Every incremental model range matches the actual
`changed_range`; whole-model changes and one-row models are valid. A separate
partial edit supplies the strict-subrange witness.

Both first and settled geometry observations bind the request and actual
render clock. A `presented` event records the requested `dataset` and uploaded
`generation`; the settled `render` itself records those values. Its geometry
cannot predate that presentation. Each frame includes a `visible` map with
effective visibility for all six geometry entries. Positive rectangles from
invisible panes and copied geometry from an unrendered frame are insufficient.

The measured `begin` precedes every action issuance and `complete` follows all
requested state transitions and renders, including control recovery. Step
completion labels alone cannot establish the measured window. For Pattern,
`state.selection` equals the step dataset and its input equals the loaded input.
State, publication and settled render also carry the same `data_identity`, the
content identity sampled independently from the selected native pattern and
from the rendered pattern buffers, plus the same project `input` identity.
This rejects a self-consistent rendered index stream for a different selection
or different pattern contents.
