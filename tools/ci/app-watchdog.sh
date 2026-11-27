#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Prepare and judge the ADR-0102 app traces.
#   app-watchdog.sh                 judge the contract's scenarios on the reduced scan
#   app-watchdog.sh --prepare-only  only collect them, for the app contract on other runs
#   app-watchdog.sh --nightly       also the nightly scenarios (R4), on the owner's full scan archive named by
#                                   EDI_WATCHDOG_ARCHIVE (CI fetches it from a release asset of edi-data)
# Pauses are only reported (ADR-0102, "Where R1 stands"); a missing or invalid trace and a control whose block was not
# seen fail. The traces go to build/app/watchdog for CI upload.
set -euo pipefail
cd "$(dirname "$0")/../.."
mode="${1:-}"
case "$mode" in
    '' | --prepare-only | --nightly) ;;
    *) echo "app-watchdog: unknown option '$mode' (--prepare-only or --nightly)" >&2; exit 2 ;;
esac
out=build/app/watchdog
fixtures=tests/fixtures/ui_responsiveness
if [ ! -x build/app/app/edi_app ]; then
    echo "app-watchdog: build/app/app/edi_app is not built - run 'pixi run -e app app-build' first" >&2
    exit 1
fi
rm -rf "$out"
mkdir -p "$out/inputs"
# The scenario runner imports the fixtures as packages from the repository's root.
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
# The scenario names under the contract's given keys. (Python on Windows ends its line with a carriage return, which
# would stay on the last name.)
contract_names() {
    python -c "import json, sys; c = json.load(open(sys.argv[1])); \
print(' '.join(name for key in sys.argv[2:] for name in c.get(key, {})))" "$fixtures/contract.json" "$@" | tr -d '\r'
}
nightly=
if [ "$mode" = --nightly ]; then
    # Checked before any input is made or any scenario starts; the reduced scan is never a stand-in.
    nightly="$(contract_names nightly_scenarios)"
    if [ -z "$nightly" ]; then
        echo "app-watchdog: --nightly needs the nightly scenarios of $fixtures/contract.json, which lists none" >&2
        exit 1
    fi
    expected="$(python -c "import json, sys; print(json.load(open(sys.argv[1]))['archive_sha256'])" \
        "$fixtures/scan-source.json" | tr -d '\r')"
    asset="the owner's scan archive, the release asset of enhantica/edi-data with SHA-256 $expected,"
    archive="${EDI_WATCHDOG_ARCHIVE:-}"
    if [ -z "$archive" ]; then
        echo "app-watchdog: --nightly needs $asset in EDI_WATCHDOG_ARCHIVE, which is unset" >&2
        exit 1
    fi
    if [ ! -f "$archive" ] || [ ! -r "$archive" ]; then
        echo "app-watchdog: $asset is missing: $archive is not a readable file" >&2
        exit 1
    fi
    actual="$(python -c "import hashlib, sys; print(hashlib.file_digest(open(sys.argv[1], 'rb'), 'sha256').hexdigest())" \
        "$archive" | tr -d '\r')"
    if [ "$actual" != "$expected" ]; then
        echo "app-watchdog: $archive is not $asset its SHA-256 is $actual" >&2
        exit 1
    fi
    input=(--archive "$archive")
else
    input=(--scan "$(python "$fixtures/generate.py" "$out/inputs/scan")")
fi
python -c "import sys; from pathlib import Path; from tests.fixtures.joint_series import ncaf; \
ncaf.prepare(Path(sys.argv[1]), points=100, descent='fast_descent')" "$out/inputs/series"
source tools/ci/app-platform.sh
EDI_CAPTURE_WIDTH=1480 EDI_CAPTURE_HEIGHT=800 app_capture_platform app-watchdog
python "$fixtures/run.py" --app build/app/app/edi_app --output "$out/runs" "${input[@]}" \
    --series "$out/inputs/series"
if [ "$mode" = --prepare-only ]; then
    exit 0
fi
failed=0
# Every scenario the contract declares, listed or dynamic (the every-tab scenario), and on the nightly its nightly ones,
# each with its control: a declared scenario without a trace fails.
scenarios="$(contract_names scenarios dynamic_scenarios) $nightly"
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
