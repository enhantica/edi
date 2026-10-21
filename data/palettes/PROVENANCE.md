# Colour palettes — provenance

One table per palette, `edi-<name>.tsv`, in the order Preferences lists them: Edi Natural (the default), Edi Coast, Edi
Garden, Edi Studio and Edi Contrast (ADR-0038). The core embeds them at build time and reads them through
`edi::pattern_colour()`, `edi::structure_colour()` and `edi::role_colour()`, the only source of dataset, structure and
chart-role colours in edi: the app's charts and icons, the pattern presentation and the report all take them from
there. A report always takes the light colours.

The colours are the ones the owner approved on 2026-10-21, stored exactly; nothing generates, adapts or retunes them.
`tools/palettes/check.py` checks each table's shape and that the tables below list the same values; it writes nothing.

| Column  | Meaning                                                                                                   |
| ------- | --------------------------------------------------------------------------------------------------------- |
| `role`  | `measured`, `structure`, `total_calculation`, `background` or `difference`                                |
| `index` | The place, from 0, in the order the rows of that role are listed; 0 for the three role colours           |
| `light` | The colour in the light theme, `#RRGGBB`                                                                  |
| `dark`  | The colour in the dark theme, `#RRGGBB`                                                                   |

Measured colours are listed in the order blue, violet, green, raspberry, teal, and structure colours in the order
orange, gold, brown, amber, olive, the most distinct first. Up to five datasets, or five structures, take the first
colours of their group in order. More take a gradient over the whole group, from its first colour to its second, mixed
in the Oklab colour space (Björn Ottosson, 2020): item i of N, from zero, at t = i / (N − 1).

## Sources

The schemes the palettes take colours from, as the earlier eighteen schemes cited them:

| Source | Reference | Licence |
| ------ | --------- | ------- |
| Coast | edi's own (the default): sea blue, lagoon teal, leaf green, violet and cyan, with structure colours from the Design Seeds nature palettes by Jessica Colaluca (wheat, plum, rose, stone, sage). | designed for edi |
| Garden | edi's own, after akulakreative's garden greenery palette (December 2024: khaki, sand, clay) and the Design Seeds sea and lagoon palettes. | designed for edi |
| Peaceful | edi's own, after paperheartdesign's peaceful palettes (blue lake, fog teal, periwinkle, deep lagoon, plum; tan, khaki, lavender, stone, sand). | designed for edi |
| Fog forest | edi's own, after the Design Seeds fog and lake palettes by Jessica Colaluca (lake blue, forest green, fog teal, heather, sand; slate, sage, stone, mist, lichen). | designed for edi |
| Okabe-Ito | Okabe and Ito, *Color Universal Design* (2008), the eight colours as R's `palette.colors()` lists them, in the order edi has used them. | values published for free use |
| Paul Tol muted | Paul Tol, *Colour Schemes* (SRON/EPS/TN/09-002, 2021), muted. | values published for free use |
| Tableau 10 | Tableau 10 (Maureen Stone, Tableau, 2016), as d3-scale-chromatic lists it (`schemeTableau10`). | ISC |
| IBM Carbon | IBM's Carbon Design System, the categorical palettes for light and dark themes (carbon-website `palettes.js`). | Apache-2.0 |
| ColorBrewer Dark2 | ColorBrewer Dark2 (Cynthia Brewer, colorbrewer2.org), as matplotlib's `Dark2`. | Apache-2.0 |
| Petroff | Matthew Petroff, *Accessible Color Sequences for Data Visualization* (2021), the ten-colour sequence, matplotlib 3.10's `petroff10` style. | matplotlib licence |
| Nord | Nord (Arctic Ice Studio), its Frost and Aurora colours: nord10, nord14, nord15, nord8, nord13, nord7, nord9, nord12, nord11. | MIT |
| Solarized | Solarized (Ethan Schoonover), its accent colours: blue, green, violet, cyan, yellow, magenta, orange, red. | MIT |
| Catppuccin | Catppuccin, Latte in the light theme and Mocha in the dark, its accents: blue, green, mauve, teal, yellow, sapphire, lavender, then peach, pink, red, maroon, flamingo, rosewater, sky. | MIT |
| Apple | Apple's system colours, light and dark (Human Interface Guidelines, Color, https://developer.apple.com/design/human-interface-guidelines/color), as guidance: blue, green, indigo, cyan, purple, mint, yellow, teal, then orange, pink, red, brown. | guidance values |
| Catppuccin neutrals | Catppuccin's Overlay 2 (background) and Subtext 0 (difference), Latte in the light theme and Mocha in the dark, <https://catppuccin.com/palette/>. | MIT |
| Edi role grey | The shared background and difference greys of edi's own palettes. | designed for edi |

