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

The table-display project also carries its fixture helper as a copied asset. After an
intentional helper change, use `PYTHONPATH=. python tests/fixtures/fittability/adapt_saved_pins.py --before-helper <previous-metadata_bytes.py>`. This reproduces the historical helper
hash, requires its saved bytes to equal its current source, and refuses any other
saved path or byte change under either uncertainty rule, using the existing checked
layout projection. The original baseline stays unchanged. A later helper edit must
match the current pin and its existing transition before advancing that transition
to the new asset hash; git retains each earlier endpoint.

The category and text-format adaptation keeps all current and original byte pins
and transition seals unchanged. Its layout adapter must recover their complete
hashes, after the existing clock, unsupported-free and fitted-number checks.
The fitted-value tolerances remain unchanged, and raw saved files are also
checked for current spacing. Verified pre-order EDI bytes supply layout metadata;
quoted descriptions may use the independently checked semicolon spelling with
the same paragraph values. See the project_categories fixture README for the
visible generator and its strict capture requirements.

A copied-helper update now validates every earlier transition in order and appends its new
endpoint. It never rewrites an older transition. The checked stop-rule projection retains
an omitted legacy chi-square value; an explicit Shift/s.u. input must still be written as such.
