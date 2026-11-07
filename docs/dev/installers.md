# Desktop installers

The packaging path builds the C++ crysta library first, links the C++ application, deploys its Qt/QML
runtime, then wraps the result with Qt Installer Framework 4.11.0. Python is a build tool only.
The installed application includes its native assistant runtime and lifetime guard.

The `Desktop installers` workflow runs each platform independently and attaches installers plus the
installation logs, rendered application image and JSON check results. Its source input is an exact
crysta commit. All platform jobs use the locked workspace in `tools/installer/pixi.toml`. Its Qt and compiler pins
match the app workspace and are checked by `installer-check`. Host SDKs supply MSVC/Windows SDK
and Xcode; portable build/runtime libraries come from Pixi. Native compilation uses at most four jobs.


## Local Linux build

Install the locked toolchain, then build against a crysta checkout:

```sh
pixi install --frozen --manifest-path tools/installer/pixi.toml
pixi run --manifest-path tools/installer/pixi.toml python "$PWD/tools/installer/package.py" \
  tools --output "$PWD/build/installer/ifw"
pixi run --manifest-path tools/installer/pixi.toml python "$PWD/tools/installer/protocol_check.py" \
  --tools "$PWD/build/installer/ifw/tools" --output "$PWD/build/installer/protocol"
pixi run --manifest-path tools/installer/pixi.toml python "$PWD/tools/installer/build.py" \
  --check-compiler --crysta-source "$PWD/../crysta" --work "$PWD/build/installer"
pixi run --manifest-path tools/installer/pixi.toml python "$PWD/tools/installer/build.py" \
  --crysta-source "$PWD/../crysta" --work "$PWD/build/installer"
pixi run --manifest-path tools/installer/pixi.toml python "$PWD/tools/installer/package.py" \
  package --stage "$PWD/build/installer/stage" --tools "$PWD/build/installer/ifw/tools" \
  --output "$PWD/build/installer/package"
```

Choose a fresh work/output directory for another build. The package directory's `installer.json` names
the generated installer and zip. Qualify it with:

```sh
pixi run --manifest-path tools/installer/pixi.toml python "$PWD/tools/installer/package.py" test \
  --installer /absolute/path/to/the/installer.zip --output build/installer/test
```

This installs into a path with spaces, removes development library paths, verifies installed bytes,
launches the real application with fresh settings, calculates the embedded ECHIDNA example, checks the
bundled assistant executable, captures a window and uninstalls. Catalogues are local fixtures; no login
or model request runs. Linux also checks every bundled ELF dependency. A failed dependency check
remains a failed qualification even if the application itself starts.

## Platform limits

These are development installers, without a signing identity or public release step. macOS uses an
ad-hoc signature and targets arm64; Windows targets x86-64. Linux targets x86-64 and is qualified on
Ubuntu 24.04. The original bundled assistant package's `zsh` helper requires glibc 2.38; an app-only smoke on an older host
does not qualify that complete upstream runtime. The installer does not replace the
system C library or graphics drivers.

See [ADR-0071](adrs/0071-desktop-installers.md) for the deployment and qualification contract.

## Online qualification and initial testing publication

Each platform first qualifies the offline bundle, then generates an online-only bootstrap and tests
its ZIP against a local file repository. The final installer artifacts contain only that online ZIP.
Development component versions use `0.0.RUN.ATTEMPT`; published calendar releases use their single
release-plan identity instead. Offline candidates remain local qualification inputs.

For a testing prerelease, manually run **Desktop installers** with
`prepare_preview_release` enabled. CI selects the next version, qualifies all three
installers, and attaches the online ZIPs to a GitHub prerelease draft. A
maintainer reviews and publishes the draft.

Enable `publish_components` to deploy the qualified component repositories
under `repository/testing/<platform>/` and refresh the testing update feed.
This can run alongside draft creation. To deploy later, run **Desktop
installers** with `publish_components` enabled and set `preview_run` to the
calendar preview's installer run ID. CI reuses the qualified files. Publish
the draft after the matching components are available.

## Standalone CLI archives

Versioned desktop qualification also builds `edi` for each platform from the
same source and engine commit. This separate build links the static engine and
uses the engine's standard thread pool and scalar math to avoid shipping
OpenMP or vector math libraries. On Windows it uses the static C++ runtime.
It excludes Qt, Python bindings and the assistant.

CI unpacks each CLI ZIP, verifies its platform dependencies and embedded
release version, and refines a fixture project with the extracted executable.
Release promotion checks the ZIP checksum and qualification receipt. The
CLI ZIPs are separate GitHub assets and require no Pages component repository.

## Calendar release and update notes

The version is `YYYY.MM.SEQUENCE`, starting at zero each month. Merged PR titles describe the user
outcome and become the release notes. Exactly one existing scope label groups a PR into Added,
Fixed or Changed; the label does not select a semantic-version increment.

Use these workflows after the release source has merged to main:

1. Run **Prepare calendar release** on main. Inspect its prepared version, complete history and notes.
2. Run **Desktop installers** at that same source with `release_plan_run` set to the preparation run
   ID and `crysta_commit` set to the complete engine source commit. Leave `publish_components` off.
   All platforms must finish their offline/online installation, calculation, rendering, dependency
   and assistant-lifetime checks. Downloadable artifacts are online ZIPs; offline packages are
   qualification inputs.
3. Run **Publish qualified calendar release** on main with `installer_run` set to that successful
   qualification run. It promotes the exact artifact IDs without rebuilding, stages a matching GitHub
   draft, deploys component repositories and their history feed, then publishes the verified assets.

The installed app and its notes must match the prepared source/version/history. A failed job, expired
artifact, mixed retry attempt, changed archive or stale release plan stops promotion. Rerun all native
jobs for a new qualification attempt; retain earlier diagnostics. A publication retry reuses the same
qualified files and matching draft, without replacing a published identity.

The history feed and bundled notes share one source. Managed calendar installations check availability
independently of optional update notifications. The red Update button follows the existing unsaved-work
guard and starts the maintenance tool. On the updated app's next launch, What's new includes every
release since the user's previous version. Ordinary developer builds retain their git version.

## Python preview distribution

Each versioned native build also produces a CPython 3.12+ stable-ABI wheel.
The wheel uses the same release version and native engine as the standalone
CLI and includes the JavaScript needed for offline reports. Qualification
installs the wheel in a fresh virtual environment without a package index,
then checks the import, command line, refinement and offline report.

The preview and stable GitHub release jobs attach the qualified wheels as
individual assets. The docs build generates a static Simple API index from
published GitHub release assets, linking the original wheels by SHA-256.
See the Python setup page for the Pixi and pip routes.
