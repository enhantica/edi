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
