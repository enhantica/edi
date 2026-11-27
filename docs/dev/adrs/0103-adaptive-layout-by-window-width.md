# 0103. Adaptive layout by window width

- **Status:** Accepted (owner, 2026-11-21: the four-range proposal)
- **Date:** 2026-11-18, amended 2026-11-21, 2026-11-22, 2026-11-23 and 2026-11-24 (the owner's numbered rules, decisions
  3, 4, 6 and 7)
- **Implementation:** ✅ Implemented
- **Priority:** High
- **Forward constraint (binding on new features):** a new control, column or status item declares its priority and its
  column type; nothing sizes itself from its content at run time, except a column of names, IDs or file names, which
  takes its text's width (T5); layout decisions read the one width range, never a
  private width test.

## Context

edi runs on a phone browser, a tablet, a laptop and a large monitor (the web app and the desktop app share the QML).
Today the window has a minimum size of 1024 × 640 logical pixels (`AppSizes.minimumAppWidth`; a browser window
below it shows an "Increase the window size" overlay), the sidebar's width is bound to the distance from the window's
right edge to the centre of the app bar's Experiment tab, a rule this ADR replaces, table columns size themselves from
their contents (ADR-0029) and visibly jump as values change, and only the status bar (ADR-0017 §17: items give way
from the end, keys shown only when all fit) and the chart toolbars (ADR-0090 point 7: controls move to a ⋯ popup least
important first, by one priority list) adapt. The owner asked (2026-11-18) for layouts that adapt to the screen size
the way web pages do, with fixed column widths, elided text and scientific notation instead of jumping columns, and a
sidebar whose width is chosen automatically, never dragged. On 2026-11-19 the owner asked for that width to change
smoothly and never shrink as the window grows, and for narrow windows to put the sidebar at the bottom; the proposal
built from it was accepted on 2026-11-21.

## Decision

1. **Four width ranges.** The window's logical width selects one range, read from one shared property
   (`AppSizes.range`, from the window width `AppSizes.appWidth`) and nowhere else:

   | Range | Width (logical px) | Typical device |
   |---|---|---|
   | compact | < 600 | phone |
   | medium | 600 – 1024 | tablet, narrow browser window |
   | expanded | 1024 – 1600 | laptop |
   | large | > 1600 | desktop monitor |

   Boundaries belong to the upper range (600 is medium, 1024 expanded, 1600 large). The range changes only when the
   width crosses a boundary. Inside a range a resize moves the chart area and, by decision 3, the sidebar's width and
   the Analysis parameter table's columns (W4); nothing else.

2. **Content by priority, as it fits.** What does not fit gives way by priority, in the schemes that already exist
   rather than a new one: the Analysis parameter table drops whole columns by its priority list (decision 4; every
   other table keeps its columns and its numbers lose digits), the chart toolbar moves controls to
   its ⋯ popup by its priority list (`toolbar_row.cpp`, ADR-0090 point 7), and the status bar gives way from the end
   (ADR-0017 §17). All three follow the room they have, so they adapt to every width without a per-range cut-off
   (amended 2026-11-21 to the accepted proposal). In the compact range the app bar shows the pages as icons only and
   hides Redo, Clear and the tooltip switch, and the status bar hides its fit values; from 600 px the app bar shows
   icons with labels.

