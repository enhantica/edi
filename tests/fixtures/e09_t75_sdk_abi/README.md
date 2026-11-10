# SDK ABI reference

`producer-lock.json` records the independent `cpp-ci` packages from crysta's
committed lock at the pinned SDK source, with its retained build tag, commit,
lock path and byte digest. Edi CI has no
sibling checkout; its app-lock gate compares against these recorded producer
rows. The SDK consumption gates separately check the actual downloaded SDK's
fingerprint against each consumer environment.

Regenerate through the visible writer, with an independent crysta checkout
carrying the source commit of edi's pinned SDK:

```sh
python tests/fixtures/e09_t75_sdk_abi/generate.py /path/to/crysta --sdk-tag build-<full-sha>
```

The writer reads the producer's committed `pixi.lock`, never edi's lock or package
output. The gate still compares every ABI package exactly. The retained build tag
provides provenance for paired SDK builds before the producer's main advances.
Compatible SDK pin updates do not require changing this frozen ABI reference;
the existing SDK consumption gates qualify the actual SDK against its consumers.
For a paired SDK update, `--ref <pinned-producer-commit>` also records the exact
committed producer lock. The SDK's retained `build-<commit>` tag keeps this source
resolvable after merge (edi ADR-0017). With neither option, the writer records
`origin/main:pixi.lock`.
