# pd-neut-tof_ncaf-wish-5bank_start-fullprof — provenance

The five-bank NCAF WISH project started at **every value of FullProf's own `.pcr`**, added on the owner's request
(2026-09-30), next to `pd-neut-tof_ncaf-wish-5bank_start-5`, which starts away from it. Registered **executing**.

## Sources

- **Everything but the start:** `pd-neut-tof_ncaf-wish-5bank_start-5` (data, excluded regions, background nodes, the
  193-parameter free set, `_peak.cutoff_fwhm 8`, `_minimizer.chi_square_tolerance 1e-4`). See its `PROVENANCE.md`.
- **The start:** every refinable value from `tmpl_five_banks_p1.pcr` (crysta `tools/spikes/fullprof_ncaf_multibank/` at
  `fb9ffbe3`): atomic positions and Biso, and per bank the scale, Zero, Dtt1, peak shape, ABSCOR1 and all 136 background
  values. That `.pcr` is FullProf's converged state (its header records a global χ² of 9.961), so this project starts
  at FullProf's minimum.

## The FullProf run (`fullprof/`)

FullProf 8.40, `~/Applications/fullprof/fp2k`, run once at authoring time and never by a test:
`printf 'tmpl_five_banks_p1\n\n' | fp2k` in a copy holding the `.pcr`, `TOF_irf_file.irf` and
`55025-{5_6,4_7,3_8,2_9,1_10}raw.gss` (all from the crysta path above). The only edit to the input is `Pcr 1 → 2`, so
fp2k writes the refined file as `tmpl_five_banks_p1.new` and leaves the input unchanged. `fullprof/` holds that input
`.pcr`, the `.new` and the `.sum`. It stopped after one cycle at a global χ² of 9.959 (9.96 in the `.sum`). Output `.prf` sha256:

- `tmpl_five_banks_p1_1.prf`: `45a34afebc24decdd1687dc33e31be46976e7a1f61d8f0ea1cbc0b76573f844d`
- `tmpl_five_banks_p1_2.prf`: `c4ef8626488ac8c30511270e1db254abaa0a61953b2faa42bc98a3e6cd823d76`
- `tmpl_five_banks_p1_3.prf`: `33e3d65a9e6af2309c548d0eac976ba9b64d58a12b90e9f11b9d6d670a3a8345`
- `tmpl_five_banks_p1_4.prf`: `d2afe5109fb80d9373f5d03c4268199d2d3911d22394af88a2292b31b9739420`
- `tmpl_five_banks_p1_5.prf`: `3b5cee5c30063b5abb25ce96b84371624001bb79e993d1d33b16e4e6924a3d64`

## Check run

`python -m edi fit <copy> --dry --report machine` (edi at `f5ea155`): converged in 2 iterations, `n_free=193`,
`n_points_fitted=18973`, `reduced_chi_square=9.4975227`, `rwp=0.07694453423`, about 8 s. It reaches the same minimum
as `pd-neut-tof_ncaf-wish-5bank_start-5` (9.497535). Per bank, Rwp agrees with this FullProf run within 0.02 %, and every
parameter is within 0.31 of FullProf's σ. The one exception is `wish_5_6`'s first background node: it moves from
FullProf's 538.77 to 612.48 even from FullProf's own start.

## expected.json

The same FullProf references as `pd-neut-tof_ncaf-wish-5bank_start-5` (`kind: reference`, FullProf's σ as tolerance),
and regression pins from the check run above.
