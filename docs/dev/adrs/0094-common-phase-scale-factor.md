# 0094. The common phase-scale factor

- **Status:** Accepted
- **Date:** 2026-11-16
- **Implementation:** ✅ Implemented
- **Priority:** High

## Context

A new experiment starts with its phase scales at 1, and its calculation can be orders of magnitude away from the
data. A fit from there spends its first steps on the scale and can stop in a false minimum. crysta computes one
factor per experiment. For a powder it matches peak heights, k = (max y_obs − baseline) / max (y_calc − y_bkg), the
baseline the 10th percentile of the measured points and y_calc all phases together: when data are first loaded the
background, cell, zero shift or wavelength is usually still off, and a least-squares factor then left the calculation
far below the data (the owner, 2026-11-17). For a single crystal it is the weighted least-squares factor over the
merged reflections the fit uses (ADR-0095). crysta also returns how well the calculated and measured powder peaks
overlap. edi decides when to apply it.

## Decision

1. **When.** Measured data loaded into an experiment, or the explicit Estimate action. Phase membership/target/enabled
   edits request one preview and keep the entered scales (amended 2026-11-19, feedback 93). A
   saved project is never rescaled on opening, so it fits as it did when saved.
2. **What.** Every enabled phase scale of the experiment is multiplied by k, so their ratios stay; a disabled link
   keeps its scale. No change without measured data, when the calculation is zero or when k is not finite and
   positive; an experiment with measured data then lists one line in Messages saying its scales were left as they
   were. A powder without background points first gets one line-segment point at the measured baseline, said in
   Messages; an existing background, or an automatic one, is never replaced.
3. **Peaks that miss.** When the calculated and measured powder peaks overlap by less than one half, Messages warns
   and names the likely causes: the wavelength, the zero shift and the cell.
4. **Estimate.** A button beside Add linked structure, styled as the Background group's Estimate, applies the factor
   again on its own.
5. **One undo step.** `edi::Edit::rescaled` runs the triggering edit and then the factor. A phase change's or
   Estimate's undo restores every link with its scale and the background points; Load data's undo restores the experiment as it was.
6. **Where.** `edi::common_scale_factor` and `edi::apply_common_scale` (core) wrap crysta's factor; the app wraps
   its phase controls and Load data with `rescaled`.

## Consequences

- A calculation lands on the data's level in one step, and phase ratios set by hand survive.
- The tallest point sets a powder's k, so noise on it moves k by its own size; the next fit corrects it.
- One forward calculation per phase edit, never a synchronous scale-estimate calculation before the preview.
- Widget formatting uses input-only spelling validation. Save, Text and export keep full computed-output validation;
  displaying fields cannot trigger TOF pattern calculations. Both ordinary and deferred widget publication use it.
- Superseded previews keep the existing latest-wins protocol: one job in flight, its token cancelled and result
  rejected, then only the newest owed state admitted. The engine's single forward call has no cancellation callback,
  so an already running call completes before rejection; it is never overlapped with another preview.
- Regression: `edi_linked_structure_calculation_tests` adds a phase to a Linux TOF powder project and compares actual
  engine work with one forward calculation. The gdb fixture counts engine calls, including internal spelling calls.
  Before the fix: four engine calls (168 structure-factor evaluations against a 56-evaluation forward control).
  The fourth call reused structure factors, so the gdb count is the authoritative calculation count.
  Source: `app/tests/linked_structure_calculation_tests.cpp` and `tests/fixtures/linked_structure_work/`;
  local debugger receipt: `~/runs/e04-t50/hotfix-link-gdb15.log`.
  After the fix the same gdb fixture records one engine call; parses stay at 23 for input validation/conversion,
  while loop renders fall from 43 to 30. Receipts: `~/runs/e04-t50/hotfix-link-count-red.log` and
  `~/runs/e04-t50/hotfix-link-count-green.log`. The native replay checks identical calculated points (including
  excluded-point NaNs) against the independent forward result. Repeated successful `gdb -p` snapshots of the
  pre-fix link action enter `compute_pattern_beba_variant` (`~/runs/e04-t50/hotfix-link-attach.log`).

## Alternatives considered

| Alternative | Verdict |
|---|---|
| Fit every phase scale jointly | Rejected: it changes the ratios a user set, and a phase absent from the data goes to zero. |
| Rescale on project open | Rejected: a saved project must fit as it did when saved. |
| Fit the background with k | Rejected: the background stays as it is, apart from the one starting point. |
| A least-squares factor for a powder | Rejected by the owner (2026-11-17): where peaks miss it scales the calculation toward zero. |
| The ratio of integrated intensities | Rejected by the owner (2026-11-17): without a background the measured baseline inflates the sum. |
