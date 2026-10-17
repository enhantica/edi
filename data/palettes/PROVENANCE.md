# Colour palettes — provenance

One table per colour scheme, `<scheme>.tsv`. The core embeds them at build time and reads them through
`edi::pattern_colour()` and `edi::structure_colour()`, the only source of experiment and structure colours in edi: the
app's charts and icons, the pattern presentation and the report all take them from there. A report always takes the
light colours. Coast is the default scheme.

| Column  | Meaning                                                                                |
| ------- | -------------------------------------------------------------------------------------- |
| `role`  | `pattern` (an experiment's colour), `gradient` (a stop of the gradient) or `structure` |
| `index` | The place, from 0, in the order the rows of that role are listed                       |
| `light` | The colour in the light theme, `#RRGGBB`                                               |
| `dark`  | The colour in the dark theme, `#RRGGBB`                                                |

Up to as many experiments as a scheme has pattern colours each takes its place's colour. With more, every experiment
takes a colour along the gradient, the first at one end and the last at the other, mixed in the Oklab colour space
(Björn Ottosson, 2020) between the gradient's two stops. Structures take the structure colours in turn.

## Rules

- **Contrast.** Every colour, and every colour the gradient can give, has a contrast ratio of at least 3:1 against its
  theme's chart background: `#FFFFFF` in the light theme (the report's too) and `#444444` in the dark one. The ratio is
  WCAG 2.x's, from relative luminance (W3C, *Web Content Accessibility Guidelines 2.1*, "contrast ratio").
- **Adapted colours.** A source colour that passes is kept. One that does not keeps its Oklab hue and chroma and moves
  only its lightness, darker in the light theme and lighter in the dark one, by the smallest step that passes. Where
  that lightness has no colour of that chroma in sRGB, the chroma shrinks to the gamut's edge. The stored colour is the
  passing 8-bit colour nearest that exact one, its lightness, chroma and hue each measured against how far they move
  across its own rounding (half a unit in each channel).
- **Distinct colours.** Within one set, in one theme, any two colours are at least 0.08 apart in Oklab. A colour that
  would come closer to an earlier one moves further from the background until it does not.
- **Apart from the calculated pattern.** Measured data must not look like the calculated pattern, whose colour is
  `#F44336` in the light theme (Oklab hue 28.8°) and `#EF9A9A` in the dark one (19.7°). Its hue range is the hues within
  45° of either, 334.7° to 73.8°; a colour of Oklab chroma under 0.04 has no hue and is never in it. A set colour in
  that range, or less than 0.10 in Oklab from the calculated colour once adapted, goes to the end of its set in both
  themes, so only the last experiments take it and an experiment keeps its hue when the theme changes. A moved colour
  still closer than 0.10 takes the smallest lightness shift, towards the background or away from it, that keeps it 0.10
  away with 3:1 contrast and its distance from the set's earlier colours. The background, residual and excluded-region
  colours are not part of this rule.
- **Seven colours at most.** A set keeps its first seven colours after the move; past them the gradient takes over.
- **Gradient.** Two colours, each a source colour's hue and chroma at a set lightness: the first at 0.36 in the light
  theme and at the darkest lightness that keeps 3:1 in the dark one, the last at the lightest that keeps 3:1 in the
  light theme and at 0.92 in the dark one. Mixed in Oklab between them, the lightness rises steadily from the first
  dataset to the last, and every colour along the way keeps 3:1, stays out of the calculated hue range and keeps 0.10
  from the calculated colour.
- **Structure colours.** Up to five, muted: each takes a candidate's hue at Oklab chroma 0.06 at most, at its own step
  of a lightness ladder (0.62, 0.56, 0.50, 0.44, 0.38 in the light theme; 0.70, 0.76, 0.82, 0.88, 0.94 in the dark one),
  the first free step where it keeps 0.08 from every measured colour and earlier structure colour in both themes,
  shifted only to keep 3:1. A neutral candidate is skipped, as each structure colour has its own hue, and so is one
  whose hue is within 25° of an earlier structure colour's. edi's own schemes list their candidates; a published
  scheme's are its own colours from the last back; then, for every scheme, the earth tones of the Design Seeds nature
  palettes (stone `#A49693`, wheat `#B09F85`, plum `#97667B`, slate `#5C6670`, sage `#9DB18E`, lichen `#CEC88A`, rose
  `#A57B7C`, artichoke `#6A4D83`).

`tools/palettes/generate.py` writes the tables from the sources below and checks each rule, every gradient colour
included; `--check` compares its output with the committed tables.

