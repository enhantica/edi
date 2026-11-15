# 0089. C++ warnings as errors, clang-tidy and cppcheck

- **Status:** Accepted
- **Date:** 2026-11-15
- **Implementation:** 🟡 Partially implemented — the warning set, `EDI_WERROR` and the two check scripts are in place;
  the existing findings and the CI jobs follow
- **Priority:** High
- **Forward constraint (binding on new features):** new C++ in edi builds without a warning under `EDI_WERROR`, and passes
  clang-tidy and cppcheck; a finding is fixed, or the line names the check it silences and why.

## Context

edi's C++ (the core, the CLI, the Python bindings, the app host and the native assistant adapter) built with the
compiler's default warnings, and nothing ran the `.clang-tidy` file it carries. crysta, which edi links, already builds
its core with a strict warning set as errors and runs clang-tidy and cppcheck in CI, under its ADR "Code quality,
formatting & static analysis (Python + C++)". The owner asked for the same checks on every line of C++ in both products.

## Decision

1. **The warning set is crysta's**: `-Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wold-style-cast
   -Wcast-align -Wnull-dereference -Woverloaded-virtual -Wdouble-promotion`, with `-Wshadow=local` on GCC and `-Wshadow`
   on Clang (`/W4` on MSVC). `cmake/edi_warnings.cmake` puts it on every hand-written C++ source of edi's own
   directories, file by file, so Qt's generated sources, nanobind's sources and the code under `third_party/` keep their
   own warnings, and the hidden test tiers are not touched. Qt, crysta and other packages found through CMake come in as
   system headers. The Python bindings take crysta's base set (`-Wall -Wextra -Wpedantic`), as crysta's bindings do,
   since nanobind's headers are not system headers there. In the code built on Qt (the app host and the assistant
   adapter) GCC's `-Wnull-dereference` is off: GCC reports it after inlining Qt's smart pointers and containers, on paths
   the code has already checked (`if (self.isNull() || ...) return; self->...`). Clang keeps it there, and clang-tidy's
   analyzer checks null dereferences on every path.
2. **`EDI_WERROR=ON` makes each of those warnings an error.** It is off for a local build and on in CI: the build scripts
   (`core-build.sh`, `app-build.sh`, `wasm-build.sh`) pass the `EDI_WERROR` environment variable to CMake.
3. **clang-tidy runs with the Clang Static Analyzer** over the same sources (`pixi run -e cpp-lint cpp-tidy`,
   `tools/ci/cpp-tidy.sh`), with edi's `.clang-tidy`, the curated set crysta's code-quality rules use, and any finding an
   error. A `.clang-tidy` file replaces clang-tidy's default checks, so it names `clang-analyzer-*` itself; its one
   exception, as in crysta, is the opt-in Padding hint, which asks for members in size order and reports layout, never
   a fault. It reads the compile commands of the app's build tree, and the core's tree for the Python bindings.
4. **cppcheck** (`pixi run -e cpp-lint cpp-cppcheck`, `tools/ci/cpp-cppcheck.sh`) checks the same sources for warning,
   performance and portability findings; any finding is an error. It reads the same compile commands as clang-tidy, so
   it sees Qt's and crysta's headers and the build's macros: without them it took Qt's smart pointers for integers and
   reported dozens of findings that are not there. One check is off, with its reason: `returnByReference`, which asks
   Qt-style getters to return their implicitly shared members (`QString`, `QStringList`) by reference, where a copy is
   a reference count.
5. **clang-tidy and clang-format come at one version on every platform**, the one crysta pins, from the `cpp-lint`
   environment that holds only the tools.
6. **A finding is fixed in the code.** Where the code is right and the check cannot see it, the line carries
   `NOLINTNEXTLINE(<check>)` or `cppcheck-suppress <id>` with its reason on the same line; no check is turned off for a
   whole file.

## Consequences

- A conversion, a shadowed name or a null path that a compiler or an analyzer can see is caught before review.
- Every C++ change pays the stricter set; code that converts between Qt's `int`/`qsizetype` and `std::size_t` spells the
  conversion out.
- The checks add CI time: clang-tidy with the analyzer is the slowest of them.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| The warning set on each whole target | Rejected: Qt's generated sources (moc, qmlcachegen, resources) would carry warnings edi cannot fix. |
| A narrower clang-tidy set for edi | Rejected: one curated set for both products keeps the rules the same on both sides of the engine boundary. |
| clang-tidy without the analyzer | Rejected: the analyzer's path-sensitive checks (null dereference, use after move, leaks) are the reason to run it. |
