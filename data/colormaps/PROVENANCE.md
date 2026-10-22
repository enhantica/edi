# Colour maps — provenance

The 2D map and the stacked patterns of a sequential fit take their colours from one of these maps, viridis by default
(ADR-0041). Each file has one row per colour, 256 rows after the header, from the low end to the high end.
`cmake/edi_core_sources.cmake` embeds the files in the core in its list's order, and `edi::scan_colour_table()` reads
them. Beside matplotlib's four, the files under "Candidates" are those the owner chooses from (2026-10-22); the ones not
chosen leave with their DEPENDENCIES.md rows.

## `viridis.tsv`, `magma.tsv`, `inferno.tsv`, `plasma.tsv`

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
`<name>` each of `viridis`, `magma`, `inferno`, `plasma`:

```
python3 -c "import ast, sys; src = open(sys.argv[1]).read(); \
  data = [ast.literal_eval(n.value) for n in ast.parse(src).body \
          if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') == '_' + sys.argv[2] + '_data'][0]; \
  print('index\tcolour'); [print(f'{i}\t#' + ''.join('%02X' % round(c * 255) for c in rgb)) for i, rgb in enumerate(data)]" \
  <matplotlib>/_cm_listed.py <name> > data/colormaps/<name>.tsv
```

The ends are `#440154` and `#FDE725` (viridis), `#000004` and `#FCFDBF` (magma), `#000004` and `#FCFFA4` (inferno),
`#0D0887` and `#F0F921` (plasma). The file this was run on, from tag v3.11.0, has SHA-256
`ddad3698f5129ceb1792a445371286c08bc9080298e657b3054aea19c9659ef9`; the command reproduces `viridis.tsv` byte for byte.

## Candidates

Each candidate's source table, its licence (in THIRD-PARTY-NOTICES, and a DEPENDENCIES.md row) and its conversion. A
256-row source is converted as above: each channel scaled by 255 and rounded, written as `#RRGGBB`. The sources were
fetched on 2026-10-22 at the commits named, of the repository each came from. `tempo`, `blues`, `purples`, `ylorrd`,
`cet-l17` and `cet-l18` start from a light colour, for the light theme (the owner, 2026-10-22); any map can also be
drawn reversed.

| Files | Source | Licence | Conversion |
| ----- | ------ | ------- | ---------- |
| `batlow`, `oslo`, `lajolla`, `acton`, `devon`, `lapaz` | Fabio Crameri's Scientific colour maps, `cmcrameri/cmaps/<name>.txt` of github.com/callumrollo/cmcrameri at `78f02a08` (256 RGB triples in [0, 1]) | MIT (Crameri) | as above |
| `thermal`, `haline`, `deep`, `dense`, `ice`, `tempo` | cmocean (Kristen Thyng), `cmocean/rgb/<name>-rgb.txt` of github.com/matplotlib/cmocean at `59c35002` | MIT | as above |
| `turbo` | Google's Turbo (Anton Mikhailov), `turbo_colormap_data` of gist `mikhailov-work/ee72ba4191942acecc03fe6da94fc73f` at `dccf2856` | Apache-2.0 | as above |
| `ylgnbu`, `pubu`, `gnbu`, `blues`, `purples`, `ylorrd` | ColorBrewer (Cynthia Brewer), the nine-class schemes of `colorbrewer_schemes.js` of github.com/axismaps/colorbrewer at `7d135fc4` | Apache-2.0 | the nine colours spread over 256: colour i at t = 8i/255 between the stops around it, mixed in Oklab as ADR-0038's gradients; the ends are the first and ninth colours |
| `cet-gouldian`, `cet-l08`, `cet-l06`, `cet-l17`, `cet-l18` | Peter Kovesi's CET perceptually uniform maps L20 (`linear_kbgoy_20-95_c57_n256.csv`), L08 (`linear_bmy_10-95_c78_n256.csv`), L06 (`linear_kbc_5-95_c73_n256.csv`), L17 (`linear_worb_100-25_c53_n256.csv`) and L18 (`linear_wyor_100-45_c55_n256.csv`) of github.com/holoviz/colorcet at `076eb84b`, `assets/CET` | CC-BY-4.0 (Kovesi, "Good Colour Maps: How to Design Them", arXiv:1509.03700) | as above |
