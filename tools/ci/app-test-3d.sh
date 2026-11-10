#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Run the app's drawn Qt Quick Test cases (edi ADR-0017 §16): the tests lane's tst_*_drawn.qml, which need the 3D
# scene, on the capture platform the UI test draws on (tools/ci/app-platform.sh) — Qt Quick 3D draws nothing on
# the offscreen platform the rest of the tier runs on. Linux: Xwayland on headless Weston with Mesa's llvmpipe
# (software OpenGL: its frame times are labelled so and never banked); macOS: cocoa, which needs a logged-in
# window session and refuses naming the session it found. Arguments go to the runner. Refuses when no drawn case
# exists, and each file's run refuses a vacuous result (app-test.sh).
set -euo pipefail
cd "$(dirname "$0")/../.."
# shellcheck source=tools/ci/app-platform.sh
source tools/ci/app-platform.sh
app_capture_platform app-test-3d
echo "app-test-3d: platform ${QT_QPA_PLATFORM:-default}${APP_DISPLAY:+ ($APP_DISPLAY)}"
shopt -s nullglob
files=(tests/unit/app/tst_*_drawn.qml)
if [ "${#files[@]}" -eq 0 ]; then
    echo "app-test-3d: no tests/unit/app/tst_*_drawn.qml - a green run would assert nothing" >&2
    exit 1
fi
status=0
for file in "${files[@]}"; do
    echo "app-test-3d: $file"
    bash tools/ci/app-test.sh -input "$file" "$@" || status=$?
done
exit "$status"