## Sources

| Scheme                                  | Source                                                                                                                                                                                                                                              | Licence                       |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| Coast (`coast.tsv`)                     | edi's own (the default): sea blue, lagoon teal, leaf green, violet and cyan, with structure colours from the Design Seeds nature palettes by Jessica Colaluca (wheat, plum, rose, stone, sage).                                                     | designed for edi              |
| Garden (`garden.tsv`)                   | edi's own, after akulakreative's garden greenery palette (December 2024: khaki, sand, clay) and the Design Seeds sea and lagoon palettes.                                                                                                           | designed for edi              |
| Peaceful (`peaceful.tsv`)               | edi's own, after paperheartdesign's peaceful palettes (blue lake, fog teal, periwinkle, deep lagoon, plum; tan, khaki, lavender, stone, sand).                                                                                                      | designed for edi              |
| Fog forest (`fog-forest.tsv`)           | edi's own, after the Design Seeds fog and lake palettes by Jessica Colaluca (lake blue, forest green, fog teal, heather, sand; slate, sage, stone, mist, lichen).                                                                                   | designed for edi              |
| Sage (`sage.tsv`)                       | edi's own, around the sage body colour `#889F8E` and mint accent `#66D795` of a Škoda Elroq, with slate blue, dusty violet, teal and ochre.                                                                                                         | designed for edi              |
| Okabe-Ito (`okabe-ito.tsv`)             | Okabe and Ito, *Color Universal Design* (2008), the eight colours as R's `palette.colors()` lists them, in the order edi has used them.                                                                                                             | values published for free use |
| Paul Tol bright (`paul-tol-bright.tsv`) | Paul Tol, *Colour Schemes* (SRON/EPS/TN/09-002, 2021), bright.                                                                                                                                                                                      | values published for free use |
| Paul Tol muted (`paul-tol-muted.tsv`)   | Paul Tol, *Colour Schemes* (SRON/EPS/TN/09-002, 2021), muted.                                                                                                                                                                                       | values published for free use |
| Tableau 10 (`tableau.tsv`)              | Tableau 10 (Maureen Stone, Tableau, 2016), as d3-scale-chromatic lists it (`schemeTableau10`).                                                                                                                                                      | ISC                           |
| Observable 10 (`observable.tsv`)        | Observable 10, Observable Plot's default since 2024 (d3-scale-chromatic `schemeObservable10`).                                                                                                                                                      | ISC                           |
| IBM Carbon (`carbon.tsv`)               | IBM's Carbon Design System, the categorical palettes for light and dark themes (carbon-website `palettes.js`).                                                                                                                                      | Apache-2.0                    |
| ColorBrewer Dark2 (`dark2.tsv`)         | ColorBrewer Dark2 (Cynthia Brewer, colorbrewer2.org), as matplotlib's `Dark2`.                                                                                                                                                                      | Apache-2.0                    |
| Petroff (`petroff.tsv`)                 | Matthew Petroff, *Accessible Color Sequences for Data Visualization* (2021), the ten-colour sequence, matplotlib 3.10's `petroff10` style.                                                                                                          | matplotlib licence            |
| Vivid (`vivid.tsv`)                     | ColorBrewer Set1 (Cynthia Brewer, colorbrewer2.org), as matplotlib's `Set1`.                                                                                                                                                                        | Apache-2.0                    |
| Nord (`nord.tsv`)                       | Nord (Arctic Ice Studio), its Frost and Aurora colours: nord10, nord14, nord15, nord8, nord13, nord7, nord9, nord12, nord11.                                                                                                                        | MIT                           |
| Solarized (`solarized.tsv`)             | Solarized (Ethan Schoonover), its accent colours: blue, green, violet, cyan, yellow, magenta, orange, red.                                                                                                                                          | MIT                           |
| Catppuccin (`catppuccin.tsv`)           | Catppuccin, Latte in the light theme and Mocha in the dark, its accents: blue, green, mauve, teal, yellow, sapphire, lavender, then peach, pink, red, maroon, flamingo, rosewater, sky.                                                             | MIT                           |
| Apple (`apple.tsv`)                     | Apple's system colours, light and dark (Human Interface Guidelines, Color, https://developer.apple.com/design/human-interface-guidelines/color), as guidance: blue, green, indigo, cyan, purple, mint, yellow, teal, then orange, pink, red, brown. | guidance values               |

## Source and stored values

### Coast

`coast.tsv`. Inspiration: <https://www.design-seeds.com/>.

