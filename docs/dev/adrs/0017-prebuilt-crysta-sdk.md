# 0017. edi consumes crysta as a pinned, prebuilt C++ SDK

- **Status:** Accepted
- **Date:** 2026-09-30
- **Implementation:** 🟡 Partially implemented — unit D builds it (the pin, the SDK download, the update
  workflow, the native artifact); crysta's publish job lands separately
- **Amended:** 2026-10-02 — §1 and §4: a pull-request head's build is published at ship only, and until then a
  paired pin is built from crysta's pull-request run; and §4 again the same
  day: a stale pin is reported by `pin currency` and refused at the final green and the merge, and a
  paired run at a stale pin builds the crysta branch's head
- **Amended:** 2026-10-03 — the forward constraint names the two trees that compile the pinned SDK's source:
  the ThreadSanitizer tree (instrumented) and the WebAssembly builds (another target, ADR-0023)
- **Priority:** High
- **Forward constraint (binding on new features):**
  - No edi path compiles crysta, except a build the native SDK cannot serve, which compiles the pinned SDK's own
    source (`build/crysta-src`) and never a working tree: the ThreadSanitizer tree (ADR-0020 §3) and the
    WebAssembly builds (ADR-0023). A new consumer of crysta's C++ package reads the pinned SDK through
    `tools/ci/build-crysta.sh`.
  - The pin moves only by an update PR merged on CI evidence, or by a paired PR pinning its crysta PR head's build.
  - edi builds only the commit and sha256 its committed pin names, whichever route delivers the bytes (§4).

## Context

edi uses crysta only as a C++ package: `core/CMakeLists.txt` links `crysta::crysta` into `edi_core`, and edi's
Python layer never imports crysta's module. Until now `tools/ci/build-crysta.sh` compiled crysta from source in
every job that needed it, and edi floated on crysta `main`. Two costs followed:

- every CI job paid a crysta build, and a local checkout could link a stale crysta build tree without noticing;
- what edi tested was a crysta tree edi built itself, never the build crysta's own CI had qualified.

The owner adopted the speed-up plan's stage 4 on 2026-09-30.

## Decision

1. **crysta publishes the build it tested.** On every PR and push, each platform's release-configuration job packs a
   C++ SDK from the tree its C++ tier and CLI corpus ran against: headers, a static non-LTO `libcrysta_core.a`, the
   CMake config, the `crysta` CLI and a manifest with the toolchain fingerprint. A `publish` job creates the
   `build-<sha>` prerelease only after every job of the run is green, and only for a push to `main`. A pull-request
   run publishes nothing: its packages stay that run's artifacts, kept 30 days. A pull-request head's build is
   published once, at ship, by crysta's manually dispatched `sdk-publish.yml`, from that head's own run and after
   the same whole-run judgement, so the bytes released are still the bytes tested.
2. **edi pins one build.** `pixi.toml` carries `CRYSTA_SDK_TAG` and `CRYSTA_SDK_SHA256` per platform, under
   `[target.<platform>.activation.env]`. `build-crysta.sh` downloads that asset, verifies its sha256, checks the
   fingerprint against edi's own environment and points `CMAKE_PREFIX_PATH` at it. A pin is one form only: each
   platform's table holds the line `CRYSTA_SDK_TAG = "build-<sha>"`, the pins name one build, and no other line
   mentions the key. `crysta_sdk.py`'s `declared_shas` is that contract. Every reader of the pin refuses any other
   form, so no reader admits a pin another cannot read.
3. **The pin moves by update PR.** An edi workflow pushes a `crysta-sdk/<sha12>` branch that changes only the pin
   lines. A maintainer opens the PR and merges it on CI evidence.
