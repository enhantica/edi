# The edi app: design inventory and look review

The edi desktop app ports easydiffractionbeta v0.9.9's pages onto edi's C++/QML host over the
gui-components base ([ADR-0015](../adrs/0015-edi-app-stack.md)). This page records what was ported
and how edi's pages compare with the owner's v0.9.9 screenshots. It also records the evidence behind
the UI test's tolerance.

## Sources

- **Layout authority:** easydiffractionbeta's QML at `ec1d04ee` (`easyDiffractionApp/Gui/Components/Pages/**`).
- **The look:** the owner's sixteen v0.9.9 screenshots, committed byte-identical under
  [`app-screenshots/originals/`](app-screenshots/originals/) with sha256 and page state in its
  `provenance.yml`. They are macOS Retina 2× captures (2560×1592 with the title bar) of the Co₂SiO₄/D20
  built-in example.
- **edi's pages:** the images `edi_app --demo` produces (Linux, Xwayland on headless Weston with Mesa
  llvmpipe OpenGL, 1280×768, device-pixel ratio 1; ADR-0015 §10), committed under
  [`app-screenshots/edi/`](app-screenshots/edi/) as the UI test's one expected set. They
  are edi's own output, a regression pin, not a claim that the look matches v0.9.9. This page's
  review is that comparison.

## What was ported

| page (original → edi) | main area | sidebar groups (Basic · Extras) | Text |
| --- | --- | --- | --- |
| Home → Home | logo, wordmark, version, Start, links | — | — |
| Project → Project | Description: name, title, description, where the project is, what it holds, load warnings | Get started · Examples · Recent projects | `project.edi` |
| Model → Structure | structure view (Qt Quick 3D) | Structures · `space_group` · `cell` · `atom_site` (ADP columns included) · Extras `scattering_length` | the structure's `.edi` |
| Experiment → Experiment | chart (placeholder) | Experiments · `experiment_type` · `data` · `instrument` · `peak` · `background` · `linked_structure` · Extras `peak` (`cutoff_fwhm`) · `excluded_region` · `absorption` · `preferred_orientation` · `scattering_source` | the experiment's `.edi` |
| Analysis → Analysis | chart (placeholder) | experiment selector · Parameters · Fitting (all three untitled and fixed open) · Extras `minimizer` · `fitting_mode` · `alias` · `constraint` (when declared) · `joint_fit` (+ `sequential_fit`, `sequential_fit_extract`, `fit_parameter`) | `analysis/analysis.edi` |
| Summary → Report | the report as rich text | Export summary (disabled) | every project file |

Each sidebar group except the named block lists, the Project actions and the Analysis parameter table
is one `.edi` category of the current block, present exactly when edi's core returns it for the
block's type. Every category the block writes as a `loop_` is a table ("loop in .edi — table in gui"):
`data` (the points, under the range summary), `linked_structure` (one row while edi calculates one
structure per experiment), `joint_fit` (written, so shown, in every fitting mode),
`sequential_fit_extract`, `fit_parameter`, and `refln` — the reflections a file carries, kept as read and
shown read-only, since edi does not model reflections and a save does not write them — beside the tables already had. Each Text tab is the
original's two untitled groups: the block selector over the page's blocks, then the text view aligned with the sidebar's content (note 12). The
analysis block declares no calculator category (`fitting_mode`, `minimizer`, `joint_fit`, and in a scan `sequential_fit`), so no Calculator group
is shown; the status bar names the engine, crysta (note 11). The shell (app bar, tool buttons, status bar, dialogs) is the base's, unmodified.
edi's own design values live in `app/qml/Style/AppSizes.qml`, as multiples of the base's font size.

## Side by side

The same page state, the original left and edi right (the demo mode's step table reproduces each
state, `app/src/demo_driver.cpp`).

