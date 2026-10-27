# Powder R factors in the fit result

Status: Accepted

## Context

A fit result held only Rwp and each bank's Rwp and χ², and only a joint fit recorded the bank rows. Users compare
fits with FullProf, which also reports Rp, the expected R, the background-corrected factors and, per phase, the Bragg
R and the structure-factor R. crysta now computes all of them from the calculated pattern (its ADR-0040, `fit_quality`)
and saves them in `analysis.edi`.

## Decision

1. **crysta computes, edi stores.** After a fit, edi asks crysta for the factors (`crysta::fit_quality`) of the fitted
   state and stores them. It computes none itself. Every fit kind records them, a single fit included.
2. **The fields mirror crysta's.** `FitResultRecord` gains `prof_r_factor`, `prof_wr_expected`, `prof_cr_factor` and
   `prof_cwr_factor`, pooled over every fitted point. Each experiment gains the same four beside `fit_prof_wr_factor`
   (`_fit_result_bank`), and each linked structure gains `fit_bragg_r_factor` and `fit_f_r_factor`
   (`_fit_result_phase`, keyed by experiment and structure). All are fractions, and all are optional, so a result saved
   before them loads and saves unchanged.
3. **A scan follows ADR 0034.** A scan saves its template file's factors, as it saves that file's correlations. A
   scan that did not fit its template file records none. Per-file factors belong in the per-file results of ADR 0034,
   not in a store of their own.
4. **Shown in per cent, Rwp first.** The fit results table lists Rwp, Rp, Rexp, cRwp and cRp, then each experiment's
   when the fit covered several, then each phase's R_Bragg and R_F, named by its structure (and experiment when there
   are several). A factor the record does not hold has no row.
5. **A factor that is not a number is none.** A fit over points with no weight or no signal gives a factor that is
   not a number. The record holds none for it, as for a factor it never had: a save leaves it out, a load reads it
   absent, and the table and the reports show nothing for it. The pooled Rwp, reduced χ² and objective value, and
   each experiment's Rwp, are optional for this reason, though a save always wrote them before. An experiment's share
   of the fit is marked by any of its fields, not by its Rwp alone.

## Consequences

- One extra calculation after a single or joint fit, to read the fitted pattern. A scan adds one, after its template
  file.
- The table grows by two rows per phase. A many-phase project gets a long table.

## Alternatives considered

- **Compute the factors in edi.** It would duplicate crysta's apportioning of the observed pattern to reflections and
  could drift from what crysta saves.
- **Save each scan file's factors.** That changes the saved project, which ADR 0034 rules out for correlations; the
  same rule keeps one rule for every saved scan field.
