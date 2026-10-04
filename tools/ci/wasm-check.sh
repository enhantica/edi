#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Check the packed web app (edi ADR-0023) from its zip, as it is delivered: the given pytest files (the wasm crysta
# CLI's fit against the native reference, the zip's contents), then the given browser driver in each case (the
# single-thread build without isolation, the multithreaded build with headers, the multithreaded build through the
# service-worker shim). Screenshots and logs go to OUT.
#
#   pixi run wasm-check <out dir> <browser driver> <pytest file>...
#
# Needs wasm-build's output (build/wasm) and wasm-toolchain's Node and Chrome.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
# shellcheck source=tools/ci/wasm-env.sh
. "$ROOT/tools/ci/wasm-env.sh"

if [ "$#" -lt 3 ]; then
  echo "usage: wasm-check.sh <out dir> <browser driver> <pytest file>..." >&2
  exit 2
fi
OUT="$(mkdir -p "$1" && cd "$1" && pwd)"
DRIVER="$2"
shift 2

EMSDK="$EDI_WASM_TOOLCHAIN/emsdk-$EDI_WASM_EMSDK"
NODE_BIN="$(echo "$EMSDK"/node/*/bin)"
CHROME="$EDI_WASM_TOOLCHAIN/chrome-$EDI_WASM_CHROME/chrome-headless-shell/linux-$EDI_WASM_CHROME/chrome-headless-shell-linux64/chrome-headless-shell"
ZIP="$ROOT/build/wasm/edi-webapp.zip"
for need in "$NODE_BIN/node" "$CHROME" "$ZIP"; do
  if [ ! -e "$need" ]; then
    echo "wasm-check: $need is missing — run pixi run -e app wasm-toolchain and wasm-build first" >&2
    exit 1
  fi
done

SITE="$OUT-site"  # beside OUT, so an upload of OUT carries the evidence without a second copy of the app
rm -rf "$SITE"
python -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' "$ZIP" "$SITE"

export PATH="$NODE_BIN:$PATH"
export EDI_WASM_ZIP="$ZIP"
export EDI_WASM_CLI_SINGLETHREAD="$ROOT/build/wasm/singlethread/crysta-prefix/bin/crysta.js"
export EDI_WASM_CLI_MULTITHREAD="$ROOT/build/wasm/multithread/crysta-prefix/bin/crysta.js"

status=0
python -m pytest -q "$@" || status=1
for mode in singlethread multithread shim; do
  echo "wasm-check: browser, $mode"
  node --experimental-websocket "$DRIVER" "$SITE" "$mode" "$OUT/$mode" "$CHROME" || status=1
done
exit "$status"
