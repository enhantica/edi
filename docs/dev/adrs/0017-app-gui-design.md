# ADR-0017 — The edi app's GUI design: layout, naming, colours and icons

- **Status:** Proposed (the owner's ideas of 2026-09-29, confirmed one by one in the loop)
- **Date:** 2026-09-29
- **Implementation:** 🟡 Partial — §1–§14 are built (ideas 10 and 18 withdrawn by the owner); the two parts of
  §14's calculator decision deferred (writing
  `crysta` on save, switching the five `cryspy` examples) landed with; §15 is built and
  §16
- **Priority:** Medium
- **Forward constraint (binding on new features):** a new page, group, field or button follows the layout,
  naming, colour and icon rules below; a change to one of them changes this ADR in the same commit.

## Context

ADR-0015 fixes the app's stack: easydiffractionbeta v0.9.9 is the layout authority, gui-components v0.9.1 is the
base, consumed unmodified, and every sidebar group is one `.edi` category. What it does not record is the design
detail the owner decides by looking at the running app: which group opens, what a tab or group is called, which
buttons show, what colour a datablock has. The owner asked on 2026-09-29 that every such choice and its
clarification be written down *"with layout, colors, etc. So, that in the future development it is clear what we
want."* This ADR is that record. It gathers the decisions it rests on and adds ideas, each cited by number.

The decisions it rests on, unchanged here:

- **Sidebar groups are `.edi` categories** (ADR-0015 §3): a group exists exactly when the core returns its
  category; Basic or Extras is a per-category choice in `app/src/category_list_model.cpp`.
- **A loop in `.edi` is a table in the GUI**: every loop category's content is a
  `TableView`, with its row count in the group title.
- **Theme:** the base's themes (Light, Dark, System); System follows the platform's colour scheme live
  (`app/qml/Globals/AppState.qml`). Every colour is a token of the base's `EaStyle.Colors`.
- **Fonts:** as ADR-0015 §10 records them — PT Sans for text, PT Mono for `.edi` text, Baloo 2 for the
  wordmark, Font Awesome 5 Solid for icons. This ADR does not restate them.

## Decision

### 1. Home and About

- **The wordmark and the version are one composition on Home and in About**, from one component
  (`Components/WordmarkWithVersion.qml`), so the two cannot drift apart (ideas 2 and 3; the owner's review of
  2026-09-29): the wordmark (`Components/Wordmark.qml`, the mark and "easy" over "diffraction") centred
  horizontally as one unit, then the version line `Version <version> (<date>)` centred on its own below it,
  one x-height of the version's font apart (measured, `FontMetrics.xHeight`; the owner, 2026-09-29, was two
  font units). The wordmark carries no caption: the version never hangs under the name.
- **The wordmark's size** is the same in both: a mark of 5 base font units (`AppSizes.homeMarkDiameter`,
  easydiffractionbeta's Home size; idea 2). In About a click on the mark opens the homepage.
- **About** stacks, each centred: the wordmark and version, then the licence links, the description, and the
  copyright footer. **Home** stacks the wordmark and version, then Start, then the two link columns.
- **The description** reads *"EasyDiffraction is a software for calculating diffraction patterns based on
  structural models and refining their parameters against experimental data."* (`ApplicationInfo.description`,
  idea 1). It wraps, centred, at a width of 1.15 × one third of its one-line width, so it takes three lines of
  similar width.
- **Online documentation** opens `https://docs.easydiffraction.org/app/` (`ApplicationInfo.docsUrl`, idea 4),
  from Home and from the app bar.

### 2. The main area and the Experiment type group

