# Declared-model compatibility witnesses

`project.py` and `generate.py` produce declared models and an exact rational
least-squares reference. They import neither numerical engine to choose the
correct values. `cosio_seed_bytes.py` reverses exactly the alias/constraint loop
and Co1/Co2 Biso flag exchange; `ncaf_follower_bytes.py` reverses only the named
NCAF y/z flag removal. Seed gates compare the resulting full blobs to their
retained original identities.

`legacy_start_tied.py` gives the numeric parser cases explicit legacy free
companions. Current NCAF examples keep only x free. Legacy companions are
ignored with the ADR-0078 warning; their recorded optional priors remain readable
and undo restores them. No current example is edited by this helper.

`byte-pins.json` is labelled serialization regression evidence. It retains the
pre-feature hashes and the earlier relation capture. `renew_byte_pins.py` permits
only the NCAF input structure and CoSiO saved structure renewal and preserves all
other hashes and file inventories. Its compiled-extension hash identifies the
capture vehicle; it is never a physical correctness oracle.

Run the visible generators from the edi root with the linked SDK selected:

```sh
PYTHONPATH=. python tests/fixtures/constraint_expressions/renew_byte_pins.py
PYTHONPATH=. python tests/fixtures/constraint_expressions/generate_byte_pins.py
```

The main generator validates inputs against retained content receipts rather
than requiring historical commits to remain reachable. The `model_commit`
strings are provenance only. Regeneration keeps every prior capture.
