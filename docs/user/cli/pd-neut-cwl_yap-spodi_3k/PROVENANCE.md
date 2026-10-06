# pd-neut-cwl_yap-spodi_3k — provenance

YAlO3 and corundum Al2O3 in one constant-wavelength neutron pattern from SPODI (FRM II), fitted as two phases.

## Starting values

**Built, not copied**, by `tools/cli_projects/build_yap_project.py` from the owner's FullProf project in
`knowledge/fitting/fullprof/pd-neut-cwl_yap-spodi_3k/` (its `PROVENANCE.md` names every file's sha256). Every value
is the committed `.pcr`'s own number, which is FullProf's converged fit, free where its code is non-zero:

| edi | FullProf |
| --- | --- |
| `_peak.type cwl-pseudo-voigt-berar-baldinozzi` | `Npr` 5 with Asy1..Asy4, shared by both phases |
| `_peak.broad_gauss_u`, `_v`, `_w` | `U`, `V`, `W` |
| `_peak.mixing_eta_0`, `_peak.mixing_eta_1` | `Shape1` (Eta0), and `X` fixed at 0 |
| `_peak.asym_beba_*` | Asy1..Asy4 through diffraction-lib issue 166's map `(-P1 - 3·P2, -P2, -P3 - 3·P4, -P4)` |
| `_peak.asym_beba_limit` | `AsyLim`, 160 |
| `_peak.cutoff_fwhm` | `Wdt`, 20 |
| `_absorption.type cylinder-hewat`, `_absorption.mu_r` | `muR`, 0.0221, fixed |
| `_atom_site.occupancy` | 1: a `.pcr` `Occ` is occupancy x site multiplicity / general multiplicity |
| background points | the 25 points of the `.pcr`, all free |
| excluded regions | the `.pcr`'s 0-4 and 153.95-180 |

The data are the points FullProf fits, 4.05° to 151.95° (2959). FullProf reads from 2.3°, but below 4° every count
and sigma is zero and excluded; edi refuses a zero sigma, so those points are left out. The fit has FullProf's 56
free parameters. Al2O3's Al1 starts at FullProf's negative B iso, -0.13591, admitted with a warning.

## Check run

`python -m edi fit <copy> --dry --report machine --verbosity full`: `status=done`, `n_free=56`,
`n_points_fitted=2959`, `iterations=23`, `reduced_chi_square=9.731184512`, `rwp=0.04051978146`, about a second.
FullProf's fit of the same project prints Rwp 4.08 % and χ² 9.88.

## expected.json

| quantity | kind | source |
| --- | --- | --- |
| `n_free` | reference | the `.pcr`'s 56 refined parameters |
| `n_points_fitted` | reference | `yap_3k.sum`, `N-P+C = 2903` plus the 56 free parameters |
| `rwp` | reference | `yap_3k.sum`, Rwp 4.08 %, within 5 % relative |
| `iterations`, `reduced_chi_square` | regression pin | the check run above |

Most fitted values lie within FullProf's standard uncertainty of FullProf's own. The four asymmetry coefficients are
not comparable: FullProf's convention differs from the paper's (diffraction-lib issue 166), and the map above is
inexact.
