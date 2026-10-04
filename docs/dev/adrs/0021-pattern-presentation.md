# ADR-0021 — The pattern presentation: one description every renderer draws

- **Status:** Proposed (plan accepted 2026-10-02)
- **Date:** 2026-10-02
- **Implementation:** 🟡 Partially implemented — the core description and the app chart are built; the notebook
  and terminal renderers land with
- **Priority:** High
- **Forward constraint (binding on new features):** a pattern renderer draws only what `edi::present_pattern`
  returns. It computes no value, chooses no colour and decimates nothing itself. A new series, scale or style is
  added to the description, never to one renderer.

## Context

The owner's visualisation decisions (2026-09-29): crysta computes every number a viewer shows; edi's core
describes the view; renderers only draw. Three renderers will draw the pattern: the app (Qt Graphs),
notebooks and the terminal. A chart of tens of thousands of points must be reduced to
what the screen can show without losing a narrow peak, the edge of an excluded region or an uncertainty bar.

## Decision

### 1. A pure function of immutable input

`edi::capture_pattern` takes, on the owner thread, the immutable buffers of one experiment (`PatternSource`).
`edi::present_pattern(source, view)` is a pure function that returns the series, the excluded bands, the axes and
the layout (`edi/presentation.hpp`). It is Qt-free and holds no crysta type.

### 2. Values

Every point of the Measured, Calculated, Background and Residual series is a row of crysta's `_data` category, and
each series names the row of each point. Each structure has one tick series at crysta's `_refln` positions. An
error bar's ends are the measured value minus and plus its standard uncertainty. The residual is crysta's. There is
no other arithmetic than the display scale.

### 3. Decimation: per pixel column, the extremes

With a plot `columns` device pixels wide and a monotonic axis, a row's pixel column is
`min(columns − 1, floor((x − x_min) / (x_max − x_min) × columns))`. A run is a stretch of consecutive visible rows
whose display value is a number. Per run and per column, a column with at most 4 rows keeps them all; otherwise it
keeps the first, the last, the least and the greatest. The measured series keeps the union of two passes: over the
measured values and over the bar ends. So every column's least and greatest value, every bar's extreme and both
ends of every gap are exact. With no width given, or an axis that is not monotonic, nothing is decimated.

LTTB is not used: it does not keep every per-pixel extreme.

### 4. Gaps, excluded regions, freshness

A row whose computed value is NaN (crysta's excluded rows) ends a run and is drawn as a gap, never as 0. The
excluded regions are the model's, not decimated. When the computed categories are not current, the calculated,
background, residual and tick series are absent.

### 5. Y scales

Linear; Sqrt as `sign(y) × sqrt(abs(y))`; Log10 as `log10(y)` for y > 0 and a gap otherwise. The residual pane is
always linear. Axis labels and hover text show original values, printed with six significant digits and a decimal
point whatever the process's locale is: the core formats them with the classic locale and changes no global one. The
chart's hover read-out (`hover_readout`) is diffraction-lib's instead: over the data or the residual, `x`, `Imeas`,
`Ibkg`, `Icalc` and `Imeas - Icalc` at the point's `_data` row, each line in its series' style; over a Bragg tick,
the structure's name, `x` and `Miller indices: (h k l)` of its `_refln` row, the Miller indices alone in the tick's
style. Its numbers have two decimals and a comma between thousands, in the same classic locale.

### 6. Layout and style

Panes from top to bottom: main, one Bragg row of 18 px per structure, residual; the rest of the height is split 0.7
to 0.3; one shared x range. One style table holds every colour, width and mark, light and dark; its values are
ADR-0017 §15's.

## Consequences

- The three renderers cannot disagree about what a pattern shows.
- A zoom, a pan or a resize is one call of the pure function.
- The description is not bound to Python; binds it.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| Each renderer selects and decimates for itself | Rejected: the owner's split puts the view description in the core, once |
| LTTB decimation | Rejected: it loses per-pixel extremes |
| Decimate on the worker | Rejected: see ADR-0020; the cost is far below a frame |
