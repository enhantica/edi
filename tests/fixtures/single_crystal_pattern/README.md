# Independent single-crystal pattern inputs

The P1 structure has one cobalt atom at the origin with unit occupancy and zero displacement. Its orthorhombic cell
is 4.3, 5.1 and 6.7 Å. The magnetic variant has a 2 μB moment along c and the Co²⁺ Brown form factor with no j₂ term.
The four measured reflections are explicit inputs, including one parallel to the moment, whose perpendicular magnetic
contribution vanishes.

[generate.py](generate.py) writes these inputs and `reference.json` without importing the app. It uses the reciprocal
cell metric, Sears (1992) b(Co) = 2.4900 fm, Brown's Co²⁺ coefficients from the supplied engine source's committed data,
and the CODATA 2018 magnetic-moment and electron-radius constants. F² is expressed in 10⁻²⁴ cm²; 1 fm = 0.1 × 10⁻¹² cm.
For an unpolarised beam, nuclear and perpendicular magnetic F² add. F uses the square root of the cumulative total.
