#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Place the web app's site folder (tools/ci/wasm-pack.sh) into the rendered docs as /webapp/ (edi ADR-0023): the
# publishing step; the docs link it.
#   bash tools/ci/docs-webapp.sh <web app folder> <rendered docs folder>
set -euo pipefail
app="${1:?the web app folder (build/wasm/site)}"
docs="${2:?the rendered docs folder (site)}"
for file in index.html coi-serviceworker.js build.json; do
  [ -f "$app/$file" ] || { echo "docs-webapp: $app/$file is missing — not a web app folder" >&2; exit 1; }
done
for folder in $(python3 -c 'import json, sys; print(" ".join(json.load(open(sys.argv[1])).values()))' "$app/build.json"); do
  [ -f "$app/$folder/edi_app.wasm" ] || { echo "docs-webapp: build.json names $folder, which $app lacks" >&2; exit 1; }
done
[ -f "$docs/index.html" ] || { echo "docs-webapp: $docs has no index.html — not a rendered docs folder" >&2; exit 1; }
if [ -e "$docs/webapp" ]; then
  echo "docs-webapp: $docs/webapp exists — the docs must not own that path" >&2
  exit 1
fi
cp -R "$app" "$docs/webapp"
echo "docs-webapp: the web app is at $docs/webapp ($(du -sh "$docs/webapp" | cut -f1))"
