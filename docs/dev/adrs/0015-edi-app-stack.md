# ADR-0015 — The edi app: easydiffractionbeta's pages on one C++/QML host over gui-components

- **Status:** Accepted
- **Date:** 2026-09-27
- **Implementation:** 🟡 Partially implemented — the host, the view-model layer, the six pages with their Basic/Extras/Text sidebars, the rich-text
  report, the demo mode and the image comparator are built; the pattern chart is built (§6) and the structure view (§6); the expected image set and
  the CI job land with the task's gates
- **Priority:** High
- **Forward constraint (binding on new features):** a page member the app shows is a typed view-model
  member over a core call — never a `QVariant`/JSON bag, never a product rule written in `app/`; a sidebar
  group is one `.edi` category of the block (or a named non-category part); a selector offers the core's
  supported set for the block's type. New pages, groups and selectors follow the same shape.

## Context

edi needs a desktop app now and a web app later (ADR-0006) from one source tree (ADR-0009). The owner's
records of 2026-09-27 set its starting point: easydiffractionbeta v0.9.9 is the layout authority, its look is
to be reproduced as **similar**, and the app exposes what edi can do today — not what the Python-backed
original could. Three facts shape the decision:

- **The original's binding** (easydiffractionbeta at `ec1d04ee`) passes every editable value as a
  `Parameter(dict)` and whole data blocks as nested dicts/lists; one field edit emits `dataBlocksChanged` for
  the whole list and cascades into a recalculation, a CIF rebuild and a refresh of every table row
  (`Logic/Model.py:281-300`, `Logic/Connections.py:81-120`). That is the part not to repeat.
- **The base, gui-components v0.9.1** (`a573a969`, the renamed EasyApp): its QML ships as a Python wheel
  without a CMake build, its `qmldir` `module` lines do not match their import URIs, it reads Python-named
  context seams (`pySettingsPath`, `pyIsTestMode`), and parts of it need QtWebEngine, QtCharts, QtTest or
  QtMultimedia.
- **The existing decisions:** ADR-0005 (the base stays generic; edi injects), ADR-0006 (everything must also
  build for the web), ADR-0009 (one C++ product core, thin hosts).

## Decision

### 1. Sourcing and capabilities

1. **The pages.** The app ports easydiffractionbeta's page structure and layout — Home, Project, Structure
   (the original's Model), Experiment, Analysis, Report (the original's Summary) — onto edi's one C++ host.
   The Python backend is not ported; every proxy member is replaced by the typed contract of §2 below. The
   port may restructure or rename the QML while keeping the design (sizes, colours, fonts, spacing): edi's
   own design values sit in `app/qml/Style/AppSizes.qml`, each a multiple of the base's font size; colours
   and fonts come only from the base's `EaStyle` tokens.
2. **The base at a verified pin.** `cmake/EdiGuiBase.cmake` fetches gui-components at the full sha
   `3897d339b60f5707bfe952fed59a20f73340e236` and declares its own QML modules under the upstream URIs
   (`EasyApplication.Gui.{Style,Globals,Logic,Animations,Elements,Components}`,
   `EasyApplication.Logic.Maintenance`) over an explicit file list. Upstream files are built byte-identical except the
   declared replacement seams: ParamTextField and TableViewParameter for parameter menu terminology and units (ADR-0029),
   Fonts for edi's font inventory (§10), and ListView for the null-safe selection-model
   initialization recorded in ADR-0029; configuration refuses another commit or local changes under `src/`. The pinned
   commit is downloaded as GitHub's archive of it, checked against a committed SHA-256, with a message and a timeout (a
   git clone inside CMake could hang without a word). An offline copy (`EDI_GUI_COMPONENTS_SRC`) is a git clone at the
   pin with an unmodified `src/`, or any other copy whose `src/` files match a committed SHA-256 of the pinned tree.
   `tools/ci/app-build.sh` keeps the build identity of a configure that did not finish, so a rerun of the same identity
   continues in `build/app` instead of starting from nothing. Left out: the Plotly/WebEngine and
   QtCharts charts, `BasicReport` (WebEngine), `GuideWindow`/`GuideWindowContainer`, `JsonListModel`,
   `RemoteController` (QtTest + QtMultimedia) and `Plotting.js` (used only by the charts). The base's Logic
   scripts keep their qmldir entries, as the upstream qmldir declares them.
