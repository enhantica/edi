# Independent structure inputs

The cubic P1 input has an Fe atom at the centre and six O atoms one Å along the Cartesian axes around it. The cell
edge is 4 Å. With a 0.1 Å minimum distance and a 0.15 Å increment over the published covalent radii (Fe 1.32 Å,
O 0.66 Å), the independent Euclidean construction gives six Fe–O distances of 1 Å and twelve O–O distances of √2 Å.
The bonded variant states those cutoffs explicitly for appearance witnesses.

[generate.py](generate.py) derives the pair list and copies the supported type keys from the supplied engine source's
committed scattering tables. Neutrons cover Rauch's extended table and Sears (1992); X-rays state Waasmaier–Kirfel
(1995), with no anomalous dispersion. The table digests are recorded in `reference.json`. No app output is an oracle.
