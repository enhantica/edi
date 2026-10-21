# Colour maps — provenance

## `viridis.tsv`

The 2D map of a sequential fit's patterns colours intensity with this map (ADR-0041). One row per colour, 256 rows
after the header, from the low end to the high end. `cmake/edi_core_sources.cmake` embeds the file in the core, and
`edi::scan_map_colour()` reads it.

| Column   | Meaning                                    |
| -------- | ------------------------------------------ |
| `index`  | The colour's place, from 0 (the low end)   |
| `colour` | The colour, `#RRGGBB`                      |

| Field   | Value                                                                                                      |
| ------- | ---------------------------------------------------------------------------------------------------------- |
| Source  | matplotlib 3.11.0, `lib/matplotlib/_cm_listed.py`, `_viridis_data` (256 RGB triples in [0, 1])             |
| Authors | Nathaniel J. Smith, Stéfan van der Walt and Eric Firing (github.com/BIDS/colormap, `colormaps.py`)      |
| Licence | CC0 1.0: "This file and the colormaps in it are released under the CC0 license / public domain dedication" (the header of `colormaps.py`); no notice is required |

**Conversion.** Each triple is scaled by 255 and rounded to the nearest integer, then written as `#RRGGBB`:

```
python3 -c "import ast, sys; src = open(sys.argv[1]).read(); \
  data = [ast.literal_eval(n.value) for n in ast.parse(src).body \
          if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') == '_viridis_data'][0]; \
  print('index\tcolour'); [print(f'{i}\t#' + ''.join('%02X' % round(c * 255) for c in rgb)) for i, rgb in enumerate(data)]" \
  <matplotlib>/_cm_listed.py > data/colormaps/viridis.tsv
```

The ends are `#440154` and `#FDE725`.
