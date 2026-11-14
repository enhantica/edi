# 0083. edi builds crysta's SDK in its own CI

- **Status:** Accepted
- **Date:** 2026-11-10
- **Implementation:** 🟡 Shared production and native consumers implemented; Windows and final consumer qualification pending
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
   library, CLI and the fingerprint manifest) for Linux x86-64, macOS arm64 and Windows x64, archives crysta's source
   at the same commit, and caches both under the exact platform, source and producer-recipe identity described
   below. A complete qualified archive cache hit skips compilation.
   It is the only place edi reads crysta.
3. **Every job uses it.** Each workflow runs the crysta-sdk job first; a consuming job restores the archives with
   `.github/actions/crysta-sdk` and needs no token. `tools/ci/crysta_sdk.py fetch` unpacks the SDK and checks it
   against the environment as before (I25); `tools/ci/crysta-src.sh` unpacks the source for the corpus and reference
   readers, the ThreadSanitizer tree and the web build. Desktop installers, native CLI and Python wheel consume
   that qualified native SDK. The web target compiles the same source with its own Emscripten toolchain and
   compiler cache; native machine code cannot serve that target.
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
- Windows SDK production and its installer consumer use the same archive contract as Unix. Their actual
  platform qualification must pass before the shared candidate ships.

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
original producer/action/publish paths together. Consumer workflows call the shared producer before their
builds. The standalone entry produces SDK artifacts; it does not itself publish or dispatch products.

The owner chose one native SDK variant per platform for desktop, CLI and Python. The existing standalone
builder's separate lean engine compilation is retired: native consumers align link/CRT settings and package
the required accelerated-runtime closure from that SDK. The existing protection against a Python process's
already loaded C++ runtime remains. Target-specific WebAssembly compilation remains necessary. The
packaging implementation and its pending qualification are detailed below.


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


Both native CMake entries resolve an exact bare ccache launcher to an absolute executable
before Windows compiler probes. The activated prefix's Library/bin is an explicit lookup
hint, so a bootstrap child does not depend on ambient PATH finding that executable. Missing
ccache refuses when requested; explicit empty, custom and list launchers retain their meaning.
The rule covers enabled project languages (Crysta C++; Edi C and C++) and preserves Unix
lookup. This keeps the existing cache
owner across the binding bootstrap, SDK and app configurations without changing the backend.

The enabled language launcher variables also join CMake's try-compile platform variables.
Compiler probes run a nested CMake project, which must inherit the chosen resolved, empty,
custom or list value instead of re-importing the original environment default. Real native
compiler configure/probe controls cover this boundary; a successful post-configure Ninja
command alone does not qualify it.


## Check locked ABI packages before cold compilation

Before installing or compiling an uncached SDK, the producer compares every required
ABI package's exact version and build in Crysta's cpp-ci lock with the installer lock.
All three platforms additionally compare Edi's default and app environments. The existing
SDK lock reader and required package inventory own this check. Missing or mismatched packages refuse before bootstrap.
A metadata-only Python setup supplies the reader's declared language version without
updating PATH or Python root hints. Only the check invokes its explicit executable;
Pixi's locked Python remains authoritative for subsequent CMake/binding builds.
The fixed matrix platform is assigned directly inside the check's script. A Windows
compiler environment already contains `Platform`, which collides case-insensitively
with a step environment entry named `PLATFORM`; Bash cannot rely on that uppercase
spelling surviving the runner's merge.

This admission check joins the producer recipe hash. Cache hits still require the
existing independent consumer manifest and binary qualification checks. Neither object
cache reuse nor matching package locks substitutes for executed SDK tests, staged runtime
qualification or source identity. The common doctest interface supplies complete standard
stream types to every test tier; the SDK's initial Ninja build collects independent
compile errors across all existing tiers and the report probe, then refuses on any failure.

Compiler-object restore prefers the exact engine lock and then the same platform's
prior objects. Ccache still checks compiler content and each full compilation input;
the broader object lookup does not admit a qualified SDK or relax package matching.
This preserves reusable objects when an unrelated lock record or compiler selector
package build changes. Complete SDK archive keys remain exact source and recipe.


