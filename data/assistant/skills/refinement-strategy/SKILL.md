---
name: refinement-strategy
description: Choose and revise a refinement strategy from actual model, data, native eligibility and scientific references.
---

# Refine from current evidence

Version: 1.6.2. Follow the user's goal, supplied constraints and actually offered
operations. This is a decision loop, not a fixed recipe, family, stage count or
target statistic. Explicit user groups/subsets/order/flags override delegated
planning; native eligibility and ownership still apply.

## Core workflow

1. **Establish essentials, then wait if needed.** Inspect the current project and
   small attachment/header portions. Use the native reader for supported format,
   columns and sigma; ask about those only after a real loading failure or genuine
   ambiguity. If probe, wavelength or TOF calibration is missing/conflicting, show
   Assistant and use offered structured questions; wait for the actual answer.
   Without that flow, issue a FINAL question and END the turn. Do no creation,
   import, independent structure preparation, setup, refinement or Save meanwhile.

2. **Find the dominant current mismatch efficiently.** Start broad numerical
   assessment with offered `inspect_data view=summary` and suitable explicit
   positive partitions. Reuse unchanged measured/sigma/geometry facts. Read exact
   peak-containing measured/calculated/residual windows and separate Bragg rows
   for unresolved positions/shape; off-peak windows assess baseline ONLY. For SC,
   inspect relevant F-squared/intensity dependence. Request complete raw arrays
   only for an explicit request or a detailed diagnostic that needs them, not
   merely because a fit ran. All exact raw data remain available without a quota.
   Check units, weighting, exclusions, native row mapping and current/adopted
   calculation availability. Summaries are neither peak assignments, fit metrics,
   total-width validation nor correlation evidence.

3. **Introduce the implicated group; retain accepted work.** Resolve observed
   position mismatch with eligible cell/offset/scale and supplied wavelength
   anchored before widths or ADPs absorb it. Assess baseline bias before ADPs;
   Estimate alone is not validation. Establish baseline evidence before profile
   interpretation.
   Keep accepted useful eligible free groups in the fit by default while adding
   ONE new unvalidated group. Introduce background/profile and coordinate/ADP
   blocks separately: assess the first new block before adding the other, with
   the other UNVALIDATED block fixed. Already accepted groups remain cumulative.
   Hold an accepted group only for explicit user/calibration/native-dependence
   requirements or a stated diagnostic based on observed correlation, confounding
   or instability; keep that comparison restorable. Do not routinely freeze and
   re-release successful groups, or require a final fixed/free sweep or extra fit.
   Collect intended eligible members across sites BEFORE constructing flags;
   finish one category/subset rather than alternate categories atom by atom.
   Use one exact uniform eligible group request when justified. Read the COMPLETE
   actual free population: set_free changes listed flags only, not omitted flags.
   No group-first order, all-free background stage or sharing rule is universal;
   explicit user groups/subsets/order/flags and automatic-background ownership win.

4. **Assess before spending the next Undo.** Reconcile actual prerequisite replies
   and settle calculation before fitting. Read returned status/adopted FIRST.
   Only an adopted outcome establishes this candidate as live work; adopted
   cancellation can retain a partial result. Refused/error/superseded or unadopted
   attempts do not adopt that candidate: reconcile the actual current state.
   Inspect actual changes, CURRENT peak/baseline residuals, total widths and SUs.
   If the adopted trial is unacceptable, use genuine latest-fit Undo while still
   available, then promptly diagnose a restorable simpler supported candidate of
   the implicated factor. Do not wander into unrelated groups to repair it.
   Stall/no_step/rejection needs fresh evidence, eligibility and anchor diagnosis;
   a parameter list, lower objective, convergence, positive ADPs or absent errors
   is not adequacy. Weakly identified quantities need a physically justified
   comparison OR an explicit unresolved limitation. Undo is not selective reversal
   or a checkpoint bank, does not restore flags, and a refused/unadopted attempt
   cannot justify undoing earlier accepted science. Fixing retains current values.

5. **Preserve useful work and state an honest endpoint.** Continue justified work
   or name the specific incomplete evidence/capability/quantities. Restricted
   convergence or negative-ADP Undo alone is not completed structure refinement;
   diagnose large reduced chi-square rather than force it to one. Save/Report may
   preserve scientifically limited work. After ordinary Save inspect authoritative
   saved/adopted values/SUs and current residuals; label old trial statistics
   pre-Save unless an offered metric actually belongs to the saved model. Use
   native `file_value ± file_su` verbatim with units, never reconstructed digits.
   Keep scientific caveats public; app/tool/skill improvements go ONLY through
   offered `diagnostics.developer_feedback` to the hidden diagnostic work report.

## Scientific references and exceptions

### Starts and native conventions

Preserve provenance, comparable objectives/observations, composition, symmetry,
genuine calibration and user flags. Defaults, including zero and initial free
flags, are starts rather than user constraints. For a new CW task needing alignment,
try the eligible joint alignment group before another offset start. Only observed
stall/rejection justifies a data-supported alternative; never import specimen,
tutorial or online fitted seeds or broaden displacement to absorb position error.

For matching offered CW families, Crysta f6e737d3aa45c0b1c01cb7b741e606cdff08d8a6
(src/core/cwl_profile.hpp, profile_chains.hpp and
include/crysta/peaks/cwl_pseudo_voigt.hpp) defines:

