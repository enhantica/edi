# 0060. Scripted GUI documentation captures

- **Status:** Accepted
- **Date:** 2026-10-30
- **Implementation:** 🟡 Partially implemented — the native capture runs by hand (`tools/docs/capture-gui.sh`); a CI
  capture job is later work
- **Priority:** Medium

## Context

The user documentation needs an illustrated walkthrough that can be redone whenever the app changes: Home, a new
project created through its form, a structure and an experiment imported separately, a fit, then Report, with one
screenshot per enabled sidebar tab. The state on each image has to come from that workflow, not from opening a finished
project. The documentation site also needs to know where each control sits on the image, so it can draw highlights.

The app already has a capture path: the demo driver (ADR-0015, ADR-0017) clicks named controls in the real app, uses
isolated settings and saves a settled frame per step. Documentation extends it rather than adding a second one.

## Decision

`edi_app --docs-capture OUTPUT` runs the bundled `app/docs/y2o3-spodi.js` plan; `--docs-script FILE` runs another plan
with the same schema. Both are exclusive with `--demo`, which keeps its defaults. Documentation uses the demo driver's
actions and settle logic.

A plan is a JavaScript expression returning `schema: 2`, one `example` id and a `build(capture)` function. The app
resolves the id in the bundled catalogue, copies that example's separate inputs (never `project.edi`) into the output
folder with their hashes, and passes their paths to `build`. `build` returns named steps: actions, description, page,
sidebar tab, highlight targets and whether to save an image. Step ids are checked as unique safe filenames. The default
`creation` workflow refuses every whole-project load; `workflow: "reference"` may open exactly its declared bundled
example, for scan and joint-fit views. The manifest records which workflow ran.

File imports call the same `loadStructure`, `loadExperiments` and `loadData` methods as the file chooser's accept
handlers; the system file picker is not automated. With `inputs: "cif-and-data"` the structure is exported as a CIF and
the measured columns as XYE from the chosen example, so the walkthrough starts from ordinary input files.

Sidebar tabs are checked after navigating: a disabled one is recorded as skipped, an enabled one is clicked and
captured. Analysis and Report images need a finished fit with its results popup closed, except Analysis steps marked
`fitPhase: "setup"`.

Each image gets a JSON sidecar: logical and pixel size, source commit, GUI base commit, script and image hashes, the
page, sidebar and fit state, and every named visible item's bounds in image coordinates after clipping. Selectors add
their option tokens, labels and the selected token from the native `OptionListModel`; controls with an icon add its
Font Awesome name. Highlight targets must exist exactly once. The layout is read twice around the frame and must not
change. `manifest.json` stays `running` or `failed` until every step completes.

The app bar, status bar and the two file-choice columns get object names. That changes identification only.

The demo driver's visibility check uses an item's layout rectangle and its ancestors' clip rectangles, the same as the
sidecar. A text field's painted-text rectangle can be empty after its text is cleared while the field is still usable.

Reference plans may take up to 30 s to settle a frame, since large projects build their pages for longer. Ordinary
demos and creation plans keep the existing bound.

## Consequences

- The documentation site imports a finished bundle and checks hashes, sizes, page and sidebar coverage and the
  post-fit state before it builds any page. Instructions for running and importing a capture are in
  [app/docs/README.md](../../../app/docs/README.md).
- A plan selects its example with one `EXAMPLE_ID`. The creation plan supports one structure and one constant-wavelength
  powder experiment with measured data; other cases refuse with a reason.
- Option lists and icon names in the docs come from the app, so the docs cannot list options the app does not offer.
