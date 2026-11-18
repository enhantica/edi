# Independent structure inputs

The cubic P1 input has an Fe atom at the centre and six O atoms 2.04006 Å along
the Cartesian axes around it. The cell edge is 6 Å. With a 0.1 Å minimum distance
and a 0.15 Å increment over the published covalent radii (Fe 1.32 Å, O 0.66 Å),
the independent Euclidean construction gives six Fe–O distances of 2.04006 Å.
O–O distances start at √2 × 2.04006 Å and exceed their covalent cutoff.
All six Fe–O neighbours are in the same nearest-neighbour shell; this avoids assuming
that crysta bonds more distant coordination shells merely because covalent radii overlap.
Reducing the increment to 0.01 Å removes those six bonds (2.04006 > 1.99);
restoring it and raising the minimum to 2.1 Å removes them by the other cutoff.
The nontrivial distance also exercises the dictionary's four-decimal display rounding.
The bonded variant states the original cutoffs explicitly for appearance witnesses.

[generate.py](generate.py) derives the pair list and copies the supported type keys from the supplied engine source's
committed scattering tables. Neutrons cover Rauch's extended table and Sears (1992); X-rays state Waasmaier–Kirfel
(1995), with no anomalous dispersion. The table digests are recorded in `reference.json`. No app output is an oracle.


`generate_polyhedra.py` enumerates declared lattice translations using only Python Cartesian
arithmetic. Orthogonal cells have axes 2,20,20 Å; skew cells have columns (2,0,0),
(6,2,0),(0,0,20) Å. Explicit radii are 5 and 2.5 Å; bond-derived radii are the
actual centre-to-corner Euclidean lengths. The largest radius is below 19 Å.
For the orthogonal examples |b|≤2 and |c|≤2 suffice, with |a|≤10; for the skew
examples |b|≤3 and |c|≤1 suffice and x=2a+6b+x_site bounds |a|≤12.
The enumeration box |a|≤20, |b|≤3, |c|≤2 therefore contains every qualifying image,
including images requiring translations outside the old adjacent-cell cube.
Inside-cell inputs have three corners and enclose no volume. Separate tilted square
and hexagon controls lie in z=x+2y and enclose no volume. Unit octahedron and cube
volumes are 4/3 and 8; their closed triangulations have 8 and 12 faces respectively.
