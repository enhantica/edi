#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Build the edi app host (edi ADR-0015) in the `app` pixi environment: crysta first (the same
# build-crysta.sh the core uses — the pinned crysta SDK, ADR-0017), then the
# CMake project with the app on and the Python bindings off, into build/app.
#
# Run on its own, each app step builds first (its task depends on app-build); a full sequence — the
# app-verify composite, the verify chains that include it, each CI app job — builds once at its start and
# runs its steps on that build (as the owner corrected it on 2026-09-29).
#
# build/app is keyed by its COMPLETE build identity, as build-crysta.sh keys its prefix: the resolved C++
# compiler and its full `-v` configuration, the flag variables, the environment (its path and every
# installed package, the sysroot among them) and the build options. Any change removes build/app and
# configures it fresh, so a CMake cache written under another environment's compilers is never reused (a
# build/app configured before the app had its own environment named a `c++` the macOS app environment
# does not provide, and every configure failed). The key is written only after a successful configure.
# app-build-recovery.sh exercises the recovery.
#
# Offline or with a local gui-components clone: EDI_GUI_COMPONENTS_SRC=<clone at the pinned commit>.
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT="$(pwd)"
_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256
    else
        echo "app-build: no sha256sum and no shasum — cannot compute the build identity." >&2
        exit 1
    fi
}
# The crysta prefix build-crysta.sh installed for this environment (its ENV_SUFFIX rule). In the
# crysta->edi consumer-contract direction (CRYSTA_SDK_DIR), link that candidate SDK, exactly as
# core-build.sh does: an app linked against the pinned prefix while edi's core follows the co-branch would
# verify a crysta the change never ran against. The prefix is part of the build identity below, so
# switching direction configures build/app fresh. EDI_CRYSTA_PREFIX is a local crysta build that
# tools/dev/app-with-crysta.sh made; it is for development only and refused in CI.
if [ -n "${EDI_CRYSTA_PREFIX:-}" ]; then
    [ -z "${CI:-}" ] || { echo "app-build: EDI_CRYSTA_PREFIX is for local development; CI links the pinned SDK" >&2; exit 1; }
    CRYSTA_PREFIX="$EDI_CRYSTA_PREFIX"
else
    bash tools/ci/build-crysta.sh
    ENV_NAME="${PIXI_ENVIRONMENT_NAME:-$(basename "${CONDA_PREFIX:-default}")}"
    case "$ENV_NAME" in default | "") ENV_SUFFIX="" ;; *) ENV_SUFFIX="-$ENV_NAME" ;; esac
    CRYSTA_PREFIX="$ROOT/build/crysta-prefix$ENV_SUFFIX"
    if [ -n "${CRYSTA_SDK_DIR:-}" ]; then
        CRYSTA_PREFIX="$ROOT/build/crysta-consumer-prefix$ENV_SUFFIX"
    fi
fi
args=(-S . -B build/app -G Ninja -DCMAKE_BUILD_TYPE=Release
      -DEDI_BUILD_APP=ON -DEDI_BUILD_BINDINGS=OFF
      -DCMAKE_PREFIX_PATH="$CRYSTA_PREFIX;${CONDA_PREFIX:?run this in the app pixi environment}"
      -DCMAKE_OSX_DEPLOYMENT_TARGET="${MACOSX_DEPLOYMENT_TARGET:-}")
if [ -n "${EDI_GUI_COMPONENTS_SRC:-}" ]; then
    args+=(-DFETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS="$EDI_GUI_COMPONENTS_SRC")
fi
BUILD_KEY="$(
    {
        printf 'cxx=%s\n' "$(command -v "${CXX:-c++}" 2>/dev/null || echo '?')"
        "${CXX:-c++}" -v 2>&1 </dev/null || true
        printf 'cxxflags=%s\ncppflags=%s\nldflags=%s\n' "${CXXFLAGS:-}" "${CPPFLAGS:-}" "${LDFLAGS:-}"
        printf 'env=%s\ncmake=%s\n' "$CONDA_PREFIX" "$(cmake --version | head -n 1)"
        printf 'launcher=%s\n' "${CMAKE_CXX_COMPILER_LAUNCHER:-}"
        printf 'packages=%s\n' "$(ls "$CONDA_PREFIX/conda-meta" 2>/dev/null | tr '\n' ' ')"
        printf 'args=%s\n' "${args[*]}"
    } | _sha256 | cut -d' ' -f1
)"
MARKER=build/app/.edi-app-build-key
if [ -d build/app ] && [ "$(cat "$MARKER" 2>/dev/null)" != "$BUILD_KEY" ]; then
    echo "app-build: build identity changed (compiler / flags / environment / options); configuring build/app fresh"
    rm -rf build/app
fi
cmake "${args[@]}"
printf '%s\n' "$BUILD_KEY" > "$MARKER"
# The host, the test runner and the image comparator by default; `app` builds the host alone.
read -r -a targets <<< "${EDI_APP_TARGETS:-edi_app edi_app_tests edi_app_ui_compare}"
cmake --build build/app --target "${targets[@]}"
