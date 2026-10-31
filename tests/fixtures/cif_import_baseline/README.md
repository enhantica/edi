# CIF import references

Syntax follows the [IUCr CIF 1.1 specification](https://www.iucr.org/what-we-do/digital-standards/cif/cif1/file-syntax).
The existing vendored core and powder dictionaries supply published names. The product
dictionary and category census supply only the exhaustive population, never expected values.

The authored values come from the input tokens. Tensor controls use ITA groups P1, 221 and
149; Ueq is trace(U)/3 in the orthogonal cell. An isotropic tensor in hexagonal axes has
U11 = U22 = U33 = 0.02, U12 = 0.01. Its source-frame back transformation uses the inverse
integer rotation; the transpose does not preserve it. B = 8 pi² U and beta = 2 pi² N U N.
These are the conversion conventions documented by cctbx adptbx and sgtbx.

`generate_metadata.py` freezes the original tracked records and their scientific-byte hashes.
Expected descriptions follow the experiment-description conversion table. The mixed-probe
PbSO4 override assigns D1A/ILL to its neutron experiment and unknowns to its laboratory one.
`generate_readers.py` captures main-reader output as labelled regression pins. Neither
file claims that engine output is an independent physical oracle. Regenerate these only
on the intended pre-change main tree, before the migration or import implementation.
