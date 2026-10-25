# Chart redraw acceptance

The placement oracle is ADR-0041's relative stack rule: a trace's height H is
P / (1 + (N - 1) * offset) in Fit mode, otherwise P * heightPercent / 100.
Baseline i is i * H * offset. The QML actor observes rowOf, peakOf and the
actual plot range, then captures the production chart through xcb/OpenGL.
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
162 datasets, Every pattern / Adaptive fit ratio at most 1.05; LBCO slider-step
cost before and after fitting within the baseline's measured noise.

Redraw and fit comparisons require the observed graphics API and renderer in
`backend` (`api`, `renderer`). `backend_comparisons` requires a llvmpipe OpenGL
row as well as any hardware rows; every row keeps its own redraw and fit bound.
Software and hardware timings are never pooled. The arithmetic tests use
synthetic samples and make no performance claim. Live samples and their backend
identity still come from the measured app, with the same machine and project
for each comparison. GPU measurements need a GPU host.
The OpenGL renderer is empty on APIs such as Metal, which have no OpenGL context.

Each backend row now keeps `fits.pattern` and `fits.stacked`, each containing
`every_pattern_ms` and `adaptive_ms`. Both tabs are mandatory and each ratio is
checked separately. `python -m tests.fixtures.fast_chart_redraws.measure_fit DIR`
runs the real app's `perf-fit-every-pattern`, `perf-fit-adaptive-pattern`,
`perf-fit-every-stacked` and `perf-fit-adaptive-stacked` routes in alternating
order, with repeated samples. Each capture must report the same Qt backend
and renderer observed independently by the native actor. The system timing
gate runs this producer; its local runs are diagnostics, and final performance
evidence still needs the quiet-machine runs the packet specifies.

Adaptive remains a separate choice in the real Analysis Settings selector.
The native actor selects it after Every pattern and follows the saved 162-file
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
