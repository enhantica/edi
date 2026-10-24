# pd-neut-xray-cwl_pbso4-d1a-lab — provenance

PbSO4 from the Rietveld round robin (R. J. Hill, J. Appl. Cryst. 25, 589, 1992), fitted against two patterns at once:
the D1A (ILL) constant-wavelength neutron pattern and the laboratory Cu Kα X-ray pattern. One structure is linked to
both experiments, so the X-ray pattern fixes the cell. The neutron wavelength stays at D1A's 1.91 Å, as in FullProf's
reference fit.

## Sources

| file | origin |
| --- | --- |
| `data/pbso4-d1a.xys` | diffraction-lib's dataset `meas-pbso4-d1a` (`measured/pbso4-d1a.xys`) |
| `data/pbso4-xray.xys` | diffraction-lib's dataset `meas-pbso4-xray` (`measured/pbso4-xray.xys`) |
| `project/` | built by `tools/cli_projects/build_catalogue_projects.py` from the two files above |

Both files come from the data repository `easyscience/diffraction` at commit
`3ec801667904578ea39f1a4f4aa941866543a669`, licensed BSD-3-Clause, and match the sha256 its `index.json` records:

| file | sha256 |
| --- | --- |
| `pbso4-d1a.xys` | `0ebfd3ed320a908a6c9418cac927d2e2ef47e168ad1d9b84bfe67d191826fdf8` |
| `pbso4-xray.xys` | `1d4508a6296bc00f1858d1833502cb524394c80900f986f2771df1d6ad797855` |

They hold the same points as the D1A and X-ray patterns of `pd-neut-cwl_pbso4_beba-asymmetry` and
`pd-xray-cwl_pbso4-lab_round-robin`. The model follows diffraction-lib's tutorial `refine-pbso4-joint` (develop
`cb2cda7b`): space group, cell start, wavelengths, background positions, excluded X-ray regions and the joint fit.

## The start

The project starts the way a user's own measurement would: zero shift 0 on both patterns, the peak profile only roughly
right (U, V, W to one significant figure, mixing 0.5, asymmetry 0), Biso 0.5 on every site, the coordinates of the
round-robin structure rounded to two decimals, and a flat background at the level read off each pattern (the tenth
percentile of the fitted intensities: 200 counts for D1A, 140 for the X-ray pattern). The free set is what a user fits
here: the cell, every free coordinate and Biso, both scales and zero shifts, both profiles with their asymmetry, the
eight D1A background points and the six Chebyshev terms of the X-ray background (51 parameters). The neutron wavelength
is fixed, as FullProf's reference fit keeps it, so the two programs fit the same model.

## Differences from the tutorial

- The tutorial fixes the profile and background at a converged fit and frees only the cell, Biso, scales, zero shifts
  and neutron wavelength; here they start rough and are free, and the wavelength is fixed.
- diffraction-lib's Bérar-Baldinozzi profile has the Thompson-Cox-Hastings Lorentzian terms; edi's has a pseudo-Voigt
  mixing parameter (`mixing_eta_0`) in their place.
- The X-ray polarization (coefficient 0.5, monochromator 2θ 26.565°) and the Bérar-Baldinozzi limits (180° neutron,
  160° X-ray) and profile cutoffs are those of edi's two single-pattern PbSO4 projects, which were checked against
  FullProf; the tutorial gives 0.58 and 28°.
- The tutorial's minimizer tolerance setting is left out; edi fits with its own minimizer.
