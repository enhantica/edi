# 0087. Experiment sets and parameters shared across experiments

- **Status:** Proposed
- **Date:** 2026-11-15
- **Implementation:** ⬜ Not implemented
- **Priority:** High
- **Forward constraint (binding on new features):** sharing a parameter across experiments, and sharing phase ratios
  across patterns, write ordinary alias and constraint rows (ADR-0024); edi adds no second kind of tie and never
  decides which parameter is dependent.

## Context

Several experiments of one sample are fitted together: the five bank pairs of a WISH measurement, the six datasets of
taurine, an X-ray and a neutron pattern. Many of their parameters should take one value for all of them (a peak
shape term of identical detectors, a wavelength), while each keeps its own scale. A series of such points
(ADR-0088) has up to 100 experiments per point, so tying them one constraint at a time by hand does not scale. The
owner asked for experiment sets (one template experiment and a table of what each member changes, like a multi-bank
instrument file) and for a "same for all experiments" switch that makes ordinary constraints. Patterns of one sample
should also be able to share their relative phase scales while each keeps its own overall scale.

Prior art surveyed (GSAS-II, Z-Rietveld, RietX, PhaseSmith, Mantid, MAUD, cryspy, CrysFML2008, CCSL, Mag2Pol,
pdffit2, bumps, lmfit, cctbx, EasyScience, diffraction-lib, SasView and the other libraries of the study corpus):

- A shared value is a hard tie that takes the follower out of the free set, never a restraint: GSAS-II's
  equivalences (the first parameter independent, the rest following, their s.u. from the covariance), Mantid's ties,
  CrysFML2008's `EQUAL`, cryspy's marks, MAUD's `setEqualTo`, lmfit's `expr`, SasView's `Mi:p = Mj.p`. Z-Rietveld,
  RietX and PhaseSmith store a shared parameter once instead. Every one keeps a scale per dataset.
- RietX shares everything by default except paths starting `instrument.` or ending `.scale`, with overrides.
- Shared phase ratios with an overall scale per pattern: Z-Rietveld's "Whole" scale mode (a per-histogram scale and a
  common mass ratio varied, the phase scales dependent), MAUD (phase amounts on the sample, an intensity scale on each
  instrument) and pdffit2 (a scale per phase shared by every dataset, a scale per dataset). GSAS-II allows it only by
  hand-written constraints; RietX, PhaseSmith, cryspy and ObjCryst keep a scale per phase per pattern.
- Templates: GSAS-II's multi-bank instrument files and "copy to like histograms", Mantid's bank-to-workspace loaders
  and MAUD's per-bank arrays all end with each dataset holding its own full copy.

## Decision

1. **Experiment sets.** A set has an id, a template experiment and its members (the template is one of them); each
   member is an ordinary experiment with its own file, as now. crysta reads, checks and writes the set (its id is not
   a datablock name; every member exists and belongs to one set). A set is made when several files are loaded as
   separate experiments or as a series of joint fits (ADR-0088), or from existing experiments of one type (Make set…
   in the Experiments group).
2. **What differs.** The Experiments group shows a set as one entry that opens to its members. Its Differences table
   lists, for each member, the values that differ from the template, computed when shown and only for the rows on
   screen; nothing about the differences is stored. Changing a template value offers "Apply to all members", one
   undoable change.
3. **Same for all experiments.** A parameter of an experiment in a set (or of any experiment when the project has
   several and no set) has a "Same for all experiments" switch, in its right-click menu and as a column of the
   Parameters table. On: for every other member, an alias for its parameter and the constraint `<member alias> =
   <leader alias>`, the leader being the set's template (or the first experiment), with generated ids
   (`same_<experiment>_<path>`, the path's dots written as underscores; a taken id gets a numeric suffix). Off: those
   rows are removed. The switch reads as on exactly when
   every member has its row in that form, so a hand edit of one row shows it as off. Each switch is one undoable change
   (ADR-0024 point 8). A parameter is offered only when every member has it.

   *Amended 2026-11-17:* the app does not show the switch for now, neither as a column nor in a menu. The rows it
   writes, the way it reads them back and its undo stay in the code and in files written by hand. The parametric fit
   (a sequential series fitted as one joint fit) will offer it through the Free box, with three states: fixed, free in
   each experiment, free and the same in all.
4. **Phase ratios shared across patterns.** A set's Linked structures group has "Phase ratios shared". On, with `a` the
   leader, `r` its first enabled linked structure and every member linking the same structures: for each other member
   `e` and structure `p ≠ r`, the constraint `s(e,p) = s(e,r) * s(a,p) / s(a,r)` on the linked scales. Each pattern's
   `s(e,r)` stays free as its overall scale; the ratios come from the leader. The reference `r` is the leader's first
   enabled linked structure whose scale is not zero; when every leader scale is zero, or members link different
   structures, the switch refuses with a plain message ("Give a phase of the template a starting scale first"). The
   reference stays the one chosen when the switch was turned on; a fit trial that drives `s(a,r)` to zero makes the
   ratio undefined and is rejected like any trial a constraint cannot evaluate, and a series point that starts from a
   zero reference scale is skipped and listed with that cause. The weight fractions are then the same for every
   member, and so are their s.u., which crysta takes through the constraints from the leader's scales.
5. **Nothing else changes.** The fit, the s.u. of a dependent, the free flags and the refusals are crysta's (ADR-0024).
   crysta fits a constraint from one experiment to another in every joint fit: powder data with one structure or
   several, and single crystals.
   A set is not a fitting mode: a joint fit, an independent fit or a series fits its members as experiments.
6. **Python and the CLI.** `project.experiment_sets.create(id=, template=, members=)`, `ExperimentSet.share(path)`,
   `.unshare(path)`, `.shared` and `.phase_ratios_shared`, each writing or removing the same rows. A CLI user writes the
   rows in the project's text files (the tutorials show them).

## Consequences

- Tying a parameter over 100 experiments is one switch and 99 constraint rows, each visible in the Constraints group.
- A file written by hand with the same rows reads as switched on.
- Overall scales are never forced equal by sharing ratios.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| A sharing map with defaults, as RietX | Rejected: the owner asked for a switch per parameter; a default map would tie parameters the user never chose |
| One stored parameter for a shared value, as Z-Rietveld and RietX | Rejected: crysta keeps every relation in one typed graph already, and a second kind of tie would need its own rules everywhere |
| A new overall-scale parameter per experiment, phase scales shared (Z-Rietveld "Whole") | Rejected: a new parameter in every experiment file and a redundant degree of freedom per pattern; the constraints give the same model on the existing scales |
| Store each member as differences from the template | Rejected: the owner asked that each member stay an ordinary experiment in the file |

## Published sources

- R. B. Von Dreele, *Combined X-ray and neutron Rietveld refinement*, in *The Rietveld Method* (ed. R. A. Young),
  pp. 227–235 (1993), doi:10.1093/oso/9780198555773.003.0012.
- J. Waser, *Least-squares refinement with subsidiary conditions*, Acta Cryst. 16, 1091–1094 (1963),
  doi:10.1107/S0365110X63002929.
- R. J. Hill and C. J. Howard, *Quantitative phase analysis from neutron powder diffraction data using the Rietveld
  method*, J. Appl. Cryst. 20, 467–474 (1987), doi:10.1107/S0021889887086199.