## Stored values

### Edi Natural

`edi-natural.tsv`. edi's own palette, kept unchanged from the study that chose it: every colour was designed for edi.

| Role | Place | Colour | Light | Light source | Dark | Dark source |
| ---- | ----- | ------ | ----- | ------------ | ---- | ----------- |
| measured | 0 | Blue | `#039EDC` | edi's own | `#71CBFE` | edi's own |
| measured | 1 | Violet | `#8989F7` | edi's own | `#C0B6E8` | edi's own |
| measured | 2 | Green | `#6EA163` | edi's own | `#A1CD97` | edi's own |
| measured | 3 | Raspberry | `#D475AD` | edi's own | `#FDA8CB` | edi's own |
| measured | 4 | Teal | `#479F93` | edi's own | `#81CAC2` | edi's own |
| structure | 0 | Orange | `#D26E3C` | edi's own | `#F59B6F` | edi's own |
| structure | 1 | Gold | `#958508` | edi's own | `#BAAD52` | edi's own |
| structure | 2 | Brown | `#936844` | edi's own | `#BD9372` | edi's own |
| structure | 3 | Amber | `#C28B0A` | edi's own | `#EBB352` | edi's own |
| structure | 4 | Olive | `#71964E` | edi's own | `#98BB79` | edi's own |
| total_calculation | 0 | Total calculation | `#CA5C6E` | edi's own | `#EE8795` | edi's own |
| background | 0 | Background | `#8A8A8A` | edi's own | `#969696` | edi's own |
| difference | 0 | Difference | `#737373` | edi's own | `#B0B0B0` | edi's own |

### Edi Coast

`edi-coast.tsv`. Measured colours led by the earlier Coast scheme's, with richer earth tones for structures, each taken unchanged from the scheme named.

| Role | Place | Colour | Light | Light source | Dark | Dark source |
| ---- | ----- | ------ | ----- | ------------ | ---- | ----------- |
| measured | 0 | Blue | `#2C90D7` | Coast | `#71BFFF` | Coast |
| measured | 1 | Violet | `#8978D7` | Coast | `#B6AAFF` | Coast |
| measured | 2 | Green | `#3CA059` | Coast | `#7CCD8E` | Coast |
| measured | 3 | Raspberry | `#CC79A7` | Okabe-Ito | `#F5C2E7` | Catppuccin |
| measured | 4 | Teal | `#079E92` | Coast | `#44D0C1` | Coast |
| structure | 0 | Orange | `#CB4B16` | Solarized | `#FAB387` | Catppuccin |
| structure | 1 | Gold | `#999933` | Paul Tol muted | `#DDCC77` | Paul Tol muted |
| structure | 2 | Brown | `#9C755F` | Tableau 10 | `#B09F85` | Coast |
| structure | 3 | Amber | `#B28600` | IBM Carbon | `#E69F00` | Okabe-Ito |
| structure | 4 | Olive | `#66A61E` | ColorBrewer Dark2 | `#A3BE8C` | Nord |
| total_calculation | 0 | Total calculation | `#CC6677` | Paul Tol muted | `#F38BA8` | Catppuccin |
| background | 0 | Background | `#8A8A8A` | Edi role grey | `#969696` | Edi role grey |
| difference | 0 | Difference | `#737373` | Edi role grey | `#B0B0B0` | Edi role grey |

### Edi Garden

`edi-garden.tsv`. The earlier Garden and Peaceful schemes' softer, quieter colours, each taken unchanged from the scheme named.

| Role | Place | Colour | Light | Light source | Dark | Dark source |
| ---- | ----- | ------ | ----- | ------------ | ---- | ----------- |
| measured | 0 | Blue | `#3D84A0` | Garden | `#7CC3E0` | Garden |
| measured | 1 | Violet | `#7172B6` | Peaceful | `#ACAFF8` | Peaceful |
| measured | 2 | Green | `#668558` | Garden | `#A2C393` | Garden |
| measured | 3 | Raspberry | `#9F6683` | Peaceful | `#E0A2C1` | Peaceful |
| measured | 4 | Teal | `#42897C` | Peaceful | `#80C8B9` | Peaceful |
| structure | 0 | Orange | `#D95F02` | ColorBrewer Dark2 | `#D08770` | Nord |
| structure | 1 | Gold | `#999933` | Paul Tol muted | `#DDCC77` | Paul Tol muted |
| structure | 2 | Brown | `#A96B59` | Petroff | `#B78A66` | Apple |
| structure | 3 | Amber | `#A6761D` | ColorBrewer Dark2 | `#EBCB8B` | Nord |
| structure | 4 | Olive | `#756E51` | Garden | `#B9AC70` | Petroff |
| total_calculation | 0 | Total calculation | `#A57B7C` | Coast | `#EBA0AC` | Catppuccin |
| background | 0 | Background | `#8A8A8A` | Edi role grey | `#969696` | Edi role grey |
| difference | 0 | Difference | `#737373` | Edi role grey | `#B0B0B0` | Edi role grey |

