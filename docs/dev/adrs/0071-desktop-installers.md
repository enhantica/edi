# ADR-0071: Self-contained desktop installers

## Status

Accepted for implementation.

## Context

The native app previously installed only its executable, notices and assistant runtime. It depended on
the developer's Qt installation. The older EasyDiffractionBeta packaged a PySide application with
PyInstaller and Qt Installer Framework, then installed and launched it in CI. Its freezing step and
online update repository do not apply to the C++ application.

## Decision

Use Qt Installer Framework 4.11.0, the latest published release at implementation time, to produce
offline qualification installers, followed by online-only distribution installers. Pin the official tools and their hashes. Build crysta from an explicit
source revision before linking edi. Use Qt's CMake deployment support to collect QML imports, platform
plugins, Qt libraries and runtime dependencies into one staged application. Include the native assistant
runtime, lifetime guard, licences and notices. No Python installation is required on the user's machine.

The installer jobs use one locked Pixi workspace on all platforms. Its Qt and native compiler pins
match the developer app workspace, with an offline gate preventing drift. Host SDKs provide the
platform-specific compiler infrastructure; users of the installed app need no Pixi environment.

Deployment is opt-in (`EDI_DEPLOY_APP`); ordinary developer and WebAssembly builds keep their existing
layout. macOS gets an application bundle; Linux and Windows get a relocatable application directory.
Use a user-writable default installation directory and do not require administrator access.
After offline qualification, publish only the online installer. Initial component repositories use
GitHub Pages under `/repository/testing/<platform>/`. Installers are development artifacts,
without a signing identity or public release step. The Preferences update controls use the installed
maintenance tool; ordinary development and WebAssembly builds do not pretend to support native updates.

Extend the existing independent docs/web-app publisher rather than adding a separate site owner.
Docs updates preserve `/webapp/`, `/repository/` and `/third-party/`; a platform repository update preserves docs,
the web app and other platforms. Only a successfully deployed full-site artifact can become the next
base. The publication jobs share the same concurrency group. Keep previous versioned component
archives for downloads already in flight, reject different bytes under a reused archive identity, and
fail before publishing if the assembled site exceeds GitHub Pages' documented one-GB limit. Initial
tests do not silently prune components still referenced by an older client.

The installed application has a bounded `--testmode <output-directory>` check. It uses fresh settings,
loads an embedded public example into a temporary directory, calculates a finite nonzero pattern with
crysta, starts the bundled assistant executable for its version only, renders the real application
window, writes a screenshot and JSON receipt, and exits. It never logs in or sends a model request.
The packaging check runs with development library paths removed, installs into an isolated path with
spaces, launches the installed application, and uninstalls it. CI uploads zipped installers and the test
receipts for Linux x86-64, Windows x86-64 and macOS arm64 independently.

## Acceptance

- The Linux installer can install, launch, calculate, render and uninstall outside the Pixi environment.
- No runtime dependency resolves into a checkout or build environment; operating-system libraries and
  graphics drivers remain platform prerequisites rather than copied system components.
- Each platform job builds crysta first, deploys edi, creates its installer and exercises the installed app.
- A missing runtime file, failed installation, missing screenshot or failed calculation fails packaging.
- Packaging tests use local fixtures; acquisition of pinned build inputs is separate from those tests.

## Sources

