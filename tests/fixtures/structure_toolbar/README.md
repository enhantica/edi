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
actual isolated app-settings file, a fresh QML engine opens the actual BEER
example and creates a new production Analysis page. Its real calculated
chart must restore the selected value. The test does not require a particular
setting key or preference-property name. It resets no product values before
reading the fresh control.

The existing settings observer optionally waits for a source object's
`acceptanceReady` Boolean, with a bounded event pump. It supplies no project,
calculated profile, button state or desired result. Sources without that
property keep their original immediate snapshot behavior. A separate observer
control reaches the real fresh calculated page even while the new button is
still missing; that is observer evidence, not a green feature verdict.

The native actor has separate scan and toolbar cases. The Python wrapper runs
the observer control, scan case and each saved-state case in separate processes,
each with the existing watchdog. Missing scan tabs cannot suppress the toolbar
checks, and a timeout in one phase cannot suppress the others.

This native settings-backed engine restart does not claim a Windows browser
reload or an OpenGL screenshot result. Those remain separate browser/rendering
proofs. The scan-view requirement still needs populated scan-pattern evidence;
its existing tab check alone is not that evidence.
