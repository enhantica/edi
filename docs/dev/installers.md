# Desktop installers

The packaging path builds the C++ crysta library first, links the C++ application, deploys its Qt/QML
runtime, then wraps the result with Qt Installer Framework 4.11.0. Python is a build tool only.
The installed application includes its native assistant runtime and lifetime guard.

The `Desktop installers` workflow runs each platform independently and attaches installers plus the
installation logs, rendered application image and JSON check results. Its source input is an exact
crysta commit. The Windows job uses the pinned official Qt 6.11.2 MSVC kit; Linux and macOS use the
locked app environment. Native compilation uses at most four parallel jobs.

## Local Linux build

Install the packaging tools into a separate Python environment:

```sh
python -m pip install -r tools/installer/requirements.txt
```

From the app environment, build against a crysta checkout:

```sh
pixi run -e app python tools/installer/build.py \
  --crysta-source ../crysta --work build/installer \
  --patchelf /absolute/path/to/patchelf
python tools/installer/package.py tools --output build/installer/ifw
python tools/installer/package.py package \
  --stage build/installer/stage --tools build/installer/ifw/tools \
  --output build/installer/package
```

Choose a fresh work/output directory for another build. The package directory's `installer.json` names
the generated installer and zip. Qualify it with:

```sh
python tools/installer/package.py test \
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