| state | original (v0.9.9) | edi |
| --- | --- | --- |
| 01 Home | ![](app-screenshots/originals/01-home.png) | ![](app-screenshots/edi/01-home.png) |
| 02 Project, no project | ![](app-screenshots/originals/02-project-no-project.png) | ![](app-screenshots/edi/02-project-no-project.png) |
| 03 Project, Examples | ![](app-screenshots/originals/03-project-examples.png) | ![](app-screenshots/edi/03-project-examples.png) |
| 04 Project, loaded | ![](app-screenshots/originals/04-project-loaded.png) | ![](app-screenshots/edi/04-project-loaded.png) |
| 05 Model / Structure: list | ![](app-screenshots/originals/05-model-models.png) | ![](app-screenshots/edi/05-model-models.png) |
| 06 Space group | ![](app-screenshots/originals/06-model-space-group.png) | ![](app-screenshots/edi/06-model-space-group.png) |
| 07 Cell | ![](app-screenshots/originals/07-model-cell.png) | ![](app-screenshots/edi/07-model-cell.png) |
| 08 Atom sites | ![](app-screenshots/originals/08-model-atom-site.png) | ![](app-screenshots/edi/08-model-atom-site.png) |
| 09 Text mode | ![](app-screenshots/originals/09-model-text-mode.png) | ![](app-screenshots/edi/09-model-text-mode.png) |
| 10 Experiments | ![](app-screenshots/originals/10-experiment-experiments.png) | ![](app-screenshots/edi/10-experiment-experiments.png) |
| 11 Profile shape / Peak | ![](app-screenshots/originals/11-experiment-profile-shape.png) | ![](app-screenshots/edi/11-experiment-profile-shape.png) |
| 12 Background | ![](app-screenshots/originals/12-experiment-background.png) | ![](app-screenshots/edi/12-experiment-background.png) |
| 13 Analysis | ![](app-screenshots/originals/13-analysis-basic.png) | ![](app-screenshots/edi/13-analysis-basic.png) |
| 14 Analysis extras, minimizer | ![](app-screenshots/originals/14-analysis-extra-minimizer.png) | ![](app-screenshots/edi/14-analysis-extra-minimizer.png) |
| 15 Summary / Report | ![](app-screenshots/originals/15-summary.png) | ![](app-screenshots/edi/15-summary.png) |
| 16 Preferences | ![](app-screenshots/originals/16-summary-preferences.png) | ![](app-screenshots/edi/16-summary-preferences.png) |

edi's capability states (no original counterpart), in the same set: `17-experiment-profile-selector`,
`18-experiment-tch`, `19-experiment-extras`, `20-experiment-tof`, `21-structure-extras`,
`22-analysis-fitting-mode`, `23-experiment-text`, `24-analysis-text`, `25-report-tof`,
`26-experiment-loaded`, `27-experiment-xray`, `ex-<id>`: every Example's Experiment page with its peak
group open, and `28-home-about`: the About dialog. `09-model-text-mode`, `23-experiment-text` and
`24-analysis-text` show the Text tab, in PT Mono. The owner's review notes of each have
their capture, mapped note by note in [`app-review-captures.json`](app-review-captures.json): `t2-01` to `t2-05`
on the light theme (the constant-wavelength instrument, the linked structure table, the Extras peak
group, the Analysis sidebar with a parameter selected, the Report's Text at a pinned time), `t2-06` to
`t2-08` on the dark theme, `t2-09` / `t2-10` on "System" following the platform appearance through the
app's seam, dark then light, then `t2-11` the Project Text tab and `t2-12` to `t2-16` the loop tables the task made visible (measured data, reflections, joint fit, a scan's extraction rules and fit
start state). `t2-17` shows the constant-wavelength instrument's four fields — a D20 copy declaring sample displacement and transparency, loaded as a user loads an edited file — sharing the row.

Extends that same Example inventory with
`ex-pd-neut-tof_cecoal-polaris_chebyshev.png`,
`ex-pd-neut-tof_ceo2-pearl_polynomial.png` and
`ex-pd-neut-cwl_lab6-11b-echidna_tch-fcj.png`. Each captures its registered project's
Experiment page in the shared baseline; the earlier Example and numbered captures remain.

## Differences

Every visible difference has a class: **O** owner direction · **C** an edi capability the original lacks
· **D** data · **S** scope (enabled by a later task) · **P** platform and capture · **T** capture
artifact. A difference with no class is a defect to fix, not a row to add.

