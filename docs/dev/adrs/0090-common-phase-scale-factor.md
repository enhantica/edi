# 0090. The common phase-scale factor

- **Status:** Accepted
- **Date:** 2026-11-16
- **Implementation:** ✅ Implemented
- **Priority:** High

## Context

A new experiment starts with its phase scales at 1, and its calculation can be orders of magnitude away from the
data. A fit from there spends its first steps on the scale and can stop in a false minimum. crysta computes one
factor per experiment, k = Σ w (y_obs − y_bkg) y_calc / Σ w y_calc², with the background held (powder and single
crystal alike; for a single crystal over the merged reflections the fit uses, ADR-0091). edi decides when to apply it.

## Decision

1. **When.** Measured data loaded into an experiment, and a phase added, removed, switched on or off or replaced. A
   saved project is never rescaled on opening, so it fits as it did when saved.
2. **What.** Every enabled phase scale of the experiment is multiplied by k, so their ratios stay; a disabled link
   keeps its scale. No change without measured data, when the calculation is zero or when k is not finite and
   positive; an experiment with measured data then lists one line in Messages saying its scales were left as they
   were.
3. **One undo step.** `edi::Edit::rescaled` runs the triggering edit and then the factor. A phase change's undo
   restores every link with its scale; Load data's undo restores the experiment as it was.
4. **Where.** `edi::common_scale_factor` and `edi::apply_common_scale` (core) wrap crysta's factor; the app wraps
   its phase controls and Load data with `rescaled`.

## Consequences

- A calculation lands on the data's level in one step, and phase ratios set by hand survive.
- A background far from the data shifts k; the next fit corrects both.
- One calculation per triggering edit, never inside a fit.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| Fit every phase scale jointly | Rejected: it changes the ratios a user set, and a phase absent from the data goes to zero. |
| Rescale on project open | Rejected: a saved project must fit as it did when saved. |
| Fit the background with k | Rejected: the background stays as it is. |
