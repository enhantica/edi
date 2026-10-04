#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Pack the web app's site (edi ADR-0023): both wasm builds (tools/ci/wasm-build.sh), the start page, the
# service-worker shim, the README naming the hosting requirement and the licence texts, into build/wasm/site
# and one archive, build/wasm/edi-webapp.zip, laid out to be unpacked as the site's folder
# (`enhantica.github.io/edi/webapp/`). Prints each build's size.
#
# Each build goes into a folder named by a hash of its files (`multithread-<hash>/`), and build.json names the two
# folders; the start page reads build.json past every cache. So a redeploy never pairs one build's script with
# another's module, whatever the host or the browser caches (the owner's LinkError, 2026-10-03), and a pair whose
# script and module come from different links is refused here (tools/ci/wasm_import_check.mjs).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
# shellcheck source=tools/ci/wasm-env.sh
. "$ROOT/tools/ci/wasm-env.sh"
OUT="$ROOT/build/wasm"
SITE="$OUT/site"
rm -rf "$SITE" "$OUT/edi-webapp.zip"
mkdir -p "$SITE"
{
  echo "EasyDiffraction web app"
  echo "edi: $(git describe --tags --always --dirty 2>/dev/null || echo unknown)"
  echo "Qt: $EDI_WASM_QT (wasm_multithread, wasm_singlethread); Emscripten: $EDI_WASM_EMSDK"
} >"$SITE/BUILD-INFO.txt"
NODE="$(ls "$EDI_WASM_TOOLCHAIN/emsdk-$EDI_WASM_EMSDK"/node/*/bin/node 2>/dev/null | head -n 1)"
[ -x "$NODE" ] || { echo "wasm-pack: no Node.js in the Emscripten toolchain — run: pixi run -e app wasm-toolchain" >&2; exit 1; }
for build in multithread singlethread; do
  app="$OUT/$build/app/app"
  for file in edi_app.js edi_app.wasm qtloader.js CRYSTA_SOURCE_SHA; do
    [ -f "$app/$file" ] || { echo "wasm-pack: $app/$file is missing — run: pixi run -e app wasm-build $build" >&2; exit 1; }
  done
  "$NODE" tools/ci/wasm_import_check.mjs "$app"
  hash="$(cat "$app/edi_app.js" "$app/edi_app.wasm" "$app/qtloader.js" | sha256sum | cut -c1-12)"
  folder="$build-$hash"
  mkdir -p "$SITE/$folder"
  cp "$app/edi_app.js" "$app/edi_app.wasm" "$app/qtloader.js" "$SITE/$folder/"
  printf -v "folder_$build" '%s' "$folder"
  raw=$(wc -c <"$app/edi_app.wasm")
  gz=$(gzip -9 -c "$app/edi_app.wasm" | wc -c)
  echo "$build ($folder/): crysta $(cat "$app/CRYSTA_SOURCE_SHA"); edi_app.wasm $raw bytes ($gz gzip -9)" >>"$SITE/BUILD-INFO.txt"
done
printf '{"multithread": "%s", "singlethread": "%s"}\n' "$folder_multithread" "$folder_singlethread" >"$SITE/build.json"
cp app/web/index.html app/web/coi-serviceworker.js app/web/README.md app/web/logo.svg app/web/logo-dark.svg \
  app/web/mark.svg app/web/name.svg app/web/name-dark.svg app/web/splash.css "$SITE/"
cp -R app/web/LICENSES "$SITE/LICENSES"
# The licence files the desktop app ships too: the app's GPL-3.0 (COPYING), the source's licence and the notices.
cp DEPENDENCIES.md LICENSE COPYING THIRD-PARTY-NOTICES "$SITE/LICENSES/"
(cd "$SITE" && python -c 'import os, sys, zipfile
with zipfile.ZipFile(sys.argv[1], "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for top, dirs, files in os.walk("."):
        dirs.sort()
        for name in sorted(files):
            path = os.path.join(top, name)
            z.write(path, os.path.relpath(path, "."))' "$OUT/edi-webapp.zip")
cat "$SITE/BUILD-INFO.txt"
echo "zip: $OUT/edi-webapp.zip $(wc -c <"$OUT/edi-webapp.zip") bytes"
