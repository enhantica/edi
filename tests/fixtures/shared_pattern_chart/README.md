# Shared pattern-chart acceptance

The native actor creates the actual application window and navigates its actual
Structure, Experiment and Analysis pages. Report charts are explicitly excluded
from the non-report chart census. No fixture substitutes a chart or supplies
view state.

The Structure tab case removes every actual experiment, checks the existing
Structure tab and disabled second Pattern tab, creates an experiment, then
removes it again. This exercises both transitions rather than only a default.
The identity case visits every host repeatedly and requires exactly one eligible
shown chart. It accepts either one reparented object or the ADR-authorized retained
per-page fallback, whose controllers pause while hidden.

The state cases originate on each of the three pages. One set uses pointer
and keyboard input to change both axes, the experiment selector, legend, hover,
a box zoom and a pan. A separate set changes every visible toolbar toggle in
turn and checks the other pages after each change. A component-curve failure
cannot suppress the axis, selector, zoom and pan receipts. Each stimulus has an observable change witness.
Momentary Reset is an action, not a toggle, and is excluded from the toggle stimulus.
Every destination must show the same selected experiment, axes, toggle states
and numerical limits. Defaults alone cannot supply the witness. Existing
control and series object names are used; the new Structure tab and experiment
selector are found by their actual text and model rather than a new object name.

A separate positive control exercises the actual legend toggle, axis selector
and both native drawing observers on the existing Experiment page.

For hidden work, every host is first visited so all retained charts exist. The
actor observes every retained hidden controller's measured revision and actual
Qt points-replacement signal through pending input/size changes. Hidden charts
must upload nothing; showing a pending chart allows exactly one catch-up. A
reparented chart already caught up has no second pending upload to perform.