3. **The sidebar width (rules W1-W7).** Lengths are in em, the app font's pixel size (14 px by default); the numbers
   are the owner's (2026-11-23, "the GUI acceptance numbers are the binding contract") and a change to one needs an
   owner decision. The switch width (`AppSizes.sideBarBelowWidth`) is the narrowest window whose main view still holds
   its widest tab bar on one line; from it the sidebar is at the side, below it at the bottom.

   - **W1** Auto depends on the window width only: the same to the pixel on every page, before and after a fit, with
     and without a project.
   - **W2** Full is edi main's rule, the window's right edge to the centre of the Experiment button, the same to the
     pixel on every page.
   - **W3** At the switch width the sidebar is at most half the window and shows Name, Value, s.u. and Free.
   - **W4** Auto grows with the window and never shrinks; the Analysis parameter table adds Start, Min, Max and Change
     in that order, each as soon as it fits, and once all fit Auto stops at all columns plus at most one column gap:
     681 px in the 14 px font, every gap of the table one em (T1); the sidebar goes to the bottom below 913 px.
   - **W5** At the Auto stop the empty space before Free is at most one column gap for every bundled example: the name
     budget is the widest bundled example's name.
   - **W6** Compact shows Name, Value, s.u. and Free (no unit column) and is wide enough for the three filter combos
     to show their whole text ("All categories (58)").
   - **W7** At the bottom the sidebar is half the window's height, at most 70 % of the page, less what the chart needs:
     120 px for the pattern's main pane and 40 px for its residual, the Bragg rows and the toolbar shown (the owner,
     2026-11-24). It depends on the window and on the most Bragg rows a pattern of the project has (one per linked
     structure, two for a magnetic one), never on the page, the tab or a fit. With two rows the chart needs 475 px, so
     the sidebar has 406 px of 860x1000. A window that leaves it under 14 em keeps the half: below 790 px high with two
     Bragg rows, 769 with one, 727 with none. It has a 1 px border along its top.
   - **W8** A chart's second control row (the Evolution chart's) starts and ends with the selector row above it, its
     picker taking the rest of the row without an ellipsis while its name fits, and neither edge moves as the selection
     changes (the owner, 2026-11-24).
   - **W9** Every report figure (experiment charts and structure views) is in the same border, its control buttons inside
     it, with the same padding on its four sides: the gap between a chart's buttons and its plot (the owner,
     2026-11-24). A chart's right side is its plot's frame, which an x tick's number may overhang; a structure's scene is
     drawn by the camera, so its buttons' distance from the top counts. Every pane of every chart, in the report and on the Pattern tab, shows its four border
     lines whole at any scroll position and any scale.
   - **W10** Every parameter name the app shows is the one the `.edi` files use and an alias refers to: the datablock's
     own name, the category, the row's id and the item (`cosio.atom_site.Co1.adp_iso`, `d20.peak.asym_fcj_1`), never a
     Python attribute path or brackets (the owner, 2026-11-24). `ParameterItem::fullName` is the one place it is made.

   The width button's other modes are steps of the same table: No change (all but Change) and Fit values (Name,
   Start, Value, s.u., the row number and Free); Manual is the width dragged. At the bottom the Analysis sidebar has
   no name filter, its reset sits at the end of the pickers' row, and the block selector shares one row with the chart
   toolbar while the selector keeps at least 30 em. The minimum window is 360 px wide, 640 px high below the switch
   width and 600 px high from it.

