# pd-neut-cwl_cosio-d20_2k: provenance

## Sources

- **Data:** the D20 (ILL) pattern at 2.344 K, `002p3440_all594631.dat` of the 213-file Co₂SiO₄ temperature scan
  `cosio-d20-scan-213f.zip` in `easyscience/diffraction` (`data/measured/`, zip sha256
  `1bd6e37d693fd47a5ff7e95e86aeb94eb8f645c8fd44fed31ab8d7255b377e23`; file sha256
  `eb0b0ebdefb0b2225cebd3d7c244d5c94132b181cd367bbba001841f89961578`), licence BSD-3-Clause. Its 1506 points with a
  non-zero uncertainty are read unchanged into the experiment's `_data` loop; the two last points, with zero
  uncertainty, are left out.
- **Model:** the nuclear structure of `pd-neut-cwl_cosio-d20`, with the cell, coordinates, zero shift and profile terms
  of a FullProf 8.40 fit of this pattern (Thompson-Cox-Hastings pseudo-Voigt), the displacement parameters of a FullProf
  fit of the 56.8 K pattern (Co1 and Co2 share one value), and the magnetic structure of ISODISTORT's description of
  Co₂SiO₄ in Pnma.1 (irrep mGM1+): its eight operators and the moments of that FullProf fit.
- **Reference:** A. Sazonov et al., *Magnetic behaviour of synthetic Co₂SiO₄*, Acta Cryst. B65 (2009) 664–675.
- **Excluded:** 0–6° and 150–180°, and 64.65–64.74°, which holds only the dead D20 detector cell at 64.6953°.
- **Background:** sixteen points, none between 7.6° and 12.6°, so none sits under the first magnetic peak.
- **Expected values:** `expected.json` holds FullProf's fit of the same pattern, background and magnetic model
  (`knowledge/fitting/fullprof/pd-neut-cwl_cosio-d20_2k/`): Rwp within 8 % of FullProf's 5.47 %, and the three
  well-determined moment components within 0.15 μB of FullProf's, about three of its standard deviations. The profile
  models differ (Bérar-Baldinozzi pseudo-Voigt here, Thompson-Cox-Hastings in FullProf), which is why Rwp gets the
  wider margin. Co1's Mz is not compared: powder data barely determine it.
