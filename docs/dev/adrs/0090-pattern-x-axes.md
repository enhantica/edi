# 0090. Pattern x axes: 2θ or TOF, d, Q and sinθ/λ

- **Status:** Accepted
- **Date:** 2026-11-15
- **Implementation:** 🟡 Partially implemented — the four axes in the pattern chart, the Stacked and Map views and the
  report, and a single crystal's reflections on Q and sinθ/λ; the project file saves the native axis and d only, so
  Q and sinθ/λ last for the session; the Meas vs calc tab on the Experiment and Analysis pages
- **Priority:** Medium

## Context

The pattern chart could show a powder pattern on its own axis (2θ or time of flight) or on d-spacing (ADR-0044). Users
compare patterns from different instruments and probes, and expect Q = 4π sinθ/λ and sinθ/λ as well (the owner,
2026-11-14).

## Decision

1. Every axis other than the native one is drawn from the d-spacing capture (ADR-0044): crysta's d column and each
   tick's reflection d. Q and sinθ/λ are conversions of d, Q = 2π/d and sinθ/λ = 1/(2d), in one core function,
   `edi::d_on_axis`, which every pattern chart, scan view and report chart uses. Both fall as d grows, so a converted
   pattern is reversed again and x still ascends.
2. The axis is named by one token set, `native`, `d_spacing`, `q` and `sin_theta_over_lambda`, read and written by
   `edi::pattern_axis_from_token` and `edi::pattern_axis_token`. Titles come from the dictionary where it has an item
   (`d (Å)`, `sin θ/λ (1/Å)`); Q, which it lacks, is titled `Q (1/Å)` and its readouts take the plain number format.
3. The choice is one project setting, `_pattern_chart.x_axis`, shared by the Analysis chart, the scan views and the
   report, as d was. The file names the native axis and d only, so Q and sinθ/λ are kept by the app for the session
   and the file keeps the axis it last saved, until the dictionary names them.
4. As for d, Q and sinθ/λ can be chosen once a calculation has given the experiment a current d column.
5. **A single crystal on Q or sinθ/λ** (the owner, 2026-11-16). Its reflections become a pattern
   (`edi::single_crystal_pattern`): each at its sinθ/λ converted by `d_on_axis` with d = 1/(2 sinθ/λ), sorted by x,
   measured and calculated F² (or F, with s.u. su / (2F)), the residual, and the linked structure's ticks with their
   h k l. The pattern chart draws it in the powder layout and colours (calculated red, ticks in the structure's
   colour), with its own F | F² setting and one more measured style, **Bars**: one calculated bar per reflection, red
   outline filled in the structure's colour, 0.012 Å⁻¹ wide in Q (the same width in sinθ/λ), so they widen when
   zoomed in, with the measured values as points with their error bars; a toolbar toggle draws the bars as one-pixel
   lines at any zoom. Contributions are named by the structure, with the powder chart's icons. The residual is drawn as bars from zero. Without measured reflections the
   calculated ones are drawn as bars with their ticks.
6. **Meas vs calc** (the owner, 2026-11-16): measured against calculated, with the y = x line, for a single crystal per
   reflection (F or F², its existing comparison chart) and for a powder per data point (`MeasCalcChart`,
   `ExperimentViewModel::measCalcPoints`). It is its own main-view tab, right after Pattern on the Experiment and
   Analysis pages, with its own settings, and is disabled until the shown experiment has measured and calculated
   values. The single-crystal Pattern tab's x box offers Q and sinθ/λ only.

## Consequences

- One conversion: a chart, a scan view and the report cannot disagree on where a point or tick lies.
- Saving Q or sinθ/λ in the project needs only the two tokens in crysta's dictionary; nothing in edi's drawing changes.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| Converting from 2θ with the wavelength (or TOF with DIFC) in each chart | Rejected: d already carries the calibration crysta applied, and a second conversion could disagree with it |
