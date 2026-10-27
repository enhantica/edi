# Colour maps — provenance

The scan views' Map, and the stacked patterns when they take a colour map, use one of six maps (ADR-0041; the owner,
2026-10-26), listed in this order: Blue-Red (the default), Viridis, Batlow, Inferno, Lapaz and Greys. Blue-Red has no
file: the core mixes it from three stops per theme (below). Each file has one row per colour, 256 rows after the
header, from the low end to the high end. `cmake/edi_core_sources.cmake` embeds the files in the core in that order,
and `edi::scan_colour_map_table()` reads them. A map's name means its colours in this order; the Map's direction
(Auto, Normal or Inverted) decides which end takes the low values.

## Blue-Red

The chart's background, then blue, then red, each half mixed in Oklab (Björn Ottosson, 2020) as ADR-0038's gradients
are: `#FFFFFF`, `#3F7FBF`, `#C8323C` in the light theme and `#444444`, `#6AA6EA`, `#FC4F81` in the dark, the dark red
matching the dark theme's calculated curve. Colour i of 256 is at t = 2i / 255 along the first half, then along the
second. Designed for edi and approved by the owner on 2026-10-26.

## `viridis.tsv`, `inferno.tsv`

| Column   | Meaning                                    |
| -------- | ------------------------------------------ |
| `index`  | The colour's place, from 0 (the low end)   |
| `colour` | The colour, `#RRGGBB`                      |

| Field   | Value                                                                                                      |
| ------- | ---------------------------------------------------------------------------------------------------------- |
| Source  | matplotlib 3.11.0, `lib/matplotlib/_cm_listed.py`, `_<name>_data` (256 RGB triples in [0, 1] per map)    |
| Authors | Nathaniel J. Smith, Stéfan van der Walt and Eric Firing (github.com/BIDS/colormap, `colormaps.py`)      |
| Licence | CC0 1.0: "This file and the colormaps in it are released under the CC0 license / public domain dedication" (the header of `colormaps.py`); no notice is required |

**Conversion.** Each triple is scaled by 255 and rounded to the nearest integer, then written as `#RRGGBB`, for
`<name>` each of `viridis` and `inferno`:

```
python3 -c "import ast, sys; src = open(sys.argv[1]).read(); \
  data = [ast.literal_eval(n.value) for n in ast.parse(src).body \
          if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') == '_' + sys.argv[2] + '_data'][0]; \
  print('index\tcolour'); [print(f'{i}\t#' + ''.join('%02X' % round(c * 255) for c in rgb)) for i, rgb in enumerate(data)]" \
  <matplotlib>/_cm_listed.py <name> > data/colormaps/<name>.tsv
```

The ends are `#440154` and `#FDE725` (viridis) and `#000004` and `#FCFFA4` (inferno). The file this was run on, from tag v3.11.0, has SHA-256
`ddad3698f5129ceb1792a445371286c08bc9080298e657b3054aea19c9659ef9`; the command reproduces `viridis.tsv` byte for byte.

## `batlow.tsv`, `lapaz.tsv`, `greys.tsv`

Each source table, its licence (in THIRD-PARTY-NOTICES, and a DEPENDENCIES.md row) and its conversion. A 256-row source
is converted as above: each channel scaled by 255 and rounded, written as `#RRGGBB`. The sources were fetched on
2026-10-22 at the commits named, of the repository each came from.

| Files | Source | Licence | Conversion |
| ----- | ------ | ------- | ---------- |
| `batlow`, `lapaz` | Fabio Crameri's Scientific colour maps, `cmcrameri/cmaps/<name>.txt` of github.com/callumrollo/cmcrameri at `78f02a08` (256 RGB triples in [0, 1]) | MIT (Crameri) | as above |
| `greys` | ColorBrewer (Cynthia Brewer), the nine-class Greys scheme of `colorbrewer_schemes.js` of github.com/axismaps/colorbrewer at `7d135fc4`: `#ffffff`, `#f0f0f0`, `#d9d9d9`, `#bdbdbd`, `#969696`, `#737373`, `#525252`, `#252525`, `#000000` | Apache-2.0 | the nine colours spread over 256: colour i at t = 8i/255 between the stops around it, mixed in Oklab as ADR-0038's gradients; the ends are the first and ninth colours. The same conversion reproduces the Blues table edi shipped before byte for byte. |
