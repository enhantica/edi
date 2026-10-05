---
title: Verification
---

# Verification

These pages compare edi calculations with reference calculations from
**FullProf**, an independent program — and, for the Bérar-Baldinozzi
asymmetry, with **cryspy**, whose coefficient convention crysta adopts.
Each page focuses on one experiment type or one additional model term.
Every expected value the pages assert against is loaded at run time from
the committed reference projects under `fullprof/` and `cryspy/`; none is
produced by edi or crysta.

## Powder, Neutron, Constant Wavelength

### LaB6 structure

- [pd-neut-cwl LaB6 basic](pd-neut-cwl_LaB6_basic.ipynb) –
  **pseudo-Voigt** profile, natural boron, no correction models
  (FullProf "Npr=7" baseline).
- [pd-neut-cwl LaB6 11B](pd-neut-cwl_LaB6_11B.ipynb) – the baseline
  pattern with the **11B isotope** (b_c = 6.65 fm from the `.pcr`'s
  additional scattering factors) instead of natural boron.
- [pd-neut-cwl LaB6 absorption](pd-neut-cwl_LaB6_absorption.ipynb) – the
  baseline pattern with the **Debye-Scherrer cylindrical absorption**
  correction (Hewat, μR = 0.7) enabled — including the per-reflection vs
  pointwise application comparison, both held against FullProf.
- [pd-neut-cwl LaB6 FCJ asymmetry](pd-neut-cwl_LaB6_fcj-asymmetry.ipynb) –
  **TCH pseudo-Voigt ⊗ Finger-Cox-Jephcoat axial-divergence asymmetry**
  (`cwl-thompson-cox-hastings`, S/L = D/L = 0.08).

### LBCO structure

- [pd-neut-cwl LBCO basic](pd-neut-cwl_LBCO_basic.ipynb) –
  **pseudo-Voigt** profile with mixed La/Ba site occupancies and no
  correction models.
- [pd-neut-cwl LBCO preferred orientation](pd-neut-cwl_LBCO_preferred-orientation.ipynb)
  – the basic pattern with **March–Dollase preferred orientation**
  (r = 1.2, random fraction 0.3, axis [0 0 1]) at FullProf's own scale,
  nothing fitted — and the uncorrected pattern held outside the pins.

### PbSO4 structure

- [pd-neut-cwl PbSO4 basic](pd-neut-cwl_PbSO4_basic.ipynb) –
  **pseudo-Voigt** profile on the **orthorhombic Pnma** cell (all
  three cell edges independent — the corpus's first non-cubic CW
  page), no correction models.
- [pd-neut-cwl PbSO4 Bérar-Baldinozzi asymmetry](pd-neut-cwl_PbSO4_beba-asymmetry.ipynb)
  – **pseudo-Voigt × Bérar-Baldinozzi asymmetry** against **cryspy**
  (unfitted), and against FullProf only through diffraction-lib issue
  166's inferred coefficient map or after an asymmetry-only fit, all at
  one 180° limit angle.

### Y2O3 structure

- [pd-neut-cwl Y2O3 isotropic ADPs](pd-neut-cwl_Y2O3_isotropic-adp.ipynb)
  – pure-Gaussian **pseudo-Voigt** profile with isotropic ADPs and
  excluded regions.

## Powder, X-ray, Constant Wavelength

### LiF structure

- [pd-xray-cwl LiF single](pd-xray-cwl_LiF_single.ipynb) – Cu Kα₁
  **pseudo-Voigt** baseline with no polarization or absorption, the scattering
  sources declared as FullProf-comparable (`it1992` f₀, `sasaki1989`
  dispersion).
- [pd-xray-cwl LiF single polarization](pd-xray-cwl_LiF_single_polarization.ipynb)
  – the same pattern with the monochromator **polarization** factor
  (`setup_polarization_coefficient` 0.5, `setup_monochromator_twotheta` 26.565°;
  FullProf `Rpolarz`, `Cthm` 0.8).

## Powder, Neutron, Time-Of-Flight

### Diamond structure

- [pd-neut-tof diamond DREAM](pd-neut-tof_diamond_dream.ipynb) –
  **Jorgensen (back-to-back exponentials ⊗ Gaussian)** profile against a
  FullProf reference fitted to McStas-simulated DREAM (ESS) data, with a
  90° bank, a linear `d_to_tof` calibration and excluded regions.

### Fe structure

- [pd-neut-tof Fe pseudo-Voigt](pd-neut-tof_Fe_pseudo-voigt.ipynb) –
  the **non-convoluted pseudo-Voigt** profile (`tof-pseudo-voigt`,
  FullProf "Npr=7"), no back-to-back exponentials.

### Ferrite and austenite, two phases

- [pd-neut-tof ferrite and austenite, BEER joint](pd-neut-tof_ferrite-austenite_beer_joint.ipynb) –
  **two phases summed** in each of two banks, calculated and fitted jointly; no reference
  comparison yet (the owner's FullProf project comes with shared-parameter constraints).

### NCAF structure

- [pd-neut-tof NCAF Jorgensen-Von Dreele (Gaussian)](pd-neut-tof_NCAF_jorgensen-von-dreele.ipynb)
  – **Jorgensen-Von Dreele (back-to-back exponentials ⊗ pseudo-Voigt)**
  profile with the Lorentzian terms (γ₀, γ₁, γ₂) forced to zero, i.e.
  the Gaussian case (FullProf "Npr=9").

### Si structure

- [pd-neut-tof Si Jorgensen](pd-neut-tof_Si_jorgensen.ipynb) –
  **Jorgensen (back-to-back exponentials ⊗ Gaussian)** profile (FullProf
  "Npr=9", Gaussian limit).
- [pd-neut-tof Si Jorgensen-Von Dreele](pd-neut-tof_Si_jorgensen-von-dreele.ipynb)
  – **Jorgensen-Von Dreele (back-to-back exponentials ⊗ pseudo-Voigt)**
  profile with Lorentzian terms (FullProf "Npr=9").
- [pd-neut-tof Si Jorgensen-Von Dreele + size/strain](pd-neut-tof_Si_jorgensen-von-dreele-size-strain.ipynb)
  – **isotropic microstructural size/strain broadening** on the
  Jorgensen-Von Dreele profile (`size_g`/`strain_g`,
  `size_l`/`strain_l`).