4. **Tables (rules T1-T12).** Every sidebar table declares its columns' kinds (`DataTable.columnKinds`): the row
   number, a mark, a name, short or long text, a number (value, s.u., displacement, change), a unit, a control, or a
   fixed width; a user's id or label is a name, a fitted parameter a value.

   - **T1** The gap between neighbouring columns' content is 1 em ± 1 px.
   - **T2** A unit starts one space after its value ± 1 px, in the value's size and never bold.
   - **T3** Trailing check boxes and buttons end at the table's right edge less the cell margin ± 1 px, with no spare
     after them.
   - **T4** Spare width, if any, is one block directly before the trailing controls.
   - **T5** A column's width comes from its kind and parameter type, the full typical value reserved, never from the
     values shown; a name, ID or file column from its text, the widest of the model role it declares
     (`DataTable.columnTexts`), read from the model, never from made rows (edi ADR-0105). Columns of one
     kind are equal to the pixel (ADP 11 = 22 = 33 = 12 = 13 = 23).
   - **T6** Column positions and widths do not change (± 0 px) across an edit, a type change (Biso to Uani), a fit, a
     load of the same project, a page switch and back, and every frame of a fast scroll.
   - **T7** A sidebar table takes the room that keeps the whole sidebar in view (the owner, 2026-11-24): the sidebar's
     height less everything else in it (group titles, the rest of its group, the open groups after it), each group
     counted at the height it rests at, so a group still opening already counts as open. A table whose rows fit shows
     them all. One whose rows do not fit shows whole rows and half the next as the cue that it scrolls, and only the
     table scrolls. The sidebar scrolls only when that would leave a table under 2.5 rows; the table then shows 2.5.
     Open tables share the room: one needing less than an equal share keeps all its rows and leaves the rest to the
     others. A row taller than the table's own (an example whose description wraps) counts at its own height. It is one
     rule for every sidebar table (`DataTable.placeRoom`); no table sets its own row count. A table is drawn from its
     first frame at that height and does not change while nothing around it opens, closes or
     resizes.
   - **T8** Numbers show at most six significant digits, fewer only when the column is at its narrowest; data tables
     (not the Analysis parameter table) go down to two significant digits ×10ⁿ (ADR-0051); a number is never cut.
   - **T9** Headers show their whole text, start with a capital letter and align as their content (numbers right, text
     left, controls centred) ± 1 px.
   - **T10** Text a user gave elides in its middle only when its column is at its minimum, keeping at least 10
     characters, the whole text in a tooltip.
   - **T11** The row-number column shows at every width.
   - **T12** The vertical scroll bar shows exactly when the content is taller than the view.

   Only the Analysis parameter table drops columns, whole ones by its priority (Change, Max, Min, Start, then the
   unit); every other table keeps its columns and its numbers lose digits. A table never scrolls sideways. This
   replaces ADR-0029's content fitting: its shared header and cell widths and alignments stay.

   **When rules conflict** the higher wins: (1) nothing the app wrote is cut, numbers, headers and fixed labels;
   (2) nothing moves after it is shown, sidebar width, column widths, table heights, cell positions; (3) columns show;
   (4) where the spare goes; (5) breathing room.

   **Never:** a number or header cut or ending in "…"; a fixed label cut; text under a combo arrow or another control;
   two sibling controls overlapping; a sideways scroll bar in the sidebar; a vertical scroll bar with nothing to
   scroll; a sidebar or column width change after a project is shown; a table growing row by row; a cell drawn at
   another column's x; a unit in bold; a header repeating its group's title.

   **What the rules do not count, and why it is not a violation** (each is in the layout check where its rule is):

   - T1 leaves out only an identified empty spare block (T4): the part of the spare column past its content, which has
     no content edge. The content before it is measured at its own edge, as are the row number, a mark and a control.
     A number column's content is its kind's typical value (T5), or the room it declares (a scan's values). A unit's gap
     is T2's, one space. An input's content is its text with the room it needs while it is edited, the bold it takes then
     and its caret: without that room, starting an edit would move the columns (T6). A selector's column is as wide as
     its longest option (T5), so its content ends at its column's margin, whichever option is chosen. A text drawn
     transparent, an input under its shortened label, draws nothing. A unit's content is its widest, deg² (T5). The
     parameter table's name ends at its budget (W5) and may hold up to one column spacing more, which is spare.
     A table whose rows are still to be measured has no cell margins yet and is not read.
   - T4: only check boxes and buttons are trailing controls. A mark is content, the spare after it, but a mark right
     before the controls (the recent projects' status) stands with them, the spare before it. The parameter table's
     name is measured against its budget (W5), and Min and Max, one kind, against the wider of their two titles (T5):
     those widths are reserved, not spare.
   - T8, T9 and N1 count the glyphs' ink, not their box: a line gap or an unused descent cut off takes nothing seen.
     Nor is ink cut by a scrolling view's own edge, in a direction that view scrolls: it is half scrolled out and shows
     whole when scrolled to. Any other clip that cuts it, inside the view or around it, is a violation.
   - T9's capital letter does not apply to a symbol written as science writes it, from this list only, its unit in
     brackets aside: b, d, h, k, l, r, x, y, z, h k l, f rand, s.u., θ, φ, ϕ, λ, χ², sin θ/λ, cRp and cRwp; nor to a
     title that is one of the project's structure names: that is text the user gave, shown as written. Both still show
     whole and align as their content.
   - T10 applies to text the project holds as given by the user (a datablock, row or alias name, an expression, a file
     name, the project's title, a recent project's folder), wherever it shows; its ten characters are counted in the
     text as drawn. Any other text, in a table too, is a fixed label and never cut (N1); a table's title never is (T9).
   - F1 leaves out only a selector alone on its row and as wide as the group (the peak profile): it stands outside the
     grid so its whole name shows (precedence 1), and starts on the grid. Any other selector starts and ends on a grid
     column, spanning whole columns.
   - F4 does not apply to a tab without an arrow or indicator: there is nothing to keep clear of, and its text is
     checked as any text is (N1). A combo box is measured as drawn, the end of its last glyph to its arrow, a shortened
     or custom line too.
   - N3 does not count the two fragments of the Home wordmark ("easy" over "diffraction"), one logo set tight, nor a
     popup (a menu, a tooltip) over the page: an overlay by design. Two texts in a popup, or two on the page, count.
   - W7 does not apply to Home, the one page without a sidebar. On every other page a missing sidebar is a violation.

   **The states** every rule holds in: every page, Project with and without a project, every main-view tab and sidebar
   tab with each group open in turn; Auto, Full, No change, Fit values and Compact (W1 in each of them, its width the
   same); windows of 1280 × 800, 1496 × 900 and 1920 × 1080 at the side and 900 × 1000 and 700 × 900 at the bottom;
   `pd-neut-cwl_cosio-d20_2k` before and after a fit, `pd-neut-tof_ncaf-wish` fitted and the 213-file scan; a site
   switched to Uani, a 24-character structure name, a fast scroll, every frame of a group unfold and the first second
   after a page switch; W7 also for a scan with three Bragg rows. The layout check in the demo driver runs one test
   per rule, named by its number, over all of them.

   **Where a rule is asserted.** Each check below writes a finding named `<rule>:<kind>` that fails its state in
   `tools/dev/gui_contract_report.py`, against the numbers above, never against the app's own; a number this ADR does
   not give is measured on a build and kept as a named constant in the demo driver.

   - W3: at 913 px the sidebar is at the side, at most half the window, with Name, Value and s.u., and at 912 px at
     the bottom (`series-point` in `e58-contract`, `W3:switch`).
   - W4: Start, Min, Max and Change join in that order, Auto is at most 681 px with all of them and never shrinks as
     the window grows (`series-point`, `W4:order`, `W4:stop`, `W4:shrink`).
   - W5: in Auto a sidebar at 681 px shows every column (`W5:stop`); no shown name is wider than the name budget
     (`W5:name`); at the stop the name column is the budget plus at most one column spacing (`W5:name-spare`). The
     budget is measured as the widest drawn name of the bundled examples (`e58-names`, each with the layout check).
   - W6: in Compact each of the three pickers draws its default text whole (`W6:picker`), read from the box.
   - T5: the filler's reserve, the part before its spare, is as wide as the other columns of its kind (`T5:filler`).
   - T6: a table's column widths hold across a type change, an edit, a page switch and back, a fit and a load of the
     same project (`e58-columns`, `T6:columns-moved`), and in every frame for 1.2 s after a page switch or an unfold
     (`e58-stable`, `T6:moved`).
   - T7: no table is drawn before its columns are measured (`e58-stable`, `T7:first-draw`).
   - T8: a table's number shows at most six significant digits, and when digits drop never fewer than two
     (`T8:digits-most`, `T8:digits-least`).
   - T11: the row-number column holds its widest row number, bold, inside its margins (`T11:narrow`).
   - C1: a legend label up to 20 characters is never cut (`C1:legend-cut`); a longer datablock name is the only piece
     cut, in its middle, with a tooltip holding the whole name (`C1:legend-name`).
   - C2: with every legend entry off, no line, scatter or filled series draws (`e58-legend`, `C2:legend-hidden-drawn`),
     the structure curves and a time-of-flight pattern included; an area's two edge lines are judged with the area.
   - D1: a dialog is at most its content's width plus 2 em (`e58-dialogs`, the fit's results at 1000 and 1496 px,
     `D1:dialog-wide`); its rows and values are read as every text is (N1, T8); a tooltip has at most 12 lines inside
     the window (`D1:tooltip-tall`).
   - The states: the report fails when a state above was reached by no run, each project state (the 2k example
     before and after a fit and with a 24-character structure name, the time-of-flight joint fit after its fit, the
     213-file scan) in each mode at each of the five windows, Project without one at each window, and the scenarios of
     the variant states (`e58-columns`, `e58-scroll`, `e58-stable`, `e58-bottomchart`). The sweep reaches the
     unfitted projects and `e58-states` the others.
   - The T5, T8 and T11 checks and the first-draw check leave out the two layouts that wait for the owner's decision
     on columns that do not fit: a scan's row with six extract columns in Compact and the expanded atom sites in
     Compact and Fit values.

5. **Charts take the remaining space.** The main area keeps the chart toolbar and selector row on one line, with
   their own priority overflow, and the chart's frame (panes and axes, ADR "the UI update rule" rule 5) scales with
   the area.

6. **The parameter popup and field rows.**

   - **F1** A field row (the cell, the peak profile, the instrument, S/L and D/L) shows at least four significant
     digits; where that does not fit it wraps into even rows (six as three and three), and two digits only when one
     field per row does not fit. No value is cut. All the field rows of one group share one grid: the same column count,
     column width and x positions to the pixel, so every field stands under the one above it (S/L and D/L under U and
     V), and a short row never stretches its fields to fill (the owner, 2026-11-23, "one grid per group").
   - **F2** A click on any parameter, a table cell or a field, opens its popup within 100 ms, at the cell or field.
   - **F3** The popup is one row under its titles: Full name, the parameter's `.edi` name (W10) as a link to its
     documentation; Value, the value input with its unit inside; s.u.; Min and Max; and Free. The s.u., Min and Max are
     disabled inputs, there before a fit too (Min and Max for now). The gaps between neighbouring cells are equal, 1 em,
     and the s.u., Min and Max inputs have one width, a whole s.u.'s in either form it is written in (0.00021,
     1.9×10⁻⁸⁸): an s.u. is never cropped, and a longer number is fitted as in a table's cell, in full on hover (the
     owner, 2026-11-24). Every cell's vertical centre is equal ± 1 px. The popup's layout and width are the same before
     and after a fit, to the pixel (the owner, 2026-11-23). Editing happens in the popup; Enter commits, Escape closes.
   - **F3a** A derived value in a table (|M|, θ, ϕ, a weight fraction and any other computed, not fittable, quantity)
     shows its value only, never "value(s.u.)"; a click opens the same popup with the full value and its s.u., the Free
     check box disabled (the owner, 2026-11-23). A moment's Cartesian and spherical components open it too, their value
     edited there and converted back to the crystal axes (2026-11-24).
   - **F4** In every combo box and button the text ends at least 0.25 em before the arrow.