| where | original | edi | class |
| --- | --- | --- | --- |
| tabs | Model, Summary | Structure, Report | O |
| sidebar tabs | Basic controls, Extra controls, Text mode | Basic, Extras, Text | O |
| Structure view, Experiment and Analysis charts | Qt Quick 3D view; QtCharts / Plotly charts | the structure view on Qt Quick 3D (ADR-0017 §16); the charts on Qt Graphs (ADR-0017 §15) | O (ADR-0015 §6: the app links Qt Graphs and Qt Quick 3D and is a GPLv3 work) |
| sidebar groups | Diffraction radiation, Measured range, Diffractometer, Profile shape, Peak asymmetry, Associated phases, Atomic displacement, Appearance, Parameter names, Calculation engine | one group per `.edi` category: Experiment type, Measured range, Instrument, Peak profile (asymmetry a subheading; its `cutoff_fwhm` in an Extras group of the same name), Linked structure; ADP columns in Atom sites; no Appearance, Parameter names or Calculation engine group | O (§15.6) |
| loop categories | Associated phases and the measured data are not tables | every `.edi` loop is a table: the measured points under the range summary, the linked structure, the joint-fit weights, the scan's extraction rules, the fit start state, and the file's reflections (read-only, as read) | O |
| type selectors | none (one profile per beam mode, no absorption, fixed minimizer) | profile, absorption, background, scattering-source, fitting-mode, descent and minimizer combos over edi's supported options; the experiment type as four disabled combos | C |
| Atom sites | type icon column; Wyckoff position `4a` | no icon; the Wyckoff letter as stored (`a`) | C (edi stores the letter only) |
| Analysis table | short iconified names; min/max `-inf`/`inf` everywhere; from–slider–to row | identity paths (`structure.cell.length_a`); min/max the admissible range (`0`…`30` Å for a length); the from–slider–to row, its limits ±50 % of the value | C |
| displayed numbers | a parameter at its uncertainty's precision, else three significant digits | the same, and every plain numeric field and table cell (cutoff, tolerance, measured range, scattering lengths, background positions, excluded regions, joint-fit weights) at three significant digits too; the stored values and the Text tabs keep full precision; the read-only data and reflection tables at six | O |
| Minimizer tolerance | — (no such field) | the tolerance the fit uses: the declared one, else crysta's default | C |
| Start fitting, Save, Undo/Redo, Export | enabled | disabled | S (E05, the report task) |
| values and counts | the example's fitted values; 52 parameters (5 free, 47 fixed); goodness of fit 4.48; CrysPy, Lmfit | `cosio-d20_start-1`'s start values; 58 parameters (43 free, 15 fixed); no fit yet; crysta, crysta | D |
| Report, fourth section | titled with the original's word for the operation | Fit | O (edi names the operation *fit*) |
| Project Description | Location, Model/Experiment/Analysis directories | Example name (or Location), counts, load warnings | C |
| window | macOS title bar, Retina 2×, macOS font hinting | headless Linux (Xwayland, llvmpipe OpenGL), 1×, FreeType without hinting | P |
| pointer | the macOS cursor in some shots | none | T |

## The UI test's tolerance: evidence

The UI test (`pixi run -e app app-ui-test`) compares the demo's images with the committed set by SSIM on
luminance, over 8×8 windows aggregated per 32×32 tile. It fails when any tile scores below 0.90 or the
image below 0.98.

| measurement | result | provenance |
| --- | --- | --- |
| Linux, run to run | 43 images, 0 failed; at most 393 pixels per image differ, by at most 3 of 255 per channel (llvmpipe's OpenGL; the earlier software-rendered set was identical run to run) | two consecutive `app-ui-test` runs on the Xwayland display, the first blessed, compared by `edi_app_ui_compare` and pixel by pixel, |
| Linux, the committed set | 43 images, 0 failed | `pixi run -e app app-ui-test` right after `app-ui-bless` at the set's source commit |
| macOS, against the committed set | pending: the first CI run of the `app` job | recorded here from that run's log |
| rehearsed reds | see below | a demo run with three deliberate changes, compared with the committed set |

**Rehearsed reds** (one demo run with deliberate changes, compared with the committed set by
`edi_app_ui_compare`; the changes were reverted):

| change | images that fail | lowest tile | whole image |
| --- | --- | --- | --- |
| a hidden field: the cell's β angle | 07-model-cell | 0.6292 | 0.9979 |
| a renamed group title: "Background" → "Backgrounds" | 17, including 10, 11, 12, 17, 26, 27 and 11 of the Examples | 0.6310 (10) … 0.8902 (lab6) | 0.9993–0.9998 |
| a moved control: the Start button one font unit lower | 01-home | −0.0961 | 0.9530 |

Each change fails through its tiles while the whole image stays above 0.98, which is why the tile threshold
exists. A missing expected image and an image of another size fail by rule (`edi_app_ui_compare`: "missing
expected image", "size … expected …").

A platform rendering difference that breaks the tolerance is reported to the owner with the measured
values. It is never absorbed by loosening the tolerance or by a per-platform set.
