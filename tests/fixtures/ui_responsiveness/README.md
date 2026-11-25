# UI responsiveness inputs and observations

The scan files come from the owner's external `44k.zip`. Personal paths and
names are removed from the reduced fixture's headers; its scientific data and
project records are preserved. `scan-source.json` records the archive identity
and each published member's SHA256.
The archive and generated scans stay outside git. `generate.py <empty-directory>`
stages the same two structures, linked powder experiment, report settings and
analysis settings with 4000 patterns on the original grid. Noise is seeded; it
does not claim scientific correctness. The template retains the original data.

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
does not compile an app. The Linux app CI job prepares traces for
`tests/system/app/test_ui_responsiveness.py` on runs that execute the app
group, with `EDI_UI_EVIDENCE=<output>`. `app-watchdog --prepare-only`
supplies the functional checks. Scheduled CI runs `app-watchdog` to report
the ordinary gaps with `gui_watchdog.py --report`. `--control` still proves
that the injected block itself produces a gap over the limit. Deterministic
checker controls also exercise strict mode.

The driver runs `--demo-only <name>` for the expanded scenario map. It opens the
supplied `EDI_DEMO_SCAN_PROJECT` for pages, Pattern navigation and series cases;
banks opens NCAF start-5. `EDI_UI_TRACE=1` enables one JSON object per
`ui-probe: ` log line. The control additionally sets `EDI_UI_BLOCK_MS=150`:
queue a real GUI-thread block while that scenario is being measured, outside
driver measurement markers. This seam is absent in normal runs. The producer
uses separate fresh app processes and settings stores for all runs.

## Every page and tab

The additional `e58-tabs` scenario uses the same dataset files as `e58-pages`,
reduced for ordinary app contract preparation and complete when the nightly archive is supplied. The runner stages a private project
with the saved template fit in `tab-fit/` and points it to the existing scan
directory. Both the normal and blocking runs open this project. The archive,
source project and pattern files keep their original bytes. The ordered actions
come from `tab_inventory.scenario_steps()`, not a frozen list in `contract.json`.
`python -m tests.fixtures.ui_responsiveness.tab_inventory` prints the complete
page/tab inventory and expanded scenario map for the CI checker and driver.
The inventory reads `Main.qml`'s mounted pages, each page's `mainTabs` or
`MainView.tabKeys`, the shared main-view tab buttons and WorkflowPage's sidebar
tab buttons. Unrecognized or ambiguous declarations refuse preparation. A new
declaration therefore enters coverage or fails loudly; unavailable/disabled
tabs cannot be silently omitted. The saved template result enables Analysis
Correlations and gives Evolution fitted points without running a fit during
the watchdog. Generate the reduced records with the CLI on the first two
patterns:

```sh
python tests/fixtures/ui_responsiveness/generate.py <empty-directory> --count 2
easydiffraction fit <empty-directory>/44k_project
```

Keep the fitted model and `analysis.edi` together in `tab-fit/project/`,
with the CLI's results table in `tab-fit/reduced.csv`. Generate `full.csv` by
running the same fit with the archive's first two patterns. The template's
measured samples are identical in both inputs. The second pattern differs, so
the fixture selects the matching results table by its SHA256 in
`second-pattern.json`. The fit coefficients exercise the real fitted view
and carry no numerical acceptance threshold.

The producer passes this input as JSON in `EDI_UI_TAB_INVENTORY` and records it
in `manifest.tab_inventory`. It is an action plan, never a success witness.
After initializing the pages, emit one `tab-inventory` event with
`witness="qml-tab-bars"`, `thread=clock.gui_thread` and `pages` sampled from
the native tab bars in the same shape as the declaration inventory. Include
all configured buttons, not only currently enabled ones. Home currently has
empty main/sidebar arrays and still requires its page visit.

