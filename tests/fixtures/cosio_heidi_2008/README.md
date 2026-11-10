# Independent HEiDi references

BP5014 (Sazonov et al., 2008), DOI 10.1107/S010876810803214X supplies the
unaltered reflection loops. The owner supplied the originals at hub
`knowledge/references/co2sio4-sc-heidi-2008/`. `generate.py --source <that-folder>`
reads the accompanying CIF and produces `reference.json` without importing either
product. Its recorded source hashes establish custody. The raw structure CIF
stays in the hub; the portable JSON records its numerical input values and s.u.

F²calc is the published FullProf column: an external correctness reference.
The independent calculation expands Pnma positions, transforms axial moments and
anisotropic U tensors, applies Brown's Co2+ j0, projects moments perpendicular to Q,
and applies the neutron Larson anisotropic correction before scale. Scattering
lengths are Gemmi's Sears 1992 table; magnetic length is the CODATA 2018 expression
also used by the existing independently authored magnetic fixture. Magnetic Pnma
is documented in the authors' IUCr 2009 contribution:
https://journals.iucr.org/a/issues/2009/a1/00/a45131/a45131.pdf.
The moments and their s.u. are the owner's BP5024 Table 4 reference
(DOI 10.1107/S0108768109042499).

The CIF omits overall scale. One scalar per temperature is calibrated from only
nuclear-only FullProf rows with F²calc > 1. Magnetic-only rows and measured F²
never determine that scalar. The native calculation inputs omit F²calc completely;
the implementation cannot recover the expected values by copying an input column.

The published covariance matrices are unavailable. The per-reflection tolerance is
0.005 (two-decimal FullProf rounding) plus three times the sum of absolute F²
changes under independent ±one-s.u. perturbations of every printed CIF parameter
and Table 4 moment. This L1 envelope allows unknown parameter correlations.
Measurement sigma never enters the F²calc reference, scale or tolerance.
A separate strict comparison checks the nominal printed-input closed form.

Two unresolved published-input discrepancies at 2.5 K are excluded only from
comparison with the external FullProf column:

| h k l | Published FullProf F²calc | Independent printed-input F² | Unchanged tolerance |
| --- | ---: | ---: | ---: |
| 4 0 1 | 816.25 | 764.080438 | 42.977722 |
| −10 4 7 | 0.08 | 0.007514 | 0.035851 |

These are the same discrepancies identified by the independent generator when
the fixture was first authored, before product parity worked. The available
printed CIF and Table 4 parameters do not reproduce those two FullProf outputs
within the stated uncertainty envelope. The original unrounded inputs and
FullProf settings are unavailable; this does not identify which publication
input or convention accounts for the difference and is not evidence that the
published FullProf values themselves are erroneous. Product values must not be
changed merely to imitate the unexplained differences.

The weak published token is exactly `0.08`, printed to two decimal places, whose
ordinary rounding interval is 0.075 through 0.085 (endpoint tie convention aside).
The nominal 0.007514 is outside that interval: rounding is not an explanation,
and the reference is not silently read as 0.008 or 0.01. The 0.005 rounding floor
already belongs to the frozen tolerance.

The exclusions are fixed by temperature and signed h k l, not selected from
product residuals. Every source row remains in the reader and native inputs.
All 1422 other 2.5 K rows, including every magnetic-only reflection, and every
300 K/55 K row retain their original tolerance. Strict nominal printed-input
closed-form parity still covers both excluded rows as well as all other rows.
The original reflection files, JSON values, scales and tolerance arrays remain
byte-identical; no tolerance was calibrated against product output. The tests
exercise changed retained rows, changed excluded nominal values and nonfinite
excluded values. The unresolved source history stays in the original receipt;
new evidence with the original calculation settings may reopen the exclusions.

The original 2.5 K sigma column is actually 2theta. It is preserved here verbatim
for reader testing. Calculation-only native inputs use unit weights at 2.5 K.
The collection gates separately recompute the owner-defined estimate from the
original higher-temperature measured F² and sigma. Unspecified "similar intensity"
and positive "near zero" boundaries remain explicit limitations until defined.
