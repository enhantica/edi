#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Check that the multithread web app fits in parallel (edi ADR-0023): the browser matrix, then crysta's
# executed-body witness. Screenshots, logs and the measured speed ratio go to OUT.
#
#   pixi run wasm-parallel-check <out dir>
#
# The matrix (tests/system/manual/web_parallel.mjs) fits the corpus projects on both isolation routes of the packed site
# and compares one worker with the parallel thread policy on the same multithread kit. The witnesses build crysta's observer probes from the
# crysta source the app compiles (build/crysta-src, or EDI_WASM_CRYSTA_SRC as in wasm-build.sh), with the web
# build's thread and SIMD options, and run them in the browser: the threaded probe must show fill chunks running at
# the same time on different workers, and the two controls (serial dispatch, backend off) must be refused after
# their chunks ran; the SIMD probe must consume the vectorised maths layer, and its two controls must be refused. Needs wasm-build's output, wasm-toolchain's Emscripten and Chrome, and the environment's Node.
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
CHROME="$EDI_WASM_TOOLCHAIN/chrome-$EDI_WASM_CHROME/chrome-headless-shell/linux-$EDI_WASM_CHROME/chrome-headless-shell-linux64/chrome-headless-shell"
ZIP="$ROOT/build/wasm/edi-webapp.zip"
for need in "$CHROME" "$ZIP"; do
  if [ ! -e "$need" ]; then
    echo "wasm-parallel-check: $need is missing — run pixi run -e app wasm-toolchain and wasm-build first" >&2
    exit 1
  fi
done
wasm_check_driver_node wasm-parallel-check
if [ -n "${EDI_WASM_CRYSTA_SRC:-}" ]; then
  SRC="$(cd "$EDI_WASM_CRYSTA_SRC" && pwd)"
else
  SRC="$ROOT/build/crysta-src"
fi
if [ ! -f "$SRC/tests/fixtures/web_parallel/build.py" ] || [ ! -f "$SRC/tests/fixtures/web_simd/build.py" ]; then
  echo "wasm-parallel-check: $SRC has no web_parallel or web_simd observer — run pixi run crysta-sdk" >&2
  exit 1
fi

# The unpacked site and the observer builds, which copy crysta's source, go to a scratch folder, so an upload of OUT
# carries the evidence alone.
SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT
SITE="$SCRATCH/site"
python -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' "$ZIP" "$SITE"
# The locked Playwright driver and its WebKit, for the matrix's route check (tools/ci/wasm-webkit.sh).
PW="$(wasm_playwright_dir)"
export PLAYWRIGHT_BROWSERS_PATH="$PW/browsers" WEB_PARALLEL_PLAYWRIGHT="$PW/node_modules/playwright-core/index.mjs"

# A reference that cannot be written fails the run, but the witness builds below still run; the matrix finds the
# folder empty and refuses.
status=0
REFERENCE="$(mktemp -d "$OUT/native-written.XXXXXX")"
if ! bash "$ROOT/tools/ci/wasm-written-reference.sh" "$REFERENCE"; then
  echo "wasm-parallel-check: the native-written reference could not be made; the matrix will refuse" >&2
  find "$REFERENCE" -mindepth 1 -delete
  status=1
fi
echo "wasm-parallel-check: the browser matrix"
node --experimental-websocket tests/system/manual/web_parallel.mjs "$SITE" "$OUT/matrix" "$CHROME" --written-reference="$REFERENCE" || status=1

# The observer builds are crysta builds for wasm, configured as wasm-build.sh configures them: Emscripten's own
# toolchain, not the environment's compilers or its Eigen.
for mode in threaded serial-dispatch serial; do
  case "$mode" in
    threaded) control=() ;;
    serial-dispatch) control=(serial-dispatch) ;;
    serial) control=(backend-off) ;;
  esac
  echo "wasm-parallel-check: the witness, $mode"
  rm -rf "$SCRATCH/observer-$mode"
  if (unset CC CXX CFLAGS CXXFLAGS CPPFLAGS LDFLAGS CONDA_PREFIX CMAKE_CXX_COMPILER_LAUNCHER CMAKE_C_COMPILER_LAUNCHER
    python "$SRC/tests/fixtures/web_parallel/build.py" "$mode" --emsdk "$EMSDK" --output "$SCRATCH/observer-$mode"); then
    (cd "$SRC" && node --experimental-websocket tests/system/manual/web_parallel_witness.mjs "$SCRATCH/observer-$mode" \
      tests/fitting/ncaf-wish-3bank-s5/project "$OUT/witness-$mode" "$CHROME" "${control[@]}") || status=1
  else
    status=1
  fi
  rm -rf "$SCRATCH/observer-$mode/build"
done

# The SIMD layer's witness in the browser (crysta tests/fixtures/web_simd): the maths layer as the multithread kit
# builds it must be consumed by every vectorised kernel, and the two controls (maths layer disabled, silent scalar
# fallback) must agree numerically and be refused as consumption.
for mode in enabled scalar fallback; do
  echo "wasm-parallel-check: the SIMD witness, $mode"
  rm -rf "$SCRATCH/simd-$mode"
  if (cd "$SRC" && unset CC CXX CFLAGS CXXFLAGS CPPFLAGS LDFLAGS CONDA_PREFIX CMAKE_CXX_COMPILER_LAUNCHER CMAKE_C_COMPILER_LAUNCHER &&
    python -m tests.fixtures.web_simd.build "$mode" --emsdk "$EMSDK" --output "$SCRATCH/simd-$mode"); then
    (cd "$SRC" && node --experimental-websocket tests/system/manual/web_simd_witness.mjs wasm "$SCRATCH/simd-$mode" "$mode" \
      "$OUT/simd-witness-$mode" "$CHROME") || status=1
  else
    status=1
  fi
  rm -rf "$SCRATCH/simd-$mode/build"
done
exit "$status"
