# `pd-xray-cwl_lif_doublet` -- FullProf verification project

Origin: diffraction-lib (<https://github.com/easyscience/diffraction-lib>, BSD-3-Clause; licence copy at `tests/fixtures/diffraction-lib-LICENSE`), upstream folder `pd-xray-cwl_lif`, set `lif_doublet_unpolarized`, pin `0d9f10e4` (full sha `0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf`). Mirrors the upstream page **`pd-xray-cwl_LiF_doublet`**. No instrument is named by the source, so none is in the folder name. Every file is **inherited byte-identical** from upstream; none is authored.

Every parameter is fixed (a forward calculation: the `.pcr` declares zero free parameters). X-ray Cu Kα doublet: `Lambda1 = 1.540560`, `Lambda2 = 1.544400` and `Ratio = 0.5`, with `Cthm = 0` and `Rpolarz = 0` (no polarization). The `.pcr` differs from `pd-xray-cwl_lif_single`'s only in `Lambda2` and `Ratio` (and its title, file-name and chi-square comment lines); the data file is the same bytes. FullProf applies anomalous dispersion from CrysFML's lab-line table (its `.out`, upstream: F `Dfp`/`Dfpp` 0.069 / 0.053, Li 0.001 / 0) and the International Tables Vol. C 4-Gaussian f₀ — which is why the page declares `_scattering_source.xray_form_factor it1992` and `.xray_dispersion sasaki1989`, the published table CrysFML's matches for Li and F.

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

FullProf.2k: `printf 'lif_doublet_unpolarized\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). The upstream result line (7.95): `=> Rp:  99.5     Rwp:  100.     Rexp:    5.25 Chi2:  364.` — the "observed" data are a dummy pattern, so only the calculated profile is a reference; the page compares against the `.prf` calculated column.

## Files (sha256)

- `lif_doublet_unpolarized.bac` `8cb78794ae7705e8212fe3dfb4cada8b85181431bfe8e6fa7a6080f7c195561e`
- `lif_doublet_unpolarized.dat` `06ba190e26656de021c199beef857cdf61acf5e05ca62564cb325d40d9628cae`
- `lif_doublet_unpolarized.pcr` `3606d681cce449694c0964282286eb35c049228bd855496c24ea76a9729e0f04`
- `lif_doublet_unpolarized.prf` `730a1b1f159bc351dcb48c7ed3aff13b809971e409cd1267b4f622a579d63a5c`
- `lif_doublet_unpolarized.sum` `6c1782aa6a32034b483bed195876e607589d49772a34e1f63a9029708b375006`

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
