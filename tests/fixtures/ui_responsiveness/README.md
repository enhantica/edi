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
A reentrant application operation or timer delivery inside them invalidates
the exclusion. The control's violating timer interval must contain the actual
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
Every request/build/completion/delivery/discard/supersede/swap carries `builder`,
`view`, `generation` and its actual clock. `build` and `built` bracket execution
and record its native thread regardless of any `scales` label. Exercise both
old and replacement requests for every builder: the old result completes after
the new result, is discarded, and cannot deliver or swap. A current result
completes, delivers and swaps on its matching real render clock. Every
incremental `model-change` records `changed_range`, sampled from the actual
changed rows, for comparison to the emitted bounds; last-row edits are valid.

Both first and settled geometry observations bind the request and actual
render clock. A `presented` event records the requested `dataset` and uploaded
`generation`; the settled `render` itself records those values. Its geometry
cannot predate that presentation. Each frame includes a `visible` map with
effective visibility for all six geometry entries. Positive rectangles from
invisible panes and copied geometry from an unrendered frame are insufficient.
