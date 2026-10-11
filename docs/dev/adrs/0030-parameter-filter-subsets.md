# Parameter filter subsets

Status: Accepted

## Context

ADR-0029 introduced aggregate Atom sites and Peak profile filters with smaller
subsets. Its Peak shape predicate selected every coefficient except `asym_*`.
That duplicated Peak profile for TOF and omitted the asymmetric rise and decay
coefficients from Peak asymmetry.

## Decision

Keep one menu level. Structure and Experiment titles use the bundled bold text
font. Atom sites includes coordinates, occupancy and both isotropic and
anisotropic displacement. Its subsets select `fract_*`, `occupancy`, and
`adp_*`/the anisotropic category respectively.

Peak profile includes every active peak coefficient. Peak broadening selects
`broad_*`; Peak mixing selects `mixing_*`; Peak asymmetry selects CW `asym_*`
and TOF `rise_alpha_*`/`decay_beta_*`. The latter coefficients' parameter specs
identify the back-to-back exponential rise and decay. These are presentation
filters; the core's category and serialization remain unchanged.

Only nonempty proper subsets appear: a subset selecting its entire category
adds no choice. Aggregate categories remain available. Counts and filters use
one predicate over the Analysis source rows; name and free/fixed filters combine
with it. Symmetry-fixed or inactive coefficients remain excluded by the source
model. Unknown categories retain a readable fallback entry.

## Verification

`tst_parameter_groups.qml` exercises CW and TOF membership, isotropic and
anisotropic displacement, all menu counts, combined name/free filters, future
categories, duplicate suppression and source-model updates/detachment.
