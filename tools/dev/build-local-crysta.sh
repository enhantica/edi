#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Build crysta from a local checkout into <crysta-checkout>/build/edi-local/prefix, for development only:
#
#   bash tools/dev/build-local-crysta.sh <caller> <crysta-checkout>
#
# app-with-crysta, cli-with-crysta and notebooks-run-with-crysta share this step. crysta's engine is built
# from the checkout as it is, in crysta's own `cpp-toolchain` pixi environment; its tests are not run. The
# prefix records the checkout's commit in `.crysta-sha`. CI and releases always use the pinned SDK
# (ADR-0017), so this refuses in CI. See docs/dev/local-crysta.md.
set -euo pipefail
caller="${1:?usage: build-local-crysta.sh <caller> <crysta-checkout>}"
[ -z "${CI:-}" ] || { echo "$caller: local development only; CI links the pinned crysta SDK" >&2; exit 1; }
src="$(cd "${2:?usage: build-local-crysta.sh <caller> <crysta-checkout>}" 2>/dev/null && pwd)" ||
    { echo "$caller: no directory '$2'" >&2; exit 1; }
if [ ! -f "$src/pixi.toml" ] || [ ! -f "$src/include/crysta/model.hpp" ]; then
    echo "$caller: $src is not a crysta checkout" >&2
    exit 1
fi
tree="$src/build/edi-local"
prefix="$tree/prefix"

# crysta builds with its own toolchain, so nothing from this (edi) environment may leak into it: a clean
# environment, keeping only the user's caches, proxies and locale.
pixi_bin="$(command -v pixi)"
clean=(env -i HOME="$HOME" TERM="${TERM:-dumb}" PATH="$(dirname "$pixi_bin"):/usr/bin:/bin:/usr/sbin:/sbin")
for name in USER LANG LC_ALL PIXI_CACHE_DIR RATTLER_CACHE_DIR XDG_CACHE_HOME CCACHE_DIR CMAKE_BUILD_PARALLEL_LEVEL \
    http_proxy https_proxy no_proxy HTTP_PROXY HTTPS_PROXY NO_PROXY SSL_CERT_FILE; do
    [ -z "${!name:-}" ] || clean+=("$name=${!name}")
done
# On a Mac, stop early when the selected SDK or Apple's C++ tools are not ready (Xcode setup or licence not done,
# Command Line Tools missing), with Apple's own message, before anything is installed or built.
if [ "$(uname -s)" = Darwin ]; then
    if ! macos_sdk="$("${clean[@]}" /usr/bin/xcrun --sdk macosx --show-sdk-path)" ||
        [ -z "$macos_sdk" ] || [ ! -d "$macos_sdk" ] ||
        ! "${clean[@]}" /usr/bin/xcrun --sdk macosx clang++ --version >/dev/null; then
        echo "$caller: the selected macOS developer tools are not ready (see Apple's message above)." >&2
        echo "$caller: open Xcode to finish its setup, or install the Command Line Tools; if Apple asks for" >&2
        echo "$caller: a licence review, run 'sudo xcodebuild -license' yourself." >&2
        exit 1
    fi
fi
echo "$caller: building crysta from $src ($(git -C "$src" describe --always --dirty 2>/dev/null || echo 'no git')); crysta's tests are not run"
# Install the locked native toolchain, without the Python package or its test extras.
"${clean[@]}" "$pixi_bin" install --frozen --manifest-path "$src/pixi.toml" -e cpp-toolchain
# shellcheck disable=SC2016  # expanded by the inner shell
"${clean[@]}" "$pixi_bin" run --as-is --manifest-path "$src/pixi.toml" -e cpp-toolchain bash -euo pipefail -c '
    cmake -S "$1" -B "$2" -G Ninja -DCMAKE_BUILD_TYPE=Release -DCRYSTA_CXX_PACKAGE=ON -DCRYSTA_LTO=OFF \
        -DCMAKE_OSX_DEPLOYMENT_TARGET="${MACOSX_DEPLOYMENT_TARGET:-}" >/dev/null
    cmake --build "$2" --target crysta_core crysta_cli
    cmake --install "$2" --prefix "$3" >/dev/null' _ "$src" "$tree" "$prefix"
git -C "$src" rev-parse HEAD > "$prefix/.crysta-sha" 2>/dev/null || echo unknown > "$prefix/.crysta-sha"