| Role      | Place | Source                | Light     | Dark      |
| --------- | ----- | --------------------- | --------- | --------- |
| pattern   | 0     | `#2C90D7` / `#71BFFF` | `#2C90D7` | `#71BFFF` |
| pattern   | 1     | `#079E92` / `#44D0C1` | `#079E92` | `#44D0C1` |
| pattern   | 2     | `#3CA059` / `#7CCD8E` | `#3CA059` | `#87D999` |
| pattern   | 3     | `#8978D7` / `#B6AAFF` | `#8978D7` | `#B6AAFF` |
| pattern   | 4     | `#0999B2` / `#43CAE7` | `#05859C` | `#58DCF9` |
| gradient  | 0     | `#3E3875`             | `#39336F` | `#8A88CC` |
| gradient  | 1     | `#2DC08E`             | `#03A97A` | `#8EFFD0` |
| structure | 0     | `#B09F85`             | `#94846A` | `#AD9C82` |
| structure | 1     | `#97667B`             | `#916678` | `#D0A2B5` |
| structure | 2     | `#9DB18E`             | `#47593A` | `#CBE0BA` |
| structure | 3     | `#6A4D83`             | `#4B395B` | `#F2E5FF` |

### Garden

`garden.tsv`. Inspiration: <https://akulakreative.com/>, <https://www.design-seeds.com/>.

| Role      | Place | Source                | Light     | Dark      |
| --------- | ----- | --------------------- | --------- | --------- |
| pattern   | 0     | `#3D84A0` / `#7CC3E0` | `#3D84A0` | `#7CC3E0` |
| pattern   | 1     | `#3D8984` / `#7CC7C2` | `#297671` | `#91DDD7` |
| pattern   | 2     | `#668558` / `#A2C393` | `#668558` | `#A2C393` |
| pattern   | 3     | `#896BA4` / `#C7A8E5` | `#896BA4` | `#C7A8E5` |
| pattern   | 4     | `#527FA4` / `#8EBDE4` | `#366185` | `#C0E2FF` |
| gradient  | 0     | `#35536B`             | `#234057` | `#7293AD` |
| gradient  | 1     | `#7E9A72`             | `#819C75` | `#D1EFC4` |
| structure | 0     | `#756E51`             | `#595337` | `#E0D8B8` |
| structure | 1     | `#DBAD93`             | `#A47C65` | `#BE947D` |
| structure | 2     | `#97667B`             | `#5A3546` | `#FFE2ED` |

### Peaceful

`peaceful.tsv`. Inspiration: <https://www.paperheartdesign.com/>, <https://www.design-seeds.com/>.

| Role      | Place | Source                        | Light     | Dark      |
| --------- | ----- | ----------------------------- | --------- | --------- |
| pattern   | 0     | `#3E7EBC` / `#7CBDFF`         | `#3E7EBC` | `#7CBDFF` |
| pattern   | 1     | `#42897C` / `#80C8B9`         | `#42897C` | `#80C8B9` |
| pattern   | 2     | `#7172B6` / `#ACAFF8`         | `#6262A5` | `#BEC2FE` |
| pattern   | 3     | `#3B888A` / `#7BC7C9`         | `#207174` | `#93E0E2` |
| pattern   | 4     | `#9F6683` / `#E0A2C1` (moved) | `#9F6683` | `#FABAD9` |
| gradient  | 0     | `#6768AB`                     | `#363371` | `#8689CE` |
| gradient  | 1     | `#5E8D83`                     | `#6F9E94` | `#BFF1E6` |
| structure | 0     | `#B7946A`                     | `#9E805E` | `#B69976` |
| structure | 1     | `#9389BD`                     | `#443C5F` | `#EBE8FF` |
| structure | 2     | `#CEC88A`                     | `#69653C` | `#CBC69A` |

### Fog forest

`fog-forest.tsv`. Inspiration: <https://www.design-seeds.com/>.

| Role      | Place | Source            | Light     | Dark      |
| --------- | ----- | ----------------- | --------- | --------- |
| pattern   | 0     | `#6495A3`         | `#6495A3` | `#6696A5` |
| pattern   | 1     | `#46653C`         | `#46653C` | `#76986C` |
| pattern   | 2     | `#7BA9A9`         | `#527E7F` | `#81AFAF` |
| pattern   | 3     | `#A78FA9`         | `#A58DA8` | `#A78FA9` |
| pattern   | 4     | `#BCB096` (moved) | `#998D74` | `#CABFA5` |
| gradient  | 0     | `#32444E`         | `#2E404A` | `#7E929D` |
| gradient  | 1     | `#9DB18E`         | `#879B79` | `#D8EDC8` |
| structure | 0     | `#9DB18E`         | `#38482A` | `#DEF3CE` |
| structure | 1     | `#97667B`         | `#916678` | `#D0A2B5` |
| structure | 2     | `#6A4D83`         | `#5C496C` | `#E2CEF7` |

