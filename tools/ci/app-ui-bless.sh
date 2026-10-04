#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Replace the committed expected images with the last app-ui-test run. Updating the set is a reviewed
# act: commit it with the reason. The set is edi's own output — a regression pin of the edi app, never
# a claim that it matches easydiffractionbeta (that is the design doc's review).
set -euo pipefail
cd "$(dirname "$0")/../.."
expected=docs/dev/design/app-screenshots/edi
actual=build/app/ui-actual
if ! compgen -G "$actual/*.png" > /dev/null || [ ! -f build/app/ui-actual.platform ]; then
    echo "app-ui-bless: no images in $actual - run 'pixi run -e app app-ui-test' first" >&2
    exit 1
fi
mkdir -p "$expected"
rm -f "$expected"/*.png
cp "$actual"/*.png "$expected"/
qt_version=$("${CONDA_PREFIX:?run this in the app pixi environment}/lib/qt6/bin/qtpaths" --qt-version)
cat > "$expected/provenance.yml" <<YAML
# The expected images of the edi app's UI test: edi's OWN output, produced by \`edi_app --demo\` and
# committed as a REGRESSION PIN of the edi app. They catch unintended change; they never assert that
# the look matches easydiffractionbeta v0.9.9 (the side-by-side review in
# docs/dev/design/app-design-inventory.md does that). One set serves every platform, compared by SSIM.
kind: regression-pin
produced_by: edi_app --demo (tools/ci/app-ui-bless.sh)
source_commit: $(git rev-parse HEAD)$( [ -n "$(git status --porcelain -- app core cmake CMakeLists.txt)" ] && echo " (with uncommitted app/core changes)")
platform: $(uname -s) $(uname -m), $(cat build/app/ui-actual.platform)
qt_version: $qt_version
window: 1280x768, device-pixel ratio 1
images: $(ls "$expected"/*.png | wc -l)
YAML
echo "app-ui-bless: $(ls "$expected"/*.png | wc -l) image(s) copied to $expected; commit them with the reason"
