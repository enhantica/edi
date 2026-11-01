# Historical category layouts

These fixtures permit the category placement and separator changes of ADR-0102
item 11 while retaining every original output byte or SHA-256 pin. Scalar item
order within a category, loop columns and rows, values, comments and multiline
payloads stay unchanged. Non-EDI files remain opaque. A projection succeeds only
if it recovers the exact historical file hash; otherwise the caller sees the
original mismatching bytes or hash.

`generate_layouts.py SOURCE --revision SHA` captures layout metadata from the
committed crysta layout reference and the immutable local fixture files/archives.
The JSON records its source revision and hash. It contains no replacement
scientific values or output digests. Current raw spacing, dictionary order and
second-save fixed points are checked separately.

The fittability corpus additionally records ADR-0102 item 12's description
spelling. The generator independently checks paragraph equality and the 80-column
semicolon format against verified old bytes. It also permits the single recorded
blank separator before an otherwise unchanged legacy comment. These exact unit
transitions are keyed by the original complete file hash. At runtime the current
unit must match the recorded spelling exactly, and the final reconstructed file
still has to recover the original hash. Changed words, values or comments fail.

To extend these records, run `python -m tests.fixtures.project_categories.generate_layouts --fittability-pinned-files DIR --observed-saves DIR`. Every old EDI document must
reproduce a frozen saved-file digest, and every required digest must be present.
The observed directory follows `projects/<inventory-index>/<rule>/saved` and
`fit_projects/<inventory-index>/<rule>/saved`. Original layouts and source
provenance are retained. A verified hash-to-layout index avoids a linear search;
it changes lookup order, not the complete-digest acceptance rule.
