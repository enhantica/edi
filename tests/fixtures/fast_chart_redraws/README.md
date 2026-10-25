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

Adaptive remains a separate choice in the real Analysis Settings selector.
The native actor selects it after Every pattern and follows the saved 162-file
scan, checking live coalescing, the ADR-0029 half-second interval, completion of
all files and restoration of the final dataset.
