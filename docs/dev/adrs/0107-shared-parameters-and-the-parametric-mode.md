# 0107. Shared parameters and the parametric fitting mode

- **Status:** Proposed
- **Date:** 2026-11-26
- **Implementation:** 🟡 In progress
- **Priority:** High

Amends [ADR-0087](0087-experiment-sets-and-shared-parameters.md) point 3 (its 2026-11-17 amendment: the Free box does
not become three-state; Shared is its own column) and [ADR-0089](0089-series-views-shared-and-per-experiment.md) point 1 (the Shared section, now named Common).
crysta's [ADR-0136](https://github.com/enhantica/crysta/blob/main/docs/dev/adrs/0136-parametric-fit-of-a-series.md)
holds the solver and the file format.

## Context

A temperature scan can be fitted as one fit in which chosen parameters take one value for every pattern, and a joint fit
can take one value for a parameter across its experiments. Programs that do this mark sharing as a tie by name or
equality (TOPAS, GSAS-II, FullProf, Jana); general fitting tools put a Share column beside Fixed (Origin, Mantid, Igor).

## Decision

1. **Two independent flags.** A parameter is fixed or free, and per pattern or shared. The four combinations are all
   valid. In Python, `p.free` and `p.shared` are booleans that never change each other.
2. **Mode.** The Fitting mode selector offers "Parametric: all as one fit" where a scan is declared, beside Sequential and
   Independent.
3. **Where it is offered.**
   - The Parameters table shows a Shared column, left of Free, in the Parametric and Joint modes only, so Free keeps its
     place at the table's right edge (owner record 1b0c100d3).
   - The Shared title is a copy of Free's: its ▾ menu shares or unshares the shown rows (Shared, Not shared, and Mixed
     when they differ), as one undo step.
   - Any parameter a fit can vary can be shared, the scale and the background included.
4. **Groups.**
   - In a scan, a parameter is shared across the points (per bank in a series of joint fits).
   - In a joint fit, the same parameter is shared across every experiment, stored under the parameter Shared was
     ticked on. That row stays in the Analysis table and carries the group; the other members' copies leave it, as a
     user constraint's dependents do (owner records 1b0c100d3, 61961fe49).
   - A parameter that is not in every experiment cannot be shared: its Shared box is disabled and says so.
   - A shared group has one value and one Free flag: editing either on any member changes all members, as one undo
     step.
   - In a joint fit, a parameter with no copy in another experiment (every structure parameter, or one only one
     experiment holds) is already one value for all experiments: its Shared box is disabled and says so. In a scan every
     point has its own copy, so structure parameters keep the box.
   - Shared never adds, changes or removes a user constraint. A parameter any of whose copies a user constraint sets
     (a dependent) cannot be shared: its Shared box is disabled and its tooltip names the constraint, as Free does for
     a parameter it cannot free. To share it, the user removes the constraint first.
5. **Values.** Checking Shared sets every member to the value of the row it was checked on. Unchecking leaves each
   member that value as its own.
6. **File.** `analysis.edi` keeps the shared names in one `_parametric_fit_shared` loop, written in every mode when not
   empty. Nothing is written as alias or constraint rows. Loading drops names the project does not hold or that a
   relation sets, and gives a group the listed parameter's value and Free flag (owner record 61961fe49).
7. **Evolution.**
   - A parameter shared across the series has one value, so it is not offered as a curve.
   - In a series of joint fits, a parameter of every experiment tied the same for all is listed once under Common,
     read from its first experiment's rows.
   - The words follow the app's: Evolution's box reads "Common" / "Per experiment", and the selector above the charts
     names experiments, never banks.

8. **Colours** (owner records 1b0c100d3, 8b4e6f965). Free check boxes take the free value's green; Shared's check boxes
   and its values on every page and popup are indigo; a value a user constraint computes is magenta on every page that
   shows it (the Analysis page hides those rows). Each has a light and a dark tone and does not depend on the palette.
9. **Sidebar** (owner record 453d6ae49). While the table shows Shared, the sidebar's Auto and Full widths grow by that
   column, from the same width rule, so no other column gives way.
10. **A running fit.** A Parametric fit redraws the selected pattern, Meas vs calc and Evolution from each iteration
    (at most four times a second, the last always); the status bar shows its iterations and joint χ², and the results
    window its one outcome, never files converged or failed.

## Consequences

- The "Same for all experiments" switch of ADR-0087 point 3 stays hidden; Shared in Joint mode takes its place without
  writing constraint rows.
- A Joint fit hands crysta each shared group as equality ties `<member> = <leader>`, built for that fit only and never
  saved or listed with the user's constraints; the result is the constrained fit's.
- The Parametric fit of a scan of one experiment is crysta's (its ADR-0136); a series of joint fits with shared
  parameters refuses until crysta supports it.
- The owner's checks of the app removed what the first design added beside Shared: the Differences group, a second
  axis and "Compare with" in Evolution, and the many-bank map (records of 2026-11-26).

## Alternatives considered

| Alternative | Verdict |
| --- | --- |
| A three-state Free box | Rejected by the owner: two checkboxes are clearer, and Shared can apply to a fixed value |
| Shared implies Free | Rejected by the owner: a fixed common value is useful |
| A sharing mark in the s.u. brackets | Rejected: not CIF |
