# pre-move serialization

`generate_bytes.py --record` captures the save output of the pre-move edi build at
`f3ea7afea400639f2a66d6acb8d922163f1ef128`, and refuses a different model/binding source closure.
`saved-bytes.json` is a **regression pin**, not an independent physics oracle.
The input inventory comes from committed CLI projects and the declared fitting corpus;
each input and each saved file carries its SHA-256. The hidden gate compares the live
inventory as well as the bytes, so an omitted project cannot silently pass.

`generate_stamps.py --source-root <baseline-checkout> --build <baseline-build>`
compiles the public `stamp_routes.hpp` vehicle using that build's recorded compiler,
ABI flags and link libraries. `stamps.tsv` records the observed native parameter routes,
not a theoretical renewal rule. Its three flags are, in crysta, value/attribute/clock;
in edi, value/epoch/unused. The preservation rows explicitly record equality instead.
The hidden gate replays the same routes without regenerating the expected flags.
The vehicle also captures the native holder and collection routes in
`holder_routes.hpp`: assignments (including equal/self), moves, swaps, node
engagement and collection structure changes. Their three flags mean changes in
the explicitly returned `Ticks` tuple for that family; `copy-differs` and
`move-differs` compare the new holder with the source before construction, while
`copy-source` and `move-source` compare the source itself. A zero tuple slot is
unused. These are observations, including unchanged stamps, not stronger promises.
The frozen witnesses retain the Python, cache, undo and scan contracts.

For the byte replay the generator copies the input project and prescribes
`created = 01 Jan 2099 00:00:00` and `last_modified = 01 Jan 2099 00:00:01`
before the real loader runs. The writer advances the latter by one second, as
specified by the existing metadata contract. No output byte is removed or normalised.
Original input hashes are still checked before this clock-controlled replay.

Python observations in `freshness.json` use `generate_freshness.py` with the same
pre-move source closure and imported package check. The small input comes from
`generate_input.py` (committed input, explicit schema-3/background/cutoff
inputs); the scan uses the committed three-frame corpus including all data-file
hashes. These are freshness regression pins, not calculated-value oracles. The
vehicle observes a held geometry window and saved calculated-category presence
before any post-write lazy read. It records crysta's existing read-only measured
setters as refusals; undo is an edi route because crysta exposes no Python undo.

`census_reference.py --source-root <checkout> --repo edi --output <file>`
prepares an independent inventory from Clang's field declarations in `model.hpp`,
including private fields, the loaders/writers' literal dotted tags, and crysta's
`identity_columns()` source table. Qualified header declarations exclude a
same-named type from an included header. The helper never reads the production
schema or census. The counterexamples exercise private fields, an included
same-named type, and a forged schema/census pair.

The binding now reads `data/category-census.json` and invokes the declared
`tools/checks/category_census.py` command against private source copies. It compares
compiler fields with member classifications and schema columns, including computed
payloads, standard containers, private fields and the one-row parameter blocks.
Literal undotted core CIF tags and every production C++ input root are inventoried;
category names assembled without a literal dotted stem remain outside this witness.
The public `edi::OneRow<Category>` witness exercises every declared cell, row-token
copy/assignment, optional engagement and category isolation. Preserved plain fields
retain renewal by changed value; recorded cells retain write-identity renewal.
Complete-census admission remains red while the generated file and loop work are
pending. The four bounded pending-state mutations prove newly named diagnostics;
they do not replace the retained complete-control refusal gates.

The gate-5 byte inventory includes every regular project file, including measured
scan `.dat` files and copied companion files. The expanded capture used the same
pre-move source/build and kept every previously recorded `.edi` hash unchanged.
No output normalisation or extension filter is applied.

R5's `plain-*` holder rows record the old epoch behavior of peak, space-group,
experiment-type, linked-structure, absorption and instrument members.
`plain_dependants.hpp` also captures changed/equal plain writes against the
pre-move engine using the hash-pinned `freshness-input`: its three bits are changes
in experiment computed-currentness, structure geometry-currentness and the
experiment epoch. The baseline includes unchanged dependants, including a
changed optional value whose canonical calculation input stays equal; it never
assumes that every native assignment renews an epoch.

## Retained API witness adaptation

The original public-release archive and its manifest remain unchanged. The receipt
records exact replacements in the geometry freshness vehicle: formatting, a wrapped
comment, and the link from its loaded experiment to the structure it actually creates.
The latter replaces the imported experiment's unrelated structure identity. All
original code tokens, assertion predicates and messages survive, apart from that
single added fixture assignment. The assignment now uses the same `structure` alias
introduced immediately above it; the immutable original and all original code tokens stay bound.

The same receipt names one GUI setup adaptation: before, an immediate check required the
initial calculation to have completed; after, the same currentness predicate is awaited
for at most ten seconds. Its diagnostic uses the public wording. Every subsequent equal-write
assertion and every other GUI byte stays unchanged. The verifier permits exactly that replacement,
and rejects re-pinned changes to its predicate, timeout or diagnostic.
Every other archived witness stays byte-identical.

Run `python tests/fixtures/c34_t28_baseline/api_witness_adaptation.py` to verify the
fixed receipt against the archived original and the live source. The verifier never
generates a pin from current source. The adapted digest is a syntactic regression
receipt, not a scientific correctness reference. The gate additionally exercises
changed predicates/messages, missing or wrong links, and receipt re-pinning attempts.

The public-release fresh-history fixture includes this visible verifier and receipt,
so its independent one-commit replay has the complete declared inputs.

The later LATP project did not exist at the pre-move build. Its separate
`post_feature_fixed_points` record in `saved-bytes.json` contains only hashes of
independently committed source inputs and a second-save fixed-point invariant,
never a fresh save-output pin. Author it with
`python -m tests.fixtures.c34_t28_baseline.generate_bytes --add-fixed-point pd-xray-cwl_latp_scan-4f`.
The inventory admits this one explicit addition and still requires every
historical case. Its save witness proves complete first/second saved inventories
and byte equality, while retaining every input byte.