3. **Seams injected by the host.** The host sets `pySettingsPath` to a writable file URL under
   `QStandardPaths::AppConfigLocation` and `pyIsTestMode` to false. edi's own objects are registered QML
   types in module `edi.app` (`QML_ELEMENT` / `QML_SINGLETON`), never context properties, so `qmllint` checks
   every page binding. Every identity the user sees comes from `ApplicationInfo`.
4. **Examples.** The Project page lists every project of edi's CLI registry (`docs/user/cli/projects.yml`),
   in registry order, then the app's own X-ray example (`app/examples/pd-xray-cwl_lif`). Each is bundled into
   the app's resources without the scan data its `_sequential_fit.data_dir` names; configuration refuses when
   the registry and the project directories disagree. Opening one extracts it to a session temporary
   directory and opens it through `load_project`, like any project directory.
5. **Selectors offer only what edi supports.** Every category edi models whose type is selectable —
   `_peak.type`, `_absorption.type`, `_background.type`, the `_scattering_source` items,
   `_fitting_mode.type`, `_minimizer.type`, `_minimizer.descent` — is a combo box offering exactly the core's
   supported set for the block's type; a one-value set is a one-entry combo. The experiment type's four axes
   are shown as disabled combo boxes: the type is read-only. Each selection writes through one core function
   (`edi/selectors.hpp`); the Python setters are unchanged, and where a rule is shared the core reproduces it
   under a parity check.
6. **What enters a project.** Structures and experiments enter only from `.edi` block files (the core's
   `load_structure_edi_file` / `load_experiment_edi_files`): the project format's schema is required, an
   experiment file must declare all four type axes and powder + bragg, a batch is checked whole before
   anything is added, and a project holds one structure. Opening a project directory keeps the loader's
   presence-tracked axes. Editability follows edi's library: what `import edi` lets a user set is editable;
   what it derives or does not let a user set is read-only.

### 2. The binding (normative)

The page → view-model contract is the packet's §3; its rules:

- **Typed.** No `QVariant`, `QVariantMap/Hash/List` or `QJson*` in any `Q_PROPERTY`, `Q_INVOKABLE`, signal
  or slot of `app/src/`; no `JSON.parse`/`JSON.stringify` and no `JsonListModel` in `app/qml/`. Collections
  are `QAbstractItemModel`s; objects are typed `QObject*`. *Closes:* the dict-shaped binding of §Context and
  untyped per-field reflection.
- **No product rule in the app.** Validation (`assign_value`), category presence and shown fields
  (`*_categories`), block text (`block_edi_text` via the save), crystal system, parameter paths
  (`parameter_entries`) and calculation are core calls; the app's own tables are presentation only (tiers,
  titles, icons, formatting). *Closes:* a second, drifting spelling of an edi rule.
- **One object per parameter.** One `ParameterItem` per shown core parameter; every view binds the same
  object; its path is the fit surface's identity path. *Closes:* views of one value disagreeing.
- **Fine-grained notification.** After a write the registry publishes, per parameter, only the fields whose
  core value changed; list models change by single-row inserts, removals and moves and one `dataChanged` per
  changed row — never a reset, except when a project is opened, created or closed. Every edit is a
  request to the calculation worker (ADR-0020): the calculation runs off the GUI thread, and its dependents
  (the pattern, a shown Text tab, the report) update once, when it is published. A replaced project's pages
  are freed before the open returns. *Closes:* the whole-list cascade of §Context.
- **Writes through the core.** A value write is `edi::assign_value` — the Python setter's range rule and
  message; a refused write changes nothing and sets `lastError`.

### 3. Sidebars

