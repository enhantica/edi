# ADR-0003: Scripted how-to coverage and configurable examples

Date: 2026-10-30
Status: implementing and publishing in batches

## Prior art

ADR-0001 defines source-matched native figures. The initial walkthrough covered the workflow and sidebar modes, while individual how-to articles were still prose. The original native script and importer also hard-coded the Y2O3 input filenames.

## Decision

The schema-2 JavaScript plan declares one `EXAMPLE_ID` and a `build(capture)` function. The app looks up that bundled example, supplies its display metadata and input filenames, and copies its separate input files and data dependencies. It does not load `project.edi`. A fixture outside the current one-structure/one-experiment template refuses explicitly. Native source/script/image hashes and all dependency hashes remain in the bundle.

The script records named `guide-*` scenes for individual app tasks as well as the complete page/sidebar inventory. `gui-guide-scenes.json` maps authored how-to headings to these scene names. The importer adds each figure after its instructions and refuses absent headings or required scenes. Per-use identifiers keep repeated figures' SVG clips unique. Changing the selected example updates filenames, titles, input downloads and screenshot geometry; no pixel coordinates live in the articles.

Detailed application topics group related GUI controls into user tasks. Practical choices and short instructions stay in these pages; equations and conventions are linked to Physics. Application, Python and Command Line retain the same workflow groups and topic order, with instructions appropriate to each interface.

## Verification

Run the real creation/import/refinement/report workflow, capture task-specific controls, save and export through the existing native seams, and check all generated links and source bindings. Exercise a second bundled refinement example by changing only the script's example id. Specialized scan illustrations need a scan fixture; a single-pattern screenshot must not be presented as a scan.

## Focused workflow topics

The application navigation groups the native controls into small task pages: symmetry/cell, atom sites, displacement, scattering lengths, instrument, profiles/cutoff, phase links, corrections, parameter relations, minimizer and display preferences. Each practical subsection is mapped to a named native capture. Broad structure and experiment pages introduce their own controls and link to these topics rather than repeat the full workflow.

Native selector choice lists are generated inside `gui-options` markers from the captured option tokens and labels. Where a Physics category is declared, every token must resolve through the model catalogue. Missing captures, missing selector choices, duplicate tokens or unresolved Physics models refuse import. Switching the configured example therefore updates the option list together with the screenshot, including a different experiment type.

## Scan references and inventories

The creation bundle remains mandatory and rejects reference-mode captures. A separate, explicitly declared native reference plan opens the selected scan, fits all its datasets and captures enabled sidebar and secondary main views. Its manifest records the distinction and completed/failed dataset counts; import refuses an unfinished scan or an open fit popup. The existing SVG renderer and image dialog handle both bundles. Named multi-image choices use the same native tabs as the rest of the guide. `GUI-SCENES.md` is generated from executed manifests, including skipped modes, actions and highlight targets, rather than maintaining another inventory by hand.
