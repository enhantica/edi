# Shared pattern-chart acceptance

The native actor creates the actual application window and navigates its actual
Structure, Experiment and Analysis pages. Report charts are explicitly excluded
from the non-report chart census. No fixture substitutes a chart or supplies
view state.

The Structure tab case removes every actual experiment, checks the existing
Structure tab and disabled second Pattern tab, creates an experiment, then
removes it again. This exercises both transitions rather than only a default.
The identity case retains the original chart reference across repeated visits
and censuses all loaded pages, including hidden ones. Recreating an equal-looking
chart or leaving a duplicate hidden chart cannot satisfy object identity.

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

For hidden work, the gate first visits every page and requires hidden pages to
own no non-report chart. It observes the actual measured-layer revision and Qt
calculated-series `pointsReplaced` signal, with a visible axis change proving
both observers respond. While the Project page is shown, a real experiment
selection and a window resize invalidate the hidden presentation. With no Pattern host shown, the chart must be effectively invisible or detached
from every window, so its scene-graph item cannot draw. Neither
series may upload drawing data; showing the same chart must consume the pending
update. These are drawing-data preparation observations, not GPU command counts.
The object-ownership census separately prevents a hidden page's duplicate graph
from escaping the observers. Native software/offscreen execution supplies no
Windows browser or OpenGL image proof.

This gate enforces the single moved chart specified by the acceptance gate. The
packet's conditional alternative needs a recorded Qt Graphs failure and ADR
before a different identity assertion is appropriate; a hidden duplicate is not
silently accepted as that alternative.