### Edi Studio

`edi-studio.tsv`. Measured colours from Catppuccin (Latte in the light theme, Mocha in the dark), with earth-tone structure colours, each taken unchanged from the scheme named; the background and difference greys are Catppuccin's neutrals.

| Role | Place | Colour | Light | Light source | Dark | Dark source |
| ---- | ----- | ------ | ----- | ------------ | ---- | ----------- |
| measured | 0 | Blue | `#1E66F5` | Catppuccin | `#89B4FA` | Catppuccin |
| measured | 1 | Violet | `#8839EF` | Catppuccin | `#CBA6F7` | Catppuccin |
| measured | 2 | Green | `#40A02B` | Catppuccin | `#A6E3A1` | Catppuccin |
| measured | 3 | Raspberry | `#EA76CB` | Catppuccin | `#F5C2E7` | Catppuccin |
| measured | 4 | Teal | `#179299` | Catppuccin | `#94E2D5` | Catppuccin |
| structure | 0 | Orange | `#FE640B` | Catppuccin | `#FAB387` | Catppuccin |
| structure | 1 | Gold | `#999933` | Paul Tol muted | `#EBCB8B` | Nord |
| structure | 2 | Brown | `#9C755F` | Tableau 10 | `#B78A66` | Apple |
| structure | 3 | Amber | `#DF8E1D` | Catppuccin | `#F9E2AF` | Catppuccin |
| structure | 4 | Olive | `#46653C` | Fog forest | `#A3BE8C` | Nord |
| total_calculation | 0 | Total calculation | `#D20F39` | Catppuccin | `#F38BA8` | Catppuccin |
| background | 0 | Background | `#7C7F93` | Catppuccin neutrals | `#9399B2` | Catppuccin neutrals |
| difference | 0 | Difference | `#6C6F85` | Catppuccin neutrals | `#A6ADC8` | Catppuccin neutrals |

### Edi Contrast

`edi-contrast.tsv`. A custom palette for colour-vision differences, inspired by the Okabe–Ito palette and Paul Tol's schemes. It is neither of them, its colours and their roles are edi's own, and it is no guarantee for every colour-vision deficiency: the source sets' accessibility claims do not carry over.

| Role | Place | Colour | Light | Light source | Dark | Dark source |
| ---- | ----- | ------ | ----- | ------------ | ---- | ----------- |
| measured | 0 | Blue | `#009DE2` | Edi Contrast, custom | `#91D4FF` | Edi Contrast, custom |
| measured | 1 | Violet | `#7264D0` | Edi Contrast, custom | `#9E96F8` | Edi Contrast, custom |
| measured | 2 | Green | `#6FA065` | Edi Contrast, custom | `#A4D89A` | Edi Contrast, custom |
| measured | 3 | Raspberry | `#D66CAC` | Edi Contrast, custom | `#FFAEDD` | Edi Contrast, custom |
| measured | 4 | Teal | `#2D9894` | Edi Contrast, custom | `#60D1BD` | Edi Contrast, custom |
| structure | 0 | Orange | `#D35E40` | Edi Contrast, custom | `#FFA273` | Edi Contrast, custom |
| structure | 1 | Gold | `#7D6500` | Edi Contrast, custom | `#B3A442` | Edi Contrast, custom |
| structure | 2 | Brown | `#7A4E24` | Edi Contrast, custom | `#B68965` | Edi Contrast, custom |
| structure | 3 | Amber | `#C38900` | Edi Contrast, custom | `#F5CD71` | Edi Contrast, custom |
| structure | 4 | Olive | `#51905B` | Edi Contrast, custom | `#91C999` | Edi Contrast, custom |
| total_calculation | 0 | Total calculation | `#C6647F` | Edi Contrast, custom | `#EC8594` | Edi Contrast, custom |
| background | 0 | Background | `#8A8A8A` | Edi role grey | `#969696` | Edi role grey |
| difference | 0 | Difference | `#737373` | Edi role grey | `#B0B0B0` | Edi role grey |
