#  NCAF five-bank I/O fixture

This directory freezes the five-bank, TOF-Jorgensen NCAF EasyDiffraction project used by the
 I/O gates. The project bytes are copied from crysta's pinned
`tools/spikes/ncaf_5bank_edi_converged_jorgensen` vehicle; `manifest.json` records the pin and a
SHA-256 for every frozen input.

`ncaf.cif` is an EDI-derived regression twin of the project's `structures/ncaf.edi`: it uses
standard CIF tags but preserves the same later refined cell, sites, occupancies, and isotropic B
values. Its only correctness claim is exact CIF-vs-project representation parity.

`published_cod_1000236.cif` is the separate, genuinely independent structural oracle: the exact
public-domain COD revision 130149 bytes for Courbion & Férey, *J. Solid State Chem.* **76** (1988)
426–431, DOI `10.1016/0022-4596(88)90239-3`. The hidden gate hand-pins its published 10.257(1) Å
cell, six sites, occupancies, and anisotropic U diagonals. Because edi's model represents an
isotropic B value, the expected published ADP is calculated only by the crystallographic closed
form `B_eq = 8π²(U11 + U22 + U33)/3`; no value comes from the EDI fixture or implementation.

`crysta_reference.json` is produced by compiling `oracle/crysta_snapshot.cpp` against edi's
installed, pinned `crysta::crysta` package and invoking crysta's own directory loader. It is an
independent loader snapshot, not output from edi.

Regenerate from an already materialised pinned crysta source/build:

```bash
PIXI_CACHE_DIR=/tmp/edi-pixi-cache UV_CACHE_DIR=/tmp/edi-uv-cache \
  ~/.pixi-conda/bin/pixi run python tests/fixtures/e02_t2_ncaf_5bank/generate.py
```

Generation is offline. It refuses a crysta source checkout or installed package whose SHA differs
from `build/crysta-src/CRYSTA_SOURCE_SHA`.