Each sidebar group is exactly one `.edi` category of the block, instantiated from the block's category model: a group exists exactly when the core returns its category. Presence follows the block's
type (diffraction-lib's category compatibility at `0ffba46f` with edi's declared divergences) or what the block carries; a category's shown fields come from the per-profile field table in
`core/include/edi/categories.hpp`, never from the model's storage walk; a field outside the profile's set is hidden while fixed and kept while free — the sidebar shows it no longer, the Analysis
table does (ADR-0017 §5). A field the space group fixes or ties to another is shown disabled, with the value symmetry implies, and the Analysis table does not list it (ADR-0019). Peak asymmetry
belongs to the Peak group (without a subheading since ADR-0017 §5); the ADP columns belong to Atom sites. The named non-category parts are the block lists (Structures, Experiments), the Project
page's actions and the Analysis parameter table. Basic or Extras is a per-category presentation choice (`app/src/category_list_model.cpp`). The Text tab shows the file a save writes for the block,
byte for byte, or the writer's refusal; it is loaded only while shown.

### 4. What E04's base gates mean now that gui-components is the maintained base

- **G03 (decoupled seams)** — upstream v0.9.1 is not decoupled. Met edi-side: the base is consumed
  byte-identical at a pinned sha, only edi's file list is built, edi injects through the base's existing
  seams, and every identity the user sees is edi's. ADR-0005's grep gate as spelled (`-e EasyApp`) matches
  every `EasyApplication` import and can never pass on the renamed base; the sha and byte-identity check plus
  the runtime identity assertion replace it (ADR-0005 amended).
- **G04 (QML gated)** — upstream has no QML gate. Met edi-side: `qmllint` and `qmlformat` over edi's QML;
  the base subset loads under the same zero-warning smoke, but its own lint findings are recorded, not gated —
  edi does not own them.
- **G01/G02** remain E07's (the CMake half is answered by §1.2; native charts and web-safe settings are not).

### 5. Recorded ADR-0006 gaps

The base's `Settings { location: … }` sites; `FolderDialog`/`FileDialog` behaviour on the web; the Text tab's
scratch-directory save (MEMFS in the browser, to be proven at E07).

### 6. Charts and 3D — Qt Graphs and Qt Quick 3D; the distributed app is GPLv3

conda-forge ships `qt6-graphs`, `qt6-quick3d` and `qt6-charts` 6.11.2 as GPL-3.0-only and `qt6-main` 6.11.2
as LGPL-3.0-only; edi's source is BSD-3 (ADR-0008). **The owner decided on 2026-09-29**: the app links Qt
Graphs for the pattern chart and Qt Quick 3D for the structure view, and the distributed app is a GPLv3 work.
edi's source stays BSD-3; the core, the Python package and the CLI link neither module. The app's licence
notice (`app/DISTRIBUTION-LICENSE.md`) says so, as `DEPENDENCIES.md` does. **Amended 2026-10-03 (owner):** the
About dialog's licence link opens that notice, bundled in the app, and the dialog carries no separate
"distributed under" sentence; its second link opens the bundled third-party notices. The notice's own links
(`COPYING`, `LICENSE`, `THIRD-PARTY-NOTICES`) open those bundled texts in the same viewer, resolved against the
notice's location, and nothing outside the bundled licence texts opens there.

The pattern chart is built on Qt Graphs (ADR-0017 §15, ADR-0020, ADR-0021). The structure view is built on Qt
Quick 3D, which the app now links (ADR-0017 §16, ADR-0022).

### 7. The comparison against Rust + Tauri 2 + TypeScript

The measurements were a dedicated measurement task. Both stacks build the same probe — Home and the Experiment page with the LBCO/HRPT
project and a 1D pattern chart — calling edi's core. Criteria: bundle size per platform and the web payload; cold and warm startup to the first
frame and to "LBCO/HRPT loaded"; plotting latency and frame rate for a 3000-point pattern; the web build from the same source; the licence and
obligations of every linked runtime component, including Qt's LGPL under static WASM linking; web/desktop reuse — the share of UI source common to
both builds; how the C++ core is called. rietx (`57d1cf5f`) is recorded as a data point (its committed `dist` is 680 KB). Every number in carries
its provenance; this decision stands until the owner rules on that table.

