# Incremental Stacked geometry

This small native fixture drives the real ScanLines scene-graph synchronization without a GPU or a fit.
It checks that changing one trace replaces only its geometry group, style changes preserve geometry,
NaN breaks stay breaks, hidden updates apply on activation, partial groups track style counts, and
replacement or scene recreation uses the latest traces.

Run `pixi run -e app --skip-deps app-test-scan-lines` from the repository root.

The fixture also checks screen-limited Stacked selection, selected/hidden/overlaid rows, zoom expansion,
and Map pixel centres, smooth edge weights, original dataset identities and out-of-range pixels.
