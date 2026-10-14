# Colour palettes — provenance

One table per colour scheme, `<scheme>.tsv`. The core embeds them at build time and reads them through
`edi::pattern_colour()` and `edi::structure_colour()`, the only source of experiment and structure colours in edi: the
app's charts and icons, the pattern presentation and the report all take them from there. A report always takes the
light colours.

| Column  | Meaning                                                                                |
| ------- | -------------------------------------------------------------------------------------- |
| `role`  | `pattern` (an experiment's colour), `gradient` (a stop of the gradient) or `structure` |
| `index` | The place, from 0, in the order the rows of that role are listed                       |
| `light` | The colour in the light theme, `#RRGGBB`                                               |
| `dark`  | The colour in the dark theme, `#RRGGBB`                                                |

Up to as many experiments as a scheme has pattern colours each takes its place's colour. With more, every experiment
takes a colour along the gradient, the first at one end and the last at the other, mixed in the Oklab colour space
(Björn Ottosson, 2020) between the two stops around it. Structures take the structure colours in turn.

## Rules

- **Contrast.** Every colour, and every colour the gradient can give, has a contrast ratio of at least 3:1 against its
  theme's chart background: `#FFFFFF` in the light theme (the report's too) and `#444444` in the dark one. The ratio is
  WCAG 2.x's, from relative luminance (W3C, *Web Content Accessibility Guidelines 2.1*, "contrast ratio").
- **Adapted colours.** A published colour that passes is kept. One that does not keeps its Oklab hue and chroma and
  moves only its lightness, darker in the light theme and lighter in the dark one, by the smallest step that passes.
  Where that lightness has no colour of that chroma in sRGB, the chroma shrinks to the gamut's edge.
- **Distinct colours.** Within one set, in one theme, any two colours are at least 0.08 apart in Oklab. A colour that
  would come closer to an earlier one moves further from the background until it does not. The closest pairs are 0.080
  (several sets) to 0.111 (Tableau, light).
- **Apart from the calculated pattern.** Measured data must not look like the calculated pattern, whose colour is
  `#F44336` in the light theme and `#EF9A9A` in the dark one: every pattern colour, the gradient's included, is at least
  0.10 from it in Oklab. A set colour that is closer in either theme goes to the end of its set in both themes, so only
  the last experiments take it and an experiment keeps its hue when the theme changes, and it takes the smallest
  lightness shift away from the background, as the contrast adaptation shifts, that keeps it 0.10 away with 3:1 contrast
  and its distance from the set's earlier colours. The background, residual and excluded-region colours are not part of
  this rule.
- **Gradients.** A gradient keeps the longest run of its published table that passes both rules, in the table's order,
  and the table lists 17 evenly spaced stops along it (an entry, or the Oklab mix of the two entries around a point
  between them).

`tools/palettes/generate.py` writes the tables from the published values below and checks each rule, every gradient
colour included; `--check` compares its output with the committed tables. It needs matplotlib (3.11.0 was used) for the
viridis, cividis, plasma and magma tables.

## Sources

| Scheme            | Pattern colours                                               | Gradient                                                           | Structure colours                                 |
| ----------------- | ------------------------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------- |
| Default           | Material Design colours (Google, 2014), the light blue first  | viridis (Stéfan van der Walt and Nathaniel Smith, 2015)            | Material orange, teal and pink                    |
| Colour-blind safe | Okabe and Ito, *Color Universal Design* (2008), all eight     | cividis (Nuñez, Anderton and Renslow, PLoS ONE 13, e0199239, 2018) | Paul Tol's muted wine, green and indigo           |
| Tableau           | Tableau 10, as matplotlib's `tab10`                           | plasma (van der Walt and Smith, 2015)                              | matplotlib's `tab20b`, first of indigo, red, gold |
| Paul Tol          | Paul Tol, *Colour Schemes* (SRON/EPS/TN/09-002, 2021), bright | Paul Tol's iridescent, its 23 colours                              | Paul Tol's high-contrast blue, yellow and red     |
| Vivid             | ColorBrewer Set1 (Cynthia Brewer, colorbrewer2.org)           | magma (van der Walt and Smith, 2015)                               | ColorBrewer Dark2's first three                   |

