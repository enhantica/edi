# Type IV synthetic references

The generator reads the BNS Wyckoff block and signed operators in the Stokes–Campbell
ISO-MAG table distributed by cryspy under its MIT licence. The shipped source is
`data/space-groups/cryspy_magnetic_data.txt.gz`, SHA-256 `dcc3f7451da30a8e3beee49d1ad91887f2ebe5db78a0e60866707e6588de9ba1`.
The table's coordinate and moment matrices, offsets and orbit multiplicities supply
`expected.json`. The generic independent coordinates are (13/100, 23/100, 31/100).
The synthetic cell has lengths (6, 7, 16) and right angles. Its parent is Pnma with
half its c length, k = (0, 0, 1/2). These inputs contain no fitted or product-generated values.

Run `python tests/fixtures/magnetic_type_iv/reference.py` in crysta to regenerate the
synthetic native files. The edi copies are the same synthetic files and expected constants.
The raw source's licence and citations are in crysta's `data/space-groups/PROVENANCE.md`.

The GUI projects are invented public Pnma, cubic and alternative-setting parents,
with explicitly written links, scales and texture. `generate_gui.py` rebuilds them.
`generate_graph.py` reads the public, independently written spglib census generator
from crysta's fixtures directory and freezes the full signed-class covering graph
for Hall 292 at k=(1/2,0,0) and (1/3,0,0). No product-derived graph is an oracle.
