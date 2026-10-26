# Drawing while a sequential fit runs

The actor opens a private copy of the saved three-file D20 scan from
`scan_template/project`, whose measured-data provenance and independent ASCII
import conventions are in `scan_template/REFERENCE.md`. It preserves every
scientific parameter, measured row and the ordinary 1000-iteration limit.
The real Main window, Analysis page, Start fitting button, worker, every-pattern
handover and structure-curve toolbar button are used. Both feature cases run a
complete real scan and require at least two distinct files observed while the
worker is still running. Every accepted running handover is inspected, not just
the final stopped frame. Each plotted measured sample must match its independently
parsed file's x and intensity exactly. Rounded x follows the reference loader.

The calculated curve's complete point vector must change from the initial curve
and between successive files. It is an observation, not a scientific golden.
The pixel check is a presentation consistency invariant: actual pixels must follow
the current published series. The cached Data table's calculated column is not a
valid reference for a transient live fit frame; it is deliberately not used.
Standalone numerical correctness stays with the independent scientific gates.

`run.sh` uses the application's normal OpenGL capture platform (Linux's private
Weston/Xwayland with Mesa llvmpipe, or macOS's logged-in Cocoa session). A software
or empty renderer cannot supply the required positive pixels. Image geometry
comes from the actual plot rectangle and axes; the independent JavaScript projects
the physical polyline and measures point-to-segment distance. The three-logical-
pixel corridor covers the two-pixel pen's half width, edge coverage and coordinate
rounding. Pixels along the calculated ink/background colour segment with at least
15% ink are classified, so a faded retained curve also fails. A baseline capture
must positively see the ordinary current curve before the fit. At a running
handover, visible initial/current curve separation must make a stale initial line
observable rather than allowing coincident paths to supply vacuous evidence.

Each structure needs a nonempty visible area and real interior pixels matching
its alpha-composited fill over the actual chart background. Samples are away
from the upper/lower edges and plot boundary; an outline, empty area, matching
background, transparent area or stale series object alone cannot pass. The
single-structure D20 witness also exercises the rule that one structure gets a
fill. Both cases save images and per-frame observations in their private working
directories. Initial/current snapshots changing file or running status during
the grab are discarded, and the liveness requirement prevents discarded frames
from silently becoming evidence.

The actor includes a separate synthetic observer control using the exact same
geometry and predicates. It accepts a current-only line and filled interior,
rejects an extra initial line, a 25%-opacity stale line, an empty renderer, an
outline without interior, and an invisible fill. These controls establish
observer sensitivity, not scientific correctness.

Run only `pytest --noconftest tests/integration/app/test_sequential_pattern_drawing.py`.
The wrapper selects and bounds each native phase separately, refuses missing,
empty, wrong, skipped or failed receipts, and kills the whole owned process group
on timeout so the fit worker/display servers cannot survive the actor. The
application environment and a built native test host are required; an explicit
`EDI_APP_TEST_RUNNER` can select a copied qualified host. A dirty copied host is
useful red-first evidence but does not certify an exact source head, SDK closure,
Windows or browser drawing. No reference values are read from a sibling product.

The emitted frame's `file` field reads `FitViewModel.scanShownFile`, the last
presented-file receipt. It does not read the current dataset, the latest fitted
file or the worker's next file. The actor reads that receipt before the grab and
rejects a capture if the receipt or running state changes across it. Its series
arrays are also read on the GUI side before the grab. This guard does not latch
the receipt to the image's scene-synchronisation event. A frame captured during
a handover therefore needs that identity timing checked before a filename/
measured-series mismatch establishes wrong scientific drawing. The independently
parsed measured columns remain the reference; no oracle is switched to the
newest fitted dataset merely to pass the handover.

The separate `scan_screen` observer instead identifies a file by independently
matching the current `PatternModel`'s measured-column hash (`modelMeasured`) and
samples `chart.measured`'s actual points in that same `afterSynchronizing`
callback. Its derived `file` is not this receipt. That observer can establish a
synchronized model/chart-source mismatch without the GUI grab's receipt-phase
ambiguity; neither gate substitutes the newest worker file for its own identity.
