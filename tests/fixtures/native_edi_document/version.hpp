#pragma once

// crysta C++ core — the single source of truth (ADR-0002). Qt-free, Python-free;
// the nanobind module and the (future) Qt/QObject adapter are thin, no-logic
// bindings over this library.

namespace crysta {

// Version string of the compiled core. Mirrors the prototype's public surface so
// `import crysta` exposes the same attributes regardless of which implementation
// the active environment installed (ADR-0029).
const char* version() noexcept;
// The git commit the artifact was built from (relay C11-T48, review-15 F1): embedded at build
// time by cmake/build_commit.cmake, so a runtime witness can bind what it measured to a source
// sha.
const char* build_commit() noexcept;

}  // namespace crysta
