# 0107. Shared parameters and the parametric fitting mode

- **Status:** Proposed
- **Date:** 2026-11-26
- **Implementation:** 🟡 In progress
- **Priority:** High

Amends [ADR-0087](0087-experiment-sets-and-shared-parameters.md) point 3 (its 2026-11-17 amendment: the Free box does
not become three-state; Shared is its own column) and [ADR-0089](0089-series-views-shared-and-per-experiment.md) point 1 (the Shared section).
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
   - The Parameters table shows a Shared column beside Free in the Parametric and Joint modes only.
   - A ▾ menu on its title shares or unshares the shown rows, or only the peak profile and instrument rows, as one undo
     step.
4. **Groups.**
   - In a scan, a parameter is shared across the points (per bank in a series of joint fits).
   - In a joint fit, the same parameter is shared across every experiment, stored under the first experiment holding it.
   - A shared group has one value and one Free flag: editing either on any member changes all members, as one undo
     step.
   - A parameter set by a constraint or by symmetry cannot be shared.
5. **Values.** Checking Shared sets every member to the value shown. Unchecking leaves each member that value as its
   own.
6. **File.** `analysis.edi` keeps the shared names in one `_parametric_fit_shared` loop, written in every mode when not
   empty. Nothing is written as alias or constraint rows. Loading drops names the project does not hold or that a
   relation sets, and gives a group its first member's Free flag.
7. **Evolution and sets.**
   - In a series of joint fits, a bank parameter tied the same for all banks is listed once under Shared, read from its
     first bank's rows.
   - "Compare with" draws a second parameter on a right axis.
   - Past ten banks, Per bank opens as a map (one row per bank, colour the value) with a switch to curves for chosen
     banks.
   - The Experiment page lists, for each experiment set, the values each member holds that differ from the template.

## Consequences

- The "Same for all experiments" switch of ADR-0087 point 3 stays hidden; Shared in Joint mode takes its place without
  writing constraint rows.
- A fit in the Parametric mode, and a Joint fit with shared parameters, refuse until crysta's solver supports them.

## Alternatives considered

| Alternative | Verdict |
| --- | --- |
| A three-state Free box | Rejected by the owner: two checkboxes are clearer, and Shared can apply to a fixed value |
| Shared implies Free | Rejected by the owner: a fixed common value is useful |
| A sharing mark in the s.u. brackets | Rejected: not CIF |
