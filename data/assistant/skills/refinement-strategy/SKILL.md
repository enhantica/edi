---
name: refinement-strategy
description: Choose adaptive Rietveld refinement stages, checkpoints, ADP models and mixed-site relationships for an Edi powder-diffraction project.
---

# Adaptive refinement of an actual Edi project

Version: 1.0.0. Scientific guidance for the available Edi APIs and official runtime, not an implemented autonomous controller or a format converter.

## Establish scope and evidence

For an authorized request to create/refine and decide the remaining details, state the bounded plan and proceed within the disclosed working copy and actual runtime permissions. Do not ask again solely because the next free group changes. Ask about missing experiment metadata, ambiguous associations, new chemical assumptions or an expanded objective. Respect actual consent, approval and Stop controls.

Inspect measured intensities, sigma/weights, exclusions, phase links, instrument/profile convention, independent variables and existing relations. Preserve this comparison population and objective across candidates. A file extension does not establish an experiment recipe. Never improve a reported residual by changing observations, uncertainty or exclusions without a separately justified and authorized change.

## Stage, compare and retain

An initial route is scale and peak-position calibration (cell/zero), followed by profile/background and then symmetry-allowed structural coordinates/ADPs. Adapt the groups to the actual misfit and identifiability. Check cell/zero correlation and independent calibration; releasing both does not prove both are determined. Keep known composition and genuine constraints authoritative.

Use a finite budget: a ceiling of 5–10 adaptive group passes is an owner-selected exploration budget, not a convergence criterion. Stop earlier on stable lack of useful improvement, unreliable steps, physical invalidity, cancellation or exhausted resources. Cycle correlated groups when useful, warming from the last accepted state; do not blindly repeat every group. Compare actual result status, convergence, residual, parameter movement, uncertainty and physical plausibility. MAX_ITER/NO_STEP are not convergence; failed/cancelled/unavailable/superseded fits do not authorize the next stage merely because some metrics look good.

Keep separate saved project checkpoints for alternative paths and the accepted best. The CLI's undo is a single pre-fit snapshot, not a multi-step checkpoint stack. Restore the accepted checkpoint after a rejected candidate and verify the loaded observations, weights, exclusions and relations. Retain failed candidates only as explicitly labelled diagnostics.

Holding another group fixed makes a group's uncertainty conditional. When identifiable and supported, finish with a joint fit/covariance of the accepted independent variables. Report unresolved correlation, fixed-variable reasons and conditional uncertainties honestly; alternating groups alone does not establish independence.

## ADPs and mixed sites

Start with an appropriate simpler ADP model. Consider anisotropic ADPs only when site symmetry, resolution, overlap, statistics and systematic-error assessment support the extra independent variables. Use the actual tensor basis and physical positive-semidefinite assessment, uncertainty/covariance and stability. A lower residual or a large raw point count alone is insufficient. If the supported API cannot express the required constraints, report that limitation rather than manufacture an equivalent model.

For species occupying the same crystallographic site within one phase, inspect whether shared coordinates/ADPs represent the intended model. Treat occupancy sums/composition separately. Preserve known fixed fractions such as 0.5/0.5 and existing affine relations. Accidental coordinate equality or different phases do not establish a shared site; do not tie every atom parameter to one variable or silently change chemistry. Confirm the actual site's allowed degrees of freedom before assigning anisotropic terms.

## Use real operations

Use the installed `edi` module with the actual configured extension. Existing `edi.Project.load(path)`, `project.save_as(new_path)` and `project.fit(on_iteration=...)` compose ordinary owned checkpoints and fitting; inspect the returned status and `converged` before continuing. The existing CLI supports `python -m edi calc PROJECT --dry --report machine` and `fit PROJECT --report machine --stream`; fit saves its working project on success. Run exploratory fits only on owned candidates. The shipped `examples/fit_lbco_hrpt.py` is one genuine two-stage public-API example, not a universal free set or chemical model. Do not use its output-parity reference as starting values or a scientific-quality target.

Report the accepted artifact, actual operations/outcomes, rejected alternatives, independent/fixed variables, uncertainty qualifications and unsupported steps. A saved project or converged solver status alone does not prove a scientifically adequate refinement.

References (read relevant sections, not a fixed universal recipe):
- McCusker et al., Rietveld refinement guidelines, sections 5, 7 and 9: https://journals.iucr.org/j/issues/1999/01/00/gl0561/
- GSAS-II constraints (shared ADPs and separate occupancy-sum constraints): https://github.com/AdvancedPhotonSource/GSAS-II-tutorials/blob/main/MDhelp/docs/commontreeitems.md
- IUCr atomic-displacement-parameter nomenclature report: https://www.iucr.org/who-we-are/commissions/commission-on-crystallographic-nomenclature/published-reports/adp
