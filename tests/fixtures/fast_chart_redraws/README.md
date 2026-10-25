# Chart redraw acceptance

The placement oracle is the independent relative stack rule: a trace's height H is
P / (1 + (N - 1) * offset) in Fit mode, otherwise P * heightPercent / 100.
Baseline i is i * H * offset. The QML actor observes the Stacked layer's rowOf and peakOf in the
unzoomed zero-to-one axis coordinates, then captures the production chart
through xcb/OpenGL. Model scan-value rows are used only for Map. The visible
[placement contract](../../../docs/dev/design/scan-renderer-interface.md#stacked-placement-and-selectors)
names the units, defaults and exact-text selector activation.
The input generator writes independent triangular traces into private scan files.

The toolbar oracle uses control types and their actual mapped rectangles. It
requires a single centred line when the controls fit; otherwise combo-only lines
above button-only lines. It visits both chart pages through Main.

For the work-count acceptance, the scan layer exposes read-only diagnostic
`traceBuildCount` and `redrawCount` values. They count actual trace reductions and
actual rendered updates, respectively. The actor checks positive invalidation as
well as zero work on restyling, and compares a synchronous burst with frames
observed on the real window. These are observations, never rendering inputs.

The minimum comes from the production window's minimumWidth/minimumHeight,
not a second numeric constant. The undersize actor releases the native window's
minimum constraint to exercise the same content-area predicate used by wasm.
A browser run still needs to exercise the compiled wasm build separately.

Timing actors and final thresholds follow the committed baseline measurement.
No timing value has been invented or banked here. The pending comparisons are:
324 datasets, repeated pan/zoom and data-redraw medians (redraw under 100 ms);
162 datasets, Every pattern, display catches up / Adaptive fit ratio at most 1.05; LBCO slider-step
cost before and after fitting within the baseline's measured noise.

Redraw and fit comparisons require the observed graphics API and renderer in
`backend` (`api`, `renderer`). `backend_comparisons` requires a llvmpipe OpenGL
row as well as any hardware rows; every row keeps its own redraw and fit bound.
Software and hardware timings are never pooled. The arithmetic tests use
synthetic samples and make no performance claim. Live samples and their backend
identity still come from the measured app, with the same machine and project
for each comparison. GPU measurements need a GPU host.
The OpenGL renderer is empty on APIs such as Metal, which have no OpenGL context.

Each backend row keeps `fits.pattern` and `fits.stacked`, with separate
`display_catches_up_ms`, `fit_waits_for_display_ms` and `adaptive_ms` samples.
Only display catches up carries the 1.05 bound. The legacy Every-pattern
baseline remains a fit-waits regression pin; it is never relabelled as catch-up.
`python -m tests.fixtures.fast_chart_redraws.measure_fit DIR` now drives the
actual update-mode UI in a native app host, records the worker-completion time,
then lets the display finish. It alternates all three modes on both tabs with
repeated samples. Each receipt retains the selected UI text, tab, complete
scientific file count and independent Qt backend. `sample.json` and
`fit-comparisons.json` retain the raw samples and separate mode ratios.
The previous producer used the app's old Every/Adaptive demo routes.
The [scan update contract](../../../docs/dev/design/scan-update-interface.md)
describes the queue, visible progress, legacy migration and parameter range
observations. Timing replay remains a local diagnostic; final performance
proof still needs the packet's quiet-machine measurements.

Adaptive remains a separate choice in the real Analysis Settings selector.
The native actor selects it after Every pattern, fit waits for the display, and follows the saved 162-file
scan, checking live coalescing, the ADR-0029 half-second interval, completion of
all files and restoration of the final dataset.

Rendering detection is compared with `QSGRendererInterface::graphicsApi` and
`glGetString(GL_RENDERER)` read in Qt's rendering callback. The normal app must
report those values at startup without forced Qt debug logs. Preferences,
Develop must display them and identify software rendering as no GPU. Its scan
renderer selector offers GPU and software/painter choices, optionally automatic; the actor
finds those choices by their displayed text rather than a new public API.
Each explicit choice is written through real input, then read and exercised by
a second host process using the same private settings file.
The restart actor lives in the system tier and runs through that two-process
harness, with an actual display and private settings, rather than the unit
runner's offscreen all-files invocation.

The [scan renderer interface](../../../docs/dev/design/scan-renderer-interface.md)
defines requested and effective choices, the loaded-scan observations, restart
persistence and the difference between llvmpipe OpenGL and Qt Quick's Software
backend. The gate previously inferred the path from the wrapper's superclass;
it now observes the selected path and rendered contribution, allowing a painted
wrapper to host the GPU line child.
