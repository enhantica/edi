#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Checks that cpp-test.sh stays red when the unit binary exits 0 without a doctest summary, and
# still runs the integration tier after it. The fault is injected through CPP_TEST_FAULT.
set -uo pipefail
cd "$(dirname "$0")/../.."
status=0
out="$(CPP_TEST_FAULT=no-summary bash tools/ci/cpp-test.sh 2>&1)" || status=$?
report() {
    echo "cpp-test-faults: $1" >&2
    tail -20 <<<"$out" >&2
    exit 1
}
if [ "$status" -eq 0 ]; then
    report 'no-summary passed; it must fail'
fi
if ! grep -qF 'edi_tests reported no test cases' <<<"$out"; then
    report 'no-summary failed without its refusal'
fi
if ! grep -qE 'cpp-test: (C\+\+ integration cases green|edi_integration_tests exited)' <<<"$out"; then
    report 'no-summary stopped before the integration tier'
fi
echo "cpp-test-faults: no-summary red, integration tier reported"
