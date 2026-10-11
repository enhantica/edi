# Legacy project-load regression witnesses

The three small projects are actual saved outputs of sealed Edi b301b6f2 with
SDK a1e0ba6d, before loop rows used ids in fit-state slots. Run `generate.py`
with that producer's pinned Python, matching `lib/edi` wrapper and explicit
`EDI_EXTENSION_DIR`. Inputs come from the committed loop_parameter_ids projects;
start values and uncertainties are assigned closed-form constants. Saved outputs
are regression inputs, never numerical correctness oracles.

Polynomial and Chebyshev saves have one-based numeric row ids and zero-based
persisted fit-state slots: their overlap reproduces the migration collision with
only three terms. The line-segment save is the corresponding positive control.
No owner archive or data is included. The invalid project is only an unsupported
schema declaration. Qt's zip-completion actor packs and unpacks the minimal project through the
production archive boundary, then exercises its request-id load routing. A
malformed archive also supplies the real decoder's message to its frontend
failure event. The browser chooser and JavaScript file-copy step are not run.
