#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# One part of the system tier, for CI's parallel system jobs:
#
#   pixi run system-tests-part <part> [<parts>]      part 1..parts, parts 3 by default
#
# pytest-split assigns every test of tests/system to exactly one part, balancing the parts by the
# recorded durations in $EDI_TEST_DURATIONS (default build/test-durations.json). A test with no
# recorded time counts as the average, so a new test needs no list kept by hand; with no file at
# all the parts are balanced by count. The run writes its own tests' durations to
# build/test-durations-<part>.json and a JUnit report to build/junit-system-<part>.xml, which CI
# keeps as artifacts and merges on main (tools/ci/merge_test_durations.py).
set -euo pipefail
part="${1:?usage: system-tests-part <part> [<parts>]}"
parts="${2:-3}"
case "$part$parts" in *[!0-9]*) echo "system-tests-part: part and parts must be whole numbers" >&2; exit 2 ;; esac
[ "$part" -ge 1 ] && [ "$part" -le "$parts" ] || { echo "system-tests-part: part $part is not in 1..$parts" >&2; exit 2; }
mkdir -p build
recorded="${EDI_TEST_DURATIONS:-build/test-durations.json}"
own="build/test-durations-$part.json"
if [ -f "$recorded" ]; then cp "$recorded" "$own"; else echo '{}' > "$own"; fi
exec python -m pytest tests/system -q \
    --splits "$parts" --group "$part" --splitting-algorithm least_duration \
    --durations-path "$own" --store-durations \
    --junitxml "build/junit-system-$part.xml"
