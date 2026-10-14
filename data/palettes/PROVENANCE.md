# Colour palettes — provenance

One table per colour scheme: `default.tsv` and `colour-blind-safe.tsv`. The core embeds both at build time and reads
them through `edi::pattern_colour()` and `edi::structure_colour()`, the only source of experiment and structure
colours in edi: the app's charts and icons, the pattern presentation and the report all take them from there.

| Column  | Meaning                                                                            |
| ------- | ---------------------------------------------------------------------------------- |
| `role`  | `pattern` (an experiment's colour) or `structure` (a structure's colour)          |
| `index` | The place, from 0, in the order the rows are listed                                |
| `light` | The colour in the light theme, `#RRGGBB`                                           |
| `dark`  | The colour in the dark theme, `#RRGGBB`                                            |

A scheme lists at least ten pattern colours. Up to that many experiments each takes its place's row; with more, the
colours are spread along a gradient between the last two pattern rows, interpolated in the Oklab colour space, the
first experiment at one end and the last at the other. No colour equals a role colour of the charts (the calculated,
background, residual and excluded-region colours).

| Scheme            | Pattern colours                                                                                        | Gradient ends                                     | Structure colours                       |
| ----------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------- | --------------------------------------- |
| Default           | Material Design colours, the first the light blue edi has always given the first experiment            | viridis's two ends (van der Walt and Smith, 2015) | Material orange, teal and pink, as before |
| Colour-blind safe | Okabe and Ito, *Color Universal Design* (2008), all eight                                             | cividis's two ends (Nuñez et al., PLoS ONE 2018)  | Paul Tol's muted wine, green and indigo |

The dark-theme colours are lighter tints of the same hues, so each reads on the dark background.
