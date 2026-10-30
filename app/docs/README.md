# GUI documentation captures

The bundled `y2o3-spodi.js` walkthrough runs the real application at 1480 by 800 pixels. It starts on Home, creates a project through its form, imports the structure and experiment separately, runs a fit, closes its results popup and visits Report. Every enabled sidebar tab is captured. Disabled tabs are recorded as skipped.

Build and run from the edi checkout:

```sh
pixi run -e app app-build
pixi run -e app bash tools/docs/capture-gui.sh /absolute/path/to/new-capture
```

For an existing native build, set `EDI_DOCS_APP` to its executable before running the capture command. On Linux the launcher starts an isolated Weston/Xwayland display with the app environment's OpenGL renderer. On macOS it needs a logged-in graphical session. The run uses isolated app settings and a temporary project; it does not modify your saved projects.

The output directory must not contain an earlier PNG or manifest. A successful run exits zero and writes `manifest.json` with `status: complete`, PNG images, matching JSON layout/state sidecars, the executed `walkthrough.js`, and separate input files. Geometry comes from the current QML items mapped into the screenshot's coordinate system. Analysis and Report captures require completed native fit results and a closed results popup.

To edit a walkthrough without rebuilding the app's bundled resources:

```sh
pixi run -e app bash tools/docs/capture-gui.sh /absolute/path/to/another-capture \
  --docs-script /absolute/path/to/walkthrough.js
```

The script evaluates to the plan object documented in [ADR-0059](../../docs/dev/adrs/0059-scripted-gui-documentation-captures.md). It receives the isolated input paths through `capture`. File imports invoke the same native load methods as the ordinary file chooser's acceptance handlers; they do not automate the operating system's file picker.

In the temporary documentation repository, validate and import the completed bundle, then build:

```sh
python website-concepts/checks/gui_capture.py /absolute/path/to/new-capture
python website-concepts/import_gui_captures.py /absolute/path/to/new-capture
python website-concepts/build.py --base-url https://enhantica.github.io/edi-website-preview/
```

The importer generates the walkthrough, workspace guide and page/sidebar reference. Responsive SVG highlights use the captured geometry. The documentation build validates hashes, dimensions, workflow order, sidebar coverage and post-fit state. The native capture remains a manual command; automatic native capture in CI is a later integration.

## Select another example

Change only `EXAMPLE_ID` near the start of `app/docs/y2o3-spodi.js`, or copy the script, change that setting and pass it with `--docs-script`. The schema-2 script declares `example` and `build(capture)`. The app resolves the bundled fixture and supplies its title, name, description and separate input paths. Structure and experiment filenames and dependent data files are discovered rather than hard-coded. The initial template requires a measured-data example with one structure and one experiment; a multi-block case needs explicit additional import steps.

The same sequence has been exercised on Y2O3/SPODI and LBCO/HRPT by changing that one setting. `guide-*` scenes supplement the workflow overview with file choices, symmetry, cell, atom sites, instrument, profiles, background, exclusions, phase links, analysis controls and report export. Selector options and their selected tokens are exported from the actual native models; documentation must not invent a second supported-options list.

Expanded detail scenes also cover uncertainty display, the measured-data table, peak cutoff, the previous fit's start values, parameter visibility and scan display updates. These remain part of the same plan and use the selected example's native controls and geometry.