7. **Icons, charts and dialogs (rules I1, C1-C3, D1).**

   - **I1** The width and pin icons use the text colour and the sidebar header's icon size, their horizontal centres
     equal ± 1 px.
   - **C1** A legend shows fixed labels whole; a datablock name over 20 characters elides in its middle, the whole
     name on hover.
   - **C2** A legend entry switched off draws nothing of what it names, the magnetic contribution included.
   - **C3** The residual axis title is at the standard axis-title size: "meas − calc" where it fits the pane's height,
     else "resid".
   - **D1** Dialogs show every row and value whole, at most the content's width plus 2 em; tooltips have at most 12
     lines and stay inside the window.

## Consequences

- The window's minimum width drops from 1024 to 360 logical pixels (decision 3), so the desktop app can be tested at
  every range by resizing; the web app's too-small overlay follows the same minimum.
- Every table, toolbar and status item gains a declared priority and column type; a new one without them fails review.
- Columns no longer jump; long names show elided, with a tooltip.
- Window-size captures at one width per range become the layout's regression check.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| A user-draggable splitter between the main area and the sidebar | Rejected by the owner (2026-11-18): "chosen automatically from a few fixed ratios" |
| A fixed ratio of the window per range (the first proposal) | Replaced by the owner (2026-11-19): a width that jumps at a range boundary does not look pleasant; the smooth, never-shrinking width replaced it |
| A drawer over the main area in narrow windows | Replaced by the owner (2026-11-19): the sidebar at the bottom, above the status bar |
| Columns sized from their contents once, at load | Rejected: still depends on the data and still changes when another project or experiment is shown (a name, ID or file column still takes its text's width, T5) |
| More than four ranges | Rejected: the owner agreed to four; more ranges multiply the captures without a clear device class |
