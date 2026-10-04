# pd-xray-cwl_lif_single — provenance

**Built, not copied**, by `tools/cli_projects/build_c15_t2_project.py` from the vendored FullProf
reference `knowledge/verification/fullprof/pd-xray-cwl_lif_single-polarization/` (diffraction-lib
`0d9f10e4`, set `lif_single_polarized`, FullProf.2k 7.95 output; its own `PROVENANCE.md`).

**Model.** The `.pcr`'s: `F m -3 m`, a = 4.0267 Å, Li1 (4a, Biso 1.2) and F1 (4b, Biso 0.8) at full
occupancy, λ = 1.540560 Å, zero 0, U/V/W/X/Y = 0.048457 / −0.083053 / 0.04 / 0 / 0.049268, `Wdt` 48,
with the scattering sources FullProf's are comparable to (`it1992` f₀, `sasaki1989` dispersion) — the
constants of the `pd-xray-cwl_LiF_single_polarization` verification page.

**Data.** The reference's "observed" `.dat` is a dummy pattern, so the measured pattern is FullProf's
**calculated** profile: the `.prf` `Icalc` column minus the `.bac` background, on FullProf's own grid
(10° to 160° in steps of 0.025°, 6001 points), read by `edi.verification.load_fullprof_calc_profile`.
Every standard uncertainty is 1, so chi-square and Rwp are regression pins without statistical
meaning.

**Free set.** `setup_polarization_coefficient` and `setup_monochromator_twotheta`, started at 0.4 and
20°. Their references are FullProf's own inputs: `Rpolarz` 0.5 and `Cthm` 0.8, that is
2θ_m = `acos(√0.8)` = 26.5650511771°.

**One conversion.** The scale is fixed at 0.02, twice the `.pcr`'s 0.01: for characteristic radiation
(`Ilo` 0) FullProf multiplies the Lorentz factor by `1 + Cthm cos²(2θ)` (manual section 3.4), which is
twice the polarization factor `P = 1 − K + K cos²(2θ_m) cos²(2θ)` at K = 0.5. It is fixed rather than
free because scale, K and 2θ_m carry only two independent numbers.

**Built before edi declared the two parameters, then reproduced.** The tree was first written with the
two `_instrument.setup_*` polarization lines added to `experiments/cu_ka.edi` by hand, because edi
could not load them yet. Once edi declared them, the builder's rerun reproduced every file byte for
byte except `project.edi`'s two metadata timestamps.

**Expectations.** `expected.json`'s two references are FullProf's own inputs above (`Rpolarz` 0.5 and
`acos(√0.8)` = 26.5650511771°); the fit lands 7.9·10⁻⁶ and 0.068° from them, under tolerances of
5·10⁻⁵ and 0.15°. Its `reduced_chi_square`, `iterations` and `rwp` are regression pins of the
`fast_descent` run, identical to crysta's corpus case `lif-xray-s1`, the same project.
