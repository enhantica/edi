#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# LLVM source-based coverage over edi's C++ core — the port of crysta's
# tools/ci/cpp-coverage-unit.sh, cut down to what edi's tier actually is.
#
# What the port KEEPS (these are the properties, not the plumbing):
#   * clang -O0 -fprofile-instr-generate -fcoverage-mapping in its OWN side tree, never a
#     shipped or parity-bearing configure;
#   * a run-unique EMPTY profile directory, so a stale profile cannot exist by construction;
#   * an EXPLICIT profile file list into `llvm-profdata merge` — never a glob, because a merge
#     that succeeds on a strict subset is still a successful command;
#   * a report header naming each percentage's own quantity AND denominator, the build, and the
#     reach — the numbers are not comparable to any gcov figure or to crysta's.
# What it DROPS, and why: crysta derives a coverage tier from a committed per-case cost table
# because instrumenting all 112 of its cases is hours-scale. edi has ONE binary and no cost
# table, so there is no subset to derive — the whole tier is instrumented and the totality gate
# collapses to "the one run wrote one profile and exited 0".
#
# REPORT-ONLY: no threshold, matching the Python half (py-cov-report). A gate set from a guess
# either blocks legitimate work or asserts nothing; raises it once cycles are measured.
#
# linux-64 only by construction: clangxx + llvm-tools are declared under
# [target.linux-64.dependencies] in pixi.toml, so this refuses early elsewhere.
set -euo pipefail
cd "$(dirname "$0")/../.."

TREE=build/coverage-unit

for tool in clang clang++ llvm-profdata llvm-cov; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "cpp-coverage-unit: $tool not on PATH — the LLVM coverage toolchain is declared" >&2
        echo "linux-64 only (pixi.toml [target.linux-64.dependencies]); this is not that leg." >&2
        exit 1
    }
done

# I17's hazard, inherited: -O0 instrumented profile counters contend across THREADS inside one
# process. edi's tier is a single process, so the fix is simply to run it single-threaded.
export OMP_NUM_THREADS=1

bash tools/ci/build-crysta.sh
# The prefix build-crysta.sh just populated: a consumer-contract build (CRYSTA_SDK_DIR set)
# installs to build/crysta-consumer-prefix, exactly as core-build.sh selects it, and configures a
# SEPARATE tree so the ordinary and consumer configurations never share a CMake cache
# (configuring against the ordinary prefix compiled the tier against a crysta the consumer build
# never produced).
if [ -n "${CRYSTA_SDK_DIR:-}" ]; then
    CRYSTA_PREFIX="$(pwd)/build/crysta-consumer-prefix"
    TREE="${TREE}-consumer"
else
    CRYSTA_PREFIX="$(pwd)/build/crysta-prefix"
fi
cmake -S . -B "$TREE" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_PREFIX_PATH="$CRYSTA_PREFIX" \
    -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
    -DCMAKE_C_FLAGS='-O0 -fprofile-instr-generate -fcoverage-mapping' \
    -DCMAKE_CXX_FLAGS='-O0 -fprofile-instr-generate -fcoverage-mapping' \
    -DCMAKE_EXE_LINKER_FLAGS='-fprofile-instr-generate'

case_files=$(cat "$TREE/edi_tests_case_files.txt" 2>/dev/null || echo 0)
if [ "${case_files:-0}" -lt 1 ]; then
    echo "cpp-coverage-unit: no edi_tests target — doctest absent, or the tier has no cases" >&2
    echo "(tests/unit/cpp/test_*.cpp). Coverage of an empty tier is not a number worth printing." >&2
    exit 1
fi
cmake --build "$TREE" --target edi_tests -j

# Run-unique EMPTY profile directory: mktemp -d guarantees a fresh dir per run, and old run
# dirs are cleared first so the tree does not accumulate them.
rm -rf "$TREE"/profraw.*
profdir="$(mktemp -d "$TREE/profraw.XXXXXX")"
[ -z "$(ls -A "$profdir")" ] || { echo "cpp-coverage-unit: profile dir not empty — refusing" >&2; exit 1; }

profile="$profdir/edi_tests.profraw"
LLVM_PROFILE_FILE="$profile" "$TREE/core/edi_tests" >"$profdir/run.log" 2>&1 || {
    echo "cpp-coverage-unit: the instrumented run failed — refusing to report coverage of a red tier" >&2
    tail -30 "$profdir/run.log" >&2 || true
    exit 1
}
# The explicit non-empty check keeps its exact spelling — `test_c11_t41_cpp_unit_coverage.py`
# asserts this literal, and the property it is asserting (the port refuses a run that wrote no
# profile) is the right one to hold. The diagnosis goes INSIDE the failure branch: swept from
# crysta's copy, on the failure path only, never as a precondition — as a precondition it broke
# crysta's I17 sandbox tests, which drive that script with a stub binary carrying no profile
# symbols. `grep -c`, never `grep -q`: -q exits on the first match, the reader takes SIGPIPE, and
# under `set -o pipefail` the check fails exactly when the symbol IS present.
[ -s "$profile" ] || {
    _reader=''
    for _candidate in llvm-nm nm; do
        command -v "$_candidate" >/dev/null 2>&1 && _reader="$_candidate" && break
    done
    if [ -n "$_reader" ] &&
        [ "$("$_reader" "$TREE/core/edi_tests" 2>/dev/null | grep -c '__llvm_profile' || true)" -eq 0 ]; then
        echo "cpp-coverage-unit: the binary carries NO __llvm_profile symbols, so it is not" >&2
        echo "instrumented — this is the BUILD, not the tests. Check that clang resolved and that" >&2
        echo "the coverage option reached the compile line; $TREE/CMakeCache.txt records both." >&2
    fi
    echo "cpp-coverage-unit: run exited 0 but wrote no profile — refusing" >&2
    exit 1
}

