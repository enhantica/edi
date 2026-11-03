# Figure palettes — provenance

One table per palette, in the order Preferences lists them: Earth (the default), Classic, Soft, Natural and
Colour-blind safe (ADR-0038). The core embeds them at build time and reads them through `edi::figure_colour()` and
`edi::role_colour()`, the only source of experiment, structure and chart-role colours in edi: the app's charts,
legends and icons, the Preferences colour strip, the pattern presentation and the report all take them from there. A
report and every saved picture take the light colours.

The colours are the ones the owner approved on 2026-10-26 (light values on the palette page's fifth version, dark
values on the second dark sheet), stored exactly; nothing generates, adapts or retunes them. The approval names were
edi earth, edi standard, edi soft, edi natural and edi clear. `tools/palettes/check.py` checks each table's shape and
that the tables below list the same values; it writes nothing.

| Column  | Meaning                                                                                 |
| ------- | --------------------------------------------------------------------------------------- |
| `role`  | `figure`, `total_calculation`, `background` or `difference`                             |
| `index` | The place, from 0, in the palette's colour order; 0 for the three role colours          |
| `light` | The colour in the light theme, `#RRGGBB`                                                |
| `dark`  | The colour in the dark theme, `#RRGGBB`                                                 |

Each palette lists eleven figure colours in the order experiments and structures take them. Earth keeps its first
two for experiments: a structure takes the first free colour from the third on. In the other four an experiment or a
structure takes the next free colour whatever its kind. Past the eleventh, items take shades between the first and
the second colour, mixed in the Oklab colour space (Björn Ottosson, 2020): position p of a project using positions up
to n - 1 at t = (p - 10) / (n - 10).

The dark colours keep each light colour's hue, read at 3:1 or more on the dark chart background (`#444444`), sit in one
lightness band so none stands out, and keep every pair of a palette at least as far apart in Oklab as in the light
theme. The calculated curve is the same crimson in all five palettes, `#AD1A6B` light and `#FC4F81` dark, which
red-green colour-blind viewers see as grey rather than as a palette colour. The background and difference greys are
edi's own, the same in all five.

Colour-blind safe was chosen for colour-vision differences by comparing simulated protanopia, deuteranopia and
tritanopia with normal vision; it is no guarantee for every colour-vision deficiency.

## Stored values

### Earth

`earth.tsv`. Approved as edi earth.

| Role | Place | Light | Dark |
| ---- | ----- | ----- | ---- |
| figure | 0 | `#618EC8` | `#6E92CB` |
| figure | 1 | `#8B9762` | `#94935C` |
| figure | 2 | `#C58A03` | `#C58901` |
| figure | 3 | `#C877B7` | `#C375C2` |
| figure | 4 | `#A27957` | `#C59B77` |
| figure | 5 | `#9B82E9` | `#9B82E9` |
| figure | 6 | `#DE7141` | `#E37646` |
| figure | 7 | `#918706` | `#AAA931` |
| figure | 8 | `#01A2C5` | `#00ABCC` |
| figure | 9 | `#4DA091` | `#4E9D91` |
| figure | 10 | `#49A45F` | `#39A55A` |
| total_calculation | 0 | `#AD1A6B` | `#FC4F81` |
| background | 0 | `#8A8A8A` | `#969696` |
| difference | 0 | `#737373` | `#B0B0B0` |

### Classic

`classic.tsv`. Approved as edi standard.

| Role | Place | Light | Dark |
| ---- | ----- | ----- | ---- |
| figure | 0 | `#6896CC` | `#6493C9` |
| figure | 1 | `#D9773A` | `#E17443` |
| figure | 2 | `#8B9762` | `#879665` |
| figure | 3 | `#6F5A8F` | `#AE98C2` |
| figure | 4 | `#2E8F8A` | `#55B1B3` |
| figure | 5 | `#B8860B` | `#C08C02` |
| figure | 6 | `#936844` | `#CA9C7B` |
| figure | 7 | `#8989F7` | `#7D82FC` |
| figure | 8 | `#8D6FC9` | `#BD8CF8` |
| figure | 9 | `#5C6BC0` | `#85A7FE` |
| figure | 10 | `#3F7F4F` | `#72B976` |
| total_calculation | 0 | `#AD1A6B` | `#FC4F81` |
| background | 0 | `#8A8A8A` | `#969696` |
| difference | 0 | `#737373` | `#B0B0B0` |

### Soft

`soft.tsv`. Approved as edi soft.

| Role | Place | Light | Dark |
| ---- | ----- | ----- | ---- |
| figure | 0 | `#6896CC` | `#6496CB` |
| figure | 1 | `#C28B0A` | `#C28305` |
| figure | 2 | `#6F5A8F` | `#AE9DC4` |
| figure | 3 | `#8989F7` | `#8384F9` |
| figure | 4 | `#479F93` | `#47A196` |
| figure | 5 | `#5E8F5A` | `#7EB77F` |
| figure | 6 | `#8D6FC9` | `#BF90FB` |
| figure | 7 | `#8C6A4A` | `#C19D7A` |
| figure | 8 | `#C877B7` | `#C776B9` |
| figure | 9 | `#D26E3C` | `#EF7B4B` |
| figure | 10 | `#918706` | `#99A004` |
| total_calculation | 0 | `#AD1A6B` | `#FC4F81` |
| background | 0 | `#8A8A8A` | `#969696` |
| difference | 0 | `#737373` | `#B0B0B0` |

### Natural

`natural.tsv`. Approved as edi natural.

| Role | Place | Light | Dark |
| ---- | ----- | ----- | ---- |
| figure | 0 | `#7C97B3` | `#888FAC` |
| figure | 1 | `#D26E3C` | `#EF7B45` |
| figure | 2 | `#039EDC` | `#039EDC` |
| figure | 3 | `#958508` | `#B0AD19` |
| figure | 4 | `#6EA163` | `#6C9C4A` |
| figure | 5 | `#936844` | `#C4A07A` |
| figure | 6 | `#479F93` | `#3CA39E` |
| figure | 7 | `#C28B0A` | `#BE8706` |
| figure | 8 | `#8989F7` | `#8D7FFB` |
| figure | 9 | `#71964E` | `#7DBB89` |
| figure | 10 | `#5C6BC0` | `#9DA2E9` |
| total_calculation | 0 | `#AD1A6B` | `#FC4F81` |
| background | 0 | `#8A8A8A` | `#969696` |
| difference | 0 | `#737373` | `#B0B0B0` |

### Colour-blind safe

`colour-blind-safe.tsv`. Approved as edi clear.

| Role | Place | Light | Dark |
| ---- | ----- | ----- | ---- |
| figure | 0 | `#3F7FBF` | `#69A9EC` |
| figure | 1 | `#C28B0A` | `#C38801` |
| figure | 2 | `#8989F7` | `#8989F7` |
| figure | 3 | `#936844` | `#C59D77` |
| figure | 4 | `#01A2C5` | `#099EC4` |
| figure | 5 | `#5E8F5A` | `#879F78` |
| figure | 6 | `#D26E3C` | `#EC7D49` |
| figure | 7 | `#479F93` | `#06A48D` |
| figure | 8 | `#918706` | `#A5AA32` |
| figure | 9 | `#C877B7` | `#BD7ABF` |
| figure | 10 | `#3F7F4F` | `#68C08A` |
| total_calculation | 0 | `#AD1A6B` | `#FC4F81` |
| background | 0 | `#8A8A8A` | `#969696` |
| difference | 0 | `#737373` | `#B0B0B0` |
