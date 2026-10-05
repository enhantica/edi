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

Two things differ, because edi cannot express them yet:

- FullProf ties the peak widths of the two phases within a pattern with shared codes. edi has one set per bank,
  so the project takes phase 1's (ferrite) values, which differ from austenite's by at most 0.02 %.
- FullProf shares one B iso between the two Fe sites (code 81). Here each site's B iso is free on its own, so the
  fit has one free parameter more than FullProf's 75.

## Check run

`python -m edi fit <copy> --dry --report machine --verbosity full`: `status=done`, `n_free=76`,
`n_points_fitted=5642`, `iterations=3`, `reduced_chi_square=6.926083272`, `rwp=0.07147118444`, under a second.
The starting values give Rwp 0.0726. FullProf's fit of the same project prints Rwp 7.06 % (S2) and 6.84 % (N2).

## expected.json

| quantity | kind | source |
| --- | --- | --- |
| `n_free` | reference | the `.pcr`'s 75 refined parameters, plus one for the B iso edi does not share |
| `iterations`, `reduced_chi_square`, `rwp` | regression pin | the check run above |

No value is compared with FullProf's fitted parameters yet. That comparison needs the shared B iso.
