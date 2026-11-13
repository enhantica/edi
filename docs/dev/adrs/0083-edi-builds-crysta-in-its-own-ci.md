# 0083. edi builds crysta's SDK in its own CI

- **Status:** Accepted
- **Date:** 2026-11-10
- **Implementation:** 🟡 Partially implemented — Linux and macOS; Windows follows
- **Priority:** High
- **Supersedes:** ADR-0017 (edi consumes crysta as a pinned, prebuilt C++ SDK)
- **Forward constraint (binding on new features):** an edi job or product that needs crysta takes the SDK and
  source of the pinned commit from the crysta-sdk workflow; it neither downloads crysta builds nor clones crysta.

## Context

edi went public, and its release has to be reproducible by anyone who can read crysta's source. Under ADR-0017
crysta's own CI published a `build-<sha>` prerelease per tested commit, and edi pinned one build per platform by
tag and sha256. Every edi job then needed a token that reads crysta's releases, an update workflow moved the pin,
and a paired branch had its own resolution rules. The owner decided on 2026-11-10 that edi's public CI builds crysta
itself, that the builds are attached to the edi release and used by every edi product, and that crysta's headers and
build logs may be public.

## Decision

1. **One pin, a commit.** `pixi.toml`'s `[activation.env]` holds `CRYSTA_COMMIT`, the crysta commit edi builds.
   `pixi run crysta-sdk-pin <sha>` moves it; `--check` proves exactly one well-formed pin.
2. **Built once per commit.** `.github/workflows/crysta-sdk.yml`, a reusable workflow, checks crysta out at the
   pinned commit with the app's read-only token, runs crysta's own `sdk-pack` (build, tests, headers, static
   library, CLI and the fingerprint manifest) for Linux x86-64 and macOS arm64, archives crysta's source at the same
   commit, and keeps both in the Actions cache under `crysta-sdk-<platform>-<sha>`. A cache hit skips the build.
   It is the only place edi reads crysta.
3. **Every job uses it.** Each workflow runs the crysta-sdk job first; a consuming job restores the archives with
   `.github/actions/crysta-sdk` and needs no token. `tools/ci/crysta_sdk.py fetch` unpacks the SDK and checks it
   against the environment as before (I25); `tools/ci/crysta-src.sh` unpacks the source for the corpus and reference
   readers, the ThreadSanitizer tree and the web build. The desktop installers build the pinned commit from that
   source; taking the prebuilt SDK there too follows with the Windows port.
4. **Attached to the release.** The publish job attaches `crysta-sdk-<sha>-<platform>.tar.gz` for each platform to
   the edi release, beside the products built with it.
5. **Retired:** downloading crysta's `build-<sha>` releases and pull-request packages, the crysta-sdk update
   workflow, the pin-currency check and paired-branch resolution.
6. **At a desk** an SDK is packed from a crysta checkout (`pixi run -e cpp-ci sdk-pack <sha> <platform> <dir>`)
   into `CRYSTA_SDK_ARCHIVES`, or used directly with `CRYSTA_SDK_DIR`.

## Consequences

- Building edi needs read access to crysta's source and nothing else of crysta's.
- The first job of a run at a new crysta commit pays crysta's build and tests once per platform; later jobs and
  runs at that commit reuse it.
- crysta's CI no longer has to publish builds for edi; its own tests stay its own.
- Windows has no SDK yet; its release installer currently builds pinned source directly. Completing the
  shared Windows SDK removes that temporary source-build path.

## Alternatives considered

- **Keep crysta's published builds (ADR-0017).** Needs a private token in every edi job and a second release
  process in crysta; rejected for the public repository.
- **Compile crysta inside every job.** No reuse between jobs, and each job would pay crysta's build; rejected.


## Shared production and exact artifact transfer

The producer also has a standalone dispatch entry. Its resolving job records the immutable engine pin and
SDK/source-receipt/setup-action recipe hash before platform jobs queue by that identity. Identical requests serialize
with a non-cancelling multi-entry concurrency queue, then inspect the cache after admission. The archive
cache is versioned and includes platform, engine pin and recipe; changes to the producer or source receipt
cannot reuse an older packing policy. The pin identifies Crysta's compiler lock and packer source.

Every consumer within a workflow downloads that run's uploaded SDK artifact through the existing
crysta-sdk action. A cache eviction after production therefore cannot break inter-job transfer. Release
publication downloads SDK artifacts from the exact qualified installer run already admitted by promote,
rather than asking for whichever matching cache remains. Both cold and warm producers require nonempty
SDK/source/checksum files and verify the archive checksum before an error-on-missing upload. The SDK reader continues its manifest,
qualification, binary hash and ABI checks; archive transfer does not substitute for them. This extends the
original producer/action/publish paths together. Upstream dispatch coordination and Windows packaging
still require completion; the standalone entry alone does not automatically trigger downstream builds.

The owner chose one native SDK variant per platform for desktop, CLI and Python. The existing standalone
builder's separate lean engine compilation is to be retired by aligning link/CRT settings and packaging the
required accelerated-runtime closure. Preserve the existing protection against a Python process's already
loaded C++ runtime. Target-specific WebAssembly compilation remains necessary. These packaging changes
are planned, not implemented by the artifact-transfer change above.


The pinned archive reader additionally binds the extracted manifest's source and platform to the requested
pin/platform before recording its cache marker. A correctly named archive containing another qualified,
self-consistent SDK is refused. Explicit diagnostic SDK-directory checks retain their existing ability to
admit a qualified candidate outside the pin; they are a different, declared input boundary.


