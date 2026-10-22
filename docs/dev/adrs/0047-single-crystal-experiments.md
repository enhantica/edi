# 0047. Single-crystal experiments

- **Status:** Proposed
- **Date:** 2026-10-22
- **Implementation:** 🟡 Partially implemented — constant-wavelength single crystals load, calculate, fit, save and
  show their chart and table; loading reflection files into a new experiment, the Python surface and time of flight
  are pending
- **Priority:** High

## Context

crysta computes single crystals: measured reflections instead of a pattern, F²calc = scale · y · |F|² per reflection
with a Becker–Coppens extinction y, and a fit of F² weighted by 1/su². edi reads and shows experiments itself and asks
crysta to calculate them (ADR-0003), so a single crystal needs a model, a reader and views here too.

## Decision

1. **Model.** An experiment whose `_experiment_type.sample_form` is `single crystal` holds `reflections` (h, k, l, the
   measured F² and its su, a wavelength per reflection for time of flight, and the calculated F² with d and
   sinθ/λ beside them) and `extinction` (type, model, radius, mosaicity). It has no `data` pattern, profile,
   background, excluded regions, absorption or preferred orientation.
2. **File.** The reader takes the `_refln` loop's measured columns and the `_extinction` category; the save goes
   through crysta's writer as every save does.
3. **Calculation and fit.** The adapter converts a single crystal to crysta's single-crystal form; a calculation
   publishes the calculated F² per reflection, and a fit runs crysta's single-crystal residual.
4. **Views.** For a single crystal the Experiment and Analysis pages show, where the pattern chart was, a chart of
   F²calc against F²meas (each reflection a point with its su bar, and the y = x line) over a table of h, k, l,
   F²meas, su, F²calc and (F²meas − F²calc)/su. The sidebar shows Extinction and leaves out the pattern-only groups.

## Consequences

- A single crystal is one more experiment kind in the same project shape; the pattern paths check for it first.
- Its examples join the app's example list as refinements.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| A separate experiment class in a heterogeneous collection | Deferred: every holder of the experiment collection would change, with nothing gained in what is shown |
| Draw the chart in the pattern chart component | Rejected: its axes, series and toolbar are a pattern's; a scatter of two intensities shares little with them |
