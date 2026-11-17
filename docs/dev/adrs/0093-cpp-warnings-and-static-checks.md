# 0093. C++ warnings as errors, clang-tidy and cppcheck

- **Status:** Accepted
- **Date:** 2026-11-15
- **Implementation:** ✅ Implemented — the warning set, `EDI_WERROR` in the core and app jobs on Linux and macOS, both
  check scripts and their CI steps; every finding is fixed and the deferred list is empty. Windows (MSVC `/W4`) and the
  WebAssembly build keep `EDI_WERROR` off until their own sweep
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
   (`core-build.sh`, `app-build.sh`, `wasm-build.sh`) pass the `EDI_WERROR` environment variable to CMake. CI sets it
   in the core jobs on Linux, macOS and Windows, where MSVC takes `/W4 /WX`, in the app jobs on Linux and macOS, in the
   WebAssembly app job, and in the `app · Windows` job, which compiles the app with MSVC on every run through the
   Windows installer's own Qt, SDK and compiler settings (`tools/ci/app-windows-build.py`). The Windows installer build
   of a pull request takes it too (`tools/installer/build.py` passes `EDI_WERROR` on).
3. **clang-tidy runs with the Clang Static Analyzer** over the same sources (`pixi run -e cpp-lint cpp-tidy`,
   `tools/ci/cpp-tidy.sh`), any finding an error. edi's `.clang-tidy` holds the groups of crysta's curated set that
   find faults: the analyzer, `bugprone`, `performance` and `cert`, with crysta's exceptions inside them. A
   `.clang-tidy` file replaces clang-tidy's default checks, so it names `clang-analyzer-*` itself; its one exception,
   as in crysta, is the opt-in Padding hint, which asks for members in size order and reports layout, never a fault.
   edi also turns off `performance-enum-size`: most of its enums are Qt's (model roles counted from `Qt::UserRole`,
   `Q_ENUM` types that QML reads), which the meta-object system handles as `int`; `bugprone-empty-catch`, since its
   teardown and optional presentation steps are `noexcept` and drop a failure on purpose; and
   `performance-no-int-to-ptr`, since its Qt table models key rows by small integers. `bugprone-exception-escape` does not
   count `bad_array_new_length` and `length_error`: libc++ throws them only for a size past `max_size()`, a request no
   allocation could meet, and libstdc++ reports that case as `bad_alloc` from `operator new`, which the check does not
   count either, so macOS (libc++) and Linux (libstdc++) are checked alike. crysta's style groups (`readability`, `modernize`, `misc`, `cppcoreguidelines`) follow in a sweep of their own:
   measured over edi's code they hold about 14 000 of the curated set's 15 200 findings, most of them braces around
   one statement, implicit conversions to bool and several declarations on one line. It reads the compile commands of the app's
   build tree, and the core's tree for the Python bindings. The bindings include nanobind's and Python's headers as
   system headers, like Qt's and crysta's, so a finding inside them (nanobind's `noexcept` move wrapper, its list
   caster) is not reported, and every check still runs on the bindings' own code.
4. **cppcheck** (`pixi run -e cpp-lint cpp-cppcheck`, `tools/ci/cpp-cppcheck.sh`) checks the same sources for warning,
   performance and portability findings; any finding is an error. It reads the same compile commands as clang-tidy, so
   it sees Qt's and crysta's headers and the build's macros: without them it took Qt's smart pointers for integers and
   reported dozens of findings that are not there. For the bindings it reads a copy of the core tree's compile
   commands in which nanobind's and Python's headers are ordinary include paths, since it does not read system ones. One check is off, with its reason: `returnByReference`, which asks
   Qt-style getters to return their implicitly shared members (`QString`, `QStringList`) by reference, where a copy is
   a reference count.
5. **clang-tidy and clang-format come at one version on every platform**, the one crysta pins, from the `cpp-lint`
   environment that holds only the tools.
6. **A finding is fixed in the code.** Where the code is right and the check cannot see it, the line carries
   `NOLINTNEXTLINE(<check>)` or `cppcheck-suppress <id>` with its reason on the same line; no check is turned off for a
   whole file.
7. **Files rewritten by a change in flight wait for it.** `tools/ci/static-checks-deferred.txt` lists them; clang-tidy
   and cppcheck skip them, as sources and as headers, until that change lands, when they are swept and the list is
   emptied. Every other file is checked.
8. **Both checks are CI steps of the app job on Linux and macOS** ("clang-tidy with the Clang Static Analyzer (zero
   findings)", "cppcheck (zero findings)"), after the build whose compile commands they read, and after `app-moc` runs moc for every app target: a test runner
   the job does not build still has its sources in those commands, and each includes its own `.moc`. They run after a failed
   step too, so one round lists every finding. They run on Linux and macOS only: their Windows run (the MSVC compile
   commands) and their WebAssembly run follow later, as the owner decided on 2026-11-17, while warnings as errors (2)
   cover every platform.

## Consequences

- A conversion, a shadowed name or a null path that a compiler or an analyzer can see is caught before review.
- Every C++ change pays the stricter set; code that converts between Qt's `int`/`qsizetype` and `std::size_t` spells the
  conversion out.
- The checks add CI time: clang-tidy with the analyzer is the slowest of them.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| The warning set on each whole target | Rejected: Qt's generated sources (moc, qmlcachegen, resources) would carry warnings edi cannot fix. |
| crysta's whole curated set at once | Deferred: its style groups would rewrite nearly every C++ file of edi while other changes are open on them; the groups that find faults go first, the style groups in a sweep of their own. |
| A separate CI job for the checks | Rejected: it would build the app a second time for the compile commands the app job already has. |
| clang-tidy without the analyzer | Rejected: the analyzer's path-sensitive checks (null dereference, use after move, leaks) are the reason to run it. |
