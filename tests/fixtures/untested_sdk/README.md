# Explicitly untested SDK fixtures

`generate.py` constructs opaque library/CLI/runtime bytes and a hand-written
manifest. Its ABI names follow the existing SDK seam inventory; expected
qualification values are independent inputs, not producer output. The fixture
claims no real compilation or qualification. It isolates the local opt-in,
count, binary-digest and fingerprint checks without downloads or builds.
