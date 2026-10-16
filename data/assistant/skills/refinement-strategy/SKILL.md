---
name: refinement-strategy
description: Choose adaptive Rietveld refinement stages, checkpoints, ADP models and mixed-site relationships for an Edi powder-diffraction project.
---

# Adaptive refinement of an actual Edi project

Version: 1.2.1. Scientific guidance for the available Edi APIs and official runtime, not an implemented autonomous controller or a format converter.

## Establish scope and evidence

For an authorized request to create/refine and decide the remaining details, state the bounded plan and proceed within the disclosed working copy and actual runtime permissions. Do not ask again solely because the next free group changes. Ask about missing experiment metadata, ambiguous associations, new chemical assumptions or an expanded objective. Respect actual consent, approval and Stop controls.

Inspect measured intensities, sigma/weights, exclusions, phase links, instrument/profile convention, independent variables and existing relations. Preserve this comparison population and objective across candidates. A file extension does not establish an experiment recipe. Never improve a reported residual by changing observations, uncertainty or exclusions without a separately justified and authorized change.

## Stage, compare and retain

An initial route is scale and peak-position calibration (cell/zero), followed by profile/background and then symmetry-allowed structural coordinates/ADPs. Adapt the groups to the actual misfit and identifiability. Check cell/zero correlation and independent calibration; releasing both does not prove both are determined. Keep known composition and genuine constraints authoritative.

Use a finite budget: a ceiling of 5–10 adaptive group passes is an owner-selected exploration budget, not a convergence criterion. Stop earlier on stable lack of useful improvement, unreliable steps, physical invalidity, cancellation or exhausted resources. Cycle correlated groups when useful, warming from the last accepted state; do not blindly repeat every group. Compare actual result status, convergence, residual, parameter movement, uncertainty and physical plausibility. MAX_ITER/NO_STEP are not convergence; failed/cancelled/unavailable/superseded fits do not authorize the next stage merely because some metrics look good.

Keep separate saved project checkpoints for alternative paths and the accepted best. A fit's pre-fit Undo is not a multi-path checkpoint stack. Native checkpoint/import/save operations must actually be offered before executing this comparison; otherwise report the limitation. Restore the accepted checkpoint after a rejected candidate and verify the loaded observations, weights, exclusions and relations. Retain failed candidates only as explicitly labelled diagnostics.

Holding another group fixed makes a group's uncertainty conditional. When identifiable and supported, finish with a joint fit/covariance of the accepted independent variables. Report unresolved correlation, fixed-variable reasons and conditional uncertainties honestly; alternating groups alone does not establish independence.

## ADPs and mixed sites

Start with an appropriate simpler ADP model. Consider anisotropic ADPs only when site symmetry, resolution, overlap, statistics and systematic-error assessment support the extra independent variables. Use the actual tensor basis and physical positive-semidefinite assessment, uncertainty/covariance and stability. A lower residual or a large raw point count alone is insufficient. If the supported API cannot express the required constraints, report that limitation rather than manufacture an equivalent model.

Before fitting, establish whether different species genuinely co-occupy the same crystallographic site within one phase, and retain the user's intended shared-coordinate/ADP model. For a confirmed mixed site, express the supported shared coordinates/ADPs before refinement, or report the precise API/symmetry obstacle; merely noting the issue is insufficient. Treat occupancy sums/composition separately and preserve known fixed fractions such as 0.5/0.5. Accidental coordinate equality or different phases do not establish a shared site. Confirm allowed independent ADP terms and the actual tensor basis; never tie unrelated parameters or change chemistry silently.

When independently refined, confirmed same-phase co-occupied-site ADPs remain unresolved or have large uncertainty, an authorized delegated refinement suffices to run at least one bounded, physically supported shared-ADP candidate trial from the retained checkpoint. Do not request an additional shared-model preference or routine approval. An explicit user no-sharing/independent-ADP constraint prevails; report that limit rather than override it, and ask only about a genuinely new chemical assumption or scope conflict. Compare the same observations/weights/exclusions and objective, actual status/convergence/improvement, physical validity, stability and jointly assessed covariance. A low residual alone does not select the model; fixing a correlated group does not prove independence. Restore the accepted complete checkpoint if the candidate is rejected. Do not turn every high uncertainty into an equality constraint.

When offered, native `add_relations` supplies an explicit affine alias/constraint batch through the existing SDK validator, live editor and Undo; inspect actual parameter paths and existing relations first. Preserve manual relations and known fixed fractions. That mechanism alone does not implement checkpointed or isolated accepted-best trials: report a missing trial/restore operation rather than using Python or fabricating a successful shared-model comparison. Development API references do not grant a production capability.

## Use real operations

Use the actually offered native `inspect_project`, `list_parameters`, `diagnostics`, `set_parameters`, `set_free` and `run_fit`. They operate on the displayed C++ project. Native edits trigger asynchronous calculation; fit completion is the actual final native report, not a busy flag. No Python runtime/module/source checkout is required or permitted as a production fallback. A live fit can publish partial adopted values and does not implement isolated accepted-best trials. Preserve the actual status, use normal native Stop/Undo and do not promise an unavailable checkpoint/restore/constraint/report operation.

Report the accepted artifact, actual operations/outcomes, rejected alternatives, independent/fixed variables, uncertainty qualifications and unsupported steps. A saved project or converged solver status alone does not prove a scientifically adequate refinement.

References (read relevant sections, not a fixed universal recipe):
- McCusker et al., Rietveld refinement guidelines, sections 5, 7 and 9: https://journals.iucr.org/j/issues/1999/01/00/gl0561/
- GSAS-II constraints (shared ADPs and separate occupancy-sum constraints): https://github.com/AdvancedPhotonSource/GSAS-II-tutorials/blob/main/MDhelp/docs/commontreeitems.md
- IUCr atomic-displacement-parameter nomenclature report: https://www.iucr.org/who-we-are/commissions/commission-on-crystallographic-nomenclature/published-reports/adp
