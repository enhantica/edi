# GUI documentation captures and annotations

Status: implemented and published, 2026-10-30. The native exporter, bundled JavaScript walkthrough and documentation overlay renderer are working. The current capture manifest records the source-matched Y2O3/SPODI capture set, input dependencies and the exact executed script. See the [Example refinement](https://enhantica.github.io/edi-website-preview/application/first-refinement/) and [Application layout](https://enhantica.github.io/edi-website-preview/application/workspace/).

## Recommendation

Extend edi's existing native `DemoDriver` capture path to produce a screenshot and its layout metadata together. Use the bundled JavaScript to select scenes and drive the built app; use Python to validate the resulting bundle and generate documentation SVG overlays. Do not build a second GUI or try to reconstruct QML layout in Python.

The screenshot supplies appearance; Qt supplies coordinates; the documentation supplies explanations and the choice of what to highlight. A writer names a control or region instead of measuring pixels.

## Sources inspected

- [Earlier application guide](https://docs.easydiffraction.org/app/how-to-use/): toolbar and its action/workflow groups, main working area, sidebar modes and status bar. Downloaded HTML: `/tmp/edi-layout-research/old-app-guide.html`.
- [NOBUGS presentation source](https://github.com/AndrewSazonov/presentations-and-posters/blob/master/2026.09.21%20-%20NOBUGS%20-%20GUI-EasyScience/index.html), plus `extra/talk.css`: the horizontal slide sections `#/15`, `#/16` and `#/18` and their vertical steps. The index blob inspected is `5dd09be1f2774f86322947a5421e1e3582c706cc`; local source copies are under `/tmp/edi-layout-research/deck/`.
- edi checkout `.worktrees/edi-ai-assistant-on-dev`: `app/main.cpp`, `app/src/demo_driver.{cpp,hpp}`, `app/qml/Main.qml`, `app/qml/Components/WorkflowPage.qml`, and `tools/ci/app-platform.sh`. Existing design records: `docs/dev/adrs/0015-edi-app-stack.md` and `0017-app-gui-design.md`.
- [Qt item-coordinate mapping](https://doc.qt.io/qt-6/qquickitem.html#mapRectToScene) and [window framebuffer capture](https://doc.qt.io/qt-6/qquickwindow.html#grabWindow).

## What to retain from the references

The presentation uses an ordinary screenshot underneath separate vector/CSS decoration:

- `#/15`: SVG `markbox` paths join the selected workflow tab to its working region. The outline is not baked into the PNG.
- `#/16`: positioned `.zone` rectangles identify the toolbar, main view, controls and status bar; separate SVG arrows show reading order.
- `#/18`: SVG outlines move between the sidebar modes, expanded groups and main-area views while the screenshots change.

The deck's annotation style is a translucent warm wash with a matching thin outline; its `talk.css` defines the colour and fill opacity. Reproduce that visual vocabulary, including tab-and-panel outlines, while generating coordinates from metadata. The presentation's current coordinates are hand-authored percentages and path points; those would drift if copied directly onto new app screenshots.

Use the earlier guide's decomposition, but current product wording. The inspected QML calls the pages Structure and Report, and the sidebar modes Main, Extra, Text and Settings. Available tabs vary by page. The layout overview should describe the default sidebar placement rather than promise it never moves: edi also has a sidebar-side preference.

## User-facing organization

Keep this under Application. The shared User guide describes the analysis model; Physics explains its scientific meaning.

1. **Find your way around:** one current screenshot introducing the toolbar, main working view, controls and status bar. Follow with toolbar action groups and workflow tabs.
2. **Views and controls:** main-area tabs, Main / Extra / Text / Settings, collapsible groups, selection, disabled controls, messages and undo.
3. **Page-specific guides:** Project, Structure, Experiment, Analysis and Report. Each explains the user's goal, where the relevant controls are, what to do and where the result appears.
4. **Assistant:** opening/closing the chat, how it relates to manual controls and how to follow its actions, using a separate captured state.

Prefer one focused annotation per instructional step. A short numbered explanation accompanies each figure; selecting a step can change the highlighted region. Keep an overview/static fallback, keyboard-operable controls and an enlarge option for small screens. The instructional text must remain useful without hover, animation or the picture, including for the built-in assistant.

Link parameter and calculation explanations to the existing Physics anchors rather than placing scientific definitions inside an SVG.

## Existing capture infrastructure to extend

`app/main.cpp` already supports `--demo <output>` and `--demo-only <prefix>`. Demo mode isolates settings, sets the design font/appearance identity, disables caret blinking and normalizes the default capture scale. `DemoDriver` seeds randomized model additions, drives controls by `objectName`, waits for calculations/page preparation and compares frames until settled before writing PNGs.

`DemoDriver::find` already searches both QObject descendants and visual children. Its on-screen check accounts for clipping ancestors. These are useful precedents, but a documentation resolver must also reject ambiguous required names and scope repeated names to the selected page/sidebar. Hidden pages stay loaded; finding a matching name alone does not prove the intended target is shown.

Many usable anchors already exist, including `appBar.tab.analysis`, `workflow.analysis.mainContent`, `workflow.analysis.manualSidebar` and the sidebar-tab names. Some large toolbar/status containers currently have QML ids or aliases without a stable `objectName`; give those explicit names instead of locating them by child order or guessed dimensions. Reuse the same semantic naming convention as tests and native GUI actions.

Do not add a second screenshot saver beside the existing one. Extract/reuse one capture operation so demo and documentation consumers can share the frame/layout contract.

## Capture bundle

For a declared scene, write a PNG, a JSON sidecar and a manifest entry as one validated bundle:

- capture/scene identifier and schema version;
- app source commit, shared GUI-components commit, built-artifact hash and fixture identity/checksum;
- Qt version, platform/renderer, theme, language and font settings;
- client-area logical dimensions, actual PNG pixel dimensions and effective scaling;
- PNG SHA-256;
- named regions/controls with scene-space bounds, clipped visible bounds, visibility/enabled state and available accessible/display labels.

Export named relevant controls and containers, not every Qt implementation object. The annotation manifest declares the required targets. Repeated delegates need stable model/record identifiers; a scrolled-away virtualized row must first be revealed by the scene actions.

Read geometry in the GUI thread with `mapRectToScene`/`mapToScene`, including ancestor transforms. Account for clipping and the selected page. Disabled but visible controls are valid annotation targets when teaching why an action is unavailable. Rectangle clipping alone does not prove lack of occlusion: scene setup must close unrelated popups/sheets or explicitly capture and describe them.

Capture the native client area, excluding the operating-system title bar. Read the image and geometry in the same settled capture operation; compare geometry before/after capture and retry/refuse if it changed. Do not pair a cached PNG from an earlier event-loop iteration with later item bounds. Explicit animated scenes require a separate declared capture rule.

Use a fresh output directory and finalize its manifest only when the whole requested bundle succeeds. Missing/ambiguous/hidden required targets, nonfinite/out-of-frame geometry, wrong page state, null images or hash mismatches are errors, not reasons to reuse an older image.

## Coordinate-free authoring

An illustrative proposed scene declaration might contain:

```yaml
scene: analysis-overview
example: pd-neut-cwl_lbco-hrpt
page: Analysis
sidebar: Main
annotations:
  - target: appBar.tab.analysis
    text: Open Analysis to choose which parameters to refine.
  - target: workflow.analysis.manualSidebar
    text: Select parameters and choose which are free to vary.
```

This is a proposed format, not an existing CLI or parser. Each scene also declares its window/theme and actions needed to expose the referenced controls. Python orchestrates these through the existing native driver rather than simulating a separate application model.

The overlay renderer resolves target names against that capture's JSON. It can generate rectangles, numbered callouts, arrows and notched tab-and-panel outlines. Captions and placement rules are authored; control coordinates are not.

## Rendering in Zensical

Use one inline responsive SVG with a logical-size `viewBox`. Place the PNG as its image layer and every highlight in that same coordinate system. The PNG may have a higher pixel density; its displayed logical size and the vectors scale together. Do not size/crop an HTML image and a separate overlay independently.

The native PNG remains clean and reusable. The same image/bounds can support several explanations without duplicate raster files. For standalone SVG downloads, embed the PNG; for the site, an inline SVG can reference the shared local PNG. Provide accessible figure text and text instructions outside the decorative vector layer.

The current homepage uses an owner-supplied screenshot with a CSS title-bar crop. A future replacement with a client-area native capture must retire that crop for the new asset; otherwise it would cut the real app toolbar. Keep that existing consumer in scope when adopting generated captures.

## Manual first, then CI

The first implementation should deliver a layout overview and a representative annotated Analysis scene, with one manual command producing and validating all required artifacts. Then expand the same mechanism to the other workflow pages, modes and the assistant. Keep screenshots for meaningful user states rather than every tab/row combination.

For CI, consume the native app artifact built for the declared source commit, run the same capture command and publish its complete bundle with the docs. Reuse the existing platform setup: Linux capture uses Xwayland/Weston with OpenGL; a generic software/offscreen fallback does not reproduce every shader/3D effect. Pin the canonical capture environment rather than promise byte-identical images across operating systems.

Checks should prove image/metadata identity, unique required targets, valid bounds and expected scene/labels, then verify SVG alignment and accessibility at representative browser widths. Geometry can update automatically, but new labels, renamed targets, moved functionality or changed workflows still need editorial review; those changes should fail explicit expectations so the affected instructions are noticed.

## Investigation result and limits

The existing `--demo-only onechart-` sequence completed successfully through the headless OpenGL capture path. The run wrote its PNGs and their provenance and exited with status zero. This exercised the capture mechanism on Analysis, Experiment and Structure views.

The binary was retained before running to prevent a concurrent relink from changing the experiment. Its CMake version label differs from the inspected checkout HEAD, and an incremental dry-run requested CMake regeneration, so it is not certified as a source-matched release screenshot. The saved provenance states that limitation explicitly. A DataTable column-width binding-loop warning was also recorded and should be investigated against a source-matched build before adopting a capture baseline.

This investigation has not implemented or validated automatic geometry export, generated production overlays, changed the public application guide, or configured a docs CI job. It establishes the visual references, the existing capture path and the proposed contract for the next implementation.

## Implemented commands

In edi (branch `docs/gui-walkthrough-y2o3`, based on `ai-assistant-on-dev`):

```sh
pixi run -e app app-build
pixi run -e app bash tools/docs/capture-gui.sh /absolute/path/to/new-capture
```

Set `EDI_DOCS_APP` to use an existing native build. An optional `--docs-script FILE` replaces the bundled JavaScript plan. On Linux the launcher supplies an isolated 1480 by 800 Weston/Xwayland display. The ordinary demo keeps its existing 1280 by 768 default.

In this preview repository:

```sh
python website-concepts/checks/gui_capture.py /absolute/path/to/new-capture
python website-concepts/import_gui_captures.py /absolute/path/to/new-capture
python website-concepts/build.py --base-url https://enhantica.github.io/edi-website-preview/
```

The committed capture manifest lists the current scenes and explicit skips for disabled tabs. Its image hashes, dimensions, source/script identity, actual sidebar state and closed post-fit popup state are validated on every documentation build. The first successful fit reports native outcome `success`. File imports use the existing file chooser acceptance methods; platform file picker dialogs are not automated. Native capture is manual for now; the documentation validation already runs in the Pages build.

Validation also rejected incomplete runs, mixed source revisions, whole-project actions, missing enabled tabs, paths escaping the bundle, open fit popups, invalid highlight bounds, wrong sidebar labels and changed PNGs. Chromium checks exercised desktop/mobile layouts and keyboard/click highlight selection. Safari was not available for this new documentation check.

## Figure and navigation revision

[ADR-0001](adrs/0001-gui-figures-and-image-dialog.md) extends the original renderer. Only the screenshot image is clipped to rounded corners; a separate square path remains visible beyond the frame and expands by 1.5 display pixels. Sidebar outlines join the actual checked tab to its body using native geometry. All figures explicitly fill their text column. Clicking an image opens a themed fullscreen dialog with the current highlight, keyboard containment, Close/Escape and focus return. The page introduction now has one Application layout page (including all sidebar views), followed by one Example refinement page. Previous URLs redirect to the consolidated pages.

## How-to coverage

[ADR-0003](adrs/0003-scripted-how-to-coverage.md) records the configurable script and task-specific guide scenes. `gui-guide-scenes.json` maps authored instructions to captures; import refuses missing headings/scenes. The importer also derives titles, filenames and input downloads from the selected fixture. The current illustrated guide batch was captured with the schema-2 factory at native source `ce108caedfe7f6637328bae9aad009deed328ddb`; its executed custom script is retained by hash in the manifest.

## Detailed task inventory

The complete inventory is the committed native `walkthrough.js` plus `manifest.json`; each action and capture/skip has an explicit entry. The how-to heading map is `gui-guide-scenes.json`. This includes uncertainty formatting, structure appearance and scattering, measurement ranges/points, peak cutoff, absorption/orientation, aliases/constraints, pre-fit values, parameter visibility and scan display updates. The importer derives practical option lists from the native selector metadata and links supported model tokens to Physics; it does not maintain another list of GUI choices.

## Conditional workflow views

Run the native `app/docs/workflow-reference.js` with its default scan id, then copy it and change only `EXAMPLE_ID` to a joint-fit example for the joint views. These explicitly declared reference runs open bundled projects; they do not replace the creation walkthrough. Import both with `--reference-bundle /path/to/scan --joint-bundle /path/to/joint`. Reference validation requires post-fit closed dialogs; scans also require a fitted result for every dataset and no failed datasets. `GUI-SCENES.md` includes action-only steps such as fitting as well as images and intentional skips.

The documentation build checks every practical subsection in every Project–Report navigation topic against the capture registry, the rendered image and current native selector choices. Adding a heading without its illustration, referring to an absent scene or keeping stale option prose refuses the build.

## Group and dark captures

[ADR-0015](adrs/0015-application-menu-follows-the-sidebar.md) adds `app/docs/group-reference.js` for conditional groups, and [ADR-0017](adrs/0017-dark-theme-screenshots.md) adds a dark run of every script. Import them all together:

```sh
python website/import_gui_captures.py LIGHT/y2o3 --reference-bundle LIGHT/scan --joint-bundle LIGHT/joint \\
  --group-bundle sc=LIGHT/sc --group-bundle magnetic=LIGHT/magnetic \\
  --dark-bundle y2o3=DARK/y2o3 --dark-bundle scan=DARK/scan --dark-bundle joint=DARK/joint \\
  --dark-bundle sc=DARK/sc --dark-bundle magnetic=DARK/magnetic
```

Change `EXAMPLE_ID` and `GROUPS` together in a copy of the script, and pass it with `--docs-script`.