4. **A paired PR pins its crysta PR head's build.** An edi pull request is *paired* when the crysta branch of the
   same name exists and its head has not landed on crysta `main` (landed: an ancestor of `main`, or a tree a `main`
   commit carries). A branch that merely exists pairs nothing: every task workspace creates one. Paired, the current
   pin names that branch's head. The one required `pin currency` job says whether the pin is
   current (paired: the branch head's build; unpaired: a build landed on crysta `main`, or edi `main`'s pin), and no
   job waits for it.

   **A stale pin is reported, and refused at the end**. A task's crysta branch moves with every crysta commit, so
   a job that failed on each of those rows said nothing new and cost a re-pin per crysta commit. Three rules
   replace it:

   - `pin currency` prints a stale pin and the fix, raises a warning on the run and passes. It fails only when the
     pin or the answer cannot be read: an unread answer is never current.
   - A pull-request or dispatched CI run that is paired, and whose pin does not name the crysta branch's head,
     builds that head: the tested package of crysta's pull-request run at it, under every condition of the next
     paragraph except the committed sha256, which a head that is not pinned does not have. So a task's edi runs test
     edi against the crysta they are developed with. One function, `crysta_paired_head` in `crysta-source.sh`,
     answers pairing for the currency check and for the build. A local build and an unpaired run build the pin.
     One run builds one crysta. The job that builds the native artifact finds the paired head, and the artifact
     records the crysta it linked, which must be that job's build (`edi_native.py pack`). A job that restores the
     artifact builds the crysta it linked, so all jobs of a run hold one build even when the crysta branch moves
     under the run, and restore proves that commit is the pin or a commit of the paired branch that crysta `main`
     lacks. The `changes` job's output and the declared-pin line stay the committed pin. Every fetch of an unpinned
     head proves its run again, and an unpacked SDK is reused only when its manifest names that commit, that run
     and that execution.
   - The pin is enforced where it matters. The final CI evidence counts an edi run only when
     the SDK it built is the pin its head derives and the paired crysta pull request's head, whose own run must be
     green; a run that built an unpinned head never counts. The merge guard proves the same at the heads it
     merges, and refuses an unpaired pin that has not landed on crysta `main`. A task re-pins once, at its final
     paired iteration.

   **One pin, two routes to its bytes**. `crysta_sdk.py` takes the pinned build from its release when crysta has
   one. Otherwise it takes the package from crysta's pull-request run at the pinned commit, and uses it only when
   all of these hold: there is exactly one pull-request run of crysta's `ci.yml` at that commit; the latest
   execution of the producing job `checks (<platform>)` succeeded; the package's manifest names that commit, that
   run and that execution; the tarball matches its `.sha256` file and the committed
   `CRYSTA_SDK_SHA256`; and the fingerprint check of §2 passes. Anything else refuses before configure. The route
   never decides which bytes are built: the committed sha256 does. `pixi run crysta-sdk-pin <sha>` reads the sha256
   values from the same two routes, and `crysta_sdk_pin.py --check` is the ship step that refuses a pin whose build
   has no release or differs from it. So a paired task pins a crysta head as soon as that head's two `checks` jobs
   have packed, and nothing is published for a head that never ships.
5. **osx-64 is not built.** edi's platforms are `linux-64` and `osx-arm64`.

**Supersedes** the earlier decision (2026-09-03) that edi floats on crysta `main`.

**Keeps** provenance (the manifest records the source sha, tree and fingerprint) and edi re-releasing with crysta.

## Consequences

- edi stops compiling crysta, which ends the stale-build class.
- A crysta change reaches edi `main` by update PR, not by the next CI run.
- A build any edi `main` commit pins is kept with its tag, so a paired PR-head pin stays buildable after the
  producer's squash merge. That is the one exception to the rule that a pinned foreign commit is reachable from that repository's `main`.
- A paired pin that has no release yet is buildable only while crysta keeps that run's artifacts (30 days). An
  expired artifact refuses and names the repair: re-run the producing job in that run, then re-pin. edi `main` never
  depends on an artifact, because the ship order publishes the release before edi merges.
- edi's CI mints its crysta token with `actions: read` beside `contents: read`. Both are read-only.
- On a desk, a fetch with neither `GITHUB_TOKEN` nor `GH_TOKEN` set asks the GitHub CLI (`gh auth token`) when it
  is installed, and never prints the token; with no token at all it refuses as before. CI has no `gh` and reads its
  environment only.
- The pin lives in `pixi.toml`, not `pixi.lock`: the lock carries no activation environment, so a pin move leaves it
  untouched.
- A conda-channel transport would need a later ADR.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Keep floating on crysta `main` and building from source | Rejected: every job pays the build, and what edi tests is not what crysta qualified. |
| A conda channel for the SDK | Deferred: the release-asset transport needs no channel hosting; a later ADR can move it. |
| Pin in `pixi.lock` | Not possible with release assets: the lock does not carry activation environment. |
| Keep osx-64 | Rejected by the owner, 2026-09-30. |


## Consumer object-cache identity

