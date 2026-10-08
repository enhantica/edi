# pd-neut-tof_ferrite-austenite-beer_joint — provenance

Ferrite and austenite (two Fe phases) against the two BEER (ESS) time-of-flight banks `expt_s2` and `expt_n2`,
fitted jointly.

## Starting values

The starting model is the owner's FullProf project, kept in
`knowledge/fitting/fullprof/pd-neut-tof_duplex-beer_pseudo-voigt/` (`owner-input.inp` is the original `.pcr`; that
folder's `PROVENANCE.md` names every file's sha256). FullProf pattern 1 is the S2 bank and pattern 2 the N2 bank.
The data are the same files FullProf read. Every value below is the `.pcr`'s own number, free where its code is
non-zero:

| edi | FullProf |
| --- | --- |
| `_instrument.calib_d_to_tof_offset`, `_linear` | `Zero` (free), `Dtt1` (fixed), per pattern |
| `_peak.broad_gauss_sigma_0`, `_1`, `_2` | `Sigma-0`, `Sigma-1`, `Sigma-2`: both use the variance `sigma2 d^4 + sigma1 d^2 + sigma0` |
| `_peak.broad_lorentz_gamma_0` | `Gamma-0` |
| `_peak.cutoff_fwhm` | `Wdt`, 12 |
| `_linked_structure.scale` | each phase's `Scale` in that pattern |
| `_atom_site.adp_iso` | `Biso`, 1.71513 |
| `_atom_site.occupancy` | 1: a `.pcr` `Occ` is occupancy x site multiplicity / general multiplicity (2/96, 4/192) |
| background points | the 31 points of each pattern; the last is fixed, as in the `.pcr` |
| excluded regions | the `.pcr`'s regions, the first ending at FullProf's TOF-min (40158.2305 µs) so that the fit uses the same points FullProf did |
| `_scattering_source.neutron_scattering_length` | `sears1992`, FullProf's own table |

FullProf shares one B iso between the two Fe sites (code 81). The project declares the same tie as a constraint,
`biso_austenite = biso_ferrite` in `analysis.edi`: ferrite's B iso is free and austenite's follows it, so the fit
has FullProf's 75 free parameters.

One thing differs: FullProf ties the peak widths of the two phases within a pattern with shared codes. edi has one
set per bank, so the project takes phase 1's (ferrite) values, which differ from austenite's by at most 0.02 %.

## Check run

`python -m edi fit <copy> --dry --report machine --verbosity full`: `status=done`, `n_free=75`,
`n_points_fitted=5642`, `iterations=3`, `reduced_chi_square=6.925333048`, `rwp=0.0714737332`, under a second.
FullProf's fit of the same project prints Rwp 7.20 % (S2) and 7.06 % (N2) over all non-excluded points.

Every fitted value is within FullProf's standard uncertainty of FullProf's own; the largest difference is bank N2's
first background point, -0.0174 against 0.025(129), 0.33 of its uncertainty, and the shared B iso is 1.7153 against
1.715(16). The tie holds in every step of the fit, as in FullProf; the earlier pins (`reduced_chi_square=6.925059031`,
`rwp=0.07147231917`) came from fits that applied it only to the result.

## expected.json

| quantity | kind | source |
| --- | --- | --- |
| `n_free` | reference | the `.pcr`'s 75 refined parameters |
| `iterations`, `reduced_chi_square`, `rwp` | regression pin | the check run above |

The fitted values are compared with FullProf's, within FullProf's standard uncertainties, by edi's FullProf
agreement test.
