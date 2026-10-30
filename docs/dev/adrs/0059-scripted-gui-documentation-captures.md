# ADR-0059: Scripted GUI documentation captures

Status: implemented; manual native workflow verified
Date: 2026-10-30

## Context and prior art

The owner requests an illustrated, reproducible Y2O3/SPODI walkthrough at 1480 × 800: Home, create a project through its form, separately import the structure and experiment, fit, close the fit-results dialog, then Report. Every enabled sidebar mode needs its own screenshot. Scientific state must arise from this workflow, not from opening a complete prepared project.

The prior implementation is DemoDriver (ADR-0015, ADR-0017): native clicks, named controls, isolated settings, seeded additions and settled-frame capture. Documentation must extend that path. Presentation highlights are a separate vector layer over screenshots; their coordinates should come from the current QML scene instead of hand measurement.

## Decision

The command edi_app --docs-capture OUTPUT runs the bundled app/docs/y2o3-spodi.js plan. The --docs-script FILE option selects another JavaScript plan with the same schema. These flags are exclusive with --demo; ordinary demo capture retains its original defaults. Documentation uses the same native action executor and settle logic.

The JavaScript returns schema, example and named steps with actions, description, workflow page, sidebar mode, highlight targets and an optional capture flag. It receives only this run's isolated project location and separate structure/experiment input paths. The native driver validates the plan and safe unique image names. Documentation refuses whole-project/example loading actions. Native import actions use the original loadStructure / loadExperiments methods called by the file chooser's acceptance handlers; the platform file chooser itself is not automated.

Sidebar candidates are checked at runtime after navigating to the page. Disabled modes produce explicit skipped manifest entries; enabled modes are clicked and captured. Analysis and Report screenshots require native fit results, no running fit and a closed results popup. The fit uses the imported input declarations and the normal fitting control.

Each screenshot has a JSON sidecar containing logical/pixel sizes, source revision from the existing build-commit witness, script and image hashes, GUI-components revision, actual page/sidebar/fit state, and named QQuickItem bounds mapped to scene coordinates with clipping. Required highlight targets must exist uniquely. Layout and framebuffer are checked again before accepting the pair. The manifest remains running/failed until every requested step completes and binds the resulting scenes, inputs, actions and executable hash.

The app bar and status bar gain stable object names, joining the existing page-region names. This changes identification only. QML geometry remains authoritative; neither the script nor the docs needs to copy dimensions for controls.

## Documentation consumer

A documentation importer validates the complete bundle, image hashes, dimensions, page/sidebar coverage and the post-fit state before generating any public pages. It uses an inline responsive SVG with the screenshot and vector highlights in one viewBox. Text instructions and a full-size image link remain available separately.

## Validation

Exercise the actual native workflow, including project creation, separate imports, all enabled sidebar modes, the fit completion/closed-popup contract and target geometry. Refuse malformed script data, stale/mismatched artifacts and missing required targets. Existing demo semantics remain covered by a representative original-mode run. A manually generated bundle is the first consumer; the same command can later consume a CI-built native app artifact.

## First verified run

The source-matched app at `eb945aa8fb5964658daeab4a5bdc488b653e3bf3` completed the bundled default walkthrough. Its manifest records 23 captured images at 1480 by 800 and explicit skips for disabled modes. The fit state is success; every Analysis and Report image has no running fit and no open results popup. The preview importer validated this complete bundle before publication.

Manual capture entry point and import instructions: [app/docs/README.md](../../../app/docs/README.md). The CI documentation build validates committed captures; native GUI capture itself is not yet scheduled in CI.

## Configurable fixture and how-to scenes

The schema-2 script declares one `EXAMPLE_ID` and a `build(capture)` factory. The native host resolves that id against the bundled catalogue, supplies its title and input filenames, and retains the separate inputs and data dependencies with hashes. It excludes `project.edi`; the workflow still creates its own project and imports the inputs. The initial template requires one structure and one experiment and measured data; a multi-block fixture refuses explicitly instead of silently dropping blocks.

Named `guide-*` scenes cover project file choices, structural symmetry/cell/sites, experiment data/instrument/profile/background/exclusions/links, analysis modes/minimizer/constraints, and report contents/formats/export status. The two native file-choice content columns gain stable names. These guide scenes supplement the complete page/sidebar inventory and drive the relevant UI controls through the original DemoDriver executor.

Selector metadata also retains the current native option tokens, display labels and selection from `OptionListModel`. This supplies the documentation's short option lists from the same source used by the app. A corrected deterministic timestamp uses the existing STAR timestamp format, so saving/export can be exercised rather than refused by the core.

GUI icon names are captured from the visible control's `fontIcon`, `keyIcon` or string `icon` property. Documentation uses those actual Font Awesome 5 names alongside the native labels; controls without a GUI icon do not gain an invented one.

Detail scenes expand the remaining project/experiment/analysis settings groups: uncertainty formatting, measured points and ranges, peak cutoff, pre-fit start values, parameter visibility and pattern-update policy during scans. They use the existing `panel` helper and do not add a second capture path.

## Specialized reference runs

A scan reference is a different user task from constructing the initial single-pattern example. A schema-2 plan may explicitly declare `workflow: "reference"`; only that mode can open its exact declared bundled example through the existing example loader. Arbitrary project paths and other example ids still refuse. The default remains `creation`, which refuses every whole-project load. The manifest carries this distinction so a documentation importer cannot substitute a reference for proof of the creation workflow. Scan captures also report total/fitted/failed counts and show the real enabled secondary views after fitting.