# Non-vacuity, same check the gate makes: coverage of zero executed cases is not coverage.
ran=$(grep -oE 'test cases: *[0-9]+' "$profdir/run.log" | grep -oE '[0-9]+' | head -1)
if [ "${ran:-0}" -lt 1 ]; then
    echo "cpp-coverage-unit: the run reported ${ran:-no} test cases — nothing was measured" >&2
    exit 1
fi

# The EXPLICIT file argument — never a glob (I17).
llvm-profdata merge -sparse "$profile" -o "$TREE/merged.profdata"

# The declared minimum: read before the report so a missing declaration refuses early.
cpp_lines_min="$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml","rb"))["tool"]["edi"]["coverage"]["cpp_lines_min"])')" || {
    echo "cpp-coverage-unit: pyproject.toml declares no [tool.edi.coverage] cpp_lines_min — refusing to report without its gate" >&2; exit 1; }
report=$(llvm-cov report "$TREE/core/edi_tests" -instr-profile="$TREE/merged.profdata" \
    core/src core/include)

total_line=$(printf '%s\n' "$report" | awk '$1 == "TOTAL"')
regions_total=$(printf '%s\n' "$total_line" | awk '{print $2}')
region_pct=$(printf '%s\n' "$total_line" | awk '{print $4}')
lines_total=$(printf '%s\n' "$total_line" | awk '{print $8}')
line_pct=$(printf '%s\n' "$total_line" | awk '{print $10}')

{
    echo "== edi C++ unit-tier coverage (report-only) =="
    echo "scope: the whole tier — $ran case(s) in the one edi_tests binary; no derived subset exists"
    echo "build: clang -O0 -fprofile-instr-generate -fcoverage-mapping — NOT the shipped Release binary"
    echo "reach: C++ unit-test reach only — says nothing about the Python tier (py-cov-report) or the fits"
    echo "denominator: the whole edi_core static archive is linked into the unit binary, so every"
    echo "  translation unit under core/src contributes whether or not a test reaches it."
    echo "Files linked this run:"
    printf '%s\n' "$report" | awk '$1 ~ /\.(cpp|hpp)$/ {print "    " $1}'
    echo "quantity: llvm-cov line coverage = $line_pct of $lines_total executable lines (core/src + core/include)"
    echo "quantity: llvm-cov region coverage = $region_pct of $regions_total total regions (core/src + core/include)"
    echo "the two quantities have different denominators and are never comparable to any gcov figure"
    echo "gate: line coverage >= ${cpp_lines_min}% (pyproject.toml [tool.edi.coverage] cpp_lines_min, seeded at the measured value)"
    echo "============================================================="
    printf '%s\n' "$report"
} | tee "$TREE/coverage-report.txt"

# The LINE minimum is a GATE, declared once in pyproject.toml. Compared on the number llvm-cov
# printed (two decimals), never re-derived; a missing or malformed declaration refuses rather
# than passing vacuously.
if ! python - "$line_pct" "$cpp_lines_min" <<'PY'
import sys
measured, minimum = sys.argv[1].rstrip('%'), sys.argv[2]
try:
    measured_f, minimum_f = float(measured), float(minimum)
except ValueError:
    print(f"cpp-coverage-unit: cannot compare line coverage {measured!r} against minimum {minimum!r}", file=sys.stderr)
    sys.exit(1)
if measured_f < minimum_f:
    print(f"cpp-coverage-unit: FAIL — line coverage {measured_f:.2f}% is below the declared minimum {minimum_f:.2f}% (pyproject.toml [tool.edi.coverage] cpp_lines_min; fix the tier, never lower the number)", file=sys.stderr)
    sys.exit(1)
print(f"cpp-coverage-unit: line coverage {measured_f:.2f}% >= minimum {minimum_f:.2f}% — gate green")
PY
then exit 1; fi

llvm-cov export "$TREE/core/edi_tests" -instr-profile="$TREE/merged.profdata" \
    -format=lcov core/src core/include >"$TREE/coverage.lcov"
echo "cpp-coverage-unit: lcov export at $TREE/coverage.lcov"
