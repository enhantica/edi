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
Docs updates preserve both `/webapp/` and `/installers/`; a platform repository update preserves docs,
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
