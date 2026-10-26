# pd-xray-cwl_pbso4-lab: provenance

Built by `tools/cli_projects/build_catalogue_projects.py` (`catalogue_cw_cases.py`), with the structure and the
experiment settings of the joint PbSO4 case (`catalogue_joint.py`).

## Sources

- **Data:** the laboratory X-ray pattern of the Rietveld round robin (R. J. Hill, J. Appl. Cryst. 25, 589 (1992)), as
  `pd-xray-cwl_pbso4-lab_round-robin` carries it, read from its `_data` loop unchanged: the 6001 points of
  diffraction-lib's dataset `meas-pbso4-xray` (`data/measured/pbso4-xray.xys` in `easyscience/diffraction` at commit `3ec801667904578ea39f1a4f4aa941866543a669`, sha256
  `1d4508a6296bc00f1858d1833502cb524394c80900f986f2771df1d6ad797855`), licence BSD-3-Clause.
- **Model:** diffraction-lib's tutorial `refine-pbso4-xray` (develop `cb2cda7b`) and the round-robin project: PbSO4 in
  `P n m a`, Cu Kα1 and Kα2 (1.54056 and 1.5444 Å, ratio 0.5), the round-robin project's polarization (0.5, monochromator
  26.565°), excluded regions 0-15° and 160-180°, a six-term Chebyshev background. The peak shape is edi's pseudo-Voigt
  with Bérar-Baldinozzi asymmetry, with a mixing parameter where the tutorial's profile has a Lorentzian width; the
  tutorial uses polarization 0.58 with a 28° monochromator.

## The start

- **Start:** zero shift 0; U, V, W at one significant figure (0.02, -0.02, 0.008), mixing 0.5, asymmetry 0; Biso 0.5 on
  every site; coordinates of the round-robin structure rounded to two decimals; cell 8.47, 5.39, 6.95 Å; scale 0.001;
  a flat background (the constant Chebyshev term at the level read off the pattern, the others 0).
- **Free (33):** the cell, the 11 free coordinates, the five Biso, U, V, W, the mixing, two asymmetry terms, the zero
  shift, the scale and the six Chebyshev terms. The tutorial keeps the coordinates and Biso fixed; here they start
  rounded, so they are free.
- **Left out:** the tutorial's minimizer settings; edi uses crysta.
