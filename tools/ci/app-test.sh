#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Run the app's Qt Quick Test tier (tests/unit/app, the tests lane's cases) with the runner `app-build`
# built. No Python and no build at test runtime: the expectations are committed files
# (tests/fixtures/e04_t1/reference and tests/fixtures/e04_t2), read by the runner itself, so the tier
# carries over to a build with no Python (the WASM app, E07); a changed expectation is a reviewed diff.
# Arguments go to the runner (-input, -o, a test function name). Refuses a missing runner, and a
# vacuous run: no case files, or a run that executed no case.
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT="$(pwd)"
runner="${EDI_APP_TEST_RUNNER:-build/app/app/edi_app_tests}"
if [ ! -x "$runner" ]; then
    echo "app-test: $runner is not built - run 'pixi run -e app app-build' first" >&2
    exit 1
fi
if ! compgen -G "tests/unit/app/tst_*.qml" > /dev/null; then
    echo "app-test: no tests/unit/app/tst_*.qml - a green run would assert nothing" >&2
    exit 1
fi
mkdir -p "$ROOT/build/app"
log="$ROOT/build/app/app-test.log"
set +e
"$runner" "$@" 2>&1 | tee "$log"
status=${PIPESTATUS[0]}
set -e
# Non-vacuity from Qt Test's own summary lines ("Totals: P passed, F failed, S skipped, ...").
ran=$(grep -oE '^Totals: [0-9]+ passed, [0-9]+ failed' "$log" | awk '{n += $2 + $4} END {print n + 0}')
if [ "$ran" -lt 1 ]; then
    echo "app-test: the runner executed no case - a green run that asserted nothing" >&2
    exit 1
fi
if [ "$status" -ne 0 ]; then
    echo "app-test: edi_app_tests exited $status" >&2
    exit "$status"
fi
echo "app-test: $ran app case(s) green"
