# ADR-0030: Example metadata and filters

Status: accepted (owner's examples table decisions, 2026-10-09).

The prior implementation is `ExampleListModel` in Session and `ExamplesGroup.qml`: it inferred sample and technique from registry IDs and displayed two lines without filters. The CLI registry is an execution contract; presentation facts now live in the app's bundled `examples/metadata.json`, with source paths for each entry. Missing facts remain “Not specified”; simulation purpose is separate from the saved fitting mode. Multi-phase examples name every sample.

The model publishes typed properties and list models, following ADR-0015. Search normalizes Unicode and case and requires every word. A property picker selects the value vocabulary; choosing a new property resets the value to All. Value counts reflect the text search, count each example once, and ignore the selected value. Zero-count choices remain available. Filtering retains registry order and immutable example IDs; clicking a filtered row opens its own ID.

Rows have three lines: samples and instrument/facility; separate coloured tags with slightly rounded corners (option B); descriptive details. Long content elides or clips and is available in a tooltip. Counts appear in the value picker only. Users clear text or select All; there is no separate reset button or results counter. This extends the Analysis filter presentation while retaining the examples-specific dependent value picker.

Configuration requires metadata for every bundled example. Metadata axes come from the saved experiment and analysis files; curated samples and origins supplement those files, without adding guessed dimensions or polarisation. Public `tst_example_filters.qml` exercises source membership, normalized search, facets, unknown facts, multiple samples and opening after filtering.
