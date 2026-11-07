# Tutorial section reference

`outline.json` retains second-level section headings from diffraction-lib's committed
Python tutorial sources. Every entry records its source Git blob and SHA-256; the common
reference commit identifies the tree in which those blobs were found. Material without
an exact reference uses the closest tutorial of the same technique. This checks structure,
not agreement of scientific output or successful execution on Colab.

`bank.py REPOSITORY COMMIT OUTPUT NAME=BLOB ...` regenerates this outline from an
independently supplied checkout. It reads source blobs, not edi notebooks. Section matching
ignores letter case; extra edi sections are allowed, and reference sections keep their order.
A documented structural departure needs an explicit reviewed update to the mapping.

The active notebook publication gate no longer compares these section outlines or requires
the published catalogue to equal this mapping. Structural alignment is deferred to later
tutorial work. These independently captured inputs remain available for that work; the
current gates retain setup declarations, sequential cell ids and cleared outputs for every
published notebook. End-to-end notebook execution remains a separate requirement.
