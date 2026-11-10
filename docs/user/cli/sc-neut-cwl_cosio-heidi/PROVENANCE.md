# sc-neut-cwl_cosio-heidi — provenance

Fit one Co₂SiO₄ crystal measured on HEiDi at MLZ at three temperatures: 300 K and 55 K, where the cobalt moments are
disordered, and 2.5 K, where they order. Each temperature has its own structure and dataset,
and the three are fitted independently (`_fitting_mode.type independent`, edi ADR-0081).

## Sources

- **Structures and data:** the supplementary files of Sazonov et al., *Structural behaviour of synthetic Co₂SiO₄ at low
  temperatures*, Acta Cryst. B 64 (2008) 661–668, doi:10.1107/S010876810803214X: the CIF with the Pnma structure at each temperature and one reflection file per
  temperature (λ = 0.552 Å). Supplied by an author.
  - `data/heidi_300k.hkl` (1624 reflections) and `data/heidi_55k.hkl` (1465), the published `bp5014-300K.hkl` and
    `bp5014-55K.hkl` unchanged, sha256
    `dcdab63cec3fd6c989adf54026200802ac58f733b9f60f639342323b0f85b6ff` and
    `b8db9c18892623bd8df3f064f4767be1dcba671879af0f1d97e065cbb8815371`.
  - `data/heidi_2k5.hkl` (1424 reflections): the published `bp5014-2.5K.hkl` with **estimated uncertainties**
    (below), sha256 `101fbbcb32645511ea3e095ba71ed7efa1841aaeb94247923b11a7f3f787cea9`.
  - `data/README.md`: what the three files hold, sha256
    `3031fa4e9d596e8637be575a23df960a7588ead94a8ed6bb1abc8b2fc3722f22`.
- **Magnetic structure:** Sazonov et al., Acta Cryst. B 65 (2009) 664–675, doi:10.1107/S0108768109042499: the
  magnetic space group Pnma (k = 0), the moment directions allowed on each site (Co1 in any direction, Co2 along b)
  and, in Table 4, the single-crystal moments the fit is compared with: Co1 (1.20(3), 3.64(2), 0.57(9)) μB, Co2
  My 3.35(2) μB.

The project's three experiments embed the files' h, k, l, F² and σ unchanged (the 2.5 K σ as estimated). The files'
F²calc column is FullProf's calculation; it is kept in the data files and never read as data.

## The 2.5 K uncertainties are estimated

The published 2.5 K file holds 2θ in its σ column. The σ used here are estimated from the other two temperatures of
the same crystal, instrument and setting, by `tools/data/estimate_cosio_heidi_su.py`. A reflection is matched by its
Laue-equivalent indices (mmm: the signs of h, k and l do not matter):

1. measured at 55 K: σ₂.₅ = max(σ₅₅ · F²₂.₅ / F²₅₅, σ₅₅), the 55 K relative error carried over and never below the 55 K
   absolute σ, which a reflection measured at or below zero at 55 K takes as it is (1301 reflections);
2. otherwise measured at 300 K: the same with the 300 K values (19 reflections);
3. otherwise, mostly reflections that Pnma forbids for nuclear scattering and that carry only magnetic intensity at
   2.5 K: from the 25 reflections estimated by 1 or 2 whose F²₂.₅ is nearest, σ₂.₅ = max(F²₂.₅ × their median
   relative error, their median σ) (104 reflections). The second term keeps a floor, so a reflection measured near
   zero (80 have F²meas = 0) does not get a vanishing σ.

The fitted 2.5 K values and their s.u. inherit this estimate.

## Start

Built by `tools/cli_projects/build_cosio_heidi.py`. Every structure starts from its published positions, every site
from one isotropic-equivalent U of 0.003 Å² (Uani, tied by site symmetry), no extinction (Larson anisotropic, all six
coefficients 0, as FullProf's model 4 the paper used), the scale 10, and at 2.5 K zero moments. Free: the scale, the
six extinction coefficients, the coordinates and tensor components site symmetry leaves free, and at 2.5 K the moment
components Co1 x, y, z and Co2 y.

## Result from this start (local diagnostic)

From this start the three fits converge, the pooled reduced χ² 0.619. At 2.5 K the moments come out as Co1
(1.198(47), 3.553(43), 0.751(138)) μB and Co2 My 3.313(45) μB, within about two s.u. of Table 4.
