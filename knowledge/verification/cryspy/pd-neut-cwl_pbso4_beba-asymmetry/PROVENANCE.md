# `pd-neut-cwl_pbso4_beba-asymmetry` -- cryspy reference

The Bérar-Baldinozzi page's **oracle**: cryspy implements the paper's Hermite form, the convention
crysta adopts, so it is the unfitted comparison. FullProf's own profile
(`../../fullprof/pd-neut-cwl_pbso4_beba-asymmetry/`) is the documented divergence record, compared
only after a fit or through diffraction-lib issue 166's inferred map.

- **Engine:** cryspy 0.12.1, run by diffraction-lib (<https://github.com/easyscience/diffraction-lib>,
  BSD-3-Clause) at pin `0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf` in its locked Python environment.
- **What was computed:** upstream's page `pd-neut-cwl_PbSO4_beba-asymmetry`, executed only through its
  first **unfitted** `calculate()` with the cryspy calculator — FullProf's P1..P4 entered as cryspy's
  `asym_beba_{a0,b0,a1,b1}` unchanged, every other parameter at the page's FullProf value. cryspy has
  no limit angle, so it corrects every reflection.
- **Grid:** upstream's FullProf loader supplies the corrected 2θ grid (2910 points, identical to the
  grid the edi loader reads from the vendored FullProf `.prf`); cryspy supplies every intensity.
  Neither crysta nor edi was imported.
- **Generator:** crysta `tests/fixtures/c11_t57_profiles/generate.py`, which wrote
  `beba/reference.tsv` there and in edi's `tests/fixtures/c11_t57_profiles/`;
  `pbso4_cryspy.tsv` is that file, copied byte-identically.
- **Columns:** corrected 2θ (deg), cryspy calculated Bragg intensity (tab-separated, no header).

## Files (sha256)

- `pbso4_cryspy.tsv` `a14896fed34d6920003a843aa41f643894356633ac2fb0c6ca2a54e5d4be9c3e`