## Shared native packaging inputs

The SDK producer qualifies Windows x64 in addition to Linux x64 and macOS arm64. Its Edi checkout
contains the producer recipe and tools; engine tests and corpus come from the exact pinned Crysta
checkout. Excluding Edi docs/tests from that producer checkout also avoids Windows reserved fixture
paths without changing the engine qualification inventory. Windows uses native MSVC inspection,
release DLL CRT, real .lib/.exe paths and the manifest-hashed transitive DLL closure. Unix keeps
its existing accelerated SDK settings. WebAssembly remains a separate target/toolchain.

Installers acquire the SDK against tools/installer/pixi.lock, including its deployment target,
and require the source export's commit to match. Desktop, native CLI and Python wheel link that
same qualified archive; neither installer nor CLI configuration builds Crysta. A newer compatible
macOS deployment target may consume an older SDK minimum; ABI package versions/builds still match
exactly. Imported MSVC packages refuse an older compiler or a different CRT mode.

The standalone dependency inspectors now live in native_runtime.py, shared by CLI and wheel
packaging. The runtime copier accepts only manifest-hashed SDK files, follows ordinary and delayed
dependencies transitively, relocates copies and verifies the extracted closure. It never patches
the SDK itself. Linux links the wheel's C++ runtime statically with hidden symbols as before;
OpenMP and vector math remain enabled. Windows carries its CRT DLLs beside the executable/module.
Actual platform packaging and co-resident Python-runtime checks remain required before shipping.

SDK compilation also restores ccache before installing the producer environment, preserving the
existing binding needed by corpus-policy hooks. The object cache is scoped by platform and actual
engine lock; ccache checks the compiler and full inputs before reuse across source pins. Artifact
cache hits still skip compilation entirely. Installer candidate builds run on an allowed PR merge
ref when it becomes ready, rather than pushing an arbitrary branch into a main/PR-only protected
environment. Main pushes and explicit diagnostic dispatch remain available. No publication input
is enabled by the candidate build.


## Native Edi artifacts within one CI run

The existing edi_native.py transport is brought onto this SDK contract: the committed engine
pin replaces the retired paired-build/tag resolver. The producer binds the actual SDK manifest
and static-library hashes, source commit/tree, lock, Python SOABI, platform, run and workspace.
It refuses source drift before packing. Consumers read those facts independently, verify the
archive and every restored byte/mode, then prove the extension imports from that tree at the
checked-out commit. Restore never falls back to compiling or to another SDK/source.

The native job packs before executing its tests so diagnostic jobs can still inspect the same
artifact after a test failure. Core waits for that producer; existing native/core test selections
are retained. Core, CLI, notebook, docs, system, app bootstrap and browser-reference jobs reuse
the default native build. The app's own Qt host/core configuration and WebAssembly target remain
separate builds; their ABI/worker definitions differ. Compiler caches continue to cover those.

The CLI/wheel dependency verifier retains the first standalone implementation's exact system
allowlist; a system-root prefix or arbitrary API-set spelling is insufficient. The Windows
DLL profile additionally admits the named Universal CRT contracts in [Microsoft KB2999226](https://support.microsoft.com/en-us/servicing/os/windows/2020/04/update-for-universal-c-runtime-in-windows).
Unknown imports must be carried from the qualified SDK or refuse. The Crysta producer applies
the same named UCRT rule, rather than trusting an arbitrary api-ms-win vendor namespace.

Runtime licence collection shares the desktop's existing nearest-package ownership and
locked-archive recovery implementation. CLI/wheel runtime files must all resolve to an actual
locked package, including compiler C++/CRT libraries, and their full notices are included in
the archive/wheel. The installed-wheel checks preserve private Linux C++ symbols, reject a
dynamic libstdc++ dependency, preload the OS C++ runtime, and exercise both real PyZMQ import
orders before calculation. PyZMQ is a locked packaging-test dependency, not a shipped app library.


The pull-request browser compile also restores the shared wasm-cache action, including the
compiler cache. It uses the same toolchain/compiler cache policy as the full browser CI and
Pages build. Changes to that action, browser build scripts or their workflows require the
pull-request multithread build and assistant-exclusion check, even without an assistant source edit.


Object and browser-toolchain caches restore before building and save explicitly after the
attempt, including a later compile or qualification failure. The shared browser action exposes
restore/save operations, and each caller saves only after its restore/setup succeeded. Object
keys distinguish the job's snapshot. Windows SDK bootstrap uses Ninja so CMake's existing
compiler launcher also applies there; MSVC and the release DLL CRT stay unchanged. Qualified
SDK archives still enter their separate cache only after complete qualification and output
checks. A saved object cache never represents a successful test or a qualified SDK.


The SDK producer installs only Crysta's cpp-ci environment, which already includes the genuine
binding and test/numerics dependencies consumed by corpus policy. Installing the default binding
first duplicated that compilation before sdk-pack installed cpp-ci. The existing setup wrapper
therefore accepts an environment selection, defaulting to its previous default for other callers.
This changes bootstrap duplication, not SDK test inventory or corpus-policy admission.


The Windows binding bootstrap selects Ninja through the environment, so Crysta's cpp
activation clears inherited Visual Studio-only platform, toolset and instance defaults for that
selection. The existing explicit -G Ninja SDK/installer calls already override those environment
defaults. Both forms are exercised by real CMake controls. MSVC still selects x64, and SDK
compiler/CRT compatibility checks remain mandatory.
