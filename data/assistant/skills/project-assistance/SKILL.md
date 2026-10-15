# Review an Edi project before changing it

Version: 1.0.0. This is guidance for the tools actually offered in the current request, not an authority to add tools or approve edits.

Read the current revision-bound project/structure/dataset/parameter/constraint context. Use `inspect_project`, `list_parameters` and `diagnostics` where available. A missing project, measured dataset or valid uncertainty is a missing prerequisite, not permission to invent it. Use `read_selected_file` only for explicitly selected text and ask for missing companions; typing a path does not select a file. Unsupported conversion remains unsupported.

Clarify the scientific goal and the intended datasets/phases, then inspect the pattern, difference curve, range, exclusions, weights, free variables and declared dependencies before recommending a change. Explain relevant uncertainty and correlations. Do not infer a chemical constraint from correlation alone or prescribe a universal refinement order.

Propose one small reviewable plan with actual parameter paths/groups, comparable objective and explicit iteration/trial/time budget. Only the real user can approve it. Existing fixed flags, affine relations, bounds, uncertainties, accepted results and selected observations remain authoritative. Do not change data, weights or exclusions merely to improve a residual.

After actual approval, use only offered typed edit/trial tools. Retain the accepted state, operate on the one isolated candidate and compare genuine results on the same objective/population/settings. Report a failed/cancelled/unavailable result truthfully; do not manufacture improvement, convergence or a report. Reject/discard unsuccessful candidates and preserve the accepted best. Ask the user when a scientific prerequisite is unclear. Stop/retirement/currentness/retention checks always take precedence over a skill suggestion.

Before claiming completion, identify what actually ran, what changed, the actual observed result, what was retained or rejected and what remains unsupported. Current tools do not provide a general FullProf/GSAS converter, arbitrary filesystem access or scan artifact publication. A selected skill does not grant those capabilities.

References:
- IUCr Rietveld refinement guidelines: https://journals.iucr.org/j/issues/1999/01/00/gl0561/
- GSAS-II sequential-refinement worked tutorial: https://advancedphotonsource.github.io/GSAS-II-tutorials/SeqRefine/SequentialTutorial.htm
