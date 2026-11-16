# 0061. Dictionary-backed parameter reference and context help

- **Status:** Accepted
- **Date:** 2026-10-30
- **Implementation:** ✅ Implemented
- **Priority:** Medium

## Context

The display bridge (ADR-0051) gives the app every parameter name. The parameter field and table cell context menus
already have a button with the parameter's key, but nothing gave it a link. The documentation site needs the same
vocabulary for its parameter reference, and its experiment tags should look like the app's.

## Decision

- `Session.documentationUrl(uid)` returns a link to the parameter's anchor in the documentation's parameter reference,
  only for a uid the dictionary knows; anything else gets an empty URL and a disabled button. The anchor is the uid with
  `.` and `_` replaced by `-`.
- The context menu's key button opens that link. The Analysis table's parameter name opens the same menu on right
  click. Value editing, the free checkbox and lazy menu creation are unchanged.
- `edi_doc_metadata` (an optional build target) prints the linked crysta dictionary as JSON: categories, items, CIF
  names, options and variants. `tools/docs/python-reference.py` lists the Python access path of each item by walking
  the bundled examples. The docs build from these, never from a copied list.
- Experiment tag labels, glyphs and colours live in `app/examples/tags.json`, read by the Examples table and by the
  docs. Colour supplements the label and never replaces it.

## Consequences

- A new dictionary item gets a documentation link without app changes.
- Tag colours change in one file for both the app and the docs.


The native Analysis parameter-icon prefixes now live in app/src/app_info.cpp rather than
a JavaScript constant in ParameterNames.qml. The metadata importer reads that same declared
C++ prefix table, refuses an unrecognized shape, and records that file's hash in its provenance.
The dictionary exporter still reads the actually linked SDK, and Python paths come from the
actual binding and committed category census. Regeneration removes retired native fields from
current reference tables; legacy input fixtures retain their historical vocabulary.