### Sage

`sage.tsv`. Inspiration: <https://www.design-seeds.com/>.

| Role      | Place | Source    | Light     | Dark      |
| --------- | ----- | --------- | --------- | --------- |
| pattern   | 0     | `#66D795` | `#2EA96A` | `#66D795` |
| pattern   | 1     | `#5C7FA3` | `#5C7FA3` | `#6F92B7` |
| pattern   | 2     | `#889F8E` | `#849A8A` | `#889F8E` |
| pattern   | 3     | `#8C7BA8` | `#73628E` | `#A795C3` |
| pattern   | 4     | `#4A9A96` | `#2E807C` | `#6BBBB6` |
| pattern   | 5     | `#C2A15F` | `#B1904F` | `#C2A15F` |
| gradient  | 0     | `#2F5D6B` | `#144451` | `#6796A5` |
| gradient  | 1     | `#66D795` | `#2EA96A` | `#97FFBF` |
| structure | 0     | `#B09F85` | `#706148` | `#D3C1A7` |
| structure | 1     | `#97667B` | `#6C4556` | `#F8C8DB` |
| structure | 2     | `#9DB18E` | `#38482A` | `#DEF3CE` |

### Okabe-Ito

`okabe-ito.tsv`. Source: <https://jfly.uni-koeln.de/color/>.

| Role      | Place | Source            | Light     | Dark      |
| --------- | ----- | ----------------- | --------- | --------- |
| pattern   | 0     | `#0072B2`         | `#0072B2` | `#3A95D8` |
| pattern   | 1     | `#E69F00`         | `#C68902` | `#E69F00` |
| pattern   | 2     | `#009E73`         | `#009E73` | `#09A378` |
| pattern   | 3     | `#56B4E9`         | `#3F9DD1` | `#56B4E9` |
| pattern   | 4     | `#F0E442`         | `#958C04` | `#F0E442` |
| pattern   | 5     | `#000000`         | `#000000` | `#8E8F8F` |
| pattern   | 6     | `#CC79A7` (moved) | `#CC79A7` | `#CC79A7` |
| gradient  | 0     | `#0072B2`         | `#004168` | `#3A95D8` |
| gradient  | 1     | `#009E73`         | `#21A87C` | `#8EFFD1` |
| structure | 0     | `#F0E442`         | `#79774D` | `#B6B488` |
| structure | 1     | `#D55E00`         | `#805945` | `#E6B9A3` |
| structure | 2     | `#56B4E9`         | `#2F586F` | `#B2DFFB` |
| structure | 3     | `#CC79A7`         | `#593549` | `#FFE2F0` |

Past the seven: `#D55E00`.

### Paul Tol bright

`paul-tol-bright.tsv`. Source: <https://sronpersonalpages.nl/~pault/>.

| Role      | Place | Source            | Light     | Dark      |
| --------- | ----- | ----------------- | --------- | --------- |
| pattern   | 0     | `#4477AA`         | `#4477AA` | `#5E93C7` |
| pattern   | 1     | `#228833`         | `#228833` | `#40A24C` |
| pattern   | 2     | `#CCBB44`         | `#A79506` | `#CCBB44` |
| pattern   | 3     | `#66CCEE`         | `#36A0C1` | `#66CCEE` |
| pattern   | 4     | `#BBBBBB`         | `#949595` | `#BBBBBB` |
| pattern   | 5     | `#AA3377` (moved) | `#AA3377` | `#DE64A5` |
| pattern   | 6     | `#EE6677` (moved) | `#C54056` | `#FEC1C4` |
| gradient  | 0     | `#4477AA`         | `#053F6D` | `#5F93C7` |
| gradient  | 1     | `#228833`         | `#48A852` | `#A1FFA7` |
| structure | 0     | `#AA3377`         | `#5A3547` | `#FFE2EF` |
| structure | 1     | `#66CCEE`         | `#285A6A` | `#ADE1F4` |

### Paul Tol muted

`paul-tol-muted.tsv`. Source: <https://sronpersonalpages.nl/~pault/>.

