# Element tables — provenance

## `element-styles.tsv`

One row per element, H to Og (118 rows after the header), in the upstream order. The structure scene reads it through
`edi::element_style_table()` (ADR-0022), and so does the app's `AppColors.element()`: it is the only
source of element colours and radii in edi. `core/CMakeLists.txt` embeds the file in the core at build time.

| Column          | Meaning                                                                            |
| --------------- | ---------------------------------------------------------------------------------- |
| `symbol`        | The element symbol                                                                 |
| `jmol`          | The Jmol (CPK) colour, `#RRGGBB`                                                   |
| `vesta`         | The VESTA colour, `#RRGGBB`; empty for the 10 elements without one                 |
| `covalent`      | The covalent radius, Angstrom                                                      |
| `van_der_waals` | The van der Waals radius, Angstrom                                                 |
| `ionic`         | The representative Shannon ionic radius, Angstrom; empty for the 25 without one    |

| Field      | Value                                                                                                                      |
| ---------- | -------------------------------------------------------------------------------------------------------------------------- |
| Source     | diffraction-lib `src/easydiffraction/display/structure/assets/elements.py`, `ELEMENT_COLORS` and `ELEMENT_RADII`             |
| Commit     | `c0654956a1281f1ea3f3467c3367167f93edee18` (github.com/easyscience/diffraction-lib), the commit crysta's covalent radii come from |
| Source SHA-256 | `45cb1a5b03c60104169e7bdb9676d9dc3eca4d43cdccd758416b4c2f4649070b` (the file at that commit)                            |
| Extracted | 2026-10-02, |
| SHA-256    | `b13e76724501bcae9c8455606ae2bcf128c219ac38ea24d4d72e148cf5c845ae`                                                           |

**Its sources**, per diffraction-lib's `display/structure/assets/LICENSES.md` at the same commit:

| Data                                         | Published source                                                                                           | Licence      |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ------------ |
| Jmol colours, covalent and van der Waals radii | EasyDiffractionBeta `easyDiffractionApp/Logic/Tables.py`, `PERIODIC_TABLE` (github.com/easyscience/EasyDiffractionBeta) | BSD-3-Clause |
| VESTA colours                                | pymatgen `src/pymatgen/vis/ElementColorSchemes.yaml`, `VESTA`; K. Momma and F. Izumi, J. Appl. Cryst. 44 (2011) 1272 | MIT          |
| Ionic radii                                  | pymatgen `dev_scripts/periodic_table_resources/Shannon_Radii.csv`; R. D. Shannon, Acta Cryst. A32 (1976) 751, one representative row per element by the selection rule of diffraction-lib's `LICENSES.md` | MIT          |

diffraction-lib itself is BSD-3-Clause. The values are scientific data.

**Extraction.** The values are copied, never recomputed:

```
git -C <diffraction-lib> show c0654956:src/easydiffraction/display/structure/assets/elements.py \
  | python3 -c "import sys; ns = {}; exec(sys.stdin.read(), ns); R, C = ns['ELEMENT_RADII'], ns['ELEMENT_COLORS']; \
      h = lambda c: '' if c is None else '#%02X%02X%02X' % tuple(c); f = lambda v: '' if v is None else repr(v); \
      print('symbol\tjmol\tvesta\tcovalent\tvan_der_waals\tionic'); \
      [print('\t'.join([s, h(C[s]['jmol']), h(C[s]['vesta']), f(r['covalent']), f(r['vdw']), f(r['ionic'])])) \
       for s, r in R.items()]" > data/elements/element-styles.tsv
```

**The covalent column equals crysta's** `data/elements/covalent-radii.tsv` (crysta's bond rule, the same commit) for
every element. A crysta SDK update that changes crysta's table fails edi's gate until this file follows.

**What is not here.** The upstream `atomic` radii: no view uses them. Deuterium (`D`) is in no table and takes the
fallbacks (pink, 1.0 Angstrom), as in diffraction-lib and in crysta's bond rule.
