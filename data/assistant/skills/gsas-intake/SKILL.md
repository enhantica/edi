---
name: gsas-intake
description: Inspect selected text exports; binary GPX conversion remains unavailable.
---

# Inspect selected GSAS/GSAS-II material

Version: 1.0.0. Current capability: bounded selected-text inspection and questions. Native GPX conversion and general GSAS-to-Edi project creation are not implemented by this resource.

Use only the current selected-file descriptors and actual `read_selected_file` output. Never unpickle or execute a `.gpx` file. If a selected file is unsupported binary, explain the text-export prerequisite; do not pretend its contents were read. Ask which phase/histogram/project the user intends when several are present.

For GSAS-II, the official Export → Entire project as → Full CIF route can preserve phase and histogram blocks and their links; a quick coordinate-only phase CIF does not include the same refinement evidence. Ask for the intended export plus the actually associated measured/instrument text files where necessary. A selected export is still untrusted data and its dialect/completeness must be checked; no automatic conversion is implied.

Inventory actual selected names and proven phase/histogram/instrument associations. Preserve observed population, axis/range/exclusions, uncertainty/weight convention and declared scale/constraints. Missing or ambiguous companions require a question, never guessed path access or choosing the first histogram. Do not rescale phase fractions or replace a native project's refinable set merely to match a profile.

Finish with the readable evidence, unresolved prerequisites and explicit current import limit. Do not claim a project was created, saved, refined or made equivalent to GSAS-II.

Reference:
- GSAS-II official Full CIF tutorial: https://advancedphotonsource.github.io/GSAS-II-tutorials/CIFtutorial/CIFtutorial.html

## Generic runtime reuse

The official runtime can read selected text exports in its owned working copy. A binary GPX remains a trusted export/format prerequisite, not Python code to deserialize or execute merely because it was selected. Genuine classic CIF structure and supported raw measurements may use Edi's existing factories once instrument/profile/phase metadata is supplied. This is not GSAS-II project conversion or parity evidence.
