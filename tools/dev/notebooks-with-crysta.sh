#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Run the tutorial notebooks against a local crysta checkout, for development only:
#
#   pixi run notebooks-run-with-crysta <crysta-checkout> [tutorial ...]
#
# crysta is built from the checkout as app-with-crysta builds it (tools/dev/build-local-crysta.sh), edi's
# Python package is built against it into build/local-crysta, the example collection is built from this
# checkout into build/collection, and the tutorials run with that package and collection, writing their
# outputs into the notebooks (as `pixi run notebooks-run` does). The pinned build/ci is left as it is. CI
# always uses the pinned SDK (ADR-0017), so this refuses in CI. See docs/dev/local-crysta.md.
set -euo pipefail
cd "$(dirname "$0")/../.."
usage="usage: pixi run notebooks-run-with-crysta <crysta-checkout> [tutorial ...]"
[ -z "${CI:-}" ] || { echo "notebooks-run-with-crysta: local development only; CI links the pinned crysta SDK" >&2; exit 1; }
[ $# -ge 1 ] || { echo "$usage" >&2; exit 1; }
src="$(cd "$1" 2>/dev/null && pwd)" || { echo "notebooks-run-with-crysta: no directory '$1'" >&2; exit 1; }
shift
root="$(pwd)"

bash tools/dev/build-local-crysta.sh notebooks-run-with-crysta "$src"
prefix="$src/build/edi-local/prefix"

# edi's Python package against that crysta, in a build tree of its own.
build="$root/build/local-crysta"
cmake -S . -B "$build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$prefix" \
    -DCMAKE_OSX_DEPLOYMENT_TARGET="${MACOSX_DEPLOYMENT_TARGET:-}" >/dev/null
cmake --build "$build" --target _edi -j ${CMAKE_BUILD_PARALLEL_LEVEL:-}
cp "$prefix/.crysta-sha" "$build/.crysta-linked-sha"

# The example collection from this checkout, so the tutorials find the files they download before the
# collection is published.
collection="$root/build/collection"
rm -rf "$collection"
python tools/data/build_collection.py populate "$collection"
python tools/data/build_collection.py index "$collection"

echo "notebooks-run-with-crysta: running the tutorials with $build and $collection"
cd website
EDI_EXTENSION_DIR="$build/python/edi" EDI_SOURCE_BUILD=1 EDI_COLLECTION="$collection" \
    python run_notebooks.py "$@"
