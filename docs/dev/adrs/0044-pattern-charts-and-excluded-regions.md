# 0044. Pattern charts and excluded regions

- **Status:** Accepted
- **Date:** 2026-10-21
- **Implementation:** ✅ Implemented
- **Priority:** High

## Context

A point inside an excluded region is not fitted, so it has no calculated, background or difference value. Project
files used to write `0.` in those cells, and a reader that does not check `_data.calc_status` takes that as a real
zero: the calculated curve drops to zero across every excluded region. The charts had the same problem in their own
way, joining the curves across a region or dropping them to zero, and offered no way to look at only the range that
is fitted.

## Decision

1. **Excluded rows carry no derived values.** On every excluded `_data` row, `intensity_calc` and `intensity_bkg` are
   `.` (inapplicable) on file and NaN in memory, and so is the difference. The d-spacing is a unit conversion of the
   measured axis and is written at every point. This is the engine's rule, and edi's loader refuses a file with
   anything but `.` in those two cells of an excluded row, naming the row. Every committed project, fixture and
   example was rewritten to this form; there is no fallback for the older `0.`.
2. **Curves break at excluded regions.** On every pattern chart (Experiment, Analysis, scans) the calculated,
   background and difference curves stop at an excluded region and start again after it, and no Bragg tick is drawn
   inside one (the owner, 2026-10-21). A reflection centred in an excluded region stays in the calculation, since its
   tails reach included points; only its tick is hidden. Measured points stay visible inside excluded regions, and each
   region has a faint tint just off the chart background.
3. **A toggle shows only the included range.** A button in the chart toolbar's group with the legend and tooltip
   buttons, with the eraser icon of the Excluded regions group and the tooltip "Show only the included range". When it
   is on, the x axis runs from the first to the last included point, interior excluded regions are empty tinted gaps
   with no measured points or curves, and reset view returns to that range. When it is off the chart
   shows the full measured range with the tint. The choice is an app setting kept between sessions.
4. **The axis selectors fit their text.** Each selector in the chart's toolbar is as wide as its longest entry or
   closed text needs, no wider, so the two need not match (the owner, 2026-10-22). The x-axis selector reads
   `x: d-spacing` once d-spacing is chosen.

## Consequences

- Any reader of a project file sees an excluded region as having no calculated pattern, which is true.
- A file written before this change has to be rewritten before it loads.
- A chart shown against d-spacing covers the whole measured range, excluded points included.
- An interior gap stays on the axis at its true width; the scale is never broken.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Keep reading `0.` on excluded rows as no value | Rejected: the file would still say the pattern is zero there to every other reader. |
| A broken x axis that removes interior gaps | Rejected: it distorts the scale, so peak positions and widths read wrongly. |
| Hide measured points in excluded regions all the time | Rejected: what was excluded should stay visible unless the user asks to see only the fitted range. |
