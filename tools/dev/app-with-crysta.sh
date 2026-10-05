#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Build and start the app against a local crysta checkout, for development only:
#
#   pixi run -e app app-with-crysta <crysta-checkout> [app arguments]
#
# crysta's engine is built from the checkout as it is, in crysta's own `cpp-ci` pixi environment, and
# installed under <crysta-checkout>/build/edi-local. The app then links that build instead of the pinned
# crysta SDK. crysta's tests are not run. CI and releases always use the pinned SDK (ADR-0017), so this
# script refuses to run in CI. See docs/dev/local-crysta.md.
set -euo pipefail
cd "$(dirname "$0")/../.."
usage="usage: pixi run -e app app-with-crysta <crysta-checkout> [app arguments]"
[ -z "${CI:-}" ] || { echo "app-with-crysta: local development only; CI links the pinned crysta SDK" >&2; exit 1; }
[ $# -ge 1 ] || { echo "$usage" >&2; exit 1; }
src="$(cd "$1" 2>/dev/null && pwd)" || { echo "app-with-crysta: no directory '$1'" >&2; exit 1; }
shift
if [ ! -f "$src/pixi.toml" ] || [ ! -f "$src/include/crysta/model.hpp" ]; then
    echo "app-with-crysta: $src is not a crysta checkout" >&2
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
echo "app-with-crysta: building crysta from $src ($(git -C "$src" describe --always --dirty 2>/dev/null || echo 'no git')); crysta's tests are not run"
# The `cpp-ci` environment is brought to crysta's lock file first, so an environment made before a pin
# moved is updated. Where crysta's own Python package is not installed yet, it stays out: its editable
# install would build all of crysta a second time. Where it is installed, it is kept as it is (pixi's
# --skip would remove it).
env_dir="$src/.pixi/envs/cpp-ci"
skip=(--skip crysta)
if compgen -G "$env_dir/lib/python3*/site-packages/crysta-*.dist-info" >/dev/null; then
    skip=()
fi
"${clean[@]}" "$pixi_bin" install --frozen --manifest-path "$src/pixi.toml" -e cpp-ci ${skip[@]+"${skip[@]}"}
# shellcheck disable=SC2016  # expanded by the inner shell
"${clean[@]}" "$pixi_bin" run --as-is --manifest-path "$src/pixi.toml" -e cpp-ci bash -euo pipefail -c '
    cmake -S "$1" -B "$2" -G Ninja -DCMAKE_BUILD_TYPE=Release -DCRYSTA_CXX_PACKAGE=ON -DCRYSTA_LTO=OFF \
        -DCMAKE_OSX_DEPLOYMENT_TARGET="${MACOSX_DEPLOYMENT_TARGET:-}" >/dev/null
    cmake --build "$2" --target crysta_core crysta_cli
    cmake --install "$2" --prefix "$3" >/dev/null' _ "$src" "$tree" "$prefix"

EDI_CRYSTA_PREFIX="$prefix" EDI_APP_TARGETS=edi_app bash tools/ci/app-build.sh
exec bash tools/ci/app-run.sh "$@"
