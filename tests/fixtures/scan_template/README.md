The three D20 scan data files and model are copied without changes from the
crysta fitting corpus at `tests/fitting/cosio-d20-scan-3f/project`. Its FullProf
and diffraction-lib provenance is retained by that corpus. `generate.py` takes
a crysta source checkout and reproduces this input. The tests compare measured
points to these files and use parameter preservation as an invariant.
