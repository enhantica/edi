# 0081. Independent fits per experiment

- **Status:** Accepted
- **Date:** 2026-11-09
- **Implementation:** ✅ Implemented
- **Priority:** High

## Context

The Co₂SiO₄ example fits the crystal at 300 K, 55 K and 2.5 K: three structures, each linked to its own single-crystal
dataset. No fitting mode took that project. `single` takes one experiment, `joint` fits single crystals over one
structure, and `independent` was a scan mode, one experiment fitted to each file of a folder. The owner chose fits that
are independent in every respect, each with its own goodness of fit, s.u. and result. crysta records the engine side.

## Decision

1. In the `independent` mode, a project without a scan (`_sequential_fit`) fits each experiment alone against the
   structures it links. With a scan declared, `independent` stays the scan mode; `single`, `joint` and `sequential` are
   unchanged.
2. Each fit is a single fit of a copy of the project holding that experiment and its structures, so it reports and
   records exactly what a single fit does. Every copy is taken before the first fit, so all start from the same values.
   The copies' values, s.u. and fit starts, each experiment's own share of the fit (`_fit_result_bank`) and its fitted
   background are written back only once every fit has succeeded; a refused or cancelled fit leaves the project as it
   was. A structure linked by two experiments is refused by name, since it cannot hold two results; joint mode fits
   it. An experiment with nothing free is not fitted and keeps its values, so a staged tutorial can fit one
   experiment at a time; a run with nothing free anywhere is refused. Each copy keeps only its own aliases and
   constraints: an alias goes with the experiment whose structures or data hold its parameter, and an enabled
   constraint with the experiment of the aliases crysta's constraint parser finds in it (its left-hand alias and the
   references on its right, so a number such as `1e-3` names no alias). A constraint naming aliases of two
   experiments ties their fits and is refused by name before any fit, as is a constraint using an alias of no
   experiment. A disabled constraint adds no relation and is left out; one that does not parse, or names no alias,
   goes to every fit, whose own checks report it; an unused alias of no experiment is dropped.
3. The project's `_fit_result` describes the run: success when every fit succeeded, the iterations, points and free
   parameters summed, the reduced χ² pooled over every experiment, and a message naming each experiment with its own
   reduced χ². Its correlations are each fit's own, side by side. Its iteration history is every fit's in project
   order, numbered on from the previous fit's, so a full machine record carries it.
4. The surfaces: `project.analysis.fit()` and `python -m edi fit` route a project like this to `fit_independent`, which
   prints and streams each experiment's fit as a single fit. The app offers `joint` and `independent` for a project of
   several experiments, `joint` staying the default. A project file saying `independent` without a scan now loads.

## Consequences

- A project of several structure and dataset pairs fits from every interface in one action.
- Each experiment's quality is read from its own bank row and the message; the pooled values describe the run.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Delegate the loop to crysta's `fit_project` | Rejected for now: edi drives its own fits so it can stream iterations and record its own result; the loop here mirrors crysta rather than calling it. |
| Seed each fit from the previous one | Rejected: that is a sequential scan; independent fits share only their start. |
