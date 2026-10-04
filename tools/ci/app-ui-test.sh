#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# The UI test (I16): the demo mode walks the page states and saves one image each;
# edi_app_ui_compare compares them with the ONE committed set, by SSIM (a tile below 0.90 or the
# image below 0.98 fails; a missing or differently sized image fails). The images and the similarity
# maps of failures are left in build/app/ui-actual and build/app/ui-diff (CI uploads them).
set -euo pipefail
cd "$(dirname "$0")/../.."
expected=docs/dev/design/app-screenshots/edi
actual=build/app/ui-actual
diff_dir=build/app/ui-diff
for binary in build/app/app/edi_app build/app/app/edi_app_ui_compare; do
    if [ ! -x "$binary" ]; then
        echo "app-ui-test: $binary is not built - run 'pixi run -e app app-build' first" >&2
        exit 1
    fi
done
rm -rf "$actual" "$diff_dir" build/app/ui-actual.platform
source tools/ci/app-platform.sh
app_capture_platform app-ui-test
# What the images were drawn on, for app-ui-bless's provenance.
echo "QT_QPA_PLATFORM=$QT_QPA_PLATFORM${APP_DISPLAY:+ ($APP_DISPLAY)}" > build/app/ui-actual.platform
build/app/app/edi_app --demo "$actual"
build/app/app/edi_app_ui_compare \
    --actual "$actual" --expected "$expected" --diff "$diff_dir"
