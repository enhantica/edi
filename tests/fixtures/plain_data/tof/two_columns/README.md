Constructed by hand for the plain-data contract.

Input rows, including rejected rows, are in `pattern.xy`. `expected.json` lists
the exact retained triples and counts. Positive square intensities 4, 9 and 16
give sigma 2, 3 and 4 when omitted. Intensity 0.25 gives sigma 1 under
sqrt(max(y, 1)), instead of diffraction-lib's 0.5. Supplied sigma remains
as written except the shared rule replacing values below 0.0001 by 1.
Zero and negative intensities are omitted for Bragg. Duplicate x retains the
first input row, before sorting. Reordered counts the retained rows whose
position changes after duplicate removal. CWL x is degrees; TOF x is 200 times
the CWL fixture x, in microseconds. No product reader generated these values.
