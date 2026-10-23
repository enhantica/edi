# Web parallel acceptance vehicles

`contract.json` records the owner's unchanged native baseline and the task's
route and speed requirements. The native scientific captures come from edi's
unchanged native CLI, linked to the declared crysta SDK. Regenerate with:

```
OMP_NUM_THREADS=4 python -m tests.fixtures.web_parallel.generate \
  .pixi/envs/default/bin/python --edi --producer '<edi and linked SDK source shas>'
```

For a saved-result schema update, add `--conditioning-from <previous-captures>`.
That directory must contain both previous native captures and their conditioning
files. The generator checks all original parameters, patterns and fit scalars
under the original bounds before retaining the native matrix and its column
bindings. It then captures the complete result bank and phase loops and checks
that the retained uncertainty bindings remain total. A changed numerical subject
requires fresh independent conditioning evidence instead.

The browser corpus is LBCO HRPT start 4 and NCAF WISH five-bank start 5. Captures
include fitted parameters, fit scalars and every measured/calculated pattern
operand. Parameter values and pattern operands retain the native captures'
relative tolerance 1e-9 and absolute tolerance 1e-11. Fitted uncertainties use
the independent native covariance conditioning derivation in
[conditioning/README.md](conditioning/README.md), with the pre-existing
machine-report relative 5e-9 and absolute 5e-10 bounds as minima. The fit's
native final Jacobian, dimensions and covariance establish the new bound;
no observed browser gap is an input. Both components of a
saved `value(uncertainty)` token are compared numerically: decimal uncertainty
is absolute, while integer uncertainty uses the mantissa's last decimal units.
An empty uncertainty, zero uncertainty and an unbracketed fixed operand remain
distinct. Nonfinite or malformed operands refuse. The owner's rounded numbers
use half a hundredth.
Browser saves follow ADR-0092's default IUCr 19 rule. Their fitted values and
uncertainties are compared with an independent decimal rounding of the native
capture; the observed token cannot choose a coarser comparison precision. Fixed
values, parameters without a positive uncertainty and pattern operands keep
the original capture bounds. The native captures and conditioning stay unchanged.
The original input baseline is chi-square 649.33; the native capture converges
in five iterations to chi-square 9.497535494 and Rwp 0.07694458606.

Run the browser matrix against the delivered site on the pinned headless browser:

```
node --experimental-websocket tests/system/manual/web_parallel.mjs \
  <unpacked-site> <persistent-output> <pinned-chrome>
```

This executes both corpus cases on the singlethread, direct-isolation and
service-worker routes through the existing browser driver. Every route checks
its kit, isolation, SharedArrayBuffer, Develop diagnostics and native numerical
reference. It records the NCAF fit durations and requires the multithread kit to
be at least 1.4 times faster on the same browser executable and runner exposing
at least four cores. Only this speed gate uses a duration threshold.

The matrix also runs `tests/system/manual/web_parallel_routes.mjs` in WebKit
against the shipped site: initial load, reload, a second page in the same browser
context and its reload, for each of the three routes. Every load observes the
completed wasm request, isolation and SharedArrayBuffer. Controlled shim documents
must receive COEP `require-corp`; Chromium cannot stand in for this regression.
Rendered UI and fitted-result checks remain in the existing full browser matrix;
this WebKit addition checks routing across reloads and navigations.
Install the locked driver and its WebKit engine before running the matrix:

```
npm ci --prefix tests/fixtures/web_parallel
node tests/fixtures/web_parallel/node_modules/playwright-core/cli.js install webkit
```

`PLAYWRIGHT_BROWSERS_PATH` can place the pinned browser in the isolated toolchain
cache. `WEB_PARALLEL_PLAYWRIGHT` can name that locked package's `index.mjs` when
the toolchain installs it outside the fixture directory. A missing driver or
browser refuses the check; it is never a skipped route. The standalone route
check accepts the same module path as its third argument.

Gate 9's before/after web-to-desktop ratio and the measured native exceptions,
mimalloc, LTO and relaxed-SIMD trials belong in the packet's results with each
run's provenance. The approximate 1.5x target is reported, not asserted here;
gate 4 retains its authorized 1.4x multithread-to-singlethread floor. Native fit
captures and cross-platform numeric tolerances remain unchanged.

