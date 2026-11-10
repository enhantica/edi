# `pd-xray-cwl_lif_single-polarization` -- FullProf verification project

Origin: diffraction-lib (<https://github.com/easyscience/diffraction-lib>, BSD-3-Clause; licence copy at `tests/fixtures/diffraction-lib-LICENSE`), upstream folder `pd-xray-cwl_lif`, set `lif_single_polarized`, pin `0d9f10e4` (full sha `0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf`). Mirrors the upstream page **`pd-xray-cwl_LiF_single_polarization`**. No instrument is named by the source, so none is in the folder name. Every file is **inherited byte-identical** from upstream; none is authored.

Every parameter is fixed (a forward calculation: the `.pcr` declares zero free parameters). X-ray, single wavelength 1.540560 Å, with the monochromator polarization term: `Cthm = 0.8` and `Rpolarz = 0.5`. The `.pcr` differs from `pd-xray-cwl_lif_single`'s only in those two values (and its title, file-name and chi-square comment lines); the data file is the same bytes. Scattering sources as there: the International Tables Vol. C 4-Gaussian f₀ and CrysFML's lab-line dispersion, declared on the page as `it1992` and `sasaki1989`.

**Convention.** FullProf's `Cthm` is cos²(2θ_m); the page's `setup_monochromator_twotheta` is the angle 2θ_m in degrees, `acos(sqrt(0.8))` = 26.5650511771°, and its `setup_polarization_coefficient` is `Rpolarz` = 0.5. With `Ilo = 0` (characteristic radiation) FullProf multiplies the Lorentz factor by `1 + Cthm cos²(2θ)` (manual section 3.4), which is twice the normalized factor `P = 1 − K + K cos²(2θ_m) cos²(2θ)` at K = 0.5; the page therefore sets its scale to twice the `.pcr` scale (see the page's method note).

**FullProf version.** The `.prf`, `.sum` and `.bac` are upstream's FullProf.2k **7.95** (Jan2023-ILL JRC) output, not the 8.40 replay the CW corpus carries: FullProf runs once, at authoring time, and this folder inherits its source bytes unchanged. Its occupancies already follow the convention (k = 1), so no refit is owed.

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`F m -3 m`: general multiplicity 192, sites 4a and 4b of multiplicity 4).

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `F m -3 m` | `Li1` (4a) | 4 / 192 | 1 | 0.02083 |
| 1 | `F m -3 m` | `F1` (4b) | 4 / 192 | 1 | 0.02083 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 0.0100000 | 0.0100000 | 1 | +0.00e+00 |

## Reproduce

FullProf.2k: `printf 'lif_single_polarized\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). The upstream result line (7.95): `=> Rp: 99.8 Rwp: 100. Rexp: 4.94 Chi2: 412.` — the "observed" data are a dummy pattern, so only the calculated profile is a reference; the page compares against the `.prf` calculated column.

## Files (sha256)

- `lif_single_polarized.bac` `423eabac3ebd8ea65c5761f79594adc82fc79ba24c7b63313292ac8c76b974c2`
- `lif_single_polarized.dat` `06ba190e26656de021c199beef857cdf61acf5e05ca62564cb325d40d9628cae`
- `lif_single_polarized.pcr` `ee0ccb367617e839ddfc2ae6c3a9904e1daba03e2d0cb8aab7c95233ae5bde4f`
- `lif_single_polarized.prf` `1b1186880704ddbdae5b6e39b0444bdb177d9b5c13ad99dd0b7f5463d1b7d849`
- `lif_single_polarized.sum` `d2b25204f6853cab5bc2b64fc931595f0b8803e8ae0f73383fd91937434a3e67`

## Evidence

```json
{
  "schema": "fullprof-evidence-1",
  "site_occupancies": {
    "1:Li1": 1.0,
    "1:F1": 1.0
  },
  "start_site_occupancies": {
    "1:Li1": 1.0,
    "1:F1": 1.0
  },
  "old_scales": [
    0.01
  ],
  "new_scales": [
    0.01
  ]
}
```
