# 0097. Adaptive layout by window width

- **Status:** Proposed
- **Date:** 2026-11-18
- **Implementation:** ⬜ Not implemented
- **Priority:** High
- **Forward constraint (binding on new features):** a new control, column or status item declares its priority and its
  column type; nothing sizes itself from its content at run time; layout decisions read the one width range, never a
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
sidebar whose width is chosen automatically from a few fixed ratios, never dragged.

## Decision

1. **Four width ranges.** The window's logical width selects one range, read from one shared property
   (`AppLayout.range`) and nowhere else:

   | Range | Width (logical px) | Typical device |
   |---|---|---|
   | compact | < 600 | phone |
   | medium | 600 – 1024 | tablet, narrow browser window |
   | expanded | 1024 – 1600 | laptop |
   | large | > 1600 | desktop monitor |

   Boundaries belong to the upper range (600 is medium, 1024 expanded, 1600 large). The range changes only when the
   width crosses a boundary, so a resize inside a range moves nothing but the chart area.

2. **Content by priority.** Every app-bar action, chart-toolbar control, status-bar item and table column has a
   priority from 1 (always shown) to 5 (only in the large range). A range shows the priorities up to its limit and
   puts the rest in the existing overflow menu. This extends the existing schemes rather than adding one: the chart
   toolbar's priority list (`toolbar_row.cpp`, ADR-0090 point 7) gains a per-range cut-off, and the status bar's
   fit-from-the-end rule (ADR-0017 §17) gains declared priorities in place of its list order. The
   app bar shows icons with labels in expanded and large, icons only in medium, and in compact a page menu and the
   page title.

3. **The sidebar width is a fixed ratio of the window per range.** compact: a drawer over the main area (88 % of the
   width, opened by a button or an edge swipe, closed by tapping outside); medium: **½**; expanded: **⅖**; large:
   **⅓** (proposed defaults until the owner chooses between the mockups' options). The ratio is not user-draggable and
   does not depend on any toolbar or tab width. The sidebar's content width (`sideBarContentWidth`) derives from the
   chosen ratio.

4. **Fixed column widths by column type.** A table column's width comes from its type, never from its rows:
   number (value, error, min, max: room for 10 characters in the table font), short text (units: 5), index (No.: 4),
   check box (one control width), and one *elastic* text column per table (name) that takes the remaining width.
   Text that does not fit is elided (at the end for names and labels, in the middle for paths and file names) and
   shows its full text in a tooltip. A number that does not fit in its column's width is written in the app's one
   scientific form (`1.23×10⁵`, ADR-0051) with as many significant digits as fit; a value with an s.u. keeps all its
   digits and writes the s.u. at the same power. The full value is in the tooltip. A table too narrow for all its
   columns drops whole columns by priority while the rest do not fit beside the name's minimum width; its header and
   rows always show the same columns. The Analysis parameter table drops Min and Max first, then Change, s.u., Start,
   the row number and the units; Name, Value and Free always show. No column
   measures its rows, and widths do not change when values change. This amends ADR-0029's width rule ("row numbers
   fit the largest displayed number; labels and units fit their content, capped at a quarter of the table width;
   numeric columns share the remaining space"): the declared-once, shared header/cell widths and the alignments of
   ADR-0029 stay; the content fitting is replaced by the column types above.

5. **Charts take the remaining space.** The main area keeps the chart toolbar and selector row on one line, with
   their own priority overflow, and the chart's frame (panes and axes, ADR "the UI update rule" rule 5) scales with
   the area.

## Consequences

- The window's minimum width drops from 1024 to the compact range's minimum (360 logical pixels) and the too-small
  overlay goes, so the desktop app can be tested at every range by resizing; the web app follows the browser window.
- Every table, toolbar and status item gains a declared priority and column type; a new one without them fails review.
- Columns no longer jump; long names show elided, with a tooltip.
- Window-size captures at one width per range become the layout's regression check.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| A user-draggable splitter between the main area and the sidebar | Rejected by the owner (2026-11-18): "chosen automatically from a few fixed ratios" |
| Continuous sidebar width (a fixed pixel width clamped to the window) | Rejected: either too narrow on large screens or too wide on tablets; ratios per range are predictable |
| Columns sized from their contents once, at load | Rejected: still depends on the data and still changes when another project or experiment is shown |
| More than four ranges | Rejected: the owner agreed to four; more ranges multiply the captures without a clear device class |