For each page emit `page-<page>`, then `tab-main-<page>-<key>` for every main
button and `tab-sidebar-<page>-<key>` for every sidebar button, in declaration
order. These are `action`/`state`/`step` operations with the existing native
transition-publication and real rendered completion witnesses. Actual selected
state names `page`, main `tab`, `sidebar_tab` and `selected_object` (the selected
button's declared objectName; empty for a page visit). A tabless area's selection
is empty or null. Both `action` and `state` identify the GUI thread. Each render's
native `displayed` snapshot includes `page`, `tab`, `sidebar_tab` and `input`; incompatible
main/sidebar selections cannot share a completion frame. Every action and its
render stay inside the measured interval on the same loaded scan identity.

The monotonic clock, ten-millisecond timer, maximum counted gap of 100 ms,
measurement-callback exclusions and real 150 ms GUI-block control are exactly
the existing rules. Every run and control must cover the complete inventory.

### Content completion

Canonical mounted-page identities must be unique after suffix removal and case
normalization, before building the page dictionary. Normalized tab identities
and the flattened action identities must also be unique. Distinct mounts must
never overwrite one another.

`content_contract.content_expectations()` classifies the scan scenario's selected
content independently of driver output. Main charts and the project/report views
must contain data; Correlations and Evolution require fitted results, Pattern
and Meas vs calc require calculated data. Before measuring, with native observers
already installed, prepare actual calculated/fitted results for the selected
experiment and scan results, preserving the loaded scan's scale.
These are real app calculations, not injected readiness booleans or fabricated
result records. A full scan fit is not required as preparation. Sidebar Text
requires the selected block's text; other declared sidebar components require
their populated controls. An absent sidebar component instead requires its
actual invitation note. A new content type requires an explicit independent
classification and otherwise refuses preparation. Home has static content.

The producer passes this contract in `EDI_UI_TAB_CONTENT_EXPECTATIONS` and stores
it in `manifest.tab_content_expectations`. It supplies input expectations only.
Native observations must establish the following additional joins:

* Each selected `state.content_sources[area]` records the actual native model's
  `input`, data/snapshot identity `data`, wanted `generation`, and native operation
  `stage` (`model`, `calculated` or `fitted`). These are sampled from the selected
  model, never copied from the expectation contract. Areas are `main`, `sidebar`,
  or `page` for tabless Home.
  Separately, `state.model_bindings` samples authoritative session/project
  selection, not a view's cached model: project, selected structure, selected
  block/page model, current dataset's calculated/fitted result, full scan and
  fitted scan-result identities/revisions. The contract's `binding` names the
  required role. Its `data` and source-model `generation` must equal that role's
  selected native identity/revision. Builder/job generations need not equal
  source-model revisions; no worker execution model is prescribed.
* `content-selected` carries `request`, `area`, `key`, native content-item `root`,
  its shown-chain `visit`, canonical native `kind`, selected `tab_object`, the
  actual model `source`, `tab_enabled`, `tab_visible`, `thread` and
  `witness="native-selected-content"`. Lazy content is resolved to the actual
  selected loader item, not its tab button or an uninstantiated component.
  Empty notes also identify their native `object`.
* Native shown-chain callbacks emit `content-shown` / `content-hidden` with
  `root`, `visit`, `thread` and their actual timestamps. A retained item can be
  revisited with a new visit identity. Compatible selections can share a visit;
  leaving an area closes it. The selected content must render before departure.
* `content-publication` records one GUI-accepted immutable content model with
  `id`, `root`, `source`, `kind`, `mode`, `unit`, `count`, `digest`, `reason`, and
  `thread`. `digest` hashes that actual accepted payload, not request metadata.
  For Stacked/Map it also records the accepted snapshot's `loaded`, `covered`
  dataset count and `failed` count. Cached accepted publications may predate the
  measured action. Work may finish asynchronously; there is no new worker-model
  or global-frame restriction.
* Every real `render.contents` lists its actual selected content consumers. Each
  carries `root`, `visit`, `publication`, `source`, `kind`, `mode`, `unit`, actual
  consumed `count` and payload `digest`, `reason`, `visible`, positive `geometry`,
  `visual_count`, and `witness="native-render-consumer"`. These fields come from
  the rendered item/applied buffer or text/model binding at synchronization;
  copying the latest publication into a frame without observing its consumer is
  invalid. Aggregate `loading` and `pending` cover all work/descendant lazy
  loaders of that selected subtree and must be zero. Stacked/Map also report
  actual applied `loaded`/`covered`/`failed`: the complete supplied dataset set
  must be covered, including when the representation is downsampled.

The request's `transition-publication.content_publications` includes all accepted
models needed by that visit. Its completion frame consumes those exact native
models with the selected source identity/generation. A page visit covers both
shown areas; an individual tab visit covers its area. Data content is nonempty;
an independently empty sidebar instead has count zero, `mode="empty"`,
`reason="no-groups"`, and its rendered `sideBar.note.invite` item. Empty content
still needs a real visible render. Cached and synchronous models are valid, as
are asynchronously accepted models, provided their consuming render occurs
inside measurement and before any incompatible selection or native departure.

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
  retains all app time outside the marker. Nightly reports intervals strictly
  over 100 ms. The explicit strict check still rejects them.
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
the same content identity. Deterministic Pattern controls verify the 100 ms
schedule and one nominal tick of jitter. Live Pattern evidence preserves the
actual input times and order through stalls. Completion labels cannot start
the first-frame clock. The producer does not set `EDI_DEMO_DELAY_MS`,
which belongs to the existing blocking helper rather than the action timer.

Exclusion spans match `measurement-enter` and `measurement-leave` from the
actual `QQuickWindow::grabWindow`, `compare-images` or `DemoDriver::find` callback.
The lookup span covers only locating the driver's control; click delivery stays
measured. Application work inside any span is refused. The marker and witness carry the
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
A queued superseded request may `cancel` without running (ADR-0100). A running
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

## Required completion and native owner

`clock.gui_thread` is a nonempty native thread identifier (a nonblank string or
positive integer). Every ownership comparison first validates it. Missing/null,
empty or whitespace identifiers do not establish ownership, even if the swap
or measurement callbacks carry the same empty value. Swap and final-delivery
records must identify this actual GUI owner; the worker execution rules above
are unchanged.

Every action's native `state` carries a nonempty `transition` identity. A
mandatory `transition-publication` event with that identity records the actual
accepted GUI publication, its `input`, `frame` and timestamp. The real `render`
for that frame includes the transition in its `transitions` list. Measurement
contains issuance, state, publication and that actual render. This witness is
required for pages and banks as well as Pattern and series; a late untagged
render cannot substitute for measured completion. Unrelated setup and
background frames need not lie inside the scenario window.

Series states/publications also identify the native `run`. `fit-finished`
records that run's actual final `work` identities (view, builder, generation),
including results-index and Pattern presentation. The final end-settled
publication must consume exactly that work list. Resolve each identity to its
actual run's request, completion, GUI delivery and consuming snapshot swap;
that swap binds its own real rendered frame; different views may finish in
different frames, all no later than the final completion render. All of these remain
inside measurement, including the final burst after the fit reports finished.
Shared snapshots still consume several stage outputs in one swap. The work
list is captured from the actual end-transition publication dependencies,
not generated by the driver from its expected scenario labels.

For page and bank completion, each render carries one `displayed` snapshot
sampled from the actual native state at scene synchronization, independently
of transition registration. It includes the loaded `input`, current `page` and current `tab` (null when
that page has no tab); bank cases also include `selection`. Every completion must match its
requested target against that snapshot. Several compatible states may share a
frame or token; incompatible page/bank states cannot alias one terminal frame.
The observation is not a list of the driver's expected targets.

For series completion, each work identity resolves its own consuming swap and
that swap's actual render, without equality to another view's frame. One view
may finish before a second view delivers. The final completion render follows
all required rendered results, inside measurement. A shared snapshot is still
valid. This does not introduce a global publication or frame barrier between
the independent view coalescers (ADR-0100 decision 4).
