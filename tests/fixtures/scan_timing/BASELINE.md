# Scan timing baseline

The comparison measures the change from the branch’s fork point, including the
engine build that fork point declares. It does not include earlier main changes
in the candidate’s cost.

Derived on 2026-10-17 in this repository:

```text
git merge-base 13db9866fc1000dc8e87e1bac8d7d7985ec62652 origin/main
a341b98154b53ea2499213a6c60b87e1371e9ce8

git rev-parse origin/main
a341b98154b53ea2499213a6c60b87e1371e9ce8

git rev-parse a341b981:pixi.toml
06e36550e650db7c956a6212cb62261552f63854
```

The canonical `tools/ci/crysta_sdk.py` reader applied to
`git show a341b981:pixi.toml` returns
`c2b02623e0b8354cec2dcfaeb2939645486c0dca` for both platforms.
The validator freezes these full source IDs so future main advances and squash
merges do not silently move the reference. A fresh baseline measurement must
compile that EDI source with that declared SDK. The receipt retains the observed
compiled source identities; old observations cannot be relabelled.

Before this adaptation the validator selected EDI
`2e04556fa042bf15028f20d8452356c90fa29c99` and crysta `fb153aeb` by prefix.
That reference belongs to the earlier correlation-performance restoration.
The independent paired-app oracle retains that historical obligation; its
receipt format and purpose differ from this scan-timing comparison.

The bound, complete-work requirements, actual Release configurations, alternating
runs, negative controls, interval definitions and current-source witness are
unchanged.
