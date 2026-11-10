# Magnetic token-reader contract

The expectations are CIF 1.1 lexical kinds and complete numeric grammar, with one shared scanner and decoder, as described by edi ADR-0078. Bare `?` and `.` are missing; quoted versions
are supplied literals. Numeric/selector literals must reach their type's validation rather
than a default. Arbitrary text stays text. Nonfinite values, suffix-bearing numbers and
malformed uncertainty digits are refused. No product output supplies an expected value.

The valid moment control is independently `(1.5, 0, 0)` in an orthogonal cell. Its spherical
form has modulus 1.5, polar angle 90 degrees and azimuth 0 degrees. Each component is tested
both as the selected declaration and, for converted forms, beside a consistent crystal-axis
form. Each field/route is a separate pytest node; the same case has valid, missing, literal
and malformed controls so refusal cannot pass by rejecting every declaration.

The route matrix describes actual readers. Form-factor rows use native tags in native inputs and the dictionary's local `_edi_magnetic_form_factor.*` names in CIF inputs. The BNS/OG transform record is
held string metadata, including arbitrary non-transform text; the parent-to-standard transform is
descriptive metadata. The child transform is interpreted. Parent IT-number metadata is kept when the
nuclear group is already declared. Its numeric admission and the BNS-family alternative
are exercised with the nuclear group absent, forcing the CIF derivation reader. This is
not permission to silently replace an invalid supplied scientific value.

A supplied text marker must remain a quoted literal in the saved column; the second save
must retain that column's exact lexemes. Computed geometry is outside this check. The
separate opaque ISO gates still require source lexemes, including multiline whitespace,
to survive verbatim; these tests do not replace or loosen those gates.

The census discovers raw readers by tag access and follows generic helpers. It separately
starts at readers of stored magnetic model text, including propagation components and child
basis/origin consumers. Numeric formatting, dictionary lookup and published radial-table
loading are reviewed terminal stages, not user CIF readers. Every discovered raw reader
requires a behaviour registration. Escape controls include new files, untagged helpers,
model-field reads, aliases, global/fragmented tags, macros, generic and indented definitions,
decorative decoder calls and local marker/delimiter handling. A strict numeric helper with
an independently chosen name is a positive control: no suggested repair name is required.


Member calls and unqualified owning members are followed. A reviewed
per-field/function inventory (including paired engine sources for edi) replaces
family registration; adding a field inside an old reader changes the obligations.
Native decoded-member probes inject supplied malformed values only after a valid
load and independently reach completion, save, second save, adapter transfer,
calculation, fit preparation and the child-origin view. Supplied quoted dots never
stand for absence. Compound arity, trailing fields, zero denominators and finite
composed arithmetic are distinct controls. Refusals name the tag and whole value.

Converted moment controls are qualified to the CIF entrance, selected and redundant;
unsupported native project spellings have explicit refusal gates. Optional symmetry
forms, child transforms and defaultable form-factor fields have admitted bare-marker
controls. All valid held fields get a second-save and canceled fit-preparation check.
The whole-source inventory/admission audit is in the system tier with a shared,
measured parse fixture; small escape controls remain in integration.

The native fit-preparation consumer belongs to integration. Its Python gate requires
`edi_integration_tests` at `build/ci/core/` or `build/ci-consumer/core/`, or the explicit
`EDI_MAGNETIC_INTEGRATION_TEST_EXE` path. It requires one selected native case to execute;
a missing target or an old binary cannot pass. The product build currently declares
only the unit target: adding the integration target from `tests/integration/cpp/test_*.cpp`
and ensuring it is built is implementation-owned build wiring. The isolated scoped consumer verifies the exact linked SDK, headers and core hashes.
No fit-preparation case is installed into the unit tier.

Held-transform metadata: `_space_group_magn_transforms.Pp_abc` changes from
interpreted compound grammar to preserved string metadata, matching dictionary
`space_group_magn_transforms.pp_abc` (dtype string). Quoted marker literals and
arbitrary text survive save/reload/second save. Whole-compound shape and finite
arithmetic checks remain on the interpreted child transform and other typed fields.
The child-transform grammar distinguishes the allowed empty whole child transform from a supplied
origin-only `;0,0,0`, which has no basis and must refuse.

The cache-layout witness uses three independently specified P1 sites. A valid layout has one supplied
`Mx,My,Mz` form and a `Ho3+`/`j0` form-factor row. The invalid layout has three
supplied forms (`Mx,My,Mz`, `Ho3+`, `j0`) and no form-factor rows; the latter two
are not moment forms. k, parent metadata, operations, centrings and numeric site
data stay fixed. A separate valid absent-k sentinel precedes the cold refusal.
Calculation must also refuse after the valid layout, both across projects and
after an in-place edit. Valid three-moment/no-factor and one-moment/factor controls
prevent rejection based merely on row count or absent optional factors.

The held-transform metadata nodes are split by individual lexical spelling (valid, missing,
literal), retaining every value and consumer assertion. The combined nodes
exceeded the integration runtime bound after literals became admitted metadata.
Other field node identities and their whole-compound witnesses remain unchanged.