viridis, plasma and magma are matplotlib's tables; cividis is the table matplotlib ships from the paper's authors.

## Published and adapted values

### Default (`default.tsv`)

| Role      | Place | Published | Light               | Dark                |
| --------- | ----- | --------- | ------------------- | ------------------- |
| pattern   | 0     | `#03A9F4` | `#009DE4` (adapted) | `#03A9F4`           |
| pattern   | 1     | `#795548` | `#795548`           | `#AE8678` (adapted) |
| pattern   | 2     | `#4CAF50` | `#45A84A` (adapted) | `#4CAF50`           |
| pattern   | 3     | `#9C27B0` | `#9C27B0`           | `#D15FE5` (adapted) |
| pattern   | 4     | `#FFC107` | `#BC8D00` (adapted) | `#FFC107`           |
| pattern   | 5     | `#3F51B5` | `#3F51B5`           | `#6F88F2` (adapted) |
| pattern   | 6     | `#00BCD4` | `#009BAF` (adapted) | `#00BCD4`           |
| pattern   | 7     | `#CDDC39` | `#899400` (adapted) | `#CDDC39`           |
| structure | 0     | `#FF9800` | `#D78000` (adapted) | `#FF9800`           |
| structure | 1     | `#009688` | `#009688`           | `#1CA091` (adapted) |
| structure | 2     | `#E91E63` | `#E91E63`           | `#FF4979` (adapted) |

Gradient: entries 0–152 of 256 in the light theme, 145–255 in the dark one.

### Colour-blind safe (`colour-blind-safe.tsv`)

| Role      | Place | Published | Light               | Dark                |
| --------- | ----- | --------- | ------------------- | ------------------- |
| pattern   | 0     | `#0072B2` | `#0072B2`           | `#3A95D8` (adapted) |
| pattern   | 1     | `#E69F00` | `#C68900` (adapted) | `#E69F00`           |
| pattern   | 2     | `#009E73` | `#009E73`           | `#11A377` (adapted) |
| pattern   | 3     | `#CC79A7` | `#CC79A7`           | `#CC79A7`           |
| pattern   | 4     | `#56B4E9` | `#3D9DD1` (adapted) | `#56B4E9`           |
| pattern   | 5     | `#F0E442` | `#958C00` (adapted) | `#F0E442`           |
| pattern   | 6     | `#000000` | `#000000`           | `#8F8F8F` (adapted) |
| pattern   | 7     | `#D55E00` | `#C45600` (adapted) | `#E56C1F` (adapted) |
| structure | 0     | `#882255` | `#882255`           | `#D86B9A` (adapted) |
| structure | 1     | `#117733` | `#117733`           | `#46A15A` (adapted) |
| structure | 2     | `#332288` | `#332288`           | `#8483F0` (adapted) |

Gradient: entries 0–162 of 256 in the light theme, 154–255 in the dark one. Moved to the end of the set, near the
calculated colour: `#D55E00`.

### Tableau (`tableau.tsv`)

