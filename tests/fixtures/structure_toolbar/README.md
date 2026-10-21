# Structure-curve toolbar acceptance

The control belongs to the pattern-chart toolbar's legend/coordinates group.
It uses the existing structure icon (`layer-group`) and the tooltip
`Show each structure's curve`. It is hidden without a calculated pattern and
off in a fresh app-settings store. Pointer input shows and hides the actual
per-structure area series. Each series starts at the background, rather than
at a preceding structure, and has a soft fill with a more opaque outline.
The outline may be the area's own border or a visible line of the same colour
following every point of its upper curve; the test does not dictate either
rendering representation.
The view choice does not modify the scientific project.

The on and off settings are tested separately. After real input writes the
actual isolated app-settings file, the original app window closes. A fresh
QML engine creates the actual production ChartToolbar component and reads its
real curve button's checked binding from the app store. It creates no graph,
sets no desired preference and supplies no calculated profile. Availability
and drawing were already checked in the real app; the fresh probe reads the
same button even while its availability flag is off by default.
The test does not require a particular
setting key or preference-property name. It resets no product values before
reading the fresh control.

The existing settings observer optionally waits for a source object's
`acceptanceReady` Boolean, with a bounded event pump. It supplies no project,
calculated profile, button state or desired result. Sources without that
property keep their original immediate snapshot behavior. A separate observer
control constructs the real fresh toolbar even while its curve button is
still missing; that is observer evidence, not a green feature verdict.

The native actor has separate scan and toolbar cases. The focused toolbar
Python wrapper runs only the two saved-state cases, each in its own process
with the existing watchdog. The older view wrapper runs its observer and scan
cases separately and does not repeat the toolbar cases. A toolbar-only run
does not start row-number, About or scan actors. A timeout in one toolbar
phase cannot suppress the other.

This native settings-backed engine restart does not claim a Windows browser
reload or an OpenGL screenshot result. Those remain separate browser/rendering
proofs. The scan-view requirement still needs populated scan-pattern evidence;
its existing tab check alone is not that evidence.

Before the shared chart, this gate created an Analysis page directly inside the
Qt test surface and treated that page as the chart owner. Its fresh-engine
snapshot likewise put an Analysis page into an ordinary Window. After the
ownership change, those fixtures could expose an unattached slot rather than
the chart a user sees; the pointer assertion failed before the feature ran.

The gate now creates the actual application window and reaches Analysis through
the actual app-bar control. It requires one visible chart in that page and
checks that both the page and chart belong to that application window before
input. Input waits for layout, movement and an explicitly requested frame, and
targets the exposed part of the real toggle. The empty-pattern check also uses
the real window: an unsaved project with a structure and no experiment, shown
on Experiment. No replacement chart or saved preference value is injected.

The before/after assertions keep default off, hidden without a calculated
pattern, toolbar group/icon/tooltip, real on/off input, one nonempty area per
structure, exact background baseline, soft fill and matching outline, unchanged
project modification state, actual settings writes and both restored Boolean
values. The host setup changes; these scientific and persistence properties do
not change.

The background and each component may be decimated onto different subsets of
the same full x grid. Before, the gate required equal point counts and compared
those independently sampled arrays by index. Now each area must have nonempty
upper/lower curves on its own common grid and span the background's full domain.
Every lower sample and every displayed background sample must equal the full
calculated experiment background at that exact x coordinate. No interpolation,
rounded tolerance or replacement background is allowed. This preserves the
unstacked-background invariant without prescribing one decimation index set.

The persistence snapshot is deliberately scoped to the production toolbar's
actual checked binding. It does not construct a second Qt Graphs application
inside the first process: that broader fresh-window fixture hit its watchdog.
The real application still supplies all input, ownership, availability and
curve-data checks before closing. This proves the actual toolbar binding
reloads both saved values in a fresh engine; it does not claim a full browser
reload or a second-process renderer restart.
