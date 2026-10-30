# 0060. Dictionary-backed reference and parameter context help

- Status: accepted
- Date: 2026-10-30

The existing display bridge (ADR-0051) supplies the GUI vocabulary. The existing ParameterField and ParameterCell context menus already offer a linked item-name button, but their parameter maps supply no URL. Reuse that button and the same menu on Analysis parameter-name right click. Preserve value editing, free toggles and lazy menu creation.

Session accepts only a known dictionary uid, constructs a stable Physics parameter anchor and returns an empty URL for unknown identities. The preview uses the same dictionary export to generate all category and item anchors. A read-only optional CMake tool exports the linked SDK dictionary, including CIF aliases and variant-specific mappings. Documentation records the source and binary hashes; the older library is a design reference, never the authority for current keys.

Experiment tag colours and vocabulary must be shared with documentation through the app's declarative tag registry. Colour supplements visible labels and the experiment's separate type axes. A selector option does not imply every cross-product of options is supported.