### 8. The report

The Report page shows a simple report as Qt rich text in a read-only text area — project information,
crystal data per structure, data collection per experiment, the fit — composed from the typed view-models
(presentation only, ADR-0009's per-surface amendment). No web view, no JavaScript, no plots. **Note for the
postponed report task:** the cross-surface direction is one core report model, a C++ HTML writer for the CLI
and export, and a `_report` category; it waits for crysta's visualisation.

### 9. Look and the UI test

`edi_app --demo <dir>` walks a compiled step table — the sixteen states of the owner's v0.9.9 screenshots on
the Co₂SiO₄/D20 example, then edi's capability states — clicking controls by `objectName` with synthesized
mouse events, waiting until two frames 100 ms apart are identical, and saving one image per state; a missing,
hidden or disabled control fails the run naming the step. The demo shows a fixed "demo" identity, so the
images do not change with each build. `edi_app_ui_compare` compares the produced images with **one**
committed set for every platform by SSIM on luminance (8×8 windows, 32×32 tiles; a tile below 0.90 or the
image below 0.98 fails; a missing or differently sized image fails). The committed images are edi's own
output — a labelled regression pin, never a claim that the look matches v0.9.9; that is the side-by-side
review in `docs/dev/design/app-design-inventory.md`.

### 10. Text rendering and fonts

This section records how edi's app gets its text on screen, what went wrong on macOS during, and what was
decided. Every number cites its source.

#### The bundled fonts

The app draws text only with fonts it bundles:

| font | draws | bundled from |
| --- | --- | --- |
| PT Sans Regular and Bold | all text | gui-components, `Resources/Fonts/PT_Sans` |
| PT Mono | the Text tabs | gui-components, `Resources/Fonts/PT_Mono` |
| Encode Sans Regular | the fit summary arrow | gui-components, `Resources/Fonts/Encode_Sans` |
| Noto Sans Regular | every character PT Sans lacks | edi, `app/resources/fonts/Noto_Sans` |
| Noto Sans Mono Regular | every character PT Mono lacks | edi, `app/resources/fonts/Noto_Sans_Mono` |
| Noto Sans Light | the large light main-area text: the placeholders and the project name | edi, `app/resources/fonts/Noto_Sans` |
| Baloo 2 Regular and SemiBold | the wordmark, on Home and in About | edi, `app/resources/fonts/Baloo_2` |
| Font Awesome 5 Free Solid | the icons | gui-components, `Resources/Fonts/FontAwesome` |

Encode Sans and Nunito are no longer bundled.

edi's fonts carry their SIL Open Font License beside them (`OFL.txt`):

| file | source | sha256 |
| --- | --- | --- |
| `NotoSans-Regular.ttf` | `github.com/notofonts/notofonts.github.io`, `fonts/NotoSans/unhinted/ttf/` | `f3961a9cde016d41a4879aecda1474d3a36d6bf54fa0e4643de029cc2248b0e8` |
| `NotoSans-Light.ttf` | the same directory | `8897d5cba2567d06d437b1de90b65d37ea4c4b40db6b8979ea26d8789ce6e030` |
| `NotoSansMono-Regular.ttf` | the same repository, `fonts/NotoSansMono/unhinted/ttf/` | `87f8ce0522a6c99b743ee5fc75b4073cfdd575639119672828b7b9944b65b4f4` |
| `Baloo2-Regular.ttf` | `github.com/google/fonts`, `ofl/baloo2/Baloo2[wght].ttf` (`d47a6852…`), cut at weight 400 by fontTools' instancer | `d1b419a61ae4921e66451c53298881e63c7d0428b5335cea8fb479c05316d0cc` |
| `Baloo2-SemiBold.ttf` | the same file, cut at weight 600 | `31d32080e5820a78d90160f6816fe792b6ffaa659dd2af853bb785e9a26599db` |

How the app gets them:

- `cmake/EdiGuiBase.cmake` compiles the base's and edi's font files into the module resources under
  `/qt/qml/EasyApplication/Gui/Resources/Fonts`.
- edi builds its own `Style/Fonts.qml` (`app/qml/Base/Gui/Style/`) in place of the base's, the one base file it
  replaces. The base's file loads Encode Sans and Nunito, and a loader without its file warns. The base's
  font set is fixed in that file, which is upstream issue easyscience/gui-components#54; edi switches back to
  the base's `Fonts.qml`, `AboutDialog` and one-line name when the base can take them (enhantica/edi#87). edi's keeps
  every name the base's components read: `fontFamily` (PT Sans), `monoFontFamily` (PT Mono),
  `secondFontFamily` (the base's large placeholder text, now Noto Sans Light), `thirdFontFamily` (Baloo 2)
  and `iconsFamily`. Serving the new faces under the old files' paths instead would bundle each face once
  per path, because `rcc` embeds a file once for every path it is listed under (measured: 2.08 MB of
  generated source for one Noto Sans path, 4.15 MB for two).
- The host and the test runner make PT Sans the application font before any QML loads
  (`engine_setup.cpp`, `use_design_font()`).

No QML or C++ names any other family. Without an application font, Qt falls back to its generic "Sans Serif".
Linux resolves that to a system font. macOS has no such family: Qt warned while resolving it, and the Qt
Quick Test tier failed on that warning.

#### Characters PT Sans and PT Mono lack

PT Sans has no Greek letters. Its character map, read with fontTools, lacks 18 of the 28 non-ASCII
characters in the app's sources: α β γ θ σ χ, the subscript digits ₀ and ₅ to ₉, and → ⇒ ≡ ⊆ █ ░. PT Mono
lacks 14 of them: α β γ θ σ χ ₀ ₅ to ₉ ⇒ ⊆.

The fallback is per family, so no character the pages render comes from the platform and monospace text stays
monospace (first the Greek letters, then every character, then per family):

- every character PT Sans lacks is drawn from the bundled Noto Sans;
- every character PT Mono lacks is drawn from the bundled Noto Sans Mono.

`use_design_font()` makes each Noto font the substitute of its PT family (`QFont::insertSubstitution`). Qt
puts a family's substitutes at the head of the fonts it tries for a glyph the family lacks, ahead of the
platform's choices, and the substitution holds for every text in that family, including text whose QML sets
`font.family`. Three other ways would not do this:

- the application's fallback font (`QFontDatabase::setApplicationFallbackFontFamilies`), because it is set per
  script, not per family, so PT Mono text would get proportional Noto Sans;
- a family list on the application font (`QFont::setFamilies`), because a QML `font.family` replaces a
  font's family list;
- a family list on each font, because a list's second family lost to another in the fallback-font
  comparison.

Measured on Linux (a check program with the app's setup):

| text | α χ ₀ ₅ ₉ drawn by | μ, Latin drawn by |
| --- | --- | --- |
| PT Sans | Noto Sans | PT Sans |
| PT Mono | Noto Sans Mono, the bundled file | PT Mono |

The machine also has a system Noto Sans Mono of the same name. The font that drew PT Mono's ₀ carries the
bundled file's `head` checksum (`c63e1fa7`), not the system file's (`665357bd`). A Greek-only fallback had left
₀ to the platform: fontconfig drew it from the machine's own Noto Sans Mono in PT Mono text, and CoreText
chooses its own.

Noto Sans lacks → ⇒ ≡ ⊆ █ ░, which would still come from the platform; the pages render none of them
(→ ⇒ ≡ ⊆ occur only in code comments, █ ░ only in the core's scan progress bar).

#### The wordmark

"easydiffraction" is drawn as the official logo lays it out (easyscience/assets-branding at `46ab481`,
`easydiffraction/source/EasyDiffraction-logo_lightmode_wfont.svg`): the logo mark, and beside it "easy" over
"diffraction" in Baloo 2. `Components/Wordmark.qml` draws it on Home and in About, with every measure a
fraction of the mark's visible diameter, as in the SVG:

| measure | fraction of the mark's diameter |
| --- | --- |
| the name's font size | 0.4309 |
| the gap between the mark and the name | 0.1094 |
| the baseline of "easy", below the mark's top | 0.3859 |
| the baseline of "diffraction", below the mark's top | 0.8198 |

- The SVG asks "easy" for weight 300, but Baloo 2 has none: its weight axis runs from 400 to 800, and the
  SVG imports only that range. So "easy" draws in Regular, as it does in the SVG, and "diffraction" in
  SemiBold.
- The mark keeps the logo's size from before the wordmark (owner, 2026-09-28): 5 units on Home, as in
  easydiffractionbeta, and 3.5 in About, as in the base's dialog. The version line starts at the name's x.
- The name stays live text, not an image, so the Home page can animate it later.
- edi's About dialog follows the base's `AboutDialog` section for section, with this wordmark in place of
  the base's one-line name, which that dialog cannot stack. Its licences link and footer follow
  easydiffractionbeta's: the repository's `DEPENDENCIES.md`, and "© 2019-2026" from the EasyDiffraction
  project's first year. edi carries its own `Fonts.qml`, About dialog
  and wordmark until the base can take them (upstream easyscience/gui-components#54; the switch back is
  enhantica/edi#87).
- There is no startup window. edi never showed the base's `SplashScreen` and no longer builds it.

#### Two layers: the font database and the font engine

Qt's font API (`QFont`, `font.family`, `font.weight`) is the same on every platform, but Qt delegates two
separate jobs to the platform:

| job | Linux | macOS | Windows |
| --- | --- | --- | --- |
| **database**: which file a family, weight and style request resolves to | fontconfig | CoreText | DirectWrite |
| **engine**: how a glyph is rasterized | FreeType | CoreText | DirectWrite |

The same QML can therefore select a different face, and draw it differently, on each platform.

#### The face-matching defect found on macOS

This defect was found with the fonts bundled before the owner's decision above. Nunito and Encode Sans have
since been replaced, and the rule it produced, selecting each face by its own loader's family and its style
name, now selects Baloo 2 SemiBold and Noto Sans Light.

**Symptom.** On macOS every one of the UI test's 42 images failed its tile threshold, while each whole image
still scored high:

- min tile 0.47–0.60, image 0.98–0.99 (for example 04-project-loaded 0.4744/0.9784, 01-home 0.5957/0.9934);
- identical to the decimal across the pre-fix app-macos CI run, the owner's M2 run at `f5c40d2`, and the M2
  run with `QT_QPA_PLATFORM=offscreen:fontengine=freetype`.

That last run changed nothing because the macOS offscreen plugin has no such option (see "Selecting FreeType, and where the tests run").

**Where it was.** Cropping the worst tiles located the defect. On Home they sit on the "easydiffraction"
wordmark: "easy" (Nunito Light, 56 px) rendered visibly heavier than on Linux, while "diffraction" (Nunito
SemiBold) matched.

**Cause.** The bundled non-Regular files carry two sets of names (read with `fc-query` from the files):

- a *typographic* family and style (name IDs 16/17), for example `Nunito` / `Light`;
- a *legacy* family and style (IDs 1/2), for example `Nunito Light` / `Regular`.

A request for "Nunito, weight Light" relies on the platform database grouping the faces by the typographic
names and matching the weight to a face. fontconfig does this, and CoreText resolved the same request to a
heavier face.

Encode Sans added a second instance of the same class. It is bundled only as Regular and Light, so the
placeholders' and project name's ExtraLight resolved to whatever each database thought nearest.

**Fix.** Each non-Regular face is selected by the family its own `FontLoader` registered on that platform
(`EaStyle.Fonts.nunitoLight.name`, …) and by its style name (`font.styleName: "Light"`), never by a weight. This
resolves to the one bundled file whether the database grouped the face under its typographic or its legacy
family. The wordmark, the placeholders, the project name and the Description rows' bold labels use it.

On Linux every loader reports the typographic family (`Nunito`, `Encode Sans`, `PT Sans`), so the other 41
images are unchanged. One pin did change, 04-project-loaded, where the project name now renders in the light
face the original v0.9.9 shows. Before, the base `TextInput`'s unfocused `font.bold: false` binding reset the
requested weight to Normal. The pin was re-blessed for that reason.

#### FreeType for users: the owner decision

The owner decided that the app renders text with Qt's FreeType engine on every platform, for users and
tests, after comparing on the M2 `edi_app` with and without
`-platform cocoa:fontengine=freetype`. Under FreeType, the toolbar and status-bar items, which are sized by
their text, shifted their spacing slightly, while the sidebar looked unchanged.

For users this means `fontengine=freetype` on the `cocoa` and `windows` platforms. Linux draws with FreeType
already.

The cost: macOS and Windows users lose the platform's native smoothing and glyph positioning, and text-sized
controls move by a few pixels.

#### Selecting FreeType, and where the tests run

In the host, and so in the demo, `select_freetype_engine()` completes `QT_QPA_PLATFORM` before the
QGuiApplication exists:

- the `cocoa` and `windows` platforms (the defaults on macOS and Windows) gain `fontengine=freetype`;
- Linux platforms render with FreeType already;
- a `-platform` argument, which outranks `QT_QPA_PLATFORM`, is kept as given.

Then `require_freetype_engine()` aborts on macOS and Windows unless the platform in use is `cocoa` or `windows`
and was started with `fontengine=freetype`. It reads only public settings: the platform name
(`QGuiApplication::platformName()`) and the platform specification the application started from. Qt has no
public call that names the font engine in use, and the app does not ship on Qt's private API for a
self-check (owner, 2026-09-28: private headers tie the build to one Qt version). So the check proves that
FreeType was requested of a platform that offers it. The UI test proves that FreeType renders, because it
compares the glyphs' pixels with the committed images.

Headless platforms limit where the tests can run. The evidence comes from conda-forge's osx-arm64
`qt6-main` 6.11.1 binaries (strings of the plugins) and from Linux runs of the same plugin sources:

- **offscreen** on macOS carries only the CoreText engine and accepts no font-engine option.
- **minimal** has FreeType, but its windows are never exposed, so Qt Quick renders no frames.

The two app gates are split by purpose:

- **The Qt test runner checks behaviour, not pixels, and runs on offscreen on every platform, macOS
  included.** It neither selects nor requires FreeType; on macOS offscreen its text uses CoreText, which no
  case measures. On cocoa, the CI Mac opened real windows that could not become active ("window not active
  after requestActivate()" for every test file), so the two cases that need keyboard or pointer focus failed
  (124 of 126, the app-macos run at edi `f6fc476`). On macOS offscreen the same tier passed 126 of 126.
- **The demo capture, which the UI test compares, draws as users see it, with FreeType.** It needs no
  keyboard focus: the demo sends its clicks straight to the window.

So on macOS the demo capture runs on **cocoa with FreeType**, in the CI Mac VM's logged-in desktop session
(owner, 2026-09-28). Three safeguards go with it:

- **Window session.** `tools/ci/app-platform.sh` stops the gate, naming the session it found, when there is
  no window session (`launchctl managername` ≠ `Aqua`). It never falls back to another platform.
- **Device-pixel ratio.** Cocoa renders at the Retina ratio (a 2560×1536 image on the owner's M2), so the demo
  pins the ratio to 1 by restarting itself once with `QT_SCALE_FACTOR` set to the inverse.
- **Fresh settings.** A demo capture or a test run reads and writes the base's settings (window geometry,
  preferences, theme, project location) in a fresh directory that lasts as long as the process. The owner's
  saved "Enable tool tips" had changed a captured image.

#### One text pipeline: render type and hinting

Two platform defaults would still make the same FreeType glyphs differ, so the app fixes both
(`use_design_font()`;, conductor seq=52):

- **Render type: Qt Quick's own** (`QQuickWindow::setTextRenderType(QtTextRendering)`, Qt Quick's default,
  stated so that no platform or environment default decides it). Qt Quick draws each glyph from a scalable
  distance field of its outline (Qt's documentation of `Text.QtRendering`), not from the platform's
  rasterization.
- **Hinting: none** (`QFont::PreferNoHinting` on the application font). Glyphs keep the shapes and advances
  the font designs, whatever the platform's hinting setting. Left to the platform, Linux takes fontconfig's
  slight hinting (the app environment's `10-hinting-slight.conf`; `fc-match -v` reports `hintstyle: 1`).

#### The Linux capture display

Linux captures the demo on an X display of its own, so Qt Quick draws through OpenGL as on a desktop and as
cocoa does on macOS (`tools/ci/app-platform.sh`):

- **Weston**'s headless backend runs a rootful **Xwayland** of the capture's size (1280×768). The app runs on it
  through `xcb`, and **Mesa's llvmpipe** draws its OpenGL. All three are conda-forge packages in the app
  environment (linux-64 only), so no system package is involved.
- The app cannot be a Wayland client of Weston itself: conda-forge's Mesa is built without the Wayland EGL
  platform (its `libEGL_mesa` reports "Wayland platform not built"; it has x11, xcb, gbm, surfaceless and
  device).
- conda-forge's only Weston (16.0.0) needs glibc 2.34. The app environment runs on a Linux platform of its
  own that declares it (`linux-64-app` in `pixi.toml`), which moves its sysroot from glibc 2.28 to 2.34; the
  default environment, the core and its wheels stay on `linux-64` at 2.28.
- The demo asks for 8 bits per colour channel. An EGL display can offer 16-bit RGB565 first: a Wayland probe
  on the host's own Mesa captured 32 red levels where the committed set had 255.

The offscreen platform the set was captured on before has only Qt Quick's **software** scene graph, and that
differed from a desktop in two ways:

- It cannot run shader effects. The base puts each popup's background under one (the Dialog, ComboBox popup
  and Menu under `ElevationEffect`, the ToolTip under `ToolTipShadow`), so the captured popups had no
  background.
- It rasterizes text natively instead of from distance fields.

Compared with that software-rendered set, the demo on the Xwayland display scores what the owner's M2 on
cocoa scored against it. The Linux column is (Mesa 26.2.3
llvmpipe, 8 bits per channel, the text pipeline above); the M2 column is the owner's run at edi `d6e44af`:

| image | M2, cocoa (min tile / image) | Linux, Xwayland + llvmpipe (min tile / image) |
| --- | --- | --- |
| 01-home | 0.8064 / 0.9961 | 0.8065 / 0.9961 |
| 06-model-space-group | 0.6119 / 0.9910 | 0.6120 / 0.9910 |
| 11-experiment-profile-shape | 0.6090 / 0.9876 | 0.6090 / 0.9876 |
| 16-summary-preferences | 0.5353 / 0.9730 | 0.5360 / 0.9736 |
| 17-experiment-profile-selector | 0.3714 / 0.9693 | 0.3710 / 0.9694 |

So the gap was on the reference side, and the set is now captured on the Xwayland display.

## Consequences

- The pages bind typed members, so `qmllint` catches a missing member at build time, and one edit updates
  exactly the views of that value.
- The base is used as it is at its pin: fixing a base defect is an upstream change and a pin move, never an
  edi edit.
- The app shows only what edi models; a new capability becomes visible by adding its category or selector
  in the core and a group in the app.
- The base's per-field controls are heavy (each builds its own context menu), so rebuilding a page's groups
  on a project or experiment change costs about a second on the joint projects; keeping per-block group
  trees is the next step if that matters.
- The app links Qt Graphs, so the distributed app is a GPLv3 work (§6); the source stays BSD-3.

## Alternatives considered

- **Vendoring the base now** — that is E08's decision taken early; rejected.
- **The base's PySide wheel** — a Python host; rejected by ADR-0009.
- **Editing the base** — rejected by ADR-0005; a needed change goes upstream.
- **`setContextProperty` for edi objects** — defeats `qmllint`'s type checking; rejected.
- **Auto-generated per-field reflection instead of typed view-models** — untyped; rejected.
- **A web view for the report** — needs QtWebEngine, which the web build cannot have; rejected for §8.