- **Main-area tab names** are the current block's icon and name, no word (ideas 6–8, then idea 23): Project
  page the `archive` icon (the app bar's Project icon) in the tab's own text colour — a project has no
  datablock colour, so the icon follows the tab's active and inactive colour as its text does — then the
  project's name; Structure page the structure's `layer-group` icon in its colour (§8) and its name; Experiment
  page the experiment's `microscope` icon in its colour and its name. With no block the tab reads the plain
  word `Project`, `Structure` or `Experiment`, without an icon: an icon alone would not say what the empty tab
  is. `Components/IconTabButton.qml` is the base's `TabButton` with its content drawn as one icon line (§10).
  Analysis keeps `Fitting`.
- **Experiment type** shows its type axes as a grid **three wide**, filled row by row — sample form, beam mode,
  probe on the first row; scattering type on the second — so each name fits and two further axes have their
  places (idea 14). Each box is `(sideBarContentWidth − 2 × fieldSpacing) / 3` wide; the rows are
  `groupContentSpacing` apart.

### 3. Sidebar groups: titles, which one opens, borders

- **Titles** follow easydiffractionbeta's group names where a category matches one. **A loop category's title is
  plural**, since it names the rows it counts; the count follows in brackets (idea 19). **Exception —
  Background**: its title names the category, not its rows, since the category holds line-segment points and
  will hold polynomial (Chebyshev) coefficients alike (the owner, 2026-09-29); it stays *Background (N)*. The
  full title table:

  | `.edi` category | Title | Loop | Icon (Font Awesome 5) |
  |---|---|:--:|---|
  | `metadata` | Project | | `archive` |
  | `space_group` | Space group | | `satellite` |
  | `cell` | Cell | | `cube` |
  | `atom_site` | Atom sites | ✓ | `atom` |
  | `scattering_length` | Scattering lengths | ✓ | `ruler` |
  | `experiment_type` | Experiment type | | `radiation` |
  | `data` | **Measured data** (was *Measured range*, idea 15): the axis summary over the points table; the count is the number of measured points (the owner, 2026-09-29), which the core's category list does not count, so `ExperimentViewModel` marks `data` a loop of that many rows | ✓ | `arrows-alt-h` |
  | `data_range` | Calculation range | | `arrows-alt-h` |
  | `instrument` | Instrument | | `microscope` |
  | `peak` | Peak profile | | `shapes` |
  | `background` | Background (the plural rule's exception, above) | ✓ | `wave-square` |
  | `linked_structure` | **Linked structures** (was *Linked structure*) | ✓ | `layer-group` |
  | `excluded_region` | Excluded regions | ✓ | `eraser` |
  | `absorption` | Absorption | | `tint` |
  | `preferred_orientation` | **Preferred orientations** (was *Preferred orientation*) | ✓ | `compass` |
  | `scattering_source` | Scattering source | | `atom` |
  | `refln` | Reflections | ✓ | `list` |
  | `minimizer` | Minimizer | | `level-down-alt` |
  | `fitting_mode` | Fitting mode | | `sliders-h` |
  | `alias` | Aliases | ✓ | `tag` |
  | `constraint` | Constraints | ✓ | `equals` |
  | `joint_fit` | **Joint-fit weights** (was *Joint fit*) | ✓ | `link` |
  | `sequential_fit` | Sequential fit | | `list-ol` |
  | `sequential_fit_extract` | **Scan extraction rules** (was *Scan extraction*) | ✓ | `filter` |
  | `fit_parameter` | **Fit start values** (was *Fit start state*) | ✓ | `history` |

  The block lists keep theirs: `Structures (N)` (`layer-group`) and `Experiments (N)` (`microscope`).
- **All foldable groups start folded** (owner, 2026-09-29), on every page and tab: the block lists
  (Structures, Experiments) and every category. **The one exception is Get started** on Project → Basic, which
  starts open, as the first thing a new user needs (the owner, 2026-09-29). Idea 10 (the top group of Basic and Extras open by
  default) is **withdrawn**, and with it the block lists' reopening for each new project. The base's
  auto-collapse is kept: opening a group folds the others on its tab. Groups that cannot fold — the shared
  block selector (§7), the untitled Analysis Parameters and Fitting groups, the Text tab's groups — are not
  affected. The demo opens each group its capture shows with a click.
- **Order:** groups follow the core's page order of categories, except where the app lists a different one
  (`presentation_order` in `app/src/category_list_model.cpp`; presentation only — the Analysis table and the
  files keep the core's order): on Experiment → Basic **Background is shown directly above Instrument**
  (the owner, 2026-09-29) and **Linked structures last** (the owner, 2026-10-04, when Excluded regions moved to
  Basic), giving block selector · Experiments · Experiment type · Background · Instrument · Peak profile ·
  Excluded regions · Linked structures.
- **Measured data is on Extras** (the owner, 2026-09-29), not Basic: its summary fields and data table are
  the first group of Experiment → Extras, above Peak profile's Extras part (the core's order among the Extras
  groups puts it first). Sidebar only: the core's category order, the files and the Analysis table are
  unchanged. Calculation range (a calculation-only experiment's grid) stays on Basic.
- **Background** shows at most four table rows (the owner, 2026-10-04; five before), then scrolls (`maxRowCountShow`, as the other tables);
  Append new point and Reset to autodetected background stay below it.
- **The last group a tab shows draws no bottom border** (idea 11). The base's `GroupBox` takes `last` from its
  parent's last child, which in a column with a `Repeater` is the last delegate whether it is shown or not
  (gui-components#55), so edi sets `last` itself (`Globals/SideBarGroups.qml`). "Shown" is the group's tab
  rule (`CategoryGroup.shown`), not `visible`, which is also false while the page is hidden.

### 4. Actions not yet implemented are shown, disabled

A button easydiffractionbeta had, or the owner asks for, whose function edi does not have yet, is **shown and
disabled** rather than left out, so the layout is final:

- **Define structure manually** beside **Load structure from file** in Structures, and **Define experiment
  manually** beside **Load experiment(s) from file(s)** in Experiments — two half-width buttons in a row, the
  second with the `plus-circle` icon, as easydiffractionbeta's (idea 13).
- **Reset to autodetected background** beside **Append new point** in Background, `undo-alt` icon
  (idea 17).
- **Open project from URL…** in Project → Basic → Get started, `link` icon (the owner, 2026-09-29, idea
  27). Get started's four buttons sit two by two: *Create a new project*, *Open an existing project*; *Save
  project as…* (§13), *Open project from URL…*.
- **Set automatically** to the right of **cutoff (FWHM)** in Extras → Peak profile, on the same row, field and
  button half the row each with their bottoms aligned, `magic` icon, and the tooltip *Not available yet* (the
  owner, 2026-09-29): there is no automatic cutoff yet. A disabled button takes no hover, so its tooltip hangs
  on the item around it.
- **In Preferences** (§12): Updates' **Check on application start** (unchecked) and **Check now**, and
  Experimental's **Zoom** (at 100 %) and **Language** (English) — each with the *Not available yet* tooltip on
  the item around it. None takes effect whatever a settings file says: no update check runs at start, no zoom
  and no language is applied.
- **A button sharing a row with a field is exactly as tall as the field's box** (the field's height less its
  title inset) and shares its bottom, so both edges line up (the owner, 2026-09-29). The base sizes the two
  from different things — a text field's box from its text line plus twice its padding, a sidebar button from
  the fixed `sideBarButtonHeight` token (2.75 font units) — so side by side the button stood taller. Rows of
  buttons only (Background's Append and Reset, the block lists' Load and Define) are all one height already;
  the cutoff row is the only field-and-button row.

### 5. Parameter fields: rows, widths, profile-unused fields, labels

- **Peak profile has no subheadings for now**. Under the profile selector its fields run **one row per
  family** (the owner's review of 2026-09-29), every row five fields wide so the columns line up and a
  shorter row leaves its last cells empty (`ExperimentViewModel.peakBackToBack` / `peakGaussian` /
  `peakLorentzian` /
  `peakOther`, by `.edi` name prefix):

  | Profile | Row 1 | Row 2 | Row 3 | Asymmetry row |
  |---|---|---|---|---|
  | TOF Jorgensen–Von Dreele | α₀ α₁ β₀ β₁ (`rise_*`, `decay_*`) | σ₀ σ₁ σ₂ size G strain G (`broad_gauss_*`) | γ₀ γ₁ γ₂ size L strain L (`broad_lorentz_*`) | — |
  | TOF Jorgensen | α₀ α₁ β₀ β₁ | σ₀ σ₁ σ₂ size G strain G | — | — |
  | TOF pseudo-Voigt | — | σ₀ σ₁ σ₂ size G strain G | γ₀ γ₁ γ₂ size L strain L | — |
  | CW pseudo-Voigt, CW Thompson–Cox–Hastings, and any CW profile | — | U V W (`broad_gauss_u/v/w`) | X Y (`broad_lorentz_x/y`) | the declared `asym_*` fields, as now |

  A fourth row takes any peak field of no family; the asymmetry fields keep their own row after them, five
  wide as the others.
- **A field the selected profile does not use is not shown in the sidebar.** The core keeps such a field in
  its category while it is free (ADR-0015 §3), so a switch of profile (TOF JvD to pseudo-Voigt or to
  Jorgensen, CW to TOF fields in the file) used to leave it as an input labelled "… (not used by this
  profile)", whose label ran over its neighbours. Now `ParameterGrid` hides it and the other fields close
  up, a family row with no used field disappears, and the field stays in the Analysis table, where it can be
  fixed. Its value is unchanged and stays in the file.
- **Every field's title is set the same way, as the combo box's** (the owner, 2026-09-29): left-aligned,
  inset from the field's left edge by the base combo box's own content padding (read at run time from a base
  `ComboBox`, not a number of edi's; 0.75 font units in v0.9.1), as wide as the field less that inset, and
  ending in "…" when longer, so no title runs past its field or over a neighbour. The vertical gap, font and
  colour are the base's own, the same for text fields and combo boxes. `Globals/FieldTitles.qml` applies it to
  `ParameterField`, `ValueField`, `SelectorField` and the Experiment type boxes — so to Space group, Cell,
  Atom-site fields, Measured data, Instrument, Peak profile, Absorption, Minimizer, Fitting mode and the rest.
  The base draws a text field's title right-aligned and a combo box's inset from the left; edi follows the
  latter everywhere.
- **Minimizer's max iterations shows the bound the fit uses**: the declared `_minimizer.max_iterations`, or,
  when none is declared, the fit's own cap (`edi::default_max_iterations()`, 50) — as the tolerance beside it
  shows crysta's default. A project that declares none showed an empty field before.
- **Fields share the full row** unless a rule above says otherwise: a row of fields takes the sidebar content
  width, split evenly (the base's `GroupRow` fields, and `ParameterGrid` with `fillRows`, as Instrument).
  Absorption now does so too: μR alone takes the row, ABSCOR1 and ABSCOR2 half each (the owner, 2026-09-29; it
  was three columns wide). The sweep found no other half-empty row; the exceptions are deliberate — Peak
  profile's five-wide rows above, and Experiment type's grid three wide (§2).

### 6. Measured data: the increment

**inc** shows one value when every step between neighbouring points reads the same at the field's display
precision (the base's three significant digits, `Utils.toDefaultPrecision`), and otherwise the smallest and
largest step as `min–max` (TOF data, merged scans; idea 16). The steps come from `RangeViewModel.stepMinimum`
and `stepMaximum`.

### 7. The block selector and the Text tab

- **One block selector per sidebar** on the Structure and Experiment pages (idea 9): a compact combo box one
  sidebar content wide (`Components/BlockSelector.qml`, `objectName` `sideBar.blocks`) whose every line reads
  as easydiffractionbeta's Text-tab selector — the block's number (minor colour), its icon in its colour (§8),
  its name — under the sidebar's Basic / Extras / Text tab bar and above every tab's content, always shown and
  never folded. It lists the page's blocks with the current one shown; choosing one makes it current on every
  tab and in the block table. It sits one font unit under the tab bar, at the groups' left padding. The base's
  `SideBar` has no place for such an item, so `WorkflowPage` makes it a child of the `SideBar`, placed under
  the tab bar, and moves the top of the base's tab view down below it (a binding on the view's
  `anchors.topMargin`) — one widget, not one per tab, and the base unmodified.
- **Block selectors: one component, one shared current block** (the owner, 2026-09-29). Every selector that
  chooses among a project's blocks is a `BlockSelector` — the shared one on Structure and Experiment, and the
  experiment selector at the top of Analysis → Basic (where it stays) — so all read number, coloured icon and
  name, in the box and the list alike. Each reads and writes the project's one current index
  (`ProjectViewModel.currentExperimentIndex` / `currentStructureIndex`), never another selector, so choosing
  an experiment on the Experiment page makes it current on Analysis and the other way round; after a choice the
  box follows the shared index again. Structures are chosen on the Structure page only (its selector and its
  Structures table share `currentStructureIndex`). The Analysis parameter table lists every parameter of the
  project, so a change of experiment keeps a selected row that is still shown (§11).
- **The selector closes with a group's bottom border on every tab** (the owner's reviews of 2026-09-29): the
  line a category group draws — `borderThickness` high, `appBorder` colour, across the sidebar — one font unit
  under the selector; the tab's content starts right under it — on Basic and Extras the first group's title, on
  Text the text view's background, with no gap. The owner first had the line on Basic and Extras only; once the
  text view filled the tab edge to edge, the Text tab took it too.
- **One project at a time, so no project selector** (the owner, 2026-09-29): the app does not open several
  projects together, so the Project, Analysis and Report Text tabs — one block each — have no selector. No Text
  tab has a selector of its own: on Structure and Experiment the shared block selector serves it. The shared
  block selector and the Analysis Basic experiment selector stay, as they choose among several blocks.
- **The Text tab's text view fills the whole tab** (idea 5, as the owner revised it on 2026-09-29): the
  sidebar's full width, edge to edge, from the top of the tab's view — right under the tab bar on Project,
  Analysis and Report; right under the shared block selector's border on Structure and Experiment, never
  over the selector — down to the sidebar's bottom, on every page's Text tab. It
  has no border and no inset box: its `textViewBackground` runs to the sidebar's edges, where the sidebar's own
  edge line stays; only the text keeps its padding of one font unit inside it. While the Text tab is shown,
  `WorkflowPage` lets the base's tab view reach the sidebar's bottom instead of stopping above Continue (a
  binding on the view's `anchors.bottomMargin`; the other tabs keep the base's). The view never gets shorter
  than 5 font units. This replaces fixed height plus the window's growth.
- **Continue is a pill** (the owner, 2026-09-29), on every page and tab that shows it: the base button's own
  background (`themeBackground`, hovered `themeBackgroundHovered1`) and 1-px border (`appBarComboBoxBorder`)
  shown, fully rounded ends (radius half its height, `sideBarButtonHeight`), as wide as its icon and text plus
  one font unit on each side, horizontally centred, one font unit above the sidebar's bottom (the base's 0.5
  plus half; it was 1.5 before the owner moved it a third of the way down, 2026-09-29). `WorkflowPage` sets
  these on the base `SideBar`'s `continueButton`; the width reads the base button's unnamed icon-and-text row,
  and the raise is a binding on its bottom margin. The base is unmodified; the base's fade above Continue moves
  with it.
- **On the Text tab** the pill floats over the text view with nothing else: the base's grey fade stays hidden
  there (`WorkflowPage` finds it as the `SideBar`'s child with a gradient). The text's last lines scroll clear
  of the pill: the view's bottom margin is the pill's height plus half a font unit
  (`AppSizes.textViewContinueClearance`). Report, which has no Continue, has no such margin
  (`TextTab.underContinue: false`).

### 8. Datablock colours and iconified names

Every datablock has a colour and an icon, as in easydiffractionbeta (ideas 12 and 20), from
`Style/AppColors.qml`:

| Block | Icon | Colour by its place in the project's list (light / dark theme) |
|---|---|---|
| structure | `layer-group` | the base's `models`: orange `#FF9800` / `#FFCC80`, teal `#009688` / `#80CBC4`, pink `#E91E63` / `#F48FB1`, then round again |
| experiment | `microscope` | light blue `#03A9F4` / `#81D4FA` (easydiffractionbeta's measured-data colour, `chartForegroundsExtra[2]`), then brown `#795548` / `#BCAAA4` (`[3]`), green `#4CAF50` / `#A5D6A7` (`[1]`), then round again |

An element's colour is the Jmol colour of the core's element table (`data/elements/element-styles.tsv`, ADR-0022
§4, the same values as easydiffractionbeta's `Logic/Tables.py`), of the type symbol's element: its first capital
letter and the lower-case letter after it (`Co2+` is Co, `162Dy` is Dy, `2H` is H). An element the table does not
have takes the minor foreground colour. The app holds no element colour of its own (`AppColors.element()` asks the
core through `ApplicationInfo.elementColor`). The colour follows
the site's type symbol as it is edited: the parameter registry reads each atom parameter's element again at
every publish (`ParameterRegistry::refreshElements`), not only when the set of parameters is rebuilt. An experiment's colour is
the one its measured data takes in the pattern chart, and a structure's is the one its Bragg ticks take (§15).

- **Block tables:** the Structures and Experiments tables have a colour column after `No.`, one table row high,
  with the block's icon in its colour (tooltip *Calculated pattern color* / *Measured pattern color*), as
  easydiffractionbeta's Models and Experiments tables.
- **Every loop table has one design** (the owner, 2026-09-29): a `No.` column first (row numbers from 1,
  in the minor colour); where the rows are datablocks — Structures, Experiments, Linked structures, Joint-fit
  weights — the block's icon in its colour next (`IconCell`, §10); left-aligned text columns (names, labels,
  paths) and centred number columns under centred headers, numbers at display precision (`TextCell`); the
  base's header style and cell insets. Joint-fit weights was the one table without `No.` and icon, its names
  flush with the table's edge; it now follows the rule. The sweep found the others already do: Measured
  data, Background, Excluded regions, Preferred orientations, Reflections, Atom sites, Scattering lengths,
  Scan extraction rules, Fit start values.
- **Linked structures:** each row shows, after `No.`, the linked structure's `layer-group` icon in that
  structure's colour (found by its name among the project's structures), then its name, the scale, and a
  remove button — disabled, since an experiment keeps its one linked structure (§4) — as easydiffractionbeta's
  Associated phases.
- **The block selector** (§7) shows the same icon and colour before each name.
- **Atom sites** (Structure page): each row shows, after `No.`, the atom-site category's icon in the site's element
  colour, as the Analysis parameter names below carry it (the owner, 2026-10-03).
- **Analysis parameter names** (`Globals/ParameterNames.qml`) are easydiffractionbeta's shortest names with
  icons and pretty labels: the block's icon in the block's colour; the category's icon (the sidebar group's,
  §3), for an atom site in its element's colour; the row — an atom's label, or a loop row's number counted
  from 1 (a background point, a preferred orientation, a linked structure: every loop category whose rows
  carry parameters, by the core's `ParameterEntry::row_label`) — in the category icon's colour; the parameter's icon in the minor colour; then its short name in
  bold (e.g. *[lbco] [atom] O [fill] **occ***). The parameter icons are easydiffractionbeta's by `.edi` name:
  `length_*`, `angle_*` `ruler`; `fract_*` `map-marker-alt`; `occupancy` `fill`; `adp_*` `arrows-alt`; `scale`
  `weight`; `setup_wavelength` and `calib_d_to_tof_*` `radiation`, except `calib_d_to_tof_offset` and the other
  `calib_*` `arrows-alt-h`; `setup_twotheta_bank` `hashtag`; `broad_*`, `rise_*`, `decay_*` `shapes`;
  `asym_*` `balance-scale-left`; background `intensity` `mountain`; none otherwise. The path stays in the
  name's tooltip, and the name filter still matches the path.

### 9. The Project description

The Project page's main area (`Pages/Project/DescriptionTab.qml`) lists, under the name, title and description:

- **Location** — always, the project's directory; for a bundled example the path of its working copy, where a
  save writes (idea 21). There is no separate *Example* row: the example's id is the working copy's folder
  name, in the path. The demo shows the working copy's temporary root as `<temporary>` (`Session.projectLocation`),
  so its images do not depend on the run's directory.
- **Structures (N)** and **Experiments (N)** — the count in brackets after the label, and as the value the
  datablock **names** (never file names: a block's file follows from its name, `structures/<name>.edi`),
  comma-separated, each after its block icon in its colour (§8), wrapping when they do not fit a line — as
  easydiffractionbeta's *Model file: lbco.cif, coo.cif* (idea 22; `Pages/Project/BlockNames.qml`).
- No *Warnings* row: the loader's warnings are the status bar's messages (§14).

### 10. An icon before a name sits on the name's centre line

Wherever an icon precedes a name — the main-area tab titles, the Project description's block names, the block
selector (box and list), the colour columns of the Structures, Experiments and Linked structures tables, and
the Analysis parameter names — icon and text are drawn by one component, `Components/IconLine.qml` (the owner's
review of 2026-09-29: the icons sat high). Its rule: the text pieces share the line's baseline; each icon is
placed so the middle of its drawn glyph (its tight bounding box, measured in the icon font) lies on the middle
of a capital's height of the text (`H`, measured in the text font). Neither the icon font's baseline nor its
line box is used: Font Awesome's metrics differ from PT Sans's, and either one draws the icon high. The line is
one text line high whatever it holds, so an icon alone centred in a table cell (`Components/IconCell.qml`, the
colour column) lies on the centre line of the centred text beside it. Pieces are separated by half a font
unit; a bold piece uses PT Sans Bold by its family and style (ADR-0015 §10). Where a line replaces a
control's content, it is given the control's full height to centre in: the block selector's list rows drop the
base menu item's vertical padding (16 on each side of a row 2.5 font units tall, which leaves no height and
clipped the line to a sliver). Rich text is no longer used for
icons: its inline glyphs sit on the font baseline and could not follow this rule.

### 11. The Analysis parameter table has a row selected

**A row of the Analysis parameter table is always selected while the table shows any** (the owner, 2026-09-29),
so the slider and its two limit boxes always show a parameter: the first shown row when a project opens, when
the current experiment changes, and when the name filter or the variability filter hides the selected row; a
row the user selected stays selected while it is shown (`ParametersGroup.ensureSelection`, over
`ParameterFilterModel.parameterAt` / `shows`). The selected row is highlighted (`tableHighlight`), as the block
tables' current row. This replaces empty start: the demo's `13-analysis-basic` now shows the first row selected
with the slider filled; `t2-04-analysis-slider` still clicks that row, and `t2-07-dark-analysis` keeps it.
The slider spans the selected value ± a half width, set when a row is selected or its value is committed (not while
dragging; `ParameterItem::sliderHalfWidth`): 0.05 Å for a lattice constant (`length_a`, `length_b`, `length_c`; the
owner, 2026-10-04), half the value's magnitude (at least 0.001) otherwise.

### 12. Preferences, and the sidebar's side

- **edi shows its own Preferences dialog** (`Components/AppPreferencesDialog.qml`), rebuilt from the base's
  pieces as the About dialog is, with the base's five tabs and layout: Prompts, Updates, Appearance,
  Experimental, Develop. The base's `PreferencesDialog` offers no way to hide or add a row, and the base's
  window always creates it; it stays hidden, as the app bar's Preferences button opens edi's dialog
  (`Preferences.dialogShown`) instead of setting the base's flag.
- **Appearance**: Theme; **Sidebar — Left or Right** (the owner, 2026-09-29); Auto collapse. **The 1D plotting
  row is removed** (the owner, 2026-09-29): edi has no choice of chart library.
- **Updates and Experimental**: shown disabled (§4).
- **Persistence**: tool tips, auto collapse and the sidebar's side persist in the app's settings file (the
  base's `Settings` mechanism and file, `EaGlobals.Vars.settingsFile`) under edi's own category
  `Edi.Preferences` (`Globals/Preferences.qml`); the theme and the logging level keep the base's own
  persistence. Once the window is complete, `Preferences.apply` hands edi's values to the base — after the
  hidden base dialog has loaded its own keys, so edi's win — and forces what is not available off: no update
  check at start, zoom 100 %. A demo or test run has its own fresh settings file, so the sidebar is on the
  right there.
- **The sidebar on the left**: the whole sidebar — its tabs, content and Continue — moves to the window's left,
  the main area with its tabs to the right, live when the preference changes. `WorkflowPage` re-anchors the
  base `ContentPage`'s two containers (reached as the parents of the main content and the sidebar) and moves the
  sidebar's border to its edge towards the main area. Nothing is mirrored: text, icons and the order of numbers
  and columns stay as they are. The base is unmodified.

### 13. Saving

Saving is active:

- **Save** (app bar, highlighted; Ctrl/Cmd+S) writes the project to its own directory; it is enabled while the
  project has unsaved changes. **Save as** (Ctrl/Cmd+Shift+S, and **Save project as…** in Project → Basic →
  Get started, beside Create and Open, `file-export`) asks for a directory (a folder dialog) and writes the
  project there, which is its directory from then on. **The app bar has no Save as button** (the owner,
  2026-09-29): its left group stays Save, Undo, Redo, Reset, as easydiffractionbeta's. A project with no
  directory of its own — a bundled example, which lives in a temporary working copy — is saved as on its first
  Save (`Session.needsSaveAs`); once saved, it is no longer the example's copy.
- **The core writes**: `Session.save` / `saveAs` call `ProjectViewModel.saveTo`, which calls
  `edi::save_project_as` (`core/include/edi/io.hpp`): the last-modified time advances before the write and is
  restored if it fails, and the directory is remembered only after it succeeds — the Python binding's
  `save_as` rule, which the binding still spells out itself (a follow-up can move it onto the core
  function). Every datablock is written: `project.edi`, `structures/<name>.edi`, `experiments/<name>.edi`,
  `analysis/analysis.edi`. QML writes no file.
- **The modified state** (`ProjectViewModel.modified`) is set by every edit that goes through the project's
  one edit path (`apply`: values, vary flags, names, types, loaded or removed blocks) and cleared by a
  successful save; opening a project starts it clear, and the demo's timestamp pin leaves it as it was. The
  window title leads with "• " while it is set.
- **A refused save** opens a dialog, *The project was not saved*, with the core's message: the Messages
  dialog's fixed content width (§14), the message wrapped inside it.
- Redo stays disabled. Undo undoes the last fit (§17); it is disabled while the model holds no fit start state.
- **Phase 2 must gate** the round trip (save, then reopen the directory: the same project, file for file), the
  modified state (set by an edit, cleared by a save, clear after an open) and an example's first Save going to
  Save as (and a later Save writing where it was saved as).

### 14. Messages: a status-bar counter and a popup


- **One list of messages** (`Session.loadWarnings`, a `WarningListModel`, the only source): the loader's
  warnings from the last open, and every message a view used to show in red — the calculation's refusal
  (idea 25), one row per distinct refusal text, which the chart placeholders no longer show (they keep their
  grey title and points/range line). Each row is a *warning* or an *error*. A new open replaces the list. A
  dismissed message leaves the list and stays away until it is raised again: a refusal is raised again by the
  next recalculation that is refused (after a model change); a load warning by the next open.
- **The status bar's last item, always present**: the `exclamation-triangle` icon, the key *Messages*, and
  the number of messages **not viewed yet** (`WarningListModel.unviewedCount`; idea 24, *"the number of
  not-viewed warning messages"*), in the status bar's own style: in the theme's red while it is above 0, and
  0 in the normal value colour once the dialog has been opened, although the list keeps its messages until
  they are dismissed. A message raised later counts again. Each message carries its own viewed state and
  the count is derived from them, so a removed message (a dismissal, a refusal that no longer holds) takes
  away exactly its own share: a viewed one leaves the count as it is, a not-viewed one lowers it by one. Named *Messages*, not *Warnings*, since it holds
  errors too.
- **Every dialog sits on whole pixels** (`Components/AppDialog.qml`: About, Preferences, Messages and the
  save refusal; the base's project-description dialog is placed the same way where edi opens it). The base
  centres a dialog with a half, so one of odd height lay on a half pixel and its edges were drawn differently
  on Linux and macOS (edi PR 97, the three-row Messages dialog); edi rounds the centred position.
- **A click opens the Messages dialog**, the same dialog as About and Preferences (the base `Dialog`: title
  bar, padding, background without an outline, OK). **Width fixed**: 38 font units
  (`AppSizes.messagesDialogContentWidth`, about Preferences' width), whatever the messages. **Height fits the
  rows** (the owner, 2026-09-29): the list is as tall as its rows (the table's content height; rows wrap), at
  least one single-line row, and at most what keeps the whole dialog inside the window between the app bar
  and the status bar less one font unit at each — above that it scrolls. It resizes while open as messages are
  dismissed, and stays centred. The list is a sidebar table (the base `TableView`, headerless and with
  alternating rows, as Examples and Recent projects), and its 1-px `appBarComboBoxBorder` frame is drawn again
  above the rows and the empty state, so nothing covers its edges. Each row: the kind's icon (warning
  `exclamation-triangle` orange; error `times-circle` red), the message wrapped onto as many lines as it needs
  (never elided, never widening the dialog; an error's text in red), and the row's dismiss button (the tables'
  `minus-circle` `TableViewButton`). Empty, the one row shows a muted `inbox` icon and *No messages* on one
  line, centred. **Dismiss all** is in the dialog's button row, beside OK (the base `DialogButtonBox`,
  right-aligned), disabled when the list is empty. Opening the dialog marks the messages viewed.
- **Removed**: the Project description's *Warnings* row (§9), the red banner that popped up after an open, and
  the chart placeholders' red *Calculation refused* line.
- **Unsupported engines warn** (the owner's decision of 2026-09-29, "2 + (b)"): the loader (`load_project`,
  `core/src/io.cpp`) warns `unsupported _minimizer.type "<value>" - using crysta` for an analysis block's
  minimizer other than `crysta`, and `unsupported _calculator.type "<value>" - using crysta` for an
  experiment's calculator other than `crysta`, once per distinct value; the run uses crysta either way. Both
  land in the message list as warnings. A third engine choice warns the same way: `project.edi`'s
  `_rendering_plot.type`, the plot renderer diffraction-lib declares (`auto`, `plotly`, `asciichartpy`). Each
  host draws with its own, so `auto` is the one supported value, and any other warns
  `unsupported _rendering_plot.type "<value>" - using auto`; a missing value (`?`) declares no choice. No
  committed project declared another value before this task. The calculator warning comes from a project's load; a single
  experiment file loaded into an open project (Load experiment(s)) passes no warnings today.
- **The other two parts of the calculator decision came with the crysta follow-up**:
  - *Writing `crysta` on save.* edi saves through crysta's writer, which now writes
    `_calculator.type crysta` in every experiment file, whatever the loaded file declared. A project opened
    with an unsupported calculator warns once and is saved as `crysta`; edi writes nothing itself.
  - *The bundled examples say `crysta`.* The five examples that declared `_calculator.type cryspy`
    (`cosio-d20` start-1 and start-4, `ncaf-wish-2bank` start-3, `si-sepd` start-2 and start-5) are crysta's
    seed projects byte for byte. crysta's seeds switched to `crysta` and the examples with them, so they
    open without the calculator warning.
- **An example that always has messages** (idea 26): `pd-neut-tof_fe_pseudo-voigt` (non-executing, so no CLI
  gate runs it) declares `_minimizer.type "bumps (lm)"`, `_calculator.type cryspy` and
  `_rendering_plot.type plotly` on purpose, so opening it lists three warnings —
  `unsupported _calculator.type "cryspy" - using crysta`,
  `unsupported _minimizer.type "bumps (lm)" - using crysta` and
  `unsupported _rendering_plot.type "plotly" - using auto` (the owner's widening of idea 26: *"and something
  else for that project to see more warning messages"*). Its comments and `PROVENANCE.md` say so.
- **The UI test's images show it** (`t4-03` to `t4-06`): the count before the messages are viewed, the list,
  the count after, and a refused calculation's error row over the neutral chart placeholder. (`t4-01` and
  `t4-02` show the Experiment type grid, §2, and Measured data's single increment, §6.)

### 15. The pattern chart

The Experiment and Analysis pages draw the pattern on Qt Graphs, from the core's one description (ADR-0021). The
chart computes nothing: it draws the series, bands and axes `edi::present_pattern` returns. Its proportions,
borders, tick counts, legend, toolbar, colours and fonts are easydiffractionbeta's, read from its chart
code (`QtCharts1dTab.qml` and the base's `QtCharts1dBase.qml`; the owner, 2026-10-02); the tick labels stay round.

- **Panes.** Three panes on one shared x range, on the chart background (white in the light theme) over the whole
  chart area: the main pane (measured with uncertainty, calculated, background, excluded bands), one row of Bragg
  ticks per structure, the residual. Of the height the toolbar and the x axis leave, the main pane takes 0.7 and the
  residual 0.3, each less half of what the tick rows take between them; a structure's row is 1.5 em high, in a
  pane half an em higher. With nothing measured there is no residual pane: the tick rows are then directly under
  the main pane, which takes the rest of the height. The x labels and title are under the lowest pane shown and
  only there — the residual, else the tick rows, else the main pane — and the plot areas share their left and right
  edges, so a tick is under its peak.
- **Borders and grid.** Every pane's plot area has a border closed on all four sides, in the chart's axis colour:
  the main pane's, the residual's and the Bragg rows'. Every pane has a grid line down it at each x tick, in the grid
  colour, so each is one column through all the panes; the main and the residual panes also have one across at each
  y tick, and the Bragg rows have none across. Borders and grid lines are one border thickness wide (1 px), drawn
  by the chart itself under everything else, and every plot area begins and ends on a whole pixel, so they are
  sharp. The border is drawn over the grid, and a grid line on a pane's edge is not drawn, so every side keeps the
  axis colour (the owner, 2026-10-02). The panes' Qt Graphs theme keeps one colour scheme whatever the app's theme,
  since a scheme change restores Qt Graphs' own axis colours. Nothing else is drawn around a plot area: no axis line and no tick mark outside it. Qt Graphs' own tick
  marks, axis lines and grid are transparent in every pane's theme; they are two pixels wide and would cross the
  tick labels. The Bragg rows are their ticks over that grid, inside their border, and nothing else: no line across,
  no tick mark and no band behind them. Qt Graphs draws those marks with shader effects, which the offscreen
  platform's software renderer skips, so a look is checked on a capture from an OpenGL platform (the UI test's).
- **Ranges and ticks.** Tick labels are round values. A fitted main y range is what is presented and a tenth of
  its span beyond each end (easydiffractionbeta's rule), with about five round ticks inside it; the x axis has about
  five. A range the user chose keeps its bounds and takes round ticks inside them.
- **The residual's range.** The residual pane is linear on every scale (ADR-0021 §5), its range centred on 0, with
  three ticks: 0 and the greatest round value inside the range, on either side. **On the linear scale it has the
  main pane's scale:** one intensity unit is as high in it as in the main pane, so its half range is half the main
  range times the two plot areas' height ratio, and a residual larger than that is cut at the pane's edge. On the
  square-root and log scales an intensity unit has no one height in the main pane — its height depends on the
  intensity — so there is no scale to follow: the range is fitted to the residual in view, the greatest absolute
  value and a tenth beyond it. Both panes label original values on every scale, so they still read against each
  other.
- **Draw order.** The grid and borders, then the measured markers and their error bars, then the lines: measured,
  background, calculated on top. The legend, the excluded bands and the hover text are over the panes.
- **Margins.** One gap of one em (the owner, 2026-10-02, after easydiffractionbeta's chart): from the toolbar
  buttons' bottom to the main plot area's top border, from the chart's top to the toolbar, and below the x title;
  and 2 em from the plot areas' right border to the chart's right edge.
- **Toolbar.** A row of square buttons (2.5 em, with a fill and a border in the axis colour) that ends at the plot
  areas' right border: legend, hover coordinates, a spacer, pan, box zoom, reset (the Home icon, as the structure
  view's), then a spacer and the y scale as a drop-down of linear, square root and log, in the toolbar drop-down
  style (`ToolbarComboBox.qml`, §16) (the owner, 2026-10-02). The legend and
  the hover coordinates are on at the start; pan and box zoom exclude each other, and box zoom is on at the start. An
  icon is in the accent colour while hovered or checked. `ChartToolButton.qml` and `ChartLegend.qml` are shared
  with the structure view (§16), whose toolbar is a row of the same buttons; `ChartToolbar.qml` is the pattern
  chart's own button list.
- **Legend.** Inside the main plot's top right corner: one line per series in the series' colour — *Measured
  (Imeas)*, *Total calculated (Icalc)*, *Background (Ibkg)*, *Residual (Imeas − Icalc)*, and per structure *Bragg
  peaks*, the structure icon and the structure's name. The legend's rows and the excluded bands reach QML as typed
  list models with named roles (`ChartLegendModel`, `ChartBandModel`), as every app model does, never as a list
  of dictionaries.
- **Pointer.** Box zoom sets the x range and the main y range to the dragged box, drawn as the base's chart draws it: a border in the theme's
  app-border colour filled with the same colour half transparent (the owner, 2026-10-02). Pan moves the x range by the dragged distance. One wheel
  notch multiplies the x span by 0.8 (towards the user: by 1.25), keeping the x under the pointer fixed. A right click resets, as the reset button
  does. A box zoom, a wheel zoom and a reset move the ranges over easydiffractionbeta's chart animation time (EaStyle.Times.chartAnimation, 250
  ms) with Qt Charts' series-animation easing (OutQuart); each frame is an ordinary refresh, the pattern presented and decimated for that frame's
  ranges, so no point of a frame's range is missing; a pan or a scale change first ends a running one at its end, a wheel notch continues from it,
  and a chart that is hidden draws no frame: its animation ends at its target, drawn when the chart is shown again (the owner, 2026-10-02). With
  hover coordinates on, the pointer shows diffraction-lib's read-out of a point within plotly's default hover distance, 20 px (a Bragg tick by its
  x alone), beside that point, and nothing elsewhere (the owner, 2026-10-02): over the data or the residual, `x`, `Imeas`, `Ibkg`, `Icalc` and
  `Imeas - Icalc` at that row, each value in its series' colour; over a Bragg tick, the structure's name, `x` and `Miller indices: (h k l)`, the Miller
  indices alone in the tick's colour (the owner, 2026-10-03). Numbers have two decimals and a comma between thousands (`edi::hover_readout`).
- **Y scales.** Square root and log are display mappings (ADR-0021 §5), and the y-scale button cycles linear,
  square root, log. On each the main y axis labels original values. A square-root axis has its ticks at round
  display values, so its labels are their squares (0, 2 500, 10 000, 22 500). A log axis has its ticks at whole
  decades, one per decade, or every second or third when there are more than five. A fitted log range is the
  measured values' decades: from the decade at or below the least measured value to the decade at or above the
  greatest presented one, and six decades when nothing is measured. A calculated value far below the measured ones
  — a pattern with no background is 1e-70 between its peaks — leaves the pane at the bottom and does not stretch
  the axis. A log range the user chose is widened to the whole decades that hold it, so every log range — fitted,
  zoomed, panned — has its ticks at whole decades: a box drawn inside one decade shows that decade between two
  ticks. On a change of scale every series is presented again, the measured markers and bars included.
- **Refresh.** A chart is refreshed only while it is shown: on the page the window shows, and on its page's
  selected tab (`WorkflowPage.current`, bound to the window's page view; `PatternChart.shown`). A page that is not
  shown stays loaded, laid out and visible in that view, clipped out of it, so `visible` does not say it. A chart not
  shown keeps its last drawing and notes that it is out of date — a publication, another experiment, a resize, a
  scale or a theme — and is refreshed once, from the latest result, when it is shown. So a parameter change is one
  calculation, one refresh of the shown chart and none of the hidden one (the owner, 2026-10-02). Each calculation
  the worker runs is announced as it begins and ends (`ProjectViewModel.calculationStarted`,
  `calculationFinished`; ADR-0020 §7).
- **Measured points and bars** are one scene-graph item behind the main pane's lines (`MeasuredLayer`): it paints
  every marker and bar into one image, which every Qt Quick renderer draws, the offscreen platform's software one
  included. The benchmark that chose it over Qt Graphs' scatter series is `pixi run -e app app-chart-bench`; its
  table is under *The measured layer's benchmark* below.
- **Colours and widths** (light / dark); the one table is `edi::pattern_style_table()`:

| Series | Colours | Mark |
|---|---|---|
| Measured, by the experiment's place | `#03A9F4` / `#81D4FA`, then `#795548` / `#BCAAA4`, then `#4CAF50` / `#A5D6A7` | 2 px line, 5 px markers, 1 px bars |
| Calculated | `#F44336` / `#EF9A9A` | 2 px line |
| Background | `#607D8B` / `#B0BEC5` | 1 px line |
| Residual | `#8BC34A` / `#C5E1A5` | 1 px line (the owner, 2026-10-02) |
| Bragg ticks, by the structure's place | `#FF9800` / `#FFCC80`, then `#009688` / `#80CBC4`, then `#E91E63` / `#F48FB1` | 1 px ticks (the owner, 2026-10-02) |
| Excluded band | `#8C8C8C` at opacity 0.15, both themes | a filled rectangle in each pane's plot area, under its grid and border (the owner, 2026-10-02: no band crosses the gaps between the panes) |

  An experiment's block colour (§8) is its measured series' colour, and a structure's is its ticks' colour.
- **Titles.** The x title by the beam mode (`2θ (°)`, `TOF (µs)`), `Intensity` and `Residual` (the owner, 2026-10-02), drawn by the
  chart itself beside the panes: Qt Graphs draws an axis title over the axis labels.
- **Fonts and labels.** The tick labels, the titles and the legend are the app's label: its font at its size
  (`EaStyle.Sizes.fontPixelSize`), as in easydiffractionbeta's chart. A y label ends beside its plot area and an x
  label is centred under its tick, close under the plot area: the chart moves them over the 15 px Qt Graphs keeps
  for the tick marks it does not draw.

#### The measured layer's benchmark

`pixi run -e app app-chart-bench` replaces the measured points of a 50 000-point pattern 200 times at each width and
times each replacement to the frame that shows it. Candidate A is a Qt Graphs `ScatterSeries` with a line series for
the bars; candidate B is `MeasuredLayer`. Measured on the development machine on 2026-10-02 (Linux, Qt 6.11.2; the
`xcb` rows render through Mesa's software OpenGL, the machine has no GPU), in milliseconds:

| Platform | Columns | Points drawn | Candidate | First population | Replacement, median | Replacement, p95 |
|---|---:|---:|---|---:|---:|---:|
| offscreen | 400 | 1 373 | A | 58.71 | 33.47 | 43.80 |
| offscreen | 400 | 1 373 | B | 4.40 | 5.70 | 6.48 |
| offscreen | 1 200 | 3 678 | A | 156.58 | 134.51 | 200.08 |
| offscreen | 1 200 | 3 678 | B | 7.56 | 5.38 | 6.31 |
| offscreen | 2 400 | 6 355 | A | 302.19 | 274.12 | 575.49 |
| offscreen | 2 400 | 6 355 | B | 11.86 | 13.14 | 17.13 |
| xcb | 400 | 1 373 | A | 377.10 | 89.33 | 160.21 |
| xcb | 400 | 1 373 | B | 9.88 | 10.45 | 17.35 |
| xcb | 1 200 | 3 678 | A | 256.50 | 163.62 | 248.04 |
| xcb | 1 200 | 3 678 | B | 29.72 | 15.44 | 25.88 |
| xcb | 2 400 | 6 355 | A | 434.67 | 198.73 | 303.84 |
| xcb | 2 400 | 6 355 | B | 34.48 | 20.84 | 34.78 |

The targets were a p95 of at most 8 ms at 1 200 columns, at most 16 ms at 2 400, and a first population of at most
100 ms. A misses every one on both platforms, by a factor of 20 and more at 1 200 columns. B meets the 1 200-column
and first-population targets on offscreen and misses the 2 400-column one by 1.13 ms; on the software-OpenGL `xcb`
platform it misses both replacement targets. B is the chart's measured layer: the lower p95 at 1 200 columns on
both platforms. The targets are not acceptance limits (the owner, 2026-10-02); a GPU machine's numbers join this
table when one is measured.

### 16. The structure view

The Structure page draws the structure on Qt Quick 3D, from the core's one description (ADR-0022). The view
computes no geometry: it draws what `edi::present_structure` and `edi::scene_drawing` return and the values of
`edi::structure_style_table()`. Its function is diffraction-lib's structure view (`display/structure/`,
`templates/structure.html.j2` at `cb2cda7b`; the owner, 2026-10-02), its buttons easydiffractionbeta's style
(§15), and its placement the one diffraction-lib's published renders show.

- **Drawing.** Atoms and bonds are Qt Quick 3D instances fed from C++: one `StructureInstances` table per mesh
  (spheres for the atoms with one site, cylinders for the half-bonds and the cell edges), packed once per
  presentation into Qt's instance buffer, so two draw calls whatever the number of atoms. A pointer event moves the
  camera only. There is no QML object per atom, bond, edge or label, and no `Repeater3D`, `InstanceList` or
  `RandomInstancing`. A shared site (lbco's La/Ba) is a sphere in wedges of relative occupancy about the home
  view's direction, in its parts' colours, all shared sites in one mesh (`SharedSiteGeometry`), so a site of two
  equal parts shows a left and a right half in the home view. The triad is three cylinders and three cones. The
  labels and the axis letters are one painted item at the places `edi::project` gives.
- **Camera.** The cameras draw the core's projection: the orthographic one (the default) through Qt's own
  orthographic camera set from the core, so Qt's picks are parallel rays too; the perspective one, with a 30° field
  of view and its screen pan, through a custom camera with the core's matrices; both are fitted as diffraction-lib fits its home view, with a band at the top kept
  clear for the toolbar and the legend (the toolbar's height with its margins). So a label and its atom agree in
  both projections. The home view — the initial one, the reset and the views along a, b and c — shows the
  structure at **`kHomeZoom` = 0.9** of that fitted size, a bit smaller with more margin (the owner, 2026-10-02);
  the orientation rule and the fit are diffraction-lib's, unchanged. The lights are diffraction-lib's (the owner, 2026-10-02): an ambient term and two headlights
  that follow the camera, a key shining from the camera-local direction (right, up, towards the camera) (0.3, 0.45,
  0.85) and a fill from (−0.4, −0.2, −0.45); the material is Phong-like, specular 0.2 with shininess 90, the same in
  both themes. The scene is lit in linear light and written out as sRGB (linear tone mapping), as three.js renders
  it. Light units do not carry over one to one (three.js's physical units carry the Lambert 1/π); Qt's brightness
  is the three.js intensity × 1.5/π, calibrated on the capture of lbco against diffraction-lib's render: each
  element's median colour within about ten levels, Co's within five. The Phong highlight (specular 0.2, shininess
  90) has no one-to-one counterpart in Qt's principled shading: the atoms, bonds and wedges are a dielectric with
  roughness 0.25 and specular amount 1, matched to the render's small, soft spot on every sphere. The orthographic
  camera stands far back along the view direction: Qt's lighting takes each view ray from the camera's position,
  and from there the rays are parallel, as an orthographic camera's are in three.js, so every atom carries the
  same highlight.
- **Placement.** Inside the view: the toolbar at the top right, one em from the top and right edges; the element
  legend at the top left; the pointer hint at the bottom left (*drag = rotate*, *wheel = zoom*, *right-drag =
  pan*, on three lines as diffraction-lib draws it); the download button at the bottom right; the hover label
  beside the pointer.
- **Colours.** Every style colour is EasyApp's `EaStyle.Colors`, bound and never written as a literal, as
  easydiffractionbeta's structure view (`StructureViewTab.qml`) uses them (the owner, 2026-10-02), so all follow the
  theme switch: the scene's background `chartBackground`, painted opaque behind the 3D item and its clear colour;
  the cell edges `grey`; the a, b and c axes and their letters `red`, `green` and `blue`; the labels
  `themeForeground` over a halo of the background; the legend and hint panels `mainContentBackgroundHalfTransparent`
  with a `chartGridLine` border; the buttons' `chartAxis` border. A theme switch redraws once. The atom colours
  are diffraction-lib's palettes, the same in both themes.
- **Toolbar.** diffraction-lib's modebar, as `ChartToolButton`s with the chart toolbar's spacing and spacer.
  Camera: projection (`cube`; *Parallel (orthographic) view* or *Perspective view*), `a`, `b`, `c` (*View along a*,
  … — the letter in bold in its axis colour, a label on the button), reset (`home`, *Reset view*: the home view, the
  projection kept). Features, one button per feature the structure has, in diffraction-lib's order: atoms (`atom`;
  all, asymmetric unit, none — *Atoms: all / asymmetric unit / none*, or *Atoms: show / hide* with no atom outside
  the asymmetric unit), labels (`tag`), bonds (`link`, when crysta found a bond), cell (`vector-square`), axes
  (`location-arrow`); a structure with no site has only cell and axes. A feature that is on shows its icon in the
  accent colour. Then the colour scheme as a drop-down (`jmol`, `vesta`) in the toolbar drop-down style
  (`ToolbarComboBox.qml`, shared with the pattern chart's y scale): the sidebar drop-downs' background, the base's
  translucent combo-box colour over the content background (the owner, 2026-10-02), at the buttons' height, as narrow as its
  widest entry with the arrow and the padding. *Download PNG*
  (`camera`) saves the view as drawn — the scene, its labels, legend and triad, without the buttons and the hint —
  to a file the user names, proposed as the structure's name with `.png`.
- **Appearance.** The atom view (`covalent`, `vdw`, `ionic`) and the atom scale (above 0, at most 1), which
  diffraction-lib's modebar does not carry, are an Appearance group on the Structure page's Extras tab, as in
  easydiffractionbeta, laid out and styled as the Instrument group (the owner, 2026-10-02): a muted caption above
  each field, the two fields side by side in equal columns over the group's width, with the same components (a
  `SelectorField` and the base's `ParamTextField`). The elements whose radius was substituted are listed under
  them. The options are view state
  of the open project, shared by every structure's view, and not saved in the project file.
- **Refresh and freshness.** The view is prepared only while it is shown, by the pattern chart's rule above
  (`StructureView.shown`, bound to `WorkflowPage.current` and the page's selected tab): a view not shown presents
  nothing, draws nothing and places no camera — a publication, another structure, an option, a theme or a size — and
  is presented once, from the latest source, when it is shown. Its `current` still turns false at once when an edit
  stales the geometry. A refused calculation keeps the last published frame; the frame is current only once the
  latest request has published its geometry and the view has presented it, whatever presents the kept frame again
  (an option, a theme, a refresh, being shown): the controller keeps the frame's source and reads the latest
  request's freshness from the structure's live source (ADR-0022 §1), as the chart reads its pattern.
- **Animation.** The a, b, c and Home buttons turn and fit the view over 1000 ms with an out-quint easing, as
  easydiffractionbeta turns its view (EasyApp's theme-change animation; the owner, 2026-10-02): the camera's
  orientation turns along the shorter arc, its zoom changes by a constant ratio and its pan linearly, and the labels
  follow every frame. A click during a turn starts the new one from where the view is; a drag, a wheel notch or a
  pan stops it there. The pattern chart's box zoom, wheel zoom and reset animate as §15 says.
- **Pointer.** A left drag of (dx, dy) pixels turns the scene dx degrees about the screen's vertical axis, then dy
  about its horizontal one; one wheel notch away multiplies the magnification by 1.25 (towards, 0.8), keeping the
  point under the pointer in the orthographic projection; a right drag pans. The magnification stays between 0.05
  and 100. No inertia. Hovering names the atom whose surface the pick hits, picking along the core's ray under the pointer: a sphere by its instance index, a shared
  site by the ordinal its triangles carry; the label shows the atom's label, its parts' elements and occupancies,
  and its fractional coordinates and symmetry code as crysta gave them.
- **Where the 3D item exists.** Only where Qt Quick draws through a graphics API Qt Quick 3D supports (OpenGL,
  software OpenGL included, Direct3D 11 and 12, Vulkan, Metal); elsewhere (the offscreen platform the Qt Quick Test
  tier runs on) the view shows one line of text, with the same state. The scene itself — the instance tables, the
  models, the camera and the lights — is a node the view always creates, which the 3D item imports, so the tables
  and their object names exist on every platform. The drawn cases run through `pixi run -e app
  app-test-3d` on the capture platform. In the browser the procedural meshes (`SphereGeometry`, `CylinderGeometry`,
  `ConeGeometry`) are built synchronously: the single-thread web build has no thread for their default asynchronous
  generation (ADR-0023 §3).

**The style table** (`edi::structure_style_table()`; light / dark; a share of `H` is of the fitted half height for
the viewport, ADR-0022 §6). Its colours are diffraction-lib's, for the renderers that draw diffraction-lib's look;
the app takes its colours from `EaStyle.Colors` instead (above), and its dimensions and lights from this table:

| Key | Light | Dark | Value | Source |
|---|---|---|---|---|
| `background` | `#FFFFFF` | `#212121` | | diffraction-lib's `display/theme.py` |
| `cell.edge` | `#222222` | `#E6E8EE` | | diffraction-lib's foreground |
| `cell.edge.radius` | | | 0.0025 · `H` | thin lines, as diffraction-lib's |
| `bond.radius` | | | 0.06 Å | diffraction-lib |
| `axis.a`, `axis.b`, `axis.c` | `#DC2828`, `#28B428`, `#2850DC` | the same | | diffraction-lib (as VESTA) |
| `axis.shaft.radius` | | | 0.009 · `H` | diffraction-lib |
| `axis.head.radius` | | | 0.028 · `H` | diffraction-lib |
| `axis.head.length` | | | 0.085 · `H` | diffraction-lib |
| `axis.overhang` | | | max(0.09 · `H`, pad + head length + `axis.clearance`) beyond the cell edge | diffraction-lib |
| `axis.clearance` | | | 0.04 · `H` | diffraction-lib |
| `axis.letter.offset` | | | 0.05 · `H` beyond the tip | diffraction-lib |
| `label` | `#222222` | `#E6E8EE` | | diffraction-lib's foreground |
| `label.halo` | `#FFFFFF` | `#212121` | | the scene's background |
| `light.ambient`, `light.key`, `light.fill` | | | 0.68, 1.25, 0.34 | diffraction-lib's three.js intensities; drawn × 1.5/π |
| `light.key.right`, `.up`, `.toward` | | | 0.3, 0.45, 0.85 | diffraction-lib's key headlight, camera-local |
| `light.fill.right`, `.up`, `.toward` | | | −0.4, −0.2, −0.45 | diffraction-lib's fill headlight, camera-local |
| `material.specular`, `material.shininess` | | | 0.2, 90 | diffraction-lib's Phong highlight |

**Mesh detail** is tuning inside this design (the owner, 2026-10-02), chosen by the number of drawn atoms:

| Drawn atoms | Sphere segments × rings | Cylinder segments |
|---|---:|---:|
| up to 500 | 32 × 16 | 16 |
| up to 5 000 | 16 × 8 | 8 |
| above | 10 × 5 | 6 |

These first values are tuned on GPU hardware, and the measured table replaces this note.

**Measured on the development machine's software OpenGL** (Xwayland on headless Weston, Mesa llvmpipe, no GPU; a
1280 × 768 view, the scene rotating; Qt Quick 3D's own frame time, median of 10 samples, milliseconds). These are
not a performance reference (the owner, 2026-10-02): they show the view draws on that display and what a capture
costs.

| Spheres | Cylinders | Mesh | Antialiasing | Frame |
|---:|---:|---|---|---|
| 90 | 218 | Qt's built-in | MSAA | 185.51 and 153.41 |
| 90 | 218 | Qt's built-in | none | 127.45 |
| 90 | 218 | 16 × 8, 8 | MSAA | 17.81 |
| 90 | 218 | 16 × 8, 8 | none | 11.98 |
| 5 760 | 8 352 | 16 × 8, 8 | MSAA | 466.43 |
| 6 119 | 44 000 | 16 × 8, 8 | MSAA | 823.00 |

**Measured on GPU hardware** (the CI Mac runner `andrewsazonovs-Virtual-Machine`, Qt Quick 3D on Metal, `bank_frames`
dispatch 37097612066 at edi `0fcccf32`; ten runs of the drawn cases, each 50 samples after 5 discarded; milliseconds).
The median is the banked value, the median of the ten runs' medians; the range is theirs; the p95 is the median of the
ten runs' p95. The drawn records do not yet report the mesh detail, the atom and bond counts, or the update's
calculation share.

| Dataset | Metric | Median | Range of the ten medians | p95 |
|---|---|---:|---|---:|
| T1 | A1 frame | 18.2 | 16.3 to 20.3 | 37.8 |
| G1 | A1 frame | 17.4 | 16.7 to 20.9 | 38.2 |
| T1 | A2 update | 67.8 | 59.1 to 70.0 | 82.5 |
| G1 | A2 update | 259.8 | 258.8 to 260.5 | 272.4 |

Frame time and update latency on GPU hardware, with the core's presentation and update times, are measured and
ratcheted, never limits; their tables join this section when measured. The app's A1 frame and A2 update medians join
bank and tool (`tools/ci/latency_bank.py`, ADR-0020 §5): `pixi run -e app app-bank-frames` runs the drawn cases ten
times, collects each run's records into a table of the latency schema with the machine, the commit and the renderer,
compares the ten runs' medians with the machine's app rows, and banks them when the machine has none or a re-bank is
owed. A machine's core and app rows are banked separately, each keeping the other. Rows drawn by a software renderer
(llvmpipe) are reported and never compared, and the tool refuses to bank them, as it refuses any record the drawn case
marks not bankable. The macOS runner runs the task on a `bank_frames` dispatch; the owner's Mac runs it by hand. Every
bank row names the committed revision it measured: a run measures the checkout's HEAD and refuses uncommitted changes,
and each timed executable names the commit it was built from itself: a latency probe carries `edi-build-commit:<sha>`
in its bytes, which the tool reads from the file it is about to run and hands to the probe to record, and the app test
runner prints `edi_app_tests: built at <sha>`, which a drawn run's table carries (`-dirty` when built with uncommitted
changes); a table naming no revision is never banked. The tool reads only a directory's `run-NN.json` tables and
refuses to write its bank rows into it.

### 17. Fitting: Start fitting, the status bar, the results and Undo

(the owner, 2026-10-02)

- **Start fitting** (Analysis, Fitting group) runs the project's fit on the worker (ADR-0020 §9) and reads *Cancel
  fitting*, with a stop icon, while it runs. For a scan mode (sequential, independent) it is disabled, and its
  tooltip names the mode. While a fit runs the parameter table is disabled and every edit is refused.
- **The chart follows the fit**: a frame of the current iteration's pattern at most once per display frame, then the
  fitted pattern when the fit ends. A fit that writes nothing puts back the pattern the project holds.
- **The status bar's keys** (the owner, 2026-10-03): every item shows its key only while all the shown items fit the
  bar's width with their keys, measured from the items themselves; otherwise each shows its icon and value. (It
  replaced a fixed window-width threshold.)
- **The status bar** gains easydiffractionbeta's three fit items, shown once a fit has run: *Fit iterations*,
  *Goodness-of-fit* (reduced χ², before → after) and *Fit status*: *Running*, then *Done*, *Max iterations*, *No step*
  or *Cancelled*. A stop that is not a convergence is shown there, not as an error.
- **A fit-results pop-up** opens when a fit ends with a result (finished, cancelled or stopped early): diffraction-lib's
  "Least-squares fit results" table, numbered rows of an icon, the metric and its value — minimizer, overall status,
  fitting time (seconds), iterations, goodness-of-fit (reduced χ²), Rwp, and each bank's Rwp for a joint fit. The
  table is built from the result the project records (`_fit_result`), so a project opened with one shows its last
  fit too: the status bar's iterations, reduced χ² and stop reason, and the same table from the Fit status item,
  which opens it on a click.
- **A refused or failed fit** shows its reason in a message dialog; the project is unchanged.
- **A fitted value outside its admissible range** (the table's min and max) is kept, as the CLI keeps it, and shown in
  red with a tooltip naming the range, as diffraction-lib's table of fitted parameters does (the owner, 2026-10-02).
  Bounded fitting is.
- **Undo** is the app bar's Undo arrow: enabled while the model holds a fit's start state (after a finished or
  cancelled fit), it restores the pre-fit state (`undo_fit`, one level) and clears the fit items.

## Consequences

- The design choices the owner makes by eye are reviewable against a written rule; the phase-2 reviewer checks
  that this ADR describes what the code does.
- Renamed titles and tabs change the UI-test images for the pages that show them; those are re-blessed in
  phase 2, with each capture checked against its idea.
- Disabled placeholders commit the layout to buttons that do nothing yet; each is enabled by the task that
  implements its function.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Keep singular loop titles (easydiffractionbeta's *Background*) | Rejected by the owner (idea 19): a loop names its rows, and the title carries their count. |
| Leave unimplemented actions out until they work | Rejected (ideas 13, 17): the owner wants the final layout visible now. |
| Fix `last` in gui-components | Deferred: the base is consumed unmodified (ADR-0015 §1); reported upstream as gui-components#55. |
