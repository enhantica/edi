# `pd-xray-cwl_lif_single-absorption` -- FullProf verification project

Origin: diffraction-lib (<https://github.com/easyscience/diffraction-lib>, BSD-3-Clause; licence copy at `tests/fixtures/diffraction-lib-LICENSE`), upstream folder `pd-xray-cwl_lif`, set `lif_single_absorption`, pin `0d9f10e4` (full sha `0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf`). Mirrors the upstream page **`pd-xray-cwl_LiF_single_absorption`**. No instrument is named by the source, so none is in the folder name. Every file is **inherited byte-identical** from upstream; none is authored.

Every parameter is fixed (a forward calculation: the `.pcr` declares zero free parameters). X-ray, single wavelength 1.540560 Å, `Cthm = 0` and `Rpolarz = 0` (no polarization), with the cylinder absorption correction `muR = 0.9`. The `.pcr` differs from `pd-xray-cwl_lif_single`'s only in `muR` (and its title, file-name and chi-square comment lines); the data file is the same bytes. FullProf applies anomalous dispersion from CrysFML's lab-line table (its `.out`, upstream: F `Dfp`/`Dfpp` 0.069 / 0.053, Li 0.001 / 0) and the International Tables Vol. C 4-Gaussian f₀ — which is why the page declares `_scattering_source.xray_form_factor it1992` and `.xray_dispersion sasaki1989`, the published table CrysFML's matches for Li and F.

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

FullProf.2k: `printf 'lif_single_absorption\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). The upstream result line (7.95): `=> Rp:  99.7     Rwp:  99.7     Rexp:    5.29 Chi2:  355.` — the "observed" data are a dummy pattern, so only the calculated profile is a reference; the page compares against the `.prf` calculated column.

## Files (sha256)

- `lif_single_absorption.bac` `9de1c5f5c110ee85ddce094f66e657c2b352f3dd8742daa936ab1dfb5abde6f0`
- `lif_single_absorption.dat` `06ba190e26656de021c199beef857cdf61acf5e05ca62564cb325d40d9628cae`
- `lif_single_absorption.pcr` `b5b183b0fb8123453bbe13246ddbb22aad335361866cd0f57cf2c3099365e7c0`
- `lif_single_absorption.prf` `3d5cea5e4e181e68481ffcdafae9191fa89e8bd5994a4e56470b02fb6492b7e4`
- `lif_single_absorption.sum` `979cf26e51652b0b548109496de5901a10e2d293867b58f57d268e6196d993b8`

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