| Role      | Place | Published | Light               | Dark                |
| --------- | ----- | --------- | ------------------- | ------------------- |
| pattern   | 0     | `#1F77B4` | `#1F77B4`           | `#4295D4` (adapted) |
| pattern   | 1     | `#2CA02C` | `#2CA02C`           | `#31A430` (adapted) |
| pattern   | 2     | `#9467BD` | `#9467BD`           | `#A97CD3` (adapted) |
| pattern   | 3     | `#8C564B` | `#8C564B`           | `#BA8174` (adapted) |
| pattern   | 4     | `#E377C2` | `#DB6FBA` (adapted) | `#E377C2`           |
| pattern   | 5     | `#7F7F7F` | `#7F7F7F`           | `#9B9B9A` (adapted) |
| pattern   | 6     | `#BCBD22` | `#9A9A00` (adapted) | `#BCBD22`           |
| pattern   | 7     | `#17BECF` | `#00A4B4` (adapted) | `#17BECF`           |
| pattern   | 8     | `#FF7F0E` | `#C96200` (adapted) | `#FF7F0E`           |
| pattern   | 9     | `#D62728` | `#CD1A20` (adapted) | `#FD524A` (adapted) |
| structure | 0     | `#393B79` | `#393B79`           | `#838ACF` (adapted) |
| structure | 1     | `#843C39` | `#843C39`           | `#C97974` (adapted) |
| structure | 2     | `#8C6D31` | `#8C6D31`           | `#AB8A4F` (adapted) |

Gradient: entries 0–131 of 256 in the light theme, 195–255 in the dark one. Moved to the end of the set, near the
calculated colour: `#FF7F0E`, `#D62728`.

### Paul Tol (`paul-tol.tsv`)

| Role      | Place | Published | Light               | Dark                |
| --------- | ----- | --------- | ------------------- | ------------------- |
| pattern   | 0     | `#4477AA` | `#4477AA`           | `#5F93C7` (adapted) |
| pattern   | 1     | `#228833` | `#228833`           | `#41A24C` (adapted) |
| pattern   | 2     | `#CCBB44` | `#A79506` (adapted) | `#CCBB44`           |
| pattern   | 3     | `#66CCEE` | `#35A0C1` (adapted) | `#66CCEE`           |
| pattern   | 4     | `#AA3377` | `#AA3377`           | `#DE64A5` (adapted) |
| pattern   | 5     | `#BBBBBB` | `#959494` (adapted) | `#BBBBBB`           |
| pattern   | 6     | `#EE6677` | `#C54156` (adapted) | `#FFC1C4` (adapted) |
| structure | 0     | `#004488` | `#004488`           | `#5591DC` (adapted) |
| structure | 1     | `#DDAA33` | `#BE8D00` (adapted) | `#DDAA33`           |
| structure | 2     | `#BB5566` | `#BB5566`           | `#D86F7E` (adapted) |

Gradient: entries 16–22 of 23 in the light theme, 0–16 in the dark one. Moved to the end of the set, near the calculated
colour: `#EE6677`.

### Vivid (`vivid.tsv`)

| Role      | Place | Published | Light               | Dark                |
| --------- | ----- | --------- | ------------------- | ------------------- |
| pattern   | 0     | `#377EB8` | `#377EB8`           | `#4E94D0` (adapted) |
| pattern   | 1     | `#4DAF4A` | `#46A844` (adapted) | `#4DAF4A`           |
| pattern   | 2     | `#984EA3` | `#984EA3`           | `#BF72CA` (adapted) |
| pattern   | 3     | `#FFFF33` | `#9A9A00` (adapted) | `#FFFF33`           |
| pattern   | 4     | `#A65628` | `#A65628`           | `#CD7A4D` (adapted) |
| pattern   | 5     | `#999999` | `#959494` (adapted) | `#999999`           |
| pattern   | 6     | `#E41A1C` | `#D1000F` (adapted) | `#FF5044` (adapted) |
| pattern   | 7     | `#FF7F00` | `#8A4100` (adapted) | `#FF7F00`           |
| pattern   | 8     | `#F781BF` | `#E16DAB` (adapted) | `#FFB7DA` (adapted) |
| structure | 0     | `#1B9E77` | `#1B9E77`           | `#22A27A` (adapted) |
| structure | 1     | `#D95F02` | `#D95F02`           | `#E66B1C` (adapted) |
| structure | 2     | `#7570B3` | `#7570B3`           | `#8C88CC` (adapted) |

Gradient: entries 0–144 of 256 in the light theme, 219–255 in the dark one. Moved to the end of the set, near the
calculated colour: `#E41A1C`, `#FF7F00`, `#F781BF`.
