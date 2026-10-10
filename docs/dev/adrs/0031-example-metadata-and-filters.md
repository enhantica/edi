# ADR-0031: Example metadata and filters

Status: accepted (owner's examples table decisions, 2026-10-09).

The prior implementation is `ExampleListModel` in Session and `ExamplesGroup.qml`: it inferred sample and technique from registry IDs and displayed two lines without filters. The CLI registry is an execution contract; presentation facts now live in the app's bundled `examples/metadata.json`, with source paths for each entry. Missing facts remain “Not specified”; simulation purpose is separate from the saved fitting mode. Multi-phase examples name every sample.

The model publishes typed properties and list models, following ADR-0015. Search normalizes Unicode and case and requires every word. A property picker selects the value vocabulary; choosing a new property resets the value to All. Value counts reflect the text search, count each example once, and ignore the selected value. Zero-count choices remain available. Filtering retains registry order and immutable example IDs; clicking a filtered row opens its own ID.

Rows have three lines: samples and instrument/facility; separate coloured tags with slightly rounded corners (option B); descriptive details. Long content elides or clips and is available in a tooltip. Counts appear in the value picker only. Users clear text or select All; there is no separate reset button or results counter. This extends the Analysis filter presentation while retaining the examples-specific dependent value picker.

Configuration requires metadata for every bundled example. Metadata axes come from the saved experiment and analysis files; curated samples and origins supplement those files, without adding guessed dimensions or polarisation. Public `tst_example_filters.qml` exercises source membership, normalized search, facets, unknown facts, multiple samples and opening after filtering.

The owner's enrichment on 2026-10-09 makes every experiment's effective native type explicit in its saved file. Every profile is recorded as `1D`. Project titles name all samples with their stored space groups and use `instrument @ facility`; descriptions identify the scientific purpose, profile/background or scan variant. Neutron beam polarisation is `none`; X-ray examples show Not applicable. Monochromator corrections are described separately and do not assert neutron polarisation. LATP's facility is SNBL (owner-supplied), its instrument unknown.

The descriptive `_metadata.instrument`, `.facility`, `.dimensionality`, `.purpose`, and neutron-only `.polarisation` tags live in each bundled project record. They are carried through load/save alongside the native metadata fields; they are not new editable core model attributes. `tools/dev/example_metadata.py` builds the app index from those records and the native type/analysis categories, and app-lint checks that the index matches. The native save/reopen/PROJECT text witness gates this persistence. Unknown origins stay unknown.

Purpose tags are green/purple and fitting-mode tags amber, with readable dark-palette variants (owner-selected option A). The owner's refinement keeps `pd`, `neut`, `tof` and `Bragg` blue, with `sg`, `xray`, `cwl`, `Total` and other technique tags neutral grey. Tags have symmetric horizontal padding doubled from the initial design. Workflow symbols distinguish Single, Joint and Sequential without extra hues; the model selects bundled Font Awesome 5 glyphs from the stored enum independently of translated labels. The base's tooltip appears only to expose an actually elided label or clipped tags, respecting the global tooltip preference.

Word tags use sentence case; compact technique codes (`pd`, `neut`, `xray`, `cwl`, `tof`) remain lowercase. The bold identity line uses bundled Noto Sans for the entire title: PT Sans Bold contains some Unicode subscript digits but lacks others, producing visibly mixed weights when fallback fonts are combined.

Purpose badges use the owner's selected bundled Font Awesome 5 symbols: `bullseye` for refinement and `wave-square` for simulation. The paired icon roles are selected from stored purpose values, so translation does not change the symbols.

The app's examples are refinement and simulation examples only (owner, 2026-10-10). A CLI project whose model is exactly
FullProf's, fitted only for its scale or against FullProf's own calculated pattern, records `_metadata.purpose
verification`; it stays in the CLI registry and its checks, and the app does not bundle it. Configuration refuses any
other purpose.
