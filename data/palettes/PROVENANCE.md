# Figure palettes — provenance

Two palettes, in the order Preferences lists them: Main (the default) and Colour-blind safe (ADR-0038, ADR-0084). The
core embeds them at build time and reads them through `edi::figure_colour()` and `edi::role_colour()`, the only source
of experiment, structure and chart-role colours in edi: the app's charts, legends and icons, the Preferences colour
strip, the pattern presentation and the report all take them from there. A report and every saved picture take the
light colours.

The colours were approved on 2026-11-10 and are stored exactly; nothing generates, adapts or retunes them at run time.
`tools/palettes/check.py` checks each table's shape and that the tables below list the same values; it writes nothing.

| Column  | Meaning                                                                                 |
| ------- | --------------------------------------------------------------------------------------- |
| `role`  | `figure`, `total_calculation`, `background` or `difference`                             |
| `index` | The place, from 0, in the palette's colour order; 0 for the three role colours          |
| `light` | The colour in the light theme, `#RRGGBB`                                                |
| `dark`  | The colour in the dark theme, `#RRGGBB`                                                 |

Each palette lists eleven figure colours by role: places 0 and 1 are experiments 1 and 2, places 2 to 4 structures
1 to 3 (orange, teal, magenta) and places 5 to 10 the six next colours (purple, brown, green, cyan, violet, mustard),
which further experiments and structures share in the order they are added. Past the eleventh, items take shades
between experiment 1's and experiment 2's colours, mixed in the Oklab colour space (Björn Ottosson, 2020). A view
that draws several datasets together (Pattern, Stacked) uses the palette's colours while they last and otherwise an
even Oklab gradient from experiment 1's colour to experiment 2's (ADR-0084).

Main keeps the earlier default palette's two experiment colours and magenta, a clearer orange, Classic's teal, purple
and green, a brown, and the earlier palettes' cyan, violet and mustard. The total calculated curve is coral-red. The
background and difference greys are edi's own, the same in both palettes.

Colour-blind safe moves each Main colour as little as it can (CIEDE2000) until every pair among the calculated curve,
the two experiments, the three structures and the background grey is at least 10.7 apart under simulated
protanopia, deuteranopia and tritanopia (Machado, Oliveira and Fernandes, 2009, severity 1). Its dark experiment 2
was then made lighter and more saturated (`#AEA381` to `#BAB58E`, CIEDE2000 5.7) so the whole experiment gradient
stays at least 8 from the dark background grey, with those thresholds kept. It was chosen for colour-vision
differences by comparing simulations with normal vision; it is no guarantee for every colour-vision deficiency.

## Stored values

### Main

`main.tsv`.

| Role | Place | Light | Dark |
| ---- | ----- | ----- | ---- |
| figure | 0 | `#618EC8` | `#6E92CB` |
| figure | 1 | `#8B9762` | `#94935C` |
| figure | 2 | `#DB7A12` | `#F5961A` |
| figure | 3 | `#2E8F8A` | `#55B1B3` |
| figure | 4 | `#C877B7` | `#C375C2` |
| figure | 5 | `#6F5A8F` | `#AE98C2` |
| figure | 6 | `#8B5A2B` | `#B8743A` |
| figure | 7 | `#3F7F4F` | `#72B976` |
| figure | 8 | `#01A2C5` | `#00ABCC` |
| figure | 9 | `#9B82E9` | `#9B82E9` |
| figure | 10 | `#958508` | `#B0AD19` |
| total_calculation | 0 | `#E5533D` | `#F26A55` |
| background | 0 | `#8A8A8A` | `#969696` |
| difference | 0 | `#737373` | `#B0B0B0` |

### Colour-blind safe

`colour-blind-safe.tsv`.

| Role | Place | Light | Dark |
| ---- | ----- | ----- | ---- |
| figure | 0 | `#548CF1` | `#6A93F8` |
| figure | 1 | `#7E996B` | `#BAB58E` |
| figure | 2 | `#DD7C0F` | `#F99A1D` |
| figure | 3 | `#1E7679` | `#73C2C0` |
| figure | 4 | `#C577B1` | `#C175B6` |
| figure | 5 | `#6F5A8F` | `#BAA6D2` |
| figure | 6 | `#88541D` | `#BC732F` |
| figure | 7 | `#4C8051` | `#5EAE5F` |
| figure | 8 | `#01A2C5` | `#0C9EBF` |
| figure | 9 | `#8675C8` | `#A49ADF` |
| figure | 10 | `#A29147` | `#BBB954` |
| total_calculation | 0 | `#D04B37` | `#F1634C` |
| background | 0 | `#8A8A8A` | `#969696` |
| difference | 0 | `#737373` | `#B0B0B0` |
