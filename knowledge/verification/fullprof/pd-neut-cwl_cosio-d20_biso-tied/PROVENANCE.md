# `pd-neut-cwl_cosio-d20_biso-tied` -- FullProf verification project (constrained refinement)

**Verification twin** of [`knowledge/fitting/fullprof/pd-neut-cwl_cosio-d20_biso-tied/`](../../../fitting/fullprof/pd-neut-cwl_cosio-d20_biso-tied/PROVENANCE.md): that project's fitted state with every parameter fixed (all codes 0, `Number of refined parameters` 0), the extraction output of this home (`Prf = 2`, `Ppl = 2`). It is a forward calculation at the refined values of the tied fit, where Co1 and Co2 carry the **same** Biso (the `biso_Co2 = biso_Co1` constraint).

Origin of the fitting project: crysta `tests/fixtures/c11_t62/origin/fullprof/start.pcr` at crysta `origin/main` `3b977af215ac9f04bba483426a9ea64ff181a183` (sha256 `4016f87e9b606c08a3167a4a7b58d459d3ee4104a78cdfd26f306b7fbc86f83e`), the canonical start of crysta's FullProf 8.40 CoSiO D20 chain: CW neutrons, wavelength 1.87 A, `P n m a` Co2SiO4, TCH pseudo-Voigt (`Npr 7`). Its Co1 Biso was tied to Co2's through the shared codeword 181, both started at 0.98759, and the fit converged with both at 0.67350. Instrument D20 (ILL). Data `01_001_497p3790.dat` (497.379 K), byte-identical to the fitting project's `cosio.dat`.

## What changed against the fitting project

The `.pcr` is the fitting project's `cosio.pcr` (the `.new` of its fit) with: the `COMM` title replaced; `Ppl` 0 -> 2 (write the `.bac`); `Number of refined parameters` 39 -> 0; and every codeword set to 0 -- the 14 background codes, the zero-shift code and the 25 atom, scale, profile and cell codes (40 nonzero codes, since codeword 181 appears on both Co1 and Co2). Every parameter value is the fitting project's, byte for byte. `Pcr` stays 2, so the run leaves the `.pcr` untouched.

**Unlike the other twins, the scale was not fitted alone first:** this twin exists to reproduce the constrained fit's own endpoint, so it evaluates the fit's values as they are.

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8; FullProf's `.sum` multiplicity column agrees). Unchanged from the source (k = 1).

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `P n m a` | `Co1` | 4 / 8 | 1 | 0.50000 |
| 1 | `P n m a` | `Co2` | 4 / 8 | 1 | 0.50000 |
| 1 | `P n m a` | `Si` | 4 / 8 | 1 | 0.50000 |
| 1 | `P n m a` | `O1` | 4 / 8 | 1 | 0.50000 |
| 1 | `P n m a` | `O2` | 4 / 8 | 1 | 0.50000 |
| 1 | `P n m a` | `O3` | 8 / 8 | 1 | 1.00000 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 1.294665 | 1.294665 | 1 | +0.00e+00 |

## Key numbers

| quantity | this twin (0 free) | fitting project (39 free) |
| --- | --- | --- |
| Biso Co1 / Co2 | 0.67350 / 0.67350 (fixed) | 0.67350078 +/- 0.10028064, one parameter |
| chi2 (conventional, all non-excluded points) | 4.674 | 4.806 |
| N-P+C | 1418 | 1379 |
| chi2 x (N-P+C) | 6627.7 | 6627.5 |
| Rwp / Rp (all non-excluded points) | 4.62 / 3.26 | 4.62 / 3.26 |
| Rwp (background-corrected, conventional) | 14.8 | 14.8 |

The two chi2 differ **only by the degrees of freedom**: FullProf divides the same weighted residual sum by N-P+C, and P is 0 here against 39 in the fit (4.674 x 1418 = 6627.7 and 4.806 x 1379 = 6627.5, equal within the printed 3-decimal rounding of chi2). Rwp and Rp, which carry no P, are identical. Pointwise, this twin's `Icalc` agrees with the fit run's final `.prf` to at most 0.18 counts (relative 4e-4) over 8-150 degrees, the rounding of the `.new`'s printed values; the only larger difference is the last point, 150.895 degrees, inside the excluded region beyond the last background anchor.

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'cosio\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 3.26 Rwp: 4.62 Rexp: 2.14 Chi2: 4.67`. `fp2k` ends with `forrtl: severe (24): end-of-file during read` at its final "continue?" prompt after `Normal end`; that is the non-interactive stdin closing, not a failure.

## Files (sha256)

- `cosio.bac` `f2320cd48c5ec97dd35185b301f6383ab4197f5a55e56316a7babb1817906464`
- `cosio.dat` `22db61d0c3782c2614c6fccb92e1b9861010bfdb391ff87fa7ab0f53abcfc37f`
- `cosio.pcr` `a25a68fa434cd2df74f85ce344e14cd4ffd9b4687c43042f3a83e679924c26a9`
- `cosio.prf` `9230df542eb1d3087bcb6f0dcd929c5455dc432b20c6224f1a8df109be2b5b3a`
- `cosio.sum` `4a622bb81fa5206f3a6c73a80a3180f3b3940e2315c60cda85ef0c85ec0738b3`

## Evidence

```json
{
  "schema": "fullprof-evidence-1",
  "site_occupancies": {
    "1:Co1": 1.0,
    "1:Co2": 1.0,
    "1:Si": 1.0,
    "1:O1": 1.0,
    "1:O2": 1.0,
    "1:O3": 1.0
  },
  "start_site_occupancies": {
    "1:Co1": 1.0,
    "1:Co2": 1.0,
    "1:Si": 1.0,
    "1:O1": 1.0,
    "1:O2": 1.0,
    "1:O3": 1.0
  },
  "old_scales": [
    1.294665
  ],
  "new_scales": [
    1.294665
  ]
}
```
