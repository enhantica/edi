# Fit eligibility witnesses

`inputs.py` authors small projects directly. The cubic witness declares P m -3 m,
whose metric ties the three lengths and fixes the angles. The triclinic witness
leaves all six cell degrees independent. Integrated-reflection inputs declare
intensities; powder inputs additionally declare positions and profile samples.
Unlinked, disabled, measured and data-free variants isolate the fit context.
The expected reasons come from the declared fit-policy contract and these input
relations, independently of either engine's output.

Run `python tests/fixtures/fittability/generate_inputs.py` to regenerate the
visible projects used by the native and real Qt observations.

`saved-main.json` is explicitly a **regression pin from main**, not a scientific
oracle. Its `source_commit` records the engine tree used. `saved_reference.py`
loads the committed project and fixture inventory and freezes each saved file's
SHA-256 under both `iucr_19` and `iucr_99`. It normalizes only the enumerated
wall-clock fields. Inputs refused by main, or carrying a blocked free choice,
are listed in `excluded`. The fitted extinction witness also requires the
constrained crystal radius to carry a nonzero propagated uncertainty.
Regenerate only against the recorded main tree, with the matching built API:
`python tests/fixtures/fittability/saved_reference.py --api <api> --output tests/fixtures/fittability/saved-main.json`.