| Role      | Place | Source    | Light     | Dark      |
| --------- | ----- | --------- | --------- | --------- |
| pattern   | 0     | `#332288` | `#332288` | `#8483F0` |
| pattern   | 1     | `#DDCC77` | `#A69540` | `#DDCC77` |
| pattern   | 2     | `#117733` | `#117733` | `#45A15A` |
| pattern   | 3     | `#88CCEE` | `#5A9DBD` | `#88CCEE` |
| pattern   | 4     | `#44AA99` | `#39A190` | `#44AA99` |
| pattern   | 5     | `#999933` | `#848315` | `#999933` |
| pattern   | 6     | `#AA4499` | `#AA4499` | `#D169BE` |
| gradient  | 0     | `#332288` | `#36268C` | `#8483F0` |
| gradient  | 1     | `#44AA99` | `#3DA494` | `#98FAE7` |
| structure | 0     | `#AA4499` | `#9D7995` | `#B691AE` |
| structure | 1     | `#999933` | `#45451C` | `#EDEFC1` |
| structure | 2     | `#44AA99` | `#4A8076` | `#87BEB3` |
| structure | 3     | `#332288` | `#4D4E73` | `#D0D3FF` |
| structure | 4     | `#CC6677` | `#82555B` | `#E8B5BA` |

Past the seven: `#CC6677`, `#882255`.

### Tableau 10

`tableau.tsv`. Source: <https://raw.githubusercontent.com/d3/d3-scale-chromatic/v3.1.0/src/categorical/Tableau10.js>.

| Role      | Place | Source            | Light     | Dark      |
| --------- | ----- | ----------------- | --------- | --------- |
| pattern   | 0     | `#4E79A7`         | `#4E79A7` | `#6693C2` |
| pattern   | 1     | `#76B7B2`         | `#5FA09C` | `#76B7B2` |
| pattern   | 2     | `#59A14F`         | `#59A14F` | `#59A14F` |
| pattern   | 3     | `#EDC949`         | `#B19204` | `#EDC949` |
| pattern   | 4     | `#AF7AA1` (moved) | `#AF7AA1` | `#B47EA6` |
| pattern   | 5     | `#F28E2C` (moved) | `#DE7C0B` | `#F28E2C` |
| pattern   | 6     | `#9C755F` (moved) | `#9C755F` | `#AE8770` |
| gradient  | 0     | `#4E79A7`         | `#133F68` | `#6792C3` |
| gradient  | 1     | `#59A14F`         | `#5DA553` | `#B0FCA5` |
| structure | 0     | `#9C755F`         | `#7F5A43` | `#E4BAA2` |
| structure | 1     | `#FF9DA7`         | `#5E3439` | `#FFE3E5` |
| structure | 2     | `#AF7AA1`         | `#8C6782` | `#CBA3BF` |
| structure | 3     | `#59A14F`         | `#405B3C` | `#C2E2BD` |

Past the seven: `#E15759`, `#FF9DA7`, `#BAB0AB`.

### Observable 10

`observable.tsv`. Source:
<https://raw.githubusercontent.com/d3/d3-scale-chromatic/v3.1.0/src/categorical/observable10.js>.

| Role      | Place | Source    | Light     | Dark      |
| --------- | ----- | --------- | --------- | --------- |
| pattern   | 0     | `#4269D0` | `#4269D0` | `#608BF5` |
| pattern   | 1     | `#EFB118` | `#C08C04` | `#EFB118` |
| pattern   | 2     | `#6CC5B0` | `#49A490` | `#6CC5B0` |
| pattern   | 3     | `#3CA951` | `#3CA951` | `#3CA951` |
| pattern   | 4     | `#A463F2` | `#A463F2` | `#AF6EFE` |
| pattern   | 5     | `#97BBF5` | `#7496CE` | `#97BBF5` |
| pattern   | 6     | `#9498A0` | `#8F929A` | `#9498A0` |
| gradient  | 0     | `#4269D0` | `#132F92` | `#608BF5` |
| gradient  | 1     | `#3CA951` | `#3CA951` | `#A0FFAB` |
| structure | 0     | `#9C6B4E` | `#916B54` | `#D1A78F` |
| structure | 1     | `#97BBF5` | `#3F5374` | `#C1D9FF` |
| structure | 2     | `#FF8AB7` | `#7F5564` | `#E5B5C5` |
| structure | 3     | `#3CA951` | `#2C4B2F` | `#D2F7D4` |

Past the seven: `#FF725C`, `#FF8AB7`, `#9C6B4E`.