- [Qt Installer Framework 4.11 release](https://www.qt.io/blog/qt-online-installer-and-qt-installer-framework-4.11.0-released)
- [Qt CMake deployment](https://doc.qt.io/qt-6/cmake-deployment.html)
- [Qt QML deployment](https://doc.qt.io/qt-6/qt-generate-deploy-qml-app-script.html)
- [Installer command line](https://doc.qt.io/qtinstallerframework/ifw-cli.html)
- [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- [Earlier installer workflow](https://github.com/easyscience/EasyDiffractionBeta/blob/master/.github/workflows/installer.yml)

## Distribution layout and mirror

GitHub Releases carries the small online installer archives. The generated component repository is a
separate static file tree on GitHub Pages. Keep `repository/<channel>/<platform>/` for installer
metadata and archives, using explicit platform/architecture names. This preserves the older project's
platform separation while distinguishing testing from stable publication.

`data/distribution.json` declares the primary Pages base and `https://download.easydiffraction.org/`
as the future mirror. Both use identical relative paths and immutable archive bytes. The mirror is
preconfigured but disabled in the installer until its content is available, so an empty mirror cannot
block the initial installation. Native update metadata can try the mirror after the primary fails.
The mirror host itself is populated by the owner; no DNS or hosting change is implied.

Keep versioned third-party report libraries under `third-party/`, separate from application repositories.
Preserve the existing pinned vendor files and their integrity hashes. Offline reports continue to embed
those libraries and do not acquire a network dependency merely because a mirror exists.

The initial supported Linux target is Ubuntu 24.04 or newer. Preserve the official helper rather than
building a custom helper or packaging a replacement system C library for older systems.

## Bootstrap dependency qualification

The Linux IFW bootstrap itself links portable X11 and utility libraries, even when its CLI uses the
offscreen platform. Relocate a copy of `installerbase` before the framework appends its payload. Ship
its non-glibc library closure and licence files beside the bootstrap in the download ZIP and inside
the component for the installed maintenance tool. Do not patch an already appended installer or
rely on Pixi paths in the user's environment. The operating system still supplies glibc.

Before compiling the application, CI exercises the real framework with tiny marker components:
unpack the distribution ZIP, install offline, update from a local file repository, uninstall, then
install and uninstall the online bootstrap. This gate qualifies installer transport only. The separate
full application gate still installs the real bundle, calculates and renders with crysta, checks runtime
dependencies, and removes the installation. No test reaches a public component server.

## Preserve upstream runtime bytes through deployment

Qt's application deployment finishes before the verified assistant files are installed. On macOS,
sign owned Mach-O files and bundle containers explicitly, excluding the upstream assistant subtree;
do not recursively re-sign that subtree. Verify the final bundle signature, then require every
assistant member and hash to match the manifest produced from the already verified build input.
Apply the same post-deployment membership and hash gate on all native platforms. A re-signed,
removed, extra or linked helper fails packaging even if it still launches.

Restored CI environments may retain package records without the extracted package-cache licence files.
During build-input acquisition, recover missing licences from the exact conda-forge archive identified
by the installed package's SHA-256. Extract only regular files below `info/licenses`, reject traversal
and linked members, and retain the recovered files beside the acquired installer tools. Packaging and
lifecycle tests then consume these local files without network access. Missing licences still fail.

## Bundle inventory

Write a native bundle inventory after deployment, with regular-file bytes, assistant-runtime bytes,
Qt modules and the largest files. Count link aliases once. Reject deployed native WebEngine, Charts,
Multimedia and test-library families, which this application does not use. Keep Qt Widgets: the native
mathematical text renderer depends on it. Keep the complete verified assistant runtime unchanged;
its size is measured separately so it cannot be mistaken for unnecessary Qt deployment.

After the offline application check passes, qualify the online ZIP using its real component repository
through a local file URL. CI retains only online installer downloads as distribution artifacts. Keep
diagnostics small: logs, receipts, screenshot and dependency inventory, without another copy of the
large offline bootstrap. Publish testing components only on an explicit manual workflow run and only
after all platform checks succeed. Publication shares the docs/web app lock and preserves their content.
Testing component identities use `0.0.RUN.ATTEMPT` to avoid overwriting earlier downloads on a retry;
they are development candidates, not entries in the calendar release history.

Some split conda runtime outputs omit upstream licence texts entirely, rather than merely losing the
cache. Keep checksum-pinned upstream GCC runtime and FreeType notices for the exact installed package
versions and declared licences in `tools/installer/licenses`. An unknown version must acquire its own
notices or fail; it cannot borrow a nearby version's texts. Keep the FreeType acknowledgement alongside
its unchanged upstream notices. Windows environment keys are read without assuming their letter case.

Conda packages can place `info/licenses` in either their info archive or their payload archive. Check
both checksum-verified members while extracting only the licence subtree; do not extract executable
payload files during licence acquisition. Keep MSVC exception semantics when adding UTF-8 compilation
flags rather than replacing them with a source-encoding flag alone.

Each qualification lifecycle gets separate home, cache and real temporary directories. Qt IFW 4.11's
Windows self-removal helper uses a fixed `uninstall.vbs` name in the process temporary directory;
sharing that directory between independent fixture installations can collide while the earlier
helper is still finishing ([upstream implementation](https://github.com/qtproject/installer-framework/blob/4.11/src/libs/installer/packagemanagercore_p.cpp)). Isolation also prevents the online-install check from borrowing warmed
component caches from the earlier update test.

Dependency licence ownership uses the longest matching suffix of the deployed path and the locked
package inventory, refusing ties. A compiler's private copy of a runtime library must not claim the
flat deployed runtime merely because their filenames agree. The existing pinned licence extraction
and missing-notice failures still apply to each selected owner.

The public consumer invokes the engine's exported CMake compiler-check interface with the locked
packaging interpreter and compiler environment. The engine owns its fixture inventory; the consumer
workflow does not cite private source or fixture paths. A missing interface or failed check refuses
the full build.

The Windows source build and its early compiler probes use the same UTF-8, C++ exception and
standard conditional-operator flags (`/utf-8 /EHsc /Zc:ternary`). MSVC 14.44 rejected same-type owner prvalues even with those conformance flags. The engine now
uses direct in-place branch returns while keeping movement deleted. A small native probe checks
the actual public type plus both branch values and copy counts before the full build. The original
failing compiler output is retained; calculation formulas and placeholder data remain intact. [Microsoft conditional-operator conformance](https://learn.microsoft.com/en-us/cpp/build/reference/zc-ternary).

## Native symbol size

Use CMake's Linux install-time stripping for owned executable targets. The development build keeps
its symbols; only the distributed copies lose non-runtime symbols. The measured app executable
retains every allocated section's bytes, address, flags and size, and passes the real calculation
and window smoke after stripping. Qt deployment and the complete verified assistant runtime remain
untouched; the existing final runtime byte/membership gate and actual installed-app checks still
apply. Other platforms keep their existing deployment behavior until separately measured.

Every committed file keeps its exact bytes on checkout (`* -text`), including skills, notices,
vendored scripts and raw data fixtures. Windows automatic newline conversion must not invalidate
checksums or silently alter independent inputs. A real local Git clone with autocrlf enabled checks
an otherwise unlisted future skill, mixed-line-ending data and binary content. Keep upstream licence
bytes unchanged. Installer metadata and its offline fixtures explicitly decode UTF-8 instead
of using the host locale. Native Windows boundary checks run before tools are acquired or builds start.

The ordinary installer-check task delegates to the locked packaging workspace, so it needs no
unrecorded Python package in the app development environment. Compiler failures retain real native
stdout/stderr in pytest diagnostics instead of hiding them behind a subprocess exit code.

Each native installer job also builds the existing assistant lifetime host and executes the recorded
process-family shutdown fixtures against that exact build directory. Sudden owner death, ordinary
retirement and active-stream shutdown must end the guard, runtime child and descendant processes.
The test uses recorded transport, isolated fixture state and no login or network. The ordinary app
test keeps its default build directory; the installer check selects its own real binaries explicitly.
