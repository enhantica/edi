# Current-row input inventory

The catalogue enumerates every production table delegate from the closed QML
census. Its expected behaviour comes from the owner's table-input decision:
clicking an editable or non-editable cell makes its row current, keyboard moves
use the same row, and exactly that row has the accent marker and bold accent
number. Light and dark themes use the same invariant.

The runtime instantiates the real table owners and delegates. Mutable tables
use real project models and their ordinary append/duplicate operations. Reflections,
fit-start, extraction-rule and message delegates receive independently authored
read-only ListModel rows to avoid requiring a calculation or fit just to exercise
input. Those rows make no claim about scientific correctness. Fit-result tables
use the existing independent saved five-bank fit fixture. Report tables receive
explicit two-row display input.

The About dependency table, report tables and the two fit-result tables
have no current-row action or numbered current-row convention. Their input cases
check that clicks and arrow keys leave them without a current-row marker.
Messages have dismiss actions and remain in the active-row inventory. The
preferred-orientation model admits one row, so that case proves entry from no
current row; the other mutable-table cases use distinct rows. The runtime never
sets currentRow, markerRow, selected indexes or backend current-row properties.

The cursor gate observes the real input item's active focus, read-only state,
cursor visibility and non-empty cursor rectangle. Background gates sample actual
window pixels after the pointer leaves an editor; their alternating and hover
colours come from the independent existing base-style fixture. Hover is exercised
separately, so an input-selection failure cannot hide a background failure.

The two reported pages also execute through the real Main window, selected page,
and sidebar. These cases separately check real cell selection, cursor state and
background pixels, so focus handling by the application cannot be hidden by a
passing standalone component check.
