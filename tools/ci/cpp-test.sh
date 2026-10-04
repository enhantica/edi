#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Edi's C++ unit gate — the one doctest binary, built in core-build's tree.
#
# The crysta precedent (tools/ci/cpp-test.sh there) shards a 112-case suite off a committed
# cost table. edi's tier is ONE binary with no cost table and no derivation, so this is the
# proportionate port: configure, build the EXCLUDE_FROM_ALL target, run it once. Sharding
# arrives here if and when the case count makes it pay, not before.
#
# This is the ONE script the pixi task and any CI surface invoke, so the surfaces cannot
# diverge (the crysta _lto_correctness.sh discipline).
#
# Fails closed, and the two refusals below are the point: a C++ tier that reports success
# because it has no cases, or because doctest is missing from the env, asserts nothing.
set -euo pipefail
cd "$(dirname "$0")/../.."

# The tier runs in core-build's own tree — build/ci, or build/ci-consumer for a candidate SDK — whose
# configure is identical to the separate build/tests this used to configure. The edi_tests target is built
# there by core-build, under its producer lock; a consumer job instead restores the tree `native ·
# <platform>` built once (EDI_NATIVE_ARTIFACT=1) and configures nothing.
if [ -n "${CRYSTA_SDK_DIR:-}" ]; then TREE=build/ci-consumer; else TREE=build/ci; fi
EDI_CORE_TARGETS=edi_tests bash tools/ci/core-build.sh

# The target is defined only when doctest resolves AND tests/unit/cpp/test_*.cpp is non-empty
# (core/CMakeLists.txt). Absent either, the tier cannot assert anything — refuse loudly rather
# than exit 0 on a vacuous run.
case_files=$(cat "$TREE/edi_tests_case_files.txt" 2>/dev/null || echo 0)
if [ "${case_files:-0}" -lt 1 ]; then
    echo "cpp-test: no edi_tests target — either doctest is absent from the env or the tier" >&2
    echo "has no cases (tests/unit/cpp/test_*.cpp). An empty C++ tier is a refusal, not a pass." >&2
    exit 1
fi

log="$TREE/edi_tests.log"
status=0
"$TREE/core/edi_tests" >"$log" 2>&1 || status=$?
cat "$log"
if [ "$status" -ne 0 ]; then
    echo "cpp-test: edi_tests exited $status" >&2
    exit "$status"
fi

# Non-vacuity: doctest exits 0 on "no test cases ran", so the reported count is what proves
# the binary did work. Parsed from doctest's own summary line.
ran=$(grep -oE 'test cases: *[0-9]+' "$log" | grep -oE '[0-9]+' | head -1)
if [ "${ran:-0}" -lt 1 ]; then
    echo "cpp-test: edi_tests reported ${ran:-no} test cases — a green run that asserted nothing" >&2
    exit 1
fi
echo "cpp-test: $ran C++ unit case(s) green"