The diagnostics text contract adds `Engine backend`, `Engine workers`, and
`WebAssembly SIMD`, retaining the existing ideal-thread, OpenMP-team and browser
core labels. The isolated kits report a std::thread pool with multiple workers
and SIMD enabled; the singlethread kit reports serial, one worker and SIMD off.

The separate executed-body witness lives in crysta's visible
`tests/fixtures/web_parallel` builders and hidden browser driver. Build it from
the same core source as the app, with the same Emscripten thread and SIMD options,
and run that browser driver as well. Configuration counts cannot replace this
execution witness. The witness driver accepts the optional last argument
`serial-dispatch` or `backend-off` for the corresponding observer build. These
control runs must complete and record executed serial bodies with the failed
rendezvous; a startup failure does not count as refusal. The serial-dispatch
control also retains configured capacity four and advertised chunks sixteen. The native performance gate remains the existing crysta A/B
harness (`tools/bench/ab_perf.py`); no new pinned duration is introduced.

The browser does not navigate Qt popup dialogs through Chrome's accessibility
DOM: those popups have no usable AX subtree in the wasm app. The app must expose
`window.ediDevelopDiagnostics(action)`, accepting `open`, `read`, and `close`
(synchronous results or Promises). `open` opens the existing Preferences dialog,
selects its existing Develop tab, then opens its existing Diagnostics dialog;
`close` completes only after both dialogs have closed (resolve its Promise
after any close animation). `read` returns a fresh object with actual QML state:
`preferencesVisible`, `developSelected`, `diagnosticsVisible`, `textVisible`,
`text` (the displayed `diagnostics.text` TextArea's text), and `providerText`
(the current `ApplicationInfo.diagnostics()` result). Visibility includes the
TextArea's effective visibility. It must operate the existing QML controls on
Qt's main thread; it must not synthesize text or state from `ediBuildInfo`, a
requested kit, or expected test values. The inspector compares displayed text
to the provider and checks the actual dialog state before and after inspection.
The regular browser run then continues its unchanged real project/fit/download
checks and records the same-browser speed matrix. `--diagnostics-only` is a
focused diagnostic, never a substitute for that full run.

The reset/reopen witness uses the app toolbar's accessible names, replacing
the former assumption that all four buttons were unnamed. The four displayed
buttons must be named `Save current state of the project`, `Undo the last change`,
`Redo the last undone change`, and
`Reset to initial state without project, model and data`, in that order. Reset
is clicked by its exact accessible name and must still remove the real project
before the downloaded project is reopened and compared with the native capture.
The existing Save, Undo and Reset names stay. The app's currently unnamed Redo
button needs `ToolTip.text: qsTr("Redo the last undone change")` and
`Accessible.name: ToolTip.text`; its existing disabled behavior is sufficient.

The live progress witness checks the status bar while fitting: it requires
an actual `Stop fitting` control and an actual
`fitting · it N` label while the fit runs. This replaces the former
`Fit iterationsN` expectation; completed outcome text and minimizer settings
cannot satisfy it. The drawn `FitProgressBar` keeps its
`Accessible.role: Accessible.ProgressBar` and `Accessible.name: bar.text`.
The wasm accessibility layer need not mirror that role into the browser DOM;
the check reads live native progress through `window.ediFitProgress()` instead.
No test-generated label or completed-results substitute is admitted.

Install `window.ediFitProgress()` in both kits alongside the existing page
bridges. Every call returns (or resolves to) a fresh object with:

- `text`: the actual QML `statusBar.fit.progress` item's current `text` property.
- `visible`: that item's effective `QQuickItem::isVisible()` value, including its parents.
- `running`: the actual native fit's `running` state, as exposed by the existing
  `statusBar.fit` item's readonly `running` property; do not infer this from text.

Read these properties on Qt's main thread. Missing native objects or read errors
must throw/reject rather than return invented defaults. Do not synthesize the
text from requested iterations, a timer, a kit name or completed fit results.
The sampler begins before the real Start fitting action, polls the live hook on
animation frames while the fit runs and stops at the successful results popup.
At least one threaded-fit sample must have `running: true`, `visible: true` and
`text` matching `fitting · it N` with a positive iteration, alongside the actual
running control. Samples are retained with the before/after states; a completed
or hidden bar, or stale text with `running: false`, cannot satisfy the witness.

Both numerical cases and the pending-upload replacement control open through
their own catalogue row. The driver types the
bundled resource id into the actual `examples.search` field using trusted CDP
pointer and keyboard input (selecting the existing search text before replacing
it), then clicks the named `examples.open.<id>` delegate.
Qt's clipped/recycled AX proxies can retain a label whose rectangle belongs to
a different row; the visible accessible name remains a witness, while fresh
native geometry locates the real click. The whole row must fit inside the actual
`examples.list` rectangle and the fixed browser viewport. No Session action or
direct-open fallback substitutes for this row input. Editor focus can scroll
Qt's accessibility host, so the prior Create-project viewport restoration now
runs before pointer actions: it resets real ancestor scroll positions and
requires the actual canvas at (0, 0), 1280 by 768. Main workflow tabs also use
fresh geometry from their `appBar.tab.<page>` controls; the unchanged selected-tab
witness must observe the requested navigation.

Saved native metadata independently binds the result to `lbco_hrpt_s4` or
`ncaf_wish_5bank_s5` before numerical comparison. A different or missing project
name refuses even if the label, geometry or fit number looks right. The native
LBCO oracle and both cases' tolerances remain unchanged; a numerical failure
prints the browser value, native value and tolerance. Real Analysis controls,
fit, project save, Reset and reopen remain required for both cases.

The native file controls also need `window.ediControlGeometry(objectName)` in
both kits, installed alongside the existing main-thread page bridges. Qt can
retain an old AX rectangle after the empty-table layout changes: the observed
Structure Load proxy still placed its center at y=187.5 while the actual drawn
button was at y=280 in the fixed 1280x768 viewport. This reader replaces the
stale proxy rectangle; the subsequent action remains trusted CDP pointer input
on the actual button, followed by its real browser chooser and native results.

Every call returns or resolves to a fresh object with `objectName`, `x`, `y`,
`width`, `height`, `visible` and `enabled`. Find exactly one effectively visible
`QQuickItem` with the requested actual `objectName` in the live QML engine roots;
read its actual name, `mapRectToScene(boundingRect())`, effective
`QQuickItem::isVisible()` and `isEnabled()` on Qt's main thread. Coordinates are
in the real Qt scene displayed at the driver's fixed viewport. Unknown,
duplicate, hidden or missing objects and read errors throw/reject. Do not
hardcode positions, read AX rectangles, force visibility, expand groups or
activate the control inside this hook.

Required names from the shipped QML are `structures.load`, `experiments.load`,
`experiments.create`, `experiments.loadData.0`, `examples.search`,
`examples.list` and each chosen `examples.open.<id>` delegate. The driver refuses wrong
names, hidden/disabled controls, nonfinite/nonpositive geometry and rectangles
outside the viewport. It still proves that `Page.fileChooserOpened.backendNodeId`
resolves to the actual `HTMLInputElement` captured from that request; single-file,
batch, cancel, superseded-request and native project-result claims are retained.

The results-popup pixel witness checks the opaque dialog margins on both sides
and at both vertical sample levels, over the otherwise white plot and sidebar.
The former central sample entered a highlighted results-table row in the
five-bank dialog and falsely rejected the actually drawn popup. The margin
background retains gui-components' declared light-theme color and tolerance;
actual Success, real popup drawing, completed fit and saved native parity are
still required, and the same witness must observe closure after Escape.

**Excluded rows rewritten ([ADR-0044](../../../docs/dev/adrs/0044-pattern-charts-and-excluded-regions.md)).** The NCAF
capture's excluded rows had `.` for the d-spacing; they now have the real d. The fitted calibration is not in the
capture, so it was solved from each bank's included rows (time of flight is linear in the three constants), which it
reproduces to 1e-11 relative, and each excluded d is the physical root, written as the shortest round trip.
`scientific_sha256` in `ncaf-conditioning.json` was updated to match.

The frozen native tokens contained NumPy scalar repr wrappers in saved phase
weight fractions. `python -m tests.fixtures.web_parallel.normalize_native_tokens`
removes only `np.float64(...)`, retaining every decimal digit. The per-token
receipt reverses to the complete original scientific hash. Conditioning matrices,
parameter bindings and numerical tolerances retain their captured values.