The prior app key covered compiler/environment/options and the SDK prefix path. Core reused its configured
tree, and the installed-consumer proof always rebuilt fresh. A replacement SDK at the same prefix can carry
older header mtimes, so path/source-stamp identity alone cannot establish object compatibility. The app key now
includes `tools/ci/sdk_content_identity.py`'s deterministic digest of the complete selected prefix's logical
paths and regular-file contents, following installed directory links with cycle/special-file refusal. Core's
ordinary and candidate trees retain an attempt content key and rebuild their generated trees when it changes or
is absent; the standalone consumer remains fresh and records its selected content key. Same-content recovery
reuses generated objects, independently of mtimes. A failed configure/build retains its attempt key so an
unchanged retry can continue. Pinned, candidate and local app-prefix routes all use this one digest; CI still
refuses the local app-prefix override. This is cache invalidation, not a substitute for fingerprint/ABI checks,
qualified SDK provenance, the committed pin or official CI evidence. No SDK/source/fixture is modified.


The successful core build separately writes `.crysta-linked-content` after its build steps complete. The
standalone installed-consumer proof compares its selected prefix digest with that **successful** unit's
content record as well as the existing source-commit records, including explicit extension selection. A
same-source content replacement refuses until that selected edi unit is rebuilt; an attempt marker or a
failed configure/build is not successful content provenance. The standalone helper resolves from the entry's
absolute repository root, preserving invocation from outside the checkout. Existing core/consumer build argv
remain unchanged; the app and explicitly invoked diagnostic builds retain their existing parallel controls.


## Local developer launcher: selected Apple prerequisites

FIRST is tools/dev/app-with-crysta.sh's existing clean-environment local SDK build
and tools/ci/app-build.sh's ordinary app build/identity, documented in local-crysta.
The local launcher now checks selected macOS SDK availability and the selected
Apple C++ tool through xcrun in that SAME clean environment before suppressed Git
metadata, Pixi installation or a build. Original stderr is preserved and failure
stops with manual setup/license instructions. Ready Command Line Tools-only
installations remain valid; no full-Xcode-only probe, automatic sudo/license
acceptance/install, compiler macro workaround or toolchain/flag change is added.
The observed license refusal precedes downstream libc++ NAN/INFINITY errors; it
is not proof of their sole cause. CI refusal remains before this local preflight;
non-Darwin paths, clean allowlist, source/argument isolation, pinned CI/release
SDK and ordinary app build remain as before. Actual Mac recovery requires the
user's ready selected installation and a subsequent genuine build.


## Selected macOS SDK compatibility and coupled compiler family

FIRST is this ADR's version-and-build SDK fingerprint, the app's explicit Mac ABI
package constraints, and the isolated local-crysta launcher. The selected Apple
SDK is also a compiler-header input: the observed SDK27/Clang19 failure remains
after licence acceptance. [FreeCAD's platform declarations](https://github.com/FreeCAD/FreeCAD/blob/main/pixi.toml)
identify the SDK27 math-header protocol and use direct Mac Clang23 drivers.
The Mac proposal therefore selects coherent Clang/libc++23 for both default and
app, removing Mac paths through older cxx-compiler metapackages. Linux compiler
constraints and LLVM22 coverage retain their original meaning; deployment13.4,
scientific source and the released SDK pin do not change.

A family constraint is not ABI evidence. Independently resolve in isolated
worktrees; record real lock package versions/builds and couple every app ABI entry
to the actual tested Mac SDK fingerprint before publication. Existing fingerprint
checks must reject an old SDK incompatible with a new compiler environment; do
not bypass them or relabel old archives. Local paired development rebuilds crysta
and edi with matching environments. A new released SDK/pin needs its ordinary
qualified producer/review route. Preserve original Linux/Windows lock records
and old environments/objects; do not update them as a side effect of a Mac solve.

The SDK27 linker also requires the patched TAPI1600.0.11.8 build4
(`hb561403_4` on arm64), per [upstream fix21](https://github.com/conda-forge/tapi-feedstock/pull/21).
Older builds reject `arm64e.x1` slices in system TBD stubs even with Clang23.
Select the patched reader in the shared Mac dependency table; preserve real
linker/SDK diagnostics and never edit SDK stubs or ignore missing system symbols.

Mac LLVM tools are resolved in the lock to23.1.3 to match Crysta's available clang-tools package,
which constrains that patch. A real attempted23.1.4 solve refused because
clang-tools23.1.4 is unavailable. Keep the existing org parity check and
SDK ABI fingerprint checks; this does not change compiler/header/runtime identities.
No Mac coverage-tools dependency is declared: the existing Linux-only
coverage-tool declaration policy remains in force.
