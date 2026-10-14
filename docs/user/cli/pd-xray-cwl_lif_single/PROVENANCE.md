# pd-xray-cwl_lif_single — provenance

**Built, not copied**, by `tools/cli_projects/build_c15_t2_project.py` from the FullProf reference
`knowledge/verification/fullprof/pd-xray-cwl_lif_doublet-absorption-polarization/`: diffraction-lib's LiF doublet input
(`0d9f10e4`, set `lif_doublet_unpolarized`) with the monochromator polarization (`Cthm` 0.8, `Rpolarz` 0.5) and the
cylinder absorption (`muR` 0.9) added, run once with FullProf.2k 8.40 (its own `PROVENANCE.md`).

**Model.** The `.pcr`'s: `F m -3 m`, a = 4.0267 Å, Li1 (4a, Biso 1.2) and F1 (4b, Biso 0.8) at full occupancy, the Cu
Kα doublet (λ₁ = 1.540560 Å, λ₂ = 1.544400 Å), zero 0, U/V/W/X/Y = 0.048457 / −0.083053 / 0.04 / 0 / 0.049268, `Wdt`
48, with the scattering sources FullProf's are comparable to (`it1992` f₀, `sasaki1989` dispersion), the
monochromator polarization (`K` 0.5, `2θ_m` = `acos(√0.8)` = 26.5650511771°) and the Hewat cylinder absorption.

**Data.** The reference's "observed" `.dat` is a dummy pattern, so the measured pattern is FullProf's **calculated**
profile: the `.prf` `Icalc` column minus the `.bac` background, on FullProf's own grid (10° to 160° in steps of
0.025°, 6001 points), read by `edi.verification.load_fullprof_calc_profile`. Every standard uncertainty is 1, so
chi-square and Rwp are regression pins without statistical meaning.

**Free set.** `setup_wavelength_2_to_1_ratio` and `mu_r`, started at 0.4 and 0.7. Their references are FullProf's own
inputs: `Ratio` 0.5 and `muR` 0.9.

**One conversion.** The scale is fixed at 0.02, twice the `.pcr`'s 0.01: for characteristic radiation (`Ilo` 0)
FullProf multiplies the Lorentz factor by `1 + Cthm cos²(2θ)` (manual section 3.4), which is twice the polarization
factor `P = 1 − K + K cos²(2θ_m) cos²(2θ)` at K = 0.5.

**Expectations.** `expected.json`'s two references are FullProf's own inputs above; the fit lands 7.3·10⁻⁵ and
2.0·10⁻⁴ from them, under tolerances of 3·10⁻⁴ and 1·10⁻³. Its `reduced_chi_square`, `iterations` and `rwp` are
regression pins of the `fast_descent` run.

**History.** The project first fitted the polarization pair alone against diffraction-lib's polarized LiF reference.
Extending it to the doublet and absorption needed data that carries all three, hence the authored reference above; the
polarization pair is now fixed at FullProf's values.
