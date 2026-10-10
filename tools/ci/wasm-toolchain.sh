#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# The WebAssembly toolchain (edi ADR-0023): Emscripten, Qt's two wasm kits and the checks' browser,
# installed once into a cache outside the workspace and reused by every build after.
#
#   Emscripten  exactly EDI_WASM_EMSDK (Qt's QT_EMCC_RECOMMENDED_VERSION for the kits; another version is fatal
#               to qt-cmake), from emsdk's git tag of the same name.
#   Qt          EDI_WASM_QT's wasm_multithread and wasm_singlethread kits through aqtinstall (pinned in pixi.toml's
#               app feature), with the modules the app links. conda-forge has no Qt for wasm.
#
# The host Qt the kits need (QT_HOST_PATH) is the app environment's own, so this runs in it:
#   pixi run -e app wasm-toolchain
# The cache is EDI_WASM_TOOLCHAIN (default ~/.cache/edi-wasm, like the app's ccache). An install is reused when
# its recorded identity matches; anything else is refused or reinstalled, never patched in place.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=tools/ci/wasm-env.sh
. "$ROOT/tools/ci/wasm-env.sh"

: "${CONDA_PREFIX:?run this in the app pixi environment: pixi run -e app wasm-toolchain}"
host_qt="$(qmake6 -query QT_VERSION 2>/dev/null || true)"
if [ "$host_qt" != "$EDI_WASM_QT" ]; then
  echo "wasm-toolchain: the app environment's Qt is ${host_qt:-unknown}, the wasm kits are $EDI_WASM_QT — they must match (QT_HOST_PATH)" >&2
  exit 1
fi
mkdir -p "$EDI_WASM_TOOLCHAIN"

# --- Emscripten ---------------------------------------------------------------------------------------
EMSDK="$EDI_WASM_TOOLCHAIN/emsdk-$EDI_WASM_EMSDK"
if [ "$(cat "$EMSDK/.edi-installed" 2>/dev/null)" != "$EDI_WASM_EMSDK" ]; then
  rm -rf "$EMSDK"
  git clone -q --depth 1 --branch "$EDI_WASM_EMSDK" https://github.com/emscripten-core/emsdk.git "$EMSDK"
  "$EMSDK/emsdk" install "$EDI_WASM_EMSDK"
  "$EMSDK/emsdk" activate "$EDI_WASM_EMSDK" >/dev/null
  rm -rf "$EMSDK/downloads"
  printf '%s\n' "$EDI_WASM_EMSDK" >"$EMSDK/.edi-installed"
fi

# --- Qt's wasm kits -----------------------------------------------------------------------------------
QT="$EDI_WASM_TOOLCHAIN/qt"
for kit in wasm_multithread wasm_singlethread; do
  id="$EDI_WASM_QT $kit $EDI_WASM_QT_MODULES"
  if [ "$(cat "$QT/$EDI_WASM_QT/$kit/.edi-installed" 2>/dev/null)" != "$id" ]; then
    rm -rf "${QT:?}/$EDI_WASM_QT/$kit"
    # shellcheck disable=SC2086  # the module list is words
    aqt install-qt all_os wasm "$EDI_WASM_QT" "$kit" -m $EDI_WASM_QT_MODULES --outputdir "$QT"
    printf '%s\n' "$id" >"$QT/$EDI_WASM_QT/$kit/.edi-installed"
  fi
done
rm -f "$EDI_WASM_TOOLCHAIN"/aqtinstall.log ./aqtinstall.log

# --- Eigen ----------------------------------------------------------------------------------------------
# crysta's public headers include Eigen, so the app needs it as a CMake package for the wasm target: the release
# crysta fetches for its own wasm build (3.4.0, the same sha256 there), installed headers-only.
EIGEN="$EDI_WASM_TOOLCHAIN/eigen-$EDI_WASM_EIGEN"
if [ "$(cat "$EIGEN/.edi-installed" 2>/dev/null)" != "$EDI_WASM_EIGEN_SHA256" ]; then
  rm -rf "$EIGEN" "$EIGEN.src"
  mkdir -p "$EIGEN.src"
  curl -fsSL "https://gitlab.com/libeigen/eigen/-/archive/$EDI_WASM_EIGEN/eigen-$EDI_WASM_EIGEN.tar.gz" -o "$EIGEN.src/eigen.tar.gz"
  got="$(sha256sum "$EIGEN.src/eigen.tar.gz" | cut -d' ' -f1)"
  if [ "$got" != "$EDI_WASM_EIGEN_SHA256" ]; then
    echo "wasm-toolchain: Eigen $EDI_WASM_EIGEN's archive has sha256 $got, edi pins $EDI_WASM_EIGEN_SHA256 — refusing" >&2
    exit 1
  fi
  tar -xzf "$EIGEN.src/eigen.tar.gz" -C "$EIGEN.src" --strip-components=1
  cmake -S "$EIGEN.src" -B "$EIGEN.src/build" -G Ninja -DCMAKE_INSTALL_PREFIX="$EIGEN" -DBUILD_TESTING=OFF \
    -DEIGEN_BUILD_DOC=OFF -DEIGEN_BUILD_PKGCONFIG=OFF >/dev/null
  cmake --install "$EIGEN.src/build" >/dev/null
  rm -rf "$EIGEN.src"
  printf '%s\n' "$EDI_WASM_EIGEN_SHA256" >"$EIGEN/.edi-installed"
fi

# --- The browser for the checks (wasm-check.sh) ------------------------------------------------------------
CHROME="$EDI_WASM_TOOLCHAIN/chrome-$EDI_WASM_CHROME"
if [ "$(cat "$CHROME/.edi-installed" 2>/dev/null)" != "$EDI_WASM_CHROME" ]; then
  rm -rf "$CHROME"
  node_bin="$(echo "$EMSDK"/node/*/bin)"
  PATH="$node_bin:$PATH" npx -y "@puppeteer/browsers@$EDI_WASM_BROWSERS_NPM" install \
    "chrome-headless-shell@$EDI_WASM_CHROME" --path "$CHROME" >/dev/null
  printf '%s\n' "$EDI_WASM_CHROME" >"$CHROME/.edi-installed"
fi

# --- WebKit for the route check (wasm-parallel-check.sh) ---------------------------------------------------
bash "$ROOT/tools/ci/wasm-webkit.sh"

# The pin is enforced where it bites: the kit's own recommended Emscripten must be the one installed.
for kit in wasm_multithread wasm_singlethread; do
  wasm_check_emsdk_pin "$QT/$EDI_WASM_QT/$kit"
done
echo "wasm-toolchain: Emscripten $EDI_WASM_EMSDK and Qt $EDI_WASM_QT (multithread, singlethread) in $EDI_WASM_TOOLCHAIN"
du -sh "$EMSDK" "$EIGEN" "$CHROME" "$(wasm_playwright_dir)" "$QT/$EDI_WASM_QT/wasm_multithread" "$QT/$EDI_WASM_QT/wasm_singlethread"
