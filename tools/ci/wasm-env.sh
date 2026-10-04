# SPDX-License-Identifier: BSD-3-Clause
# The WebAssembly toolchain pins and paths (edi ADR-0023), sourced by wasm-toolchain.sh, wasm-build.sh and wasm-check.sh. A Qt
# bump moves EDI_WASM_QT with the app environment's qt6-main, and EDI_WASM_EMSDK with it to that Qt's
# QT_EMCC_RECOMMENDED_VERSION: wasm_check_emsdk_pin refuses any other pairing.
EDI_WASM_QT=6.11.2
EDI_WASM_EMSDK=4.0.7
# The modules the app links beyond qtbase and qtdeclarative (aqt adds those): the pattern chart (qtgraphs), the
# structure view (qtquick3d, with qtquicktimeline and qtshadertools behind it).
EDI_WASM_QT_MODULES="qtgraphs qtquick3d qtquicktimeline qtshadertools"
# Eigen for the wasm target: crysta's fallback release, at the sha256 crysta's CMakeLists.txt pins too.
EDI_WASM_EIGEN=3.4.0
EDI_WASM_EIGEN_SHA256=8586084f71f9bde545ee7fa6d00288b264a2b7ac3607b974e54d13e7162c1c72
# The browser the web app's checks drive: Chrome headless shell, installed by @puppeteer/browsers (its 2.x line
# runs on emsdk's Node 20).
EDI_WASM_CHROME=146.0.7680.153
EDI_WASM_BROWSERS_NPM=2.13.2
: "${EDI_WASM_TOOLCHAIN:=$HOME/.cache/edi-wasm}"

# wasm_check_emsdk_pin <kit dir>: the kit's recorded Emscripten version must be EDI_WASM_EMSDK.
wasm_check_emsdk_pin() {
  local want
  want="$(sed -n 's/.*QT_EMCC_RECOMMENDED_VERSION "\{0,1\}\([0-9][0-9.]*\)"\{0,1\}.*/\1/p' \
    "$1/lib/cmake/Qt6/QtPublicWasmToolchainHelpers.cmake" "$1"/lib/cmake/Qt6/*.cmake 2>/dev/null | head -n 1)"
  if [ -z "$want" ]; then
    echo "wasm: $1 records no QT_EMCC_RECOMMENDED_VERSION — refusing to guess the Emscripten pin" >&2
    return 1
  fi
  if [ "$want" != "$EDI_WASM_EMSDK" ]; then
    echo "wasm: Qt $EDI_WASM_QT ($1) wants Emscripten $want, edi pins $EDI_WASM_EMSDK — move the pin with the kit" >&2
    return 1
  fi
}
