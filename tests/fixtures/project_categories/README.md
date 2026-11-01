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
