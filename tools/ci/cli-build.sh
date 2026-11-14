#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Build the edi command line (`easydiffraction`) into build/cli, as app-build builds the app: crysta first
# (the pinned crysta SDK, ADR-0017, through the same build-crysta.sh), then only the CLI target. The CLI has
# a tree of its own, so a local crysta build (cli-with-crysta) never reaches build/ci, which the Python
# package and the tests use.
#
# EDI_CRYSTA_PREFIX is a local crysta build that tools/dev/cli-with-crysta.sh made; it is for development
# only and refused in CI. crysta's location is given on every configure, so the next plain build goes back
# to the pinned SDK.
set -euo pipefail
cd "$(dirname "$0")/../.."
if [ -n "${EDI_CRYSTA_PREFIX:-}" ]; then
    [ -z "${CI:-}" ] || { echo "cli-build: EDI_CRYSTA_PREFIX is for local development; CI links the pinned SDK" >&2; exit 1; }
    prefix="$EDI_CRYSTA_PREFIX"
else
    bash tools/ci/build-crysta.sh
    prefix="$(pwd)/build/crysta-prefix"
fi
cmake -S . -B build/cli -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_PREFIX_PATH="$prefix" -Dcrysta_DIR="$prefix/lib/cmake/crysta" \
    -DCMAKE_OSX_DEPLOYMENT_TARGET="${MACOSX_DEPLOYMENT_TARGET:-}"
# A bare -j would override CMAKE_BUILD_PARALLEL_LEVEL, so its value, when set, is passed to -j.
cmake --build build/cli --target easydiffraction -j ${CMAKE_BUILD_PARALLEL_LEVEL:-}
cp "$prefix/.crysta-sha" build/cli/.crysta-linked-sha
