#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Check that the multithread web app fits in parallel (edi ADR-0023): the browser matrix, then crysta's
# executed-body witness. Screenshots, logs and the measured speed ratio go to OUT.
#
#   pixi run wasm-parallel-check <out dir>
#
# The matrix (tests/system/manual/web_parallel.mjs) fits the corpus projects on all three routes of the packed site
# and times the multithread kit against the singlethread one. The witness builds crysta's observer probe from the
# crysta source the app compiles (build/crysta-src, or EDI_WASM_CRYSTA_SRC as in wasm-build.sh), with the web
# build's thread and SIMD options, and runs it in the browser: the threaded probe must show fill chunks running at
# the same time on different workers, and the two controls (serial dispatch, backend off) must be refused after
# their chunks ran. Needs wasm-build's output and wasm-toolchain's Emscripten, Node and Chrome.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
# shellcheck source=tools/ci/wasm-env.sh
. "$ROOT/tools/ci/wasm-env.sh"

if [ "$#" -ne 1 ]; then
  echo "usage: wasm-parallel-check.sh <out dir>" >&2
  exit 2
fi
OUT="$(mkdir -p "$1" && cd "$1" && pwd)"

EMSDK="$EDI_WASM_TOOLCHAIN/emsdk-$EDI_WASM_EMSDK"
NODE_BIN="$(echo "$EMSDK"/node/*/bin)"
CHROME="$EDI_WASM_TOOLCHAIN/chrome-$EDI_WASM_CHROME/chrome-headless-shell/linux-$EDI_WASM_CHROME/chrome-headless-shell-linux64/chrome-headless-shell"
ZIP="$ROOT/build/wasm/edi-webapp.zip"
for need in "$NODE_BIN/node" "$CHROME" "$ZIP"; do
  if [ ! -e "$need" ]; then
    echo "wasm-parallel-check: $need is missing — run pixi run -e app wasm-toolchain and wasm-build first" >&2
    exit 1
  fi
done
if [ -n "${EDI_WASM_CRYSTA_SRC:-}" ]; then
  SRC="$(cd "$EDI_WASM_CRYSTA_SRC" && pwd)"
else
  SRC="$ROOT/build/crysta-src"
fi
if [ ! -f "$SRC/tests/fixtures/web_parallel/build.py" ]; then
  echo "wasm-parallel-check: $SRC has no web_parallel observer — run pixi run crysta-sdk" >&2
  exit 1
fi

# The unpacked site goes to a scratch folder, so an upload of OUT carries the evidence without a copy of the app.
SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT
SITE="$SCRATCH/site"
python -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' "$ZIP" "$SITE"
export PATH="$NODE_BIN:$PATH"

status=0
echo "wasm-parallel-check: the browser matrix"
node --experimental-websocket tests/system/manual/web_parallel.mjs "$SITE" "$OUT/matrix" "$CHROME" || status=1

# The observer builds are crysta builds for wasm, configured as wasm-build.sh configures them: Emscripten's own
# toolchain, not the environment's compilers or its Eigen.
for mode in threaded serial-dispatch serial; do
  case "$mode" in
    threaded) control=() ;;
    serial-dispatch) control=(serial-dispatch) ;;
    serial) control=(backend-off) ;;
  esac
  echo "wasm-parallel-check: the witness, $mode"
  rm -rf "$OUT/observer-$mode"
  if (unset CC CXX CFLAGS CXXFLAGS CPPFLAGS LDFLAGS CONDA_PREFIX CMAKE_CXX_COMPILER_LAUNCHER CMAKE_C_COMPILER_LAUNCHER
    python "$SRC/tests/fixtures/web_parallel/build.py" "$mode" --emsdk "$EMSDK" --output "$OUT/observer-$mode"); then
    (cd "$SRC" && node --experimental-websocket tests/system/manual/web_parallel_witness.mjs "$OUT/observer-$mode" \
      tests/fitting/ncaf-wish-3bank-s5/project "$OUT/witness-$mode" "$CHROME" "${control[@]}") || status=1
  else
    status=1
  fi
  rm -rf "$OUT/observer-$mode/build"  # the witness's evidence is its output; the build tree is ~100 MB
done
exit "$status"