- Gaussian H_G² = U tan²(theta) + V tan(theta) + W.
- TCH Lorentz H_L = X tan(theta) + Y/cos(theta).
- Ordinary pseudo-Voigt eta = eta0 + eta1*(2theta in DEGREES); these are not TCH X/Y.

Theta is native Bragg angle, not offset-shifted observed angle. Apply only to the
matching actual engine/family/settings; another version/TOF model needs its own
facts. Do not swap conventions from an external program. Type/profile changes
may reset settings: inspect current values/eligibility. Definitions are not seeds
or proof of scientific adequacy.

### Native eligibility, imports and backgrounds

Import a supplied CIF unless manual entry is requested. Initial Estimate uses
current saved type/mode/settings unless manual anchors are explicit. Inspect
anchors/terms/eligibility without imposing anchors or bypassing automatic ownership.
Revisit eligible background when residuals implicate it, not as universal all-free
setup. Obey fittability; alternative starts/families need supported operations and
restorable state. Revisit temporary freezes and formerly unstable groups when new
evidence makes them identifiable; negative-ADP Undo does not finish that assessment.

### Widths, identifiability and implicated-group recovery

Assess actual TOTAL components over measured reflections/range, including high
angles. X/Y are not universally exclusive; signed coefficients alone are not
invalidity and positive Gaussian width does not certify Lorentz width. Unknown
geometry/checks stay unknown. After a rejected/unidentified profile trial, promptly
assess a physically justified simpler eligible SAME-family coefficient candidate,
or state why comparison is unavailable/unjustified. Do not zero/fix from sign,
postpone diagnosis by unrelated groups, or change profile family plus unrelated
baseline/structure simultaneously for diagnosis. Never replay partial/uncertain
effects, bypass ownership/change action mode, or replace inputs to lower objective.

Use actual completed-fit correlation pairs when offered, with original fit/call
provenance and explicitly unknown current-model validity. Missing/empty pairs do
not establish independence/covariance availability; large SUs are not correlations
and positive values alone are not identifiability. Repeated parameter reads are
not new information about an undetermined model.

### Single-crystal exceptions

Use actual F-squared residual/intensity dependence for appropriate extinction/ADP
assessment. Use current native extinction family, mosaic options and parameters;
fittable/fit_reason wins over a powder release group applied to inactive SC fields.
Enter a supplied size/radius in its actual field/units, without invented diameter
conversion. Choose from evidence, not screenshots. Zero sensitivity depends on
model/other values and is not limited to mixed Becker–Coppens. Only observed
stall/sensitivity can justify a small positive, physically explained supported
trial start: inspect response/SU and keep it restorable. Zero alone is insufficient;
never use another experiment's fitted value.

### Mixed sites and shared displacement models

Establish actual same-phase co-occupancy/scope before relations/shared coordinates.
Weak independent isotropic ADPs at a mixed-species site can justify a sharing
TRIAL with an explicit physical assumption; position/symmetry alone never demands
it. Distinct same-element sites in similar bonding environments may also justify
restorable sharing from weak identifiability/actual correlations: co-location is
unnecessary, element alone insufficient. If unresolved, consider justified broader
or overall isotropic groups OR state unavailable comparison/lost information.
One failed trial settles neither alternatives nor required sharing. Negative ADPs
alone do not mandate sharing or replacing established anisotropy. Keep Biso/Uiso
conversion/units correct. Symmetry is not a modelling constraint: preserve
independent coordinates/occupancies, compare residuals/SUs/complexity, and never
equate arbitrary anisotropic tensors across frames. Affine constraints are not
geometric restraints. No universal X-ray atom order applies to neutrons; report
conditional uncertainties/correlations honestly.

### Saving and numerical claims

After ordinary requested/delegated Save inspect authoritative saved values/SUs and
CURRENT residuals against accepted pre-Save values: Save can round/adopt/recalculate.
Old run_fit metrics remain pre-Save/pre-edit unless an offered metric actually
belongs to the saved model. Parameter reads, calculation-current/no-error flags
and unquantified residual checks do NOT verify chi-square/Rwp/objective equality.
Do not invent APIs/degrees of freedom, silently refit, or require reopening.
Disclose material changes/undetermined values while preserving genuine commit/path
facts. Ordinary Save may preserve an explicitly incomplete project; it is not
scientific validation. Quote native file_value and file_su VERBATIM as value ± SU
with units, never reconstructed parenthetic digits. If unavailable, give actual
numerical SU or state absence, never zero. Distinguish observation/assumption/unknown.

### Research, public caveats and hidden developer feedback

When guidance/supported routes leave needed information unresolved, use offered
public search/read: Edi source/docs, current engine/API facts or primary literature.
Query public concepts, not raw data, unpublished sample details, credentials or
private paths. Retain actual URLs/citations and label inferred decisions; research
cannot manufacture an Edi operation/result. Ask only genuinely missing facts or
indispensable user action. Automatic work reports retain history/research but do
not veto science. Send app/tool/skill improvement suggestions ONLY through offered
diagnostics.developer_feedback to hidden diagnostic work report, never purpose,
chat or scientific Report. Scientific caveats and user-needed errors stay public.

Read starting references where relevant, without replacing actual data/model/scope:

- McCusker et al., Rietveld refinement guidelines: https://journals.iucr.org/j/issues/1999/01/00/gl0561/
- Toby, International Tables H, Rietveld refinement and model simplification (2019): https://onlinelibrary.wiley.com/iucr/itc/Ha/ch4o7v0001/
- Young (ed.), The Rietveld Method: https://doi.org/10.1093/oso/9780198555773.001.0001
