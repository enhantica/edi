---
name: project-assistance
description: Inspect actual project context and propose bounded approved work.
---

# Review an Edi project before changing it

Version: 1.1.0. This is guidance for the tools actually offered in the current request, not an authority to add tools or approve edits.

Read the current revision-bound project/structure/dataset/parameter/constraint context. Use `inspect_project`, `list_parameters` and `diagnostics` where available. A missing project, measured dataset or valid uncertainty is a missing prerequisite, not permission to invent it. Use `read_selected_file` only for explicitly selected text and ask for missing companions; typing a path does not select a file. Unsupported conversion remains unsupported.

Clarify the scientific goal and the intended datasets/phases, then inspect the pattern, difference curve, range, exclusions, weights, free variables and declared dependencies before recommending a change. Explain relevant uncertainty and correlations. Do not infer a chemical constraint from correlation alone or prescribe a universal refinement order.

Propose one small reviewable plan with actual parameter paths/groups, comparable objective and explicit iteration/trial/time budget. Only the real user can approve it. Existing fixed flags, affine relations, bounds, uncertainties, accepted results and selected observations remain authoritative. Do not change data, weights or exclusions merely to improve a residual.

After actual approval, use only offered typed edit/trial tools. Retain the accepted state, operate on the one isolated candidate and compare genuine results on the same objective/population/settings. Report a failed/cancelled/unavailable result truthfully; do not manufacture improvement, convergence or a report. Reject/discard unsuccessful candidates and preserve the accepted best. Ask the user when a scientific prerequisite is unclear. Stop/retirement/currentness/retention checks always take precedence over a skill suggestion.

Before claiming completion, identify what actually ran, what changed, the actual observed result, what was retained or rejected and what remains unsupported. Current tools do not provide a general FullProf/GSAS converter, arbitrary filesystem access or scan artifact publication. A selected skill does not grant those capabilities.

References:
- IUCr Rietveld refinement guidelines: https://journals.iucr.org/j/issues/1999/01/00/gl0561/
- GSAS-II sequential-refinement worked tutorial: https://advancedphotonsource.github.io/GSAS-II-tutorials/SeqRefine/SequentialTutorial.htm

## Generic official-runtime edition

When Edi actually supplies the generic runtime, its supported shell/file tools replace the restricted manifest calls above. Inspect the runtime's actual capabilities; do not invent tools named after these prose steps. Operate on Edi's disclosed owned working copy, retain original inputs and accepted checkpoints. A user request to create/refine with the remaining choices delegated is authorization to choose and execute scientifically justified free groups within that objective and the actual runtime permissions. State a bounded working plan and proceed; do not demand new approval for every ordinary group or fit. Ask when a missing scientific prerequisite, changed objective or new chemical assumption needs a user decision. The restricted typed-tool compatibility path above still requires its real plan-approval mechanism; guidance never bypasses a runtime approval or consent boundary. Consult the relevant refinement-strategy skill for adaptive staging, covariance and mixed-site decisions. Existing installed Edi supports `python -m edi calc PROJECT --dry --report machine`, `fit PROJECT --report machine --stream`, `undo PROJECT`, and `report PROJECT --check`. Fit writes its working project by default; it is not a harmless inspection command. Never run it on the original project as an exploratory probe.

For an actual CIF plus raw diffraction measurement, reuse `edi.StructureFactory.from_cif_path` and `edi.ExperimentFactory.from_data_path`. Raw supported input is x/y/optional sigma; the actual reader skips nonnumeric rows, drops nonpositive y, supplies missing uncertainty and sorts/deduplicates x as documented by that factory. Explain those changes instead of promising byte-for-byte data interpretation. Ask for sample form, beam mode, radiation, scattering type, wavelength or TOF calibration, peak profile/background and phase associations when missing. A `.dat` extension alone does not identify them.

The companion `create_from_selected.py` is a reference API composition, requiring an explicit validated experiment recipe and a new output directory. It is not a FullProf/GPX converter, does not run refinement, and has not yet been executed in the prototype. The runtime may inspect/run it only inside the owned workspace after prerequisites are genuine. Use `Project.load` to reopen the saved candidate and the existing machine calc report to verify a real calculation before claiming readiness. Final display/publication in the open application remains the host's separately approved current-owner boundary.
