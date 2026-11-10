# Independent references

`published-elements.tsv` is extracted directly from diffraction-lib's published
data module at `c0654956a1281f1ea3f3467c3367167f93edee18`. `provenance.json`
records both file hashes, the upstream sources and licences, and the command.
The generator evaluates only literal dictionaries and reads no edi code.
The product table is compared against this fixture, never used to generate it.

Camera expectations are computed independently in the hidden tests from the
formulas of diffraction-lib's `templates/structure.html.j2` at `cb2cda7b`.
The zero-total equal-share rule and isotope extraction are intentional owner
plan deviations from diffraction-lib, specified by the structure-scene design.

Radius-substitution reporting follows I5 and diffraction-lib `cb2cda7b`:
`assets/radii.py:radius_for` gives an unknown or empty element `(1.0, True)`,
and `builder.py:structure_feature_availability` adds every substituted symbol
to a set and returns it sorted, including the empty string. An unmatched site
maps to that empty symbol under I4. Four unmatched sites therefore report
`[""]`, distinct from an empty report `[]`. This property is separate from
seam row 9's occupancy fractions, which the gate exercises independently.

`generated.hpp` constructs M1's deterministic G1 input through the public model.
Geometry expectations always come from crysta's own API; input generation is
not a correctness oracle. Performance targets are reported, never thresholds.

The G1 general-position sites declare Wyckoff letter `l` for `F m -3 m`,
as required by crysta's public structure reader and CIF writer. Its 192-fold
general-position symmetry is unchanged; the same letter appears in both the
model constructor and generated text. The pick fixture declares `a` for `P 1`.
These are input metadata, not geometry expectations.

M1's §P13 amendment adds one calculation-only CW experiment linked to G1,
with the explicitly declared three-point grid 10, 11, 12 degrees and no
measured intensities or uncertainties. `write_calculation_project` writes
the structure and metadata through the public writer, then writes this
literal input experiment: the CIF writer intentionally refuses to save
calculation-only grids as observations. Both the native probe's model and
the drawn gate's directory loader receive this experiment. Geometry inputs,
independent engine expectations and the fifty samples/five warmups stay
the same. The same small grid makes the P1 pick project loadable.
