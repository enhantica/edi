#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# The integration tests whose wiring vectors run on the real app (tests/fixtures/native_ui_script). The core job has no
# app, so there they skip; this runs them on the test runner the app job has just built from the same commit. Without
# that runner it fails rather than skips.
set -euo pipefail
runner=${EDI_APP_TEST_RUNNER:-}
if [ -z "$runner" ] || [ ! -f "$runner" ] || [ ! -x "$runner" ]; then
  echo "native-wiring-tests: EDI_APP_TEST_RUNNER must name the edi_app_tests this job built (got '${runner}')" >&2
  exit 1
fi
files=(
  tests/integration/py/test_scan_app_contract.py
  tests/integration/py/test_scan_extended_contract.py
  tests/integration/py/test_plain_data_picker.py
  tests/integration/py/test_project_load_messages.py
  tests/integration/py/test_reset_and_required.py
  tests/integration/py/test_correlation_app_contract.py
  tests/integration/py/test_correlation_option_bindings.py
  tests/integration/py/test_chart_axis_labels.py
  tests/integration/py/test_multiphase_app_contract.py
  tests/integration/py/test_table_display.py
  tests/integration/py/test_weight_fraction_app.py
  tests/integration/py/test_report_axis_controls.py
  tests/integration/py/test_pattern_background_report.py
  tests/integration/py/test_report_renderer_seams.py
)
for file in "${files[@]}"; do
  if [ ! -f "$file" ]; then
    echo "native-wiring-tests: $file is listed but missing; update this list with the tests that moved" >&2
    exit 1
  fi
done
# The runner must load the wiring fixture before any vector runs. This also loads it from disk once, so the first
# vector does not spend its time limit on a cold start.
if ! QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software "$runner" -input tests/fixtures/native_ui_script/tst_native_script.qml \
  -functions >/dev/null; then
  echo "native-wiring-tests: $runner cannot load tests/fixtures/native_ui_script/tst_native_script.qml" >&2
  exit 1
fi
exec python -m pytest "${files[@]}" -q "$@"
