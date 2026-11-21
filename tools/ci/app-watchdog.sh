#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# The GUI watchdog (ADR-0096): each responsiveness scenario and its control run on the built app with the UI trace on
# (tests/fixtures/ui_responsiveness/run.py), then tools/ci/gui_watchdog.py checks every scenario's GUI-thread gaps: none
# over 100 ms that is not the demo driver's own work, and each control's injected 150 ms block seen. Inputs: the reduced
# scan made from the owner's template (tests/fixtures/ui_responsiveness/generate.py), or the full 43 802-pattern scan
# from the archive EDI_WATCHDOG_ARCHIVE names (the nightly), which the producer checks against its recorded checksum
# before extracting it (--archive); the NCAF five-bank start-5 project; the 100-point synthetic
# series (tests/fixtures/joint_series). EDI_WATCHDOG_REPORT=1 prints without failing, for a baseline. The traces go to
# build/app/watchdog (CI uploads them).
set -euo pipefail
cd "$(dirname "$0")/../.."
out=build/app/watchdog
if [ ! -x build/app/app/edi_app ]; then
    echo "app-watchdog: build/app/app/edi_app is not built - run 'pixi run -e app app-build' first" >&2
    exit 1
fi
rm -rf "$out"
mkdir -p "$out/inputs"
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
report=()
[ "${EDI_WATCHDOG_REPORT:-}" != 1 ] || report=(--report)
failed=0
for scenario in e58-pages e58-banks e58-pattern e58-series; do
    python tools/ci/gui_watchdog.py --trace "$out/runs/$scenario/trace.jsonl" --scenario "$scenario" "${report[@]}" ||
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
