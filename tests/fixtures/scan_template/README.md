The three D20 scan data files and model are copied without changes from the
crysta fitting corpus at `tests/fitting/cosio-d20-scan-3f/project`. Its FullProf
and diffraction-lib provenance is retained by that corpus. `generate.py` takes
a crysta source checkout and reproduces this input. The tests compare measured
points to these files and use parameter preservation as an invariant.

Before: the five-coefficient Thompson–Cox–Hastings profile used the historical
pseudo-Voigt token. After: `generate.py --update-profile` changes only its token
to `cwl-tch-pseudo-voigt`; every coefficient, observation, uncertainty and other
fixture byte remains frozen. The separate Caglioti/mixing pseudo-Voigt profile
does not own the Lorentzian X/Y coefficients.

**Excluded rows rewritten ([ADR-0044](../../../docs/dev/adrs/0044-pattern-charts-and-excluded-regions.md)).** Each excluded `_data` row now has the d-spacing computed from the
file's own instrument, written like the file's other d values, and `.` for `intensity_calc` and `intensity_bkg`
instead of `0.`. Included rows are unchanged, and the recorded hashes of these files moved with them.
