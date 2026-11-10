# `pd-neut-cwl_cosio-d20_biso-tied` -- FullProf fitting project (constrained refinement)

Origin: crysta `tests/fixtures/c11_t62/origin/fullprof/start.pcr` at crysta `origin/main` `3b977af215ac9f04bba483426a9ea64ff181a183` (last changed by `d641668e9b4bfd02011b5a62ff3a3495cb6f2d53`; sha256 `4016f87e9b606c08a3167a4a7b58d459d3ee4104a78cdfd26f306b7fbc86f83e`), the canonical fitting start of the FullProf 8.40 CoSiO D20 chain that crysta's `c11_t62/origin/README.md` documents: CW neutrons, wavelength 1.87 A, `P n m a` Co2SiO4, TCH pseudo-Voigt (`Npr 7`), `Wdt 8`, 39 free parameters (14 background anchors, zero, 16 atomic, scale, U V W Y, a b c), exclusions 0-8 and 150-180 degrees. Instrument D20 (ILL; the data header's `d20` run line). Data: `01_001_497p3790.dat` (497.379 K, the first file of the chain), byte-identical to edi `docs/user/cli/pd-neut-cwl_cosio-d20_scan-324f/project/experiments/d20_scan/01_001_497p3790.dat` (sha256 recorded in crysta `tests/fixtures/c11_t62/scan-inputs.json`), renamed to the `.pcr` stem because `fp2k` reads `<stem>.dat` by default.

A **fitting** project: parameters free, `Pcr = 2` (FullProf writes `.new`, never over the `.pcr`). It is the independent reference for a **user constraint** `biso_Co2 = biso_Co1`: the isotropic displacement parameters of Co1 and Co2 refine as **one** shared parameter. `full-fit.out` is the run that reached convergence (its exact input is `full-fit.inp`), and the committed `.pcr` is the `.new` it wrote, byte for byte. Rerunning FullProf over the committed `.pcr` converges at cycle 1 and gives the committed `.prf`/`.sum`.

## What changed against the source

Four edits, nothing else (`diff start.pcr full-fit.inp`):

| line | source | `full-fit.inp` | why |
| --- | --- | --- | --- |
| `COMM` | `CoSiO D20 downward chain, FullProf, crysta template start` | `CoSiO D20 01_001 497.379 K, Biso(Co1) and Biso(Co2) tied: codeword 181` | title only |
| `Pcr` flag | `1` | `2` | fitting home: FullProf writes `.new` |
| `Co1` Biso code | `0.00` (fixed) | `181.00` | the tie: Co1 joins Co2's codeword 18, multiplier 1.0 |
| `Co1` Biso value | `0.01000` | `0.98759` (Co2's start value) | equal starts, see below |

Codeword 18 (`181.00`) was already Co2's Biso, so no new parameter number is introduced and `Number of refined parameters` stays **39**: codewords 1-39 remain contiguous (1-14 background, 15 zero, 16-31 atoms, 32 scale, 33-36 profile, 37-39 cell). FullProf names the shared parameter `Biso_Co1_ph1` (its first occurrence).

**Equal starts are required.** A FullProf codeword constrains the **shift**, not the value: each parameter is its own start plus multiplier x the shift of the parameter number. A first attempt with Co1 still starting at `0.01000` converged (chi2 4.801) with Co1 = 0.16557 and Co2 = 1.14316 -- both moved by the same 0.15557, so `Biso(Co2) - Biso(Co1)` stayed at its starting 0.97759. Starting Co1 at Co2's value makes the tie an equality at every cycle. That attempt is not committed.

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8; FullProf's `.sum` multiplicity column agrees). The source already follows it (k = 1); no occupancy was changed.

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
| 1 | 1.230743 | 1.294665 | 1 | +5.19e-02 |

The scale is not conserved: the fit refines it together with the displacement parameters it correlates with, and Co1's Biso moves from the source's fixed 0.01 to the shared refined value. This is a refinement result, not an occupancy restatement.

## Key numbers

FullProf values from `full-fit.out` (parameter list, final cycle) and the `.sum`. The **untied** column is the unchanged source `start.pcr` run once over the same data (`Pcr = 1`, not committed; its chi2 4.81 matches the first row of crysta's `chain.tsv`).

| quantity | tied (this project) | untied source |
| --- | --- | --- |
| Biso Co1 | 0.67350078 +/- 0.10028064 | 0.01 (fixed) |
| Biso Co2 | 0.67350078 +/- 0.10028064 (same parameter) | 1.0193310 +/- 0.15918042 |
| `.new` Biso Co1 / Co2 | 0.67350 / 0.67350 | -- |
| chi2 (conventional, all non-excluded points) | 4.806 | 4.809 |
| Rwp / Rp (all non-excluded points) | 4.62 / 3.26 | 4.63 / 3.26 |
| Rwp (background-corrected, conventional) | 14.8 | 14.8 |
| N-P+C | 1379 | 1379 |
| converged at cycle | 10 | 10 |

The committed `.sum` (the rerun over the committed `.pcr`) prints Co1 and Co2 Biso as `0.673(100)` each, chi2 4.806 (`.out` value).

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'cosio\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 3.26 Rwp: 4.62 Rexp: 2.11 Chi2: 4.81`. The fit itself was the same command over `full-fit.inp` saved as `cosio.pcr`; its `cosio.out` is committed as `full-fit.out`. `fp2k` ends with `forrtl: severe (24): end-of-file during read` at its final "continue?" prompt after `Normal end`; that is the non-interactive stdin closing, not a failure.

## Files (sha256)

- `cosio.dat` `22db61d0c3782c2614c6fccb92e1b9861010bfdb391ff87fa7ab0f53abcfc37f`
- `cosio.pcr` `bed760266eb3f48af2099a16a3d2c53e45f32096aa89fe5323e3de216faee617`
- `cosio.prf` `3ccb9d9636eccefb333513950245e3f1d64aa16f5fa07f082b2b41672f5ac83b`
- `cosio.sum` `cdebf8cb8f5bc52d27bbfb7c2ac19cd2bf376b3f9c110e51acf81ed2a3daad1b`
- `full-fit.inp` `9415ada4e3fac864f0269e5de8cb0859a84ff25df1e5f1bdf62fa65f373a211c`
- `full-fit.out` `debfffd0ffa4912543155d998d57a896fa85c46b32fc7e464a88e71331bad88c`

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
    1.230743
  ],
  "new_scales": [
    1.294665
  ],
  "fit_out": "full-fit.out",
  "fit_inputs": {
    "full-fit.out": "full-fit.inp"
  },
  "nonuniform_change": "Occupancies unchanged (k = 1). The scale moves +5.2% because this is a refinement with a new constraint, not a restatement: Co1's Biso, fixed at 0.01 in the source, is tied to Co2's (shared codeword 181, both started at 0.98759) and refines with the scale."
}
```