Failed native SDK qualification retains its raw XML and stdout/stderr observations
in a separate platform/source-named diagnostic artifact after the packer removes
its scratch checkout. Diagnostic artifacts never use the qualified SDK artifact
name, never satisfy consumer transfer, and never populate the qualified archive
cache. The existing successful-output checks and publication gates remain required.


Source receipt append and archive-file extraction use the same Python tarfile helper
in the SDK producer, installer and core/source consumer. Windows drive prefixes must
remain local path operands; shell tar may interpret a drive colon as a remote host.
Git still creates the source archive from the exact pin, the receipt still binds its
Git objects, and extraction uses the SDK reader's data filter. The helper belongs to
the producer recipe identity, so a changed archive policy cannot reuse an older recipe.


## Three-platform Edi native qualification

The `native`, `core` and `cli-python` matrices include Linux x64, macOS arm64 and Windows
x64. Windows is a leg of the same jobs and tasks, not an installer-only substitute for Edi
qualification. Native production runs the same C++ unit/integration binaries and CLI/Python
stream parity check; core and CLI jobs restore the same-run platform artifact and execute the
same declared tests. All three legs use Bash; Windows uses Git for Windows Bash and the
qualified MSVC toolset. Unix shell packages remain target-specific in Pixi. Python's minor
and the Windows CRT/OpenMP package identities match the SDK/installer contract.

The existing installer checkout policy for Windows reserved device filenames also applies to
native and test consumers. Its sparse selection removes only filenames Windows cannot
represent; it does not filter the native test inventory. The matrix/checkout gates compare
all three hosts and the original installer policy, and reject an omitted host or sibling SDK.
Windows executable suffixes and the qualified `.lib` SDK member are resolved explicitly.

Native artifact production validates both shipped CLI version forms: release builds print
`edi <version>` and ordinary builds print `easydiffraction (edi core <version>)`. Both require
a successful process and one complete version line, alongside the existing exact-source
extension and executable checks. This corrects the obsolete release-only expectation without
changing CLI output. Native compiler caches save after an attempted build even when a later
packaging/test check fails, following the existing app and SDK cache policy. SDK archive
cache identity and qualification remain unchanged by these consumer repairs.


The native CLI uses the existing `core/src/windows_sdk.hpp` import boundary for
Windows APIs, including its performance observer build. That wrapper already removes
GDI's `ERROR` macro before it can replace the public fit-status enum. CLI entry points
and transport code share that boundary; direct SDK imports cannot bypass it. The
Windows native compile and the importer census gate this existing portability rule.

The early ABI check now covers installer, root default and app locks on all three
platforms. The former Windows exception applied before the root manifest supported
Windows; it is removed with that support. The selected metadata interpreter runs
the same lock reader for every consumer. Changing this producer recipe invalidates
the qualified archive cache once; compiler object caches remain eligible for reuse.

Installer compiler objects follow the same explicit restore/save boundary as SDK
and native CI builds. A successful restore may save objects after a later build or
qualification failure; cancellation or a failed/skipped restore prevents saving.
The exact platform/toolchain cache key is retained. This does not promote failed
SDK archives, native artifacts or installers into qualified release inputs.

Native test probes must include SDK declarations with their original access specifiers.
MSVC encodes member access in decorated names; an access-keyword macro around an indirect
SDK include can therefore link on ELF while requesting different symbols on Windows.
The internal cache-index probe uses public accessors and needs no such macro. The retained
transaction probe preloads the SDK umbrella before its application-only access injection.
A source census exercises comments, raw strings, continued directives and conditional
preloads, and rejects the committed failing internal-probe preimage. The actual transposed
index exercise remains a required native executable; no SDK exports or package variant change.

Consumer compiler-cache families use the committed root manifest and lock bytes at HEAD.
The working lock may acquire editable-package metadata while Pixi realizes the app environment;
that cannot change the restore/save family within a job. Missing committed inputs refuse
before environment/output files are modified. This groups candidate compiler objects only:
ccache still hashes compiler content and full compilation inputs, and SDK/native artifact
admission retains its independent source, ABI, recipe and qualification checks. Actual helper
subprocess tests exercise local rewrites, real committed changes and missing Git/input proof
for all three runner labels. No SDK qualification recipe changes for this repair.
