# Magnetic reference inputs

The magnetic operations are ISODISTORT 6.12.2's Pnma.1 operations in `cosio/isodistort.mcif`.
The moment components are the frozen state Co1 (0.70, 2.60, 0.30) and Co2 (0, 2.97, 0) μB.
For each diagonal operation the axial vector is det(R) R m. The stabilisers give three free
components at 4a and only My at 4c. The tests expand these operations independently.

The fixed FullProf input uses the final printed cell, profile, zero and background of
`g2_main_bshared/cosio.new`, the positions printed in `cosio1.mcif`, and the shared Co Biso 0.269.
Positions are frozen at that file's printed precision. The moments use the frozen state above.
`values.json` records the numbers. Both phases have identical scale, cell and profile.
Absorption and asymmetry are zero. Every parameter code is zero.

The magnetic form factor coefficients are P. J. Brown, International Tables for Crystallography,
Vol. C §4.4.5. Co2+ j0 is (0.4332, 14.3553, 0.5857, 4.6077, -0.0382, 0.1338, 0.0179),
and j2 is (1.9049, 11.644, 1.3159, 4.357, 0.3146, 1.645, 0.0017).
These agree with CrysFML2008 `CFML_Tables/Tab_Set_ScatterT.f90` rows MCO2 and magnetic_j2 CO2.
j2 includes the leading s². The neutron magnetic amplitude constant is 2.695 fm/μB.

FullProf 8.40, February 2026, generated the committed outputs. Run from `cosio/` with
`FULLPROF` pointing to the installed suite, using `printf 'cosio\n\n\n' | "$FULLPROF/fp2k"`.
The engine tests read committed outputs only. SHA256 values are in `manifest.json`.
FullProf may finish with EOF at its final continuation prompt after reporting normal completion.

The profile relative L2 tolerance is 0.01, from the existing fixed-parameter X-ray FullProf
fixture. Magnetic windows use the same bound on signal above background. The reflection
comparison uses half the printed final digit, with one scale from nuclear reflections.

The observed file's two trailing points at 150.7953 and 150.8953 degrees have zero
uncertainty. The native EDI copy assigns them uncertainty 1 so both readers accept the file.
Both points are excluded. The original FullProf input is retained byte for byte.

The strict magnetic reflection comparison remains unresolved. For (100), the closed form
with p_n = 2.695 gives 4.560243525162284 in FullProf squared-factor units, while FullProf's
`cosio.hkl` prints 4.56166. For (001), the corresponding values are 29.329438587233753 and
29.33859. The effective constants inferred separately from these rows are near 2.69542.
These values come from `reference.magnetic_squared` and the committed reflection rows.
The current profile comparison retains its predeclared 0.01 bound. No strict per-reflection
agreement is claimed until the amplitude convention is reconciled.

The position-rounding contract also needs reconciliation. The exact PCR cell gives
(200) d = 5.154032 Å, while `cosio.hkl` prints 5.154033 Å. The difference is 0.000001 Å,
twice half the printed final digit. The strict position gate records this reference-contract
failure separately from missing magnetic behavior. Its tolerance has not been enlarged.

The fixed-parameter 2.3 K app reflection and tick oracles use `cosio-2k-reference.edi`,
the documented example's original structure at edi 4f77e01b. The measured grid is the
published D20 experiment. The fit-start gate separately loads the current published
example unchanged.