### IBM Carbon

`carbon.tsv`. Source:
<https://raw.githubusercontent.com/carbon-design-system/carbon-website/main/src/data/data-visualization/palettes.js>.

| Role      | Place | Source                | Light     | Dark      |
| --------- | ----- | --------------------- | --------- | --------- |
| pattern   | 0     | `#6929C4` / `#8A3FFC` | `#6929C4` | `#A075FF` |
| pattern   | 1     | `#1192E8` / `#33B1FF` | `#1192E8` | `#33B1FF` |
| pattern   | 2     | `#005D5D` / `#007D79` | `#005D5D` | `#399E99` |
| pattern   | 3     | `#198038` / `#6FDC8C` | `#198038` | `#6FDC8C` |
| pattern   | 4     | `#002D9C` / `#4589FF` | `#002D9C` | `#4A8CFE` |
| pattern   | 5     | `#B28600` / `#D2A106` | `#B28600` | `#D2A106` |
| pattern   | 6     | `#009D9A` / `#08BDBA` | `#009D9A` | `#08BDBA` |
| gradient  | 0     | `#6929C4` / `#8A3FFC` | `#4B0096` | `#A075FF` |
| gradient  | 1     | `#009D9A` / `#08BDBA` | `#1AA5A2` | `#70FFFB` |
| structure | 0     | `#A56EFF` / `#D4BBFF` | `#8A7FA6` | `#A596BE` |
| structure | 1     | `#8A3800` / `#BA4E00` | `#936A56` | `#D2A691` |
| structure | 2     | `#012749` / `#BAE6FF` | `#496685` | `#A0CBE4` |
| structure | 3     | `#B28600` / `#D2A106` | `#62502A` | `#E9D6AB` |
| structure | 4     | `#EE538B` / `#D12771` | `#5D3440` | `#FFE3EA` |

Past the seven: `#9F1853` / `#FF7EB6`, `#FA4D56` / `#FA4D56`, `#570408` / `#FFF1F1`, `#EE538B` / `#D12771`, `#012749` /
`#BAE6FF`, `#8A3800` / `#BA4E00`, `#A56EFF` / `#D4BBFF`.

### ColorBrewer Dark2

`dark2.tsv`. Source: <https://colorbrewer2.org/export/colorbrewer.json>.

| Role      | Place | Source            | Light     | Dark      |
| --------- | ----- | ----------------- | --------- | --------- |
| pattern   | 0     | `#1B9E77`         | `#1B9E77` | `#1EA27B` |
| pattern   | 1     | `#7570B3`         | `#7570B3` | `#8C88CC` |
| pattern   | 2     | `#66A61E`         | `#66A51D` | `#66A61E` |
| pattern   | 3     | `#E6AB02`         | `#BE8D01` | `#E6AB02` |
| pattern   | 4     | `#A6761D`         | `#A5751C` | `#B78632` |
| pattern   | 5     | `#666666`         | `#666666` | `#8E8F8F` |
| pattern   | 6     | `#E7298A` (moved) | `#E7298A` | `#FD449C` |
| gradient  | 0     | `#7570B3`         | `#3A326F` | `#8D87CD` |
| gradient  | 1     | `#1B9E77`         | `#2EA77F` | `#8DFFD3` |
| structure | 0     | `#A6761D`         | `#654E2A` | `#EED3AC` |
| structure | 1     | `#66A61E`         | `#364927` | `#DCF4CB` |

Past the seven: `#D95F02`.

### Petroff

`petroff.tsv`. Source:
<https://raw.githubusercontent.com/matplotlib/matplotlib/v3.10.8/lib/matplotlib/mpl-data/stylelib/petroff10.mplstyle>.

| Role      | Place | Source            | Light     | Dark      |
| --------- | ----- | ----------------- | --------- | --------- |
| pattern   | 0     | `#3F90DA`         | `#3F90DA` | `#4294DE` |
| pattern   | 1     | `#94A4A2`         | `#899896` | `#94A4A2` |
| pattern   | 2     | `#832DB6`         | `#832DB6` | `#BB6AF4` |
| pattern   | 3     | `#B9AC70`         | `#A2955A` | `#B9AC70` |
| pattern   | 4     | `#717581`         | `#717581` | `#B3B8C4` |
| pattern   | 5     | `#92DADD`         | `#489094` | `#92DADD` |
| pattern   | 6     | `#FFA90E` (moved) | `#BA7905` | `#FFA90E` |
| gradient  | 0     | `#832DB6`         | `#590083` | `#BB6AF3` |
| gradient  | 1     | `#92DADD`         | `#59A0A3` | `#ABF4F7` |
| structure | 0     | `#92DADD`         | `#0C4C4E` | `#BCF8FA` |
| structure | 1     | `#B9AC70`         | `#6D633A` | `#CEC599` |
| structure | 2     | `#A96B59`         | `#6F473B` | `#FCCABC` |

