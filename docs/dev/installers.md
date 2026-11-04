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
pixi run --manifest-path tools/installer/pixi.toml python "$PWD/tools/installer/build.py" \
  --crysta-source "$PWD/../crysta" --work "$PWD/build/installer"
pixi run --manifest-path tools/installer/pixi.toml python "$PWD/tools/installer/package.py" \
  tools --output "$PWD/build/installer/ifw"
pixi run --manifest-path tools/installer/pixi.toml python "$PWD/tools/installer/package.py" \
  package --stage "$PWD/build/installer/stage" --tools "$PWD/build/installer/ifw/tools" \
  --output "$PWD/build/installer/package"
```

Choose a fresh work/output directory for another build. The package directory's `installer.json` names
the generated installer and zip. Qualify it with:

```sh
pixi run --manifest-path tools/installer/pixi.toml python "$PWD/tools/installer/package.py" test \
  --installer /absolute/path/to/the/installer.run --output build/installer/test
```

This installs into a path with spaces, removes development library paths, verifies installed bytes,
launches the real application with fresh settings, calculates the embedded ECHIDNA example, checks the
bundled assistant executable, captures a window and uninstalls. Catalogues are local fixtures; no login
or model request runs. Linux also checks every bundled ELF dependency. A failed dependency check
remains a failed qualification even if the application itself starts.

## Platform limits

These are development installers, without a signing identity or public release step. macOS uses an
ad-hoc signature and targets arm64; Windows targets x86-64. Linux targets x86-64 and is qualified on
Ubuntu 24.04. The original bundled assistant package's `zsh` helper requires glibc 2.38; an older host
can run the app but cannot qualify that complete upstream runtime. The installer does not replace the
system C library or graphics drivers.

See [ADR-0071](adrs/0071-desktop-installers.md) for the deployment and qualification contract.

## Online qualification and initial testing publication

Each platform first qualifies the offline bundle, then generates an online-only bootstrap and tests
its ZIP against a local file repository. The final installer artifacts contain only that online ZIP.
Development component versions use `0.0.RUN.ATTEMPT`; published calendar releases use their single
release-plan identity instead. Offline candidates remain local qualification inputs.

The manual workflow's `publish_components` input enables initial GitHub Pages publication after every
platform passes. This writes only `repository/testing/<platform>/`, preserving the docs, web app,
other platform repositories and previous immutable component archives. It does not publish a stable
GitHub release. The future download-domain mirror remains disabled until it is populated.
