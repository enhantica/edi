# `pd-xray-cwl_pbso4-lab_round-robin` -- FullProf verification project

Origin: diffraction-lib (<https://github.com/easyscience/diffraction-lib>, BSD-3-Clause; licence copy at `tests/fixtures/diffraction-lib-LICENSE`), upstream folder `pd-xray-cwl_pbso4_round-robin`, set `pbsox`, pin `0d9f10e4` (full sha `0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf`). Mirrors the upstream page **`pd-xray-cwl_PbSO4_round-robin`**. The source is the laboratory X-ray data set of the Rietveld refinement round robin (R. J. Hill, J. Appl. Cryst. 25, 589 (1992)), so the folder name says `lab`. Every file is **inherited byte-identical** from upstream; none is authored.

Every parameter is fixed (a forward calculation: the `.pcr` declares zero free parameters). X-ray Cu Kα doublet (`Lambda1 = 1.540560`, `Lambda2 = 1.544400`, `Ratio = 0.5`), characteristic radiation (`Ilo = 0`) with `Cthm = 0.8`, the Thompson-Cox-Hastings pseudo-Voigt (`Npr = 7`) with Bérar-Baldinozzi asymmetry (`Asy1..4 = -0.41356, 0, 1.26777, 0`, `AsyLim = 160`), a 6-term polynomial background, and the excluded regions 0–10° and 154–180°.

**What the page can and cannot compare.** edi has no Npr 7 + Bérar-Baldinozzi model, and FullProf's asymmetry coefficients have no exact map to the paper's, so the page fits the pseudo-Voigt's widths, mixing and asymmetry to this profile and gates its closeness as regression pins. It does not count toward diffraction-lib parity.

**FullProf version.** The `.prf`, `.sum` and `.bac` are upstream's FullProf.2k **7.95** (Jan2023-ILL JRC) output: FullProf runs once, at authoring time, and this folder inherits its source bytes unchanged. Its occupancies already follow the convention (k = 1), so no refit is owed.

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`P n m a`: general multiplicity 8, sites 4c of multiplicity 4 and 8d of multiplicity 8).

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `P n m a` | `Pb` (4c) | 4 / 8 | 1 | 0.50000 |
| 1 | `P n m a` | `S` (4c) | 4 / 8 | 1 | 0.50000 |
| 1 | `P n m a` | `O1` (4c) | 4 / 8 | 1 | 0.50000 |
| 1 | `P n m a` | `O2` (4c) | 4 / 8 | 1 | 0.50000 |
| 1 | `P n m a` | `O3` (8d) | 8 / 8 | 1 | 1.00000 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 0.0004703142 | 0.0004703142 | 1 | +0.00e+00 |

## Reproduce

FullProf.2k: `printf 'pbsox\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). The upstream result line (7.95): `=> Rp:  15.8     Rwp:  17.0     Rexp:    6.81 Chi2:  6.27` — the observed data are the round robin's measured pattern; the page compares against the `.prf` calculated column.

## Files (sha256)

- `pbsox.bac` `d3b8a079bdc75063650ee7365dbd6c47a6c5bda85e15a28125ebba9115ae138d`
- `pbsox.dat` `ee2d5d38e9d44f68734605360b6fe1f40b3a5492cd839ad9db8617b9a30ae143`
- `pbsox.pcr` `08036035bd6025c64db57d58ceccd95cbb85ad2cc9c69484ee8db2ec9e2f4c84`
- `pbsox.prf` `8e46b904360a9d1bd61d39c093cf3a06ef53a37354e37b599289901950ffc0d5`
- `pbsox.sum` `b904aa92dfd24f2474ccf3984885f404891285e102735c81b999aaa4ebc6660e`

## Evidence

```json
{
  "schema": "fullprof-evidence-1",
  "site_occupancies": {
    "1:Pb": 1.0,
    "1:S": 1.0,
    "1:O1": 1.0,
    "1:O2": 1.0,
    "1:O3": 1.0
  },
  "start_site_occupancies": {
    "1:Pb": 1.0,
    "1:S": 1.0,
    "1:O1": 1.0,
    "1:O2": 1.0,
    "1:O3": 1.0
  },
  "old_scales": [
    0.0004703142
  ],
  "new_scales": [
    0.0004703142
  ]
}
```