Past the seven: `#BD1F01`, `#A96B59`, `#E76300`.

### Vivid

`vivid.tsv`. Source: <https://colorbrewer2.org/export/colorbrewer.json>.

| Role      | Place | Source            | Light     | Dark      |
| --------- | ----- | ----------------- | --------- | --------- |
| pattern   | 0     | `#377EB8`         | `#377EB8` | `#4F94CF` |
| pattern   | 1     | `#4DAF4A`         | `#46A844` | `#4DAF4A` |
| pattern   | 2     | `#984EA3`         | `#984EA3` | `#BF72CA` |
| pattern   | 3     | `#FFFF33`         | `#9A9A05` | `#FFFF33` |
| pattern   | 4     | `#999999`         | `#949595` | `#999999` |
| pattern   | 5     | `#A65628` (moved) | `#A65628` | `#CD7A4C` |
| pattern   | 6     | `#F781BF` (moved) | `#E16DAB` | `#ED78B6` |
| gradient  | 0     | `#377EB8`         | `#00406B` | `#4E94D0` |
| gradient  | 1     | `#4DAF4A`         | `#45A844` | `#A4FF9F` |
| structure | 0     | `#F781BF`         | `#90667A` | `#CFA2B7` |
| structure | 1     | `#A65628`         | `#6E4835` | `#FACCB6` |
| structure | 2     | `#FFFF33`         | `#65663D` | `#C6C89B` |
| structure | 3     | `#984EA3`         | `#513755` | `#FCE1FF` |

Past the seven: `#E41A1C`, `#FF7F00`.

### Nord

`nord.tsv`. Source: <https://raw.githubusercontent.com/nordtheme/nord/develop/src/nord.scss>.

| Role      | Place | Source    | Light     | Dark      |
| --------- | ----- | --------- | --------- | --------- |
| pattern   | 0     | `#5E81AC` | `#5E81AC` | `#6D92BE` |
| pattern   | 1     | `#A3BE8C` | `#829D6C` | `#A3BE8C` |
| pattern   | 2     | `#B48EAD` | `#B089A8` | `#B48EAD` |
| pattern   | 3     | `#88C0D0` | `#669DAD` | `#88C0D0` |
| pattern   | 4     | `#EBCB8B` | `#A08143` | `#EBCB8B` |
| pattern   | 5     | `#8FBCBB` | `#4F7B7A` | `#ABD9D7` |
| pattern   | 6     | `#81A1C1` | `#446380` | `#D1E8FF` |
| gradient  | 0     | `#5E81AC` | `#1E3E65` | `#6E92BD` |
| gradient  | 1     | `#A3BE8C` | `#839C6C` | `#D3F0BC` |
| structure | 0     | `#BF616A` | `#946669` | `#D5A2A5` |
| structure | 1     | `#EBCB8B` | `#523F19` | `#FEE9BE` |
| structure | 2     | `#B48EAD` | `#664661` | `#F0C9E9` |

Past the seven: `#D08770`, `#BF616A`.

### Solarized

`solarized.tsv`. Source: <https://raw.githubusercontent.com/altercation/solarized/master/README.md>.

| Role      | Place | Source            | Light     | Dark      |
| --------- | ----- | ----------------- | --------- | --------- |
| pattern   | 0     | `#268BD2`         | `#268BD2` | `#3395DC` |
| pattern   | 1     | `#859900`         | `#859900` | `#859900` |
| pattern   | 2     | `#6C71C4`         | `#6C71C4` | `#8288DD` |
| pattern   | 3     | `#2AA198`         | `#2AA198` | `#2AA198` |
| pattern   | 4     | `#B58900`         | `#B58900` | `#B58900` |
| pattern   | 5     | `#D33682` (moved) | `#D33682` | `#F1549B` |
| pattern   | 6     | `#CB4B16` (moved) | `#C3440C` | `#EA6736` |
| gradient  | 0     | `#268BD2`         | `#014069` | `#3295DD` |
| gradient  | 1     | `#859900`         | `#8A9E12` | `#DBF278` |
| structure | 0     | `#DC322F`         | `#A87972` | `#C1918A` |
| structure | 1     | `#D33682`         | `#7F5564` | `#E5B5C5` |
| structure | 2     | `#B58900`         | `#84724B` | `#C2AF86` |
| structure | 3     | `#2AA198`         | `#245D58` | `#ABE5DE` |
| structure | 4     | `#6C71C4`         | `#3C3F62` | `#E6EAFF` |

