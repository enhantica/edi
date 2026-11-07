The control tests take their expectations from the application's shared UI rules:
All, Important and Off; Important initially; a 1500 ms delay; and migration of the
saved boolean to Off or Important. The nondefault persistence witness uses 2371 ms.
Tooltip property discovery allows spelling differences without replacing those rules.

The level matrix previously required the declaration on the button. It now discovers
it on the tooltip use, as the shared rule permits. Migration previously seeded only
the old boolean; it now removes the new level first, so it exercises a legacy store.
The disabled application witness is Save in a new application with no project. At
Important and All, hovering Save must show why saving is unavailable and how to
enable it. The tooltip may be hosted by an enabled wrapper to receive hover input.

The container census previously rejected a retained clip even with its own layer.
It now accepts that boundary: a clipped child crossing an enclosing clip needs a
layer between them. Plain nested clips and an unrelated child's layer still fail.

The tooltip timer observer reads Qt's actual registered delay timer and delivers its
expiry event on an injected clock. It neither changes the production delay nor sleeps.
The original 1000 ms fade is checked separately. The restart observer creates another
production engine and window and sends a real pointer click to its tooltip button.

The table actor supplies a Qt ListModel with 1000 rows and the widest text at row 917.
Qt FontMetrics supplies the independent text advances. Delegate construction is counted
from the actor. Every delegate must belong to the actual ListView; the count of
delegates created outside that view must be exactly zero. Header and
body widths, scrolling, and an off-screen data edit are separate observations.

The census includes the configured base QML selected by CMake, as well as app QML.
`deferred.json` records the two overlap branch heads and their changed QML paths from
`git diff --name-only origin/main...HEAD -- app core`. These files wait for the final
shared-control pass. No unrecorded file is exempt. The final pass must retire this list.

Earlier style and table tests used the boolean tooltip flag to enable their witnesses;
they now select All and restore the previous level. The preferences migration test
previously asserted false/true in the legacy store; it now asserts Off and a retained
new-store All while preserving the old-store value. The preferences layout and fit
results tests previously required the checkbox; they now require the level chooser and
delay row. No existing test source pins the Help or bug app-bar buttons; the existing
Home feedback interaction tests remain applicable.
