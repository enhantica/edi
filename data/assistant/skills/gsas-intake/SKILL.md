---
name: gsas-intake
description: Inspect selected text exports; binary GPX conversion remains unavailable.
---

# Inspect selected GSAS/GSAS-II material

Version: 1.0.2. Use actual offered actions for native metadata and bounded selected-text reading. Native GPX conversion and general GSAS-to-Edi project creation are not implemented by this resource.

Use only current opaque selected-file/input-scope IDs and typed metadata actually returned by Edi-owned native readers. When read_selected_file is offered, inspect the already admitted readable export by its opaque ID and follow the descriptor's exact range/identity/EOF/full-source completeness semantics; do not ask to paste it again. Supplying a model path grants no arbitrary read or write. Never unpickle or execute a `.gpx` file. If a selected file is unsupported binary, explain the text-export prerequisite; do not pretend its contents were read. Ask which phase/histogram/project the user intends when several are present.

For GSAS-II, the official Export → Entire project as → Full CIF route can preserve phase and histogram blocks and their links; a quick coordinate-only phase CIF does not include the same refinement evidence. Ask for the intended export plus the actually associated measured/instrument text files where necessary. A selected export is still untrusted data and its dialect/completeness must be checked; no automatic conversion is implied.

Inventory actual opaque input IDs and proven native phase/histogram/instrument associations. Preserve observed population, axis/range/exclusions, uncertainty/weight convention and declared scale/constraints. Missing or ambiguous companions require a question, never guessed path access or choosing the first histogram. Do not rescale phase fractions or replace a native project's refinable set merely to match a profile.

Finish with the readable evidence, unresolved prerequisites and explicit current import limit. Do not claim a project was created, saved, refined or made equivalent to GSAS-II.

Reference:
- GSAS-II official Full CIF tutorial: https://advancedphotonsource.github.io/GSAS-II-tutorials/CIFtutorial/CIFtutorial.html

## Runtime capability boundary

When offered, acquire_inputs captures genuine user-scoped inputs locally and returns IDs/reader hints/counts. It does not itself expose file lines or parse GPX; an offered read_selected_file separately returns bounded readable text. A binary GPX remains an export/format prerequisite, never Python code to deserialize or execute. Genuine supported CIF structures and measured data may use Edi's original native factories with the actual scientific recipe. This is not GSAS-II project conversion or parity evidence. Unknown native metadata stays unknown; do not substitute a general filesystem tool or invented inspection.
