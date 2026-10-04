 fitting-mode inputs come from 's synthetic irregular project.
`generate.py` copies that input, declares each fitting mode, and removes two
background rows and two free flags from `second` to make both the parameter
inventories and free counts unequal. `counts.json` records the independent CIF
declarations using 's diffraction-lib field inventory. The live crysta probe
then removes symmetry-dependent structural declarations. No edi output supplies
the expected counts. Selection tests assert both directions for the source table,
Analysis proxy, status bar and model/rendered Report, with joint invariance.
The experiments are independently named `hrpt` and `second`; no fitted or
calculated value is a correctness oracle. The app tier loads each persisted mode,
changes the shared selector in both directions, and checks the filtering invariant.
Symmetry expectations are computed live by the test-only crysta API probe, from
each committed CLI structure, independently of edi's adapter and app.
