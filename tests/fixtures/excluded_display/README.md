# Excluded pattern inputs

`generate.py` uses only Python's standard library. Each grid has leading,
interior and trailing closed excluded intervals. The CW d-spacing reference is
Bragg's inverse at wavelength 1.54 Å, on the raw measured angle despite the
nonzero instrument offset. The TOF reference solves
`t = 37 + 5000 d + 2.5 d²` using its positive root.

Measured intensities and uncertainties are authored analytic inputs. They are
not predictions of a fitted structure. The cubic phase supplies reflections
inside and outside the interior gap. `cw-scan` repeats the CW observations in
two files to exercise the scan chart path.
