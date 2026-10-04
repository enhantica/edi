#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Build the edi app for the browser (edi ADR-0023): crysta and the app, once per Qt wasm kit, then the site
# zip (tools/ci/wasm-pack.sh). Run in the app environment, after wasm-toolchain:
#   pixi run -e app wasm-build                 # both builds and the zip
#   pixi run -e app wasm-build multithread     # one build, no zip (or: singlethread)
#
# crysta is compiled here for wasm — the second place edi compiles crysta after the ThreadSanitizer tree
# (tools/ci/tsan-worker.sh), for the same reason: the prebuilt SDK is a native build. The source is the pinned
# SDK's own (build/crysta-src, from `pixi run crysta-sdk`), so the browser computes with the crysta the
# native app links. EDI_WASM_CRYSTA_SRC=<crysta checkout> builds a co-branch instead (a diagnostic, recorded in
# the build's identity with its dirty state).
#
# Trees: build/wasm/<kit>/{crysta,crysta-prefix,app}. crysta is rebuilt only when its identity (source,
# kit, Emscripten) changes; the app configures incrementally per kit.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
# shellcheck source=tools/ci/wasm-env.sh
. "$ROOT/tools/ci/wasm-env.sh"
: "${CONDA_PREFIX:?run this in the app pixi environment: pixi run -e app wasm-build}"

EMSDK="$EDI_WASM_TOOLCHAIN/emsdk-$EDI_WASM_EMSDK"
EIGEN_DIR="$EDI_WASM_TOOLCHAIN/eigen-$EDI_WASM_EIGEN/share/eigen3/cmake"
QT="$EDI_WASM_TOOLCHAIN/qt/$EDI_WASM_QT"
if [ "$(cat "$EMSDK/.edi-installed" 2>/dev/null)" != "$EDI_WASM_EMSDK" ] || [ ! -d "$EIGEN_DIR" ]; then
  echo "wasm-build: no toolchain in $EDI_WASM_TOOLCHAIN — run: pixi run -e app wasm-toolchain" >&2
  exit 1
fi
# shellcheck disable=SC1091
EMSDK_QUIET=1 . "$EMSDK/emsdk_env.sh" >/dev/null
emcc_version="$(emcc -dumpversion)"
if [ "$emcc_version" != "$EDI_WASM_EMSDK" ]; then
  echo "wasm-build: emcc is $emcc_version, edi pins $EDI_WASM_EMSDK" >&2
  exit 1
fi
# The app environment's compilers, their flags (-march, -fno-plt, …: the host's) and its compiler cache are
# the native build's; Emscripten's toolchain names its own.
unset CC CXX CFLAGS CXXFLAGS CPPFLAGS LDFLAGS DEBUG_CFLAGS DEBUG_CXXFLAGS DEBUG_CPPFLAGS
unset CMAKE_CXX_COMPILER_LAUNCHER CMAKE_C_COMPILER_LAUNCHER
# The app environment hosts Qt's build tools only. Without CONDA_PREFIX, crysta's package config takes Eigen from
# Eigen3_DIR (the wasm one) instead of looking for it in that environment.
HOST="$CONDA_PREFIX"
unset CONDA_PREFIX

# The crysta source and its identity.
if [ -n "${EDI_WASM_CRYSTA_SRC:-}" ]; then
  SRC="$(cd "$EDI_WASM_CRYSTA_SRC" && pwd)"
  SHA="$(git -C "$SRC" rev-parse HEAD)"
  if [ -n "$(git -C "$SRC" status --porcelain --untracked-files=no)" ]; then
    SHA="$SHA+dirty-$(git -C "$SRC" diff HEAD | sha256sum | cut -c1-12)"
  fi
  echo "wasm-build: crysta from $SRC at $SHA (EDI_WASM_CRYSTA_SRC — a co-branch, not the pin)"
else
  SRC="$ROOT/build/crysta-src"
  SHA="$(cat "$SRC/CRYSTA_SOURCE_SHA" 2>/dev/null)" \
    || { echo "wasm-build: build/crysta-src is missing — run: pixi run crysta-sdk" >&2; exit 1; }
  echo "wasm-build: crysta $SHA (the pinned SDK's source)"
fi

build_kit() {
  local flavour="$1" kit threads owner out key
  case "$flavour" in
    multithread) threads=ON owner=OFF ;;
    singlethread) threads=OFF owner=ON ;;
    *) echo "wasm-build: unknown build '$flavour' (multithread, singlethread)" >&2; return 1 ;;
  esac
  kit="$QT/wasm_$flavour"
  wasm_check_emsdk_pin "$kit"
  out="$ROOT/build/wasm/$flavour"

  key="crysta $SHA kit $EDI_WASM_QT/$flavour emsdk $EDI_WASM_EMSDK eigen $EDI_WASM_EIGEN_SHA256 fetched"
  if [ "$(cat "$out/crysta-prefix/.edi-wasm-key" 2>/dev/null)" != "$key" ]; then
    echo "wasm-build: crysta for $flavour"
    rm -rf "$out/crysta" "$out/crysta-prefix"
    # crysta takes Eigen from a conda environment only, and the app environment's is a host build, so crysta
    # fetches its pinned release (the same version and sha256 as ours) for the wasm target.
    emcmake cmake -S "$SRC" -B "$out/crysta" -G Ninja --no-warn-unused-cli -DCMAKE_BUILD_TYPE=Release \
      -DCRYSTA_CXX_PACKAGE=ON -DCRYSTA_WASM_THREADS="$threads" -DCRYSTA_OPENMP=OFF -DCRYSTA_SLEEF=OFF \
      -DCMAKE_DISABLE_FIND_PACKAGE_doctest=ON -DCRYSTA_EIGEN_FETCH=ON \
      -DCMAKE_INSTALL_PREFIX="$out/crysta-prefix"
    cmake --build "$out/crysta"
    cmake --install "$out/crysta" >/dev/null
    printf '%s\n' "$key" >"$out/crysta-prefix/.edi-wasm-key"
  fi

  echo "wasm-build: the app for $flavour"
  # The version the app shows, refreshed on every build: app/CMakeLists.txt caches it at the first configure.
  local args=(-S . -B "$out/app" -G Ninja --no-warn-unused-cli -DCMAKE_BUILD_TYPE=Release
    -DEDI_APP_VERSION="$(git describe --tags --always --dirty 2>/dev/null || echo 0.0.0+unknown)"
    -DEDI_BUILD_APP=ON -DEDI_BUILD_BINDINGS=OFF -DEDI_WORKER_OWNER_THREAD="$owner"
    -DQT_HOST_PATH="$HOST" -DQT_HOST_PATH_CMAKE_DIR="$HOST/lib/cmake"
    -Dcrysta_DIR="$out/crysta-prefix/lib/cmake/crysta" -DEigen3_DIR="$EIGEN_DIR")
  if [ -n "${EDI_GUI_COMPONENTS_SRC:-}" ]; then
    args+=(-DFETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS="$EDI_GUI_COMPONENTS_SRC")
  fi
  # qt-cmake carries no exec bit in Qt's all_os archive.
  sh "$kit/bin/qt-cmake" "${args[@]}"
  cmake --build "$out/app" --target edi_app
  printf '%s\n' "$SHA" >"$out/app/app/CRYSTA_SOURCE_SHA"
  ls -l "$out/app/app/edi_app.wasm"
}

if [ "$#" -eq 0 ]; then
  build_kit multithread
  build_kit singlethread
  bash "$ROOT/tools/ci/wasm-pack.sh"
else
  for flavour in "$@"; do
    build_kit "$flavour"
  done
fi
