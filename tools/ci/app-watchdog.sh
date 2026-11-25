#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Prepare the ADR-0102 app traces. The nightly run reports ordinary GUI gaps, refuses
# invalid traces and verifies the deliberate blocks. --prepare-only supplies the app contract on
# other runs. EDI_WATCHDOG_ARCHIVE selects the checksummed full owner scan.
# The traces go to build/app/watchdog for CI upload.
set -euo pipefail
cd "$(dirname "$0")/../.."
out=build/app/watchdog
if [ ! -x build/app/app/edi_app ]; then
    echo "app-watchdog: build/app/app/edi_app is not built - run 'pixi run -e app app-build' first" >&2
    exit 1
fi
rm -rf "$out"
mkdir -p "$out/inputs"
# The scenario runner imports the fixtures as packages from the repository's root.
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
if [ -n "${EDI_WATCHDOG_ARCHIVE:-}" ]; then
    input=(--archive "$EDI_WATCHDOG_ARCHIVE")
else
    input=(--scan "$(python tests/fixtures/ui_responsiveness/generate.py "$out/inputs/scan")")
fi
python -c "import sys; from pathlib import Path; from tests.fixtures.joint_series import ncaf; \
ncaf.prepare(Path(sys.argv[1]), points=100, descent='fast_descent')" "$out/inputs/series"
source tools/ci/app-platform.sh
EDI_CAPTURE_WIDTH=1480 EDI_CAPTURE_HEIGHT=800 app_capture_platform app-watchdog
python tests/fixtures/ui_responsiveness/run.py --app build/app/app/edi_app --output "$out/runs" "${input[@]}" \
    --series "$out/inputs/series"
if [ "${1:-}" = --prepare-only ]; then
    exit 0
fi
failed=0
# Every scenario the contract declares, listed or dynamic (the every-tab scenario), with its control: each produced run
# is judged.
# (Python on Windows ends its line with a carriage return, which would stay on the last name.)
scenarios="$(python -c "import json; c = json.load(open('tests/fixtures/ui_responsiveness/contract.json')); \
print(' '.join([*c['scenarios'], *c.get('dynamic_scenarios', {})]))" | tr -d '\r')"
for scenario in $scenarios; do
    python tools/ci/gui_watchdog.py --trace "$out/runs/$scenario/trace.jsonl" --scenario "$scenario" --report ||
        failed=1
    # The control must hold its block and fail on it: a check that passes it cannot see a blocked GUI thread. Exit 1
    # also means a refused trace, so only the checker's own line for a seen block counts.
    set +e
    seen="$(python tools/ci/gui_watchdog.py --trace "$out/runs/$scenario-control/trace.jsonl" --scenario "$scenario" \
        --control)"
    status=$?
    set -e
    printf '%s\n' "$seen"
    if [ "$status" -ne 1 ] || ! grep -qx "gui_watchdog: $scenario: the control block was seen" <<<"$seen"; then
        echo "app-watchdog: $scenario's control ended with status $status without its block seen over the limit" >&2
        failed=1
    fi
done
exit "$failed"
