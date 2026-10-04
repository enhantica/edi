# `pd-neut-tof_si-sepd_ikeda-carpenter` -- FullProf fitting project

Origin: Built by the conductor from FullProf's `Examples/arg_si.pcr` (vendored by edi #74): profile switched to **Ikeda-Carpenter (x) pseudo-Voigt** (`Npr 13`), the four IC shape terms fixed (alph0 0, alph1 0.879, beta0 21.668, kappa 75.321), the author's own 16 parameters free. Data `Examples/arg_si.dat`, renamed to the stem. Instrument SEPD (crysta fitting case `si-sepd`).

A **fitting** project: parameters free, `Pcr = 2` (FullProf writes `.new`, never over the `.pcr`). restated the occupancies (below), moved the factor into the scale, and fitted every free parameter to convergence again: `full-fit.out` is that run (its first cycle carries the restated `Occ`; its exact input is `full-fit.inp`), and the committed `.pcr` is the `.new` it wrote, byte for byte. Rerunning FullProf over the committed `.pcr` converges and reproduces the committed `.prf`/`.sum` apart from the run-date and CPU-time lines.

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8). FullProf's TOF extinction term scales with |F|^2, so a restated phase's `Extinc` moves by 1/k^2 with the scale.

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `F d 3 m` | `Si` | 8 / 192 | 1 | 0.04167 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 0.680728 | 392.022 | 0.04167 | -3.93e-05 |

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'arg_si_ic\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 8.42 Rwp: 5.52 Rexp: 3.66 Chi2: 2.28`.

## Files (sha256)

- `arg_si_ic.dat` `261b9e2846b0b159dab906e144d5f05e36cdad36a42edf1df848720043568e5b`
- `arg_si_ic.pcr` `6be69b01b0965cea948da2a8d4c52a1659e1ef58d175fb4635defb9713878bc7`
- `arg_si_ic.prf` `b85daa174ad0df3f60e58f88a6699aee8a066c5598088a56e8530c7bec2c5d60`
- `arg_si_ic.sum` `bb3827527010a1185d26e8d89ecbbc3f08602c7ef7db300aa0b8337d01b41883`
- `full-fit.inp` `bbe2d23289cbcb07c26f2edf621d6e53fa31980ff4761f5e70da43958d67dfa4`
- `full-fit.out` `151bce63cbba4becdeb60396c747c8d307a78f276dc12acfefc378cf1e961580`

## Evidence

```json
{
  "schema": "fullprof-evidence-1",
  "site_occupancies": {
    "1:Si": 1.0
  },
  "start_site_occupancies": {
    "1:Si": 1.0
  },
  "old_scales": [
    0.6807285
  ],
  "new_scales": [
    392.0215
  ],
  "fit_out": "full-fit.out",
  "fit_inputs": {
    "full-fit.out": "full-fit.inp"
  }
}
```
