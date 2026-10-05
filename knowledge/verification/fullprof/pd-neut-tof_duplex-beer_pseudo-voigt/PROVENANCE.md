# BEER duplex FullProf archive, inactive

Owner-supplied BEER duplex project: ferrite and austenite, two neutron
TOF banks at 90 degrees, Npr 7 pseudo-Voigt. This archive is INACTIVE: no
test, fitting-corpus entry or verification page compares against it. It will
be activated only when shared site-parameter constraints are available.

FullProf.2k 8.40 (Feb2026-ILL JRC). Executable: `~/Applications/fullprof/fp2k`.
One authoring-time invocation, in the fitting home:
`printf 'duplex_mode6-IRF\n\n' | ~/Applications/fullprof/fp2k > full-fit.out 2>&1`.
No test runs FullProf. `owner-input.inp` retains the original owner PCR bytes.
`full-fit.inp` records the exact run input: only the two data paths were made
local and Pcr changed from 1 to 2 to preserve the input and write `.new`.
The number of fitted variables, all parameter values and codes are retained.

FullProf Occ = site occupancy * site multiplicity / general multiplicity.
The fully occupied ferrite Fe site is 2a of I m -3 m: 2/96 = 1/48.
The fully occupied austenite Fe site is 4a of F m -3 m: 4/192 = 1/48.
Both owner Occ values are 0.02083, their five-decimal representation of 1/48;
this is not a partial physical occupancy. No occupancy or scale was restated.
Both Fe Biso parameters share code 81 in the fitting input and `.new`.
That shared parameter constraint must be preserved when verification is
activated; this archive does not activate it.

SHA256 proves both owner data files byte-identical to the existing measured
BEER data under `tests/fixtures/multiphase/beer/data/`. Both homes link to that
single copy with local `.dat` names. No additional data copy is committed.

This is the all-fixed twin at the `.new` values. Every background, calibration,
atom, scale, profile, cell and preferred-orientation code is zero, and the
declared parameter count is zero. `capture_fullprof_beer.py` creates it without
running FullProf. The two profiles and summary are copied from the SINGLE
fitting invocation's final state; they are not claimed as a separate twin run.

Executable SHA256: `b8cb5cdb00ef55f2fef9004ef070324a459f2fcc92ad5c4613f2ea06118c9f1f`.

File SHA256:

- `Duplex_in_HR_for_IRF_N2.dat` `c4166d5ced0595d814ce99cb5a8e032ee83e1a26a575172d5c1609a7f1361bf2`
- `Duplex_in_HR_for_IRF_S2.dat` `cfa0e32227587856d96e1d0936783be310cdf756a6f09aacd9da72a82612ebc4`
- `duplex_mode6-IRF.pcr` `b2d26c89fed1796cbcf8338f519b87f5c9c6d2dcb7b2b0f67ae030c006d73abb`
- `duplex_mode6-IRF.sum` `b56260fe0d7e18d31cbcb0c6de6ef9613d56bba3eafc763de59499291d19fcd9`
- `duplex_mode6-IRF_1.prf` `f93e259664a1ba3cbdd0e18df21d72ef84d556f147a6891f9be1f466b183d2d8`
- `duplex_mode6-IRF_2.prf` `3e4c20ed69b63084e188e5bf3093d85233c8e35727460fbc3f9fa2f9a9f998ef`
