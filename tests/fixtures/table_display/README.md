# Table display witnesses

The expected strings come from the owner's declared display rule: values with magnitude at least 1e6, or nonzero magnitude below 1e-4, use four significant digits in scientific notation. Values at 1e-4 and zero remain plain. The scientific value keeps its display precision as a narrow cell clips its end. The supplied background value 22900000 with s.u. 100000 must display as `2.290e7` and `0.010e7`; editing shows `22900000`.

| Supplied value | Display |
| --- | --- |
| 999999 | 999999 |
| 1000000 | 1.000e6 |
| 0.0001 | 0.0001 |
| 0.00009999 | 9.999e-5 |
| 0 | 0 |
| -1000000 | -1.000e6 |
| -0.00001 | -1.000e-5 |
| 22900000 | 2.290e7 |

The project is the small, independently supplied message-wrapping project with its first background intensity replaced by the stated value and s.u. It is a display input, not a calculated reference.

The QML checks measure the live atom table's numbering width and equal coordinate/occupancy widths at two sidebar widths, exercise its live category picker and free-parameter cells, and inspect the actual background cell's s.u. and editing text. The JavaScript runner separately invokes the real QML functions for threshold arithmetic and all four zero/nonzero combinations of sequential ok/fail counts. It supplies only Qt's translation helper and named colour tokens; it does not reproduce the number formatter or the count formatter.