Past the seven: `#DC322F`.

### Catppuccin

`catppuccin.tsv`. Source: <https://raw.githubusercontent.com/catppuccin/palette/main/palette.json>.

| Role      | Place | Source                | Light     | Dark      |
| --------- | ----- | --------------------- | --------- | --------- |
| pattern   | 0     | `#1E66F5` / `#89B4FA` | `#1E66F5` | `#89B4FA` |
| pattern   | 1     | `#40A02B` / `#A6E3A1` | `#40A02B` | `#A6E3A1` |
| pattern   | 2     | `#8839EF` / `#CBA6F7` | `#8839EF` | `#CBA6F7` |
| pattern   | 3     | `#179299` / `#94E2D5` | `#179299` | `#A0EFE2` |
| pattern   | 4     | `#209FB5` / `#74C7EC` | `#01778A` | `#7ED2F7` |
| pattern   | 5     | `#7287FD` / `#B4BEFE` | `#7287FD` | `#C4CCFE` |
| pattern   | 6     | `#04A5E5` / `#89DCEB` | `#019FDC` | `#D8F9FF` |
| gradient  | 0     | `#8839EF` / `#CBA6F7` | `#4D0094` | `#A37FCD` |
| gradient  | 1     | `#179299` / `#94E2D5` | `#33A3AA` | `#A9F6E9` |
| structure | 0     | `#DC8A78` / `#F5E0DC` | `#A7796F` | `#AD9996` |
| structure | 1     | `#DF8E1D` / `#F9E2AF` | `#7A5D3D` | `#D5C298` |
| structure | 2     | `#40A02B` / `#A6E3A1` | `#627D5C` | `#9BBB99` |

Past the seven: `#DF8E1D` / `#F9E2AF`, `#FE640B` / `#FAB387`, `#EA76CB` / `#F5C2E7`, `#D20F39` / `#F38BA8`, `#E64553` /
`#EBA0AC`, `#DD7878` / `#F2CDCD`, `#DC8A78` / `#F5E0DC`.

### Apple

`apple.tsv`. Source: <https://developer.apple.com/design/human-interface-guidelines/color>,
<https://developer.apple.com/tutorials/data/design/human-interface-guidelines/color.json>.

| Role      | Place | Source                | Light     | Dark      |
| --------- | ----- | --------------------- | --------- | --------- |
| pattern   | 0     | `#0088FF` / `#0091FF` | `#0088FF` | `#0091FF` |
| pattern   | 1     | `#34C759` / `#30D158` | `#05AC42` | `#30D158` |
| pattern   | 2     | `#6155F5` / `#6D7CFF` | `#6155F5` | `#7A8BFE` |
| pattern   | 3     | `#00C0E8` / `#3CD3FE` | `#07A2C5` | `#3CD3FE` |
| pattern   | 4     | `#CB30E0` / `#DB34F2` | `#CB30E0` | `#E540FC` |
| pattern   | 5     | `#00C8B3` / `#00DAC3` | `#0AA391` | `#00DAC3` |
| pattern   | 6     | `#FFCC00` / `#FFD600` | `#B69001` | `#FFD600` |
| gradient  | 0     | `#6155F5` / `#6D7CFF` | `#3401AA` | `#7484FF` |
| gradient  | 1     | `#00C8B3` / `#00DAC3` | `#03A796` | `#7CFFEA` |
| structure | 0     | `#AC7F5E` / `#B78A66` | `#A27D63` | `#BB9679` |
| structure | 1     | `#FF383C` / `#FF4245` | `#825651` | `#E9B6B1` |
| structure | 2     | `#00C3D0` / `#00D2E0` | `#477F84` | `#83BDC2` |
| structure | 3     | `#FFCC00` / `#FFD600` | `#5F5129` | `#E4D8AB` |
| structure | 4     | `#CB30E0` / `#DB34F2` | `#523755` | `#FCE1FF` |

Past the seven: `#00C3D0` / `#00D2E0`, `#FF8D28` / `#FF9230`, `#FF2D55` / `#FF375F`, `#FF383C` / `#FF4245`, `#AC7F5E` /
`#B78A66`.
