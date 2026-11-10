#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Build and start the app against a local crysta checkout, for development only:
#
#   pixi run -e app app-with-crysta <crysta-checkout> [app arguments]
#
# crysta's engine is built from the checkout as it is, in crysta's own `cpp-toolchain` pixi environment, and
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
# crysta's engine from the checkout, into <crysta>/build/edi-local/prefix (shared with notebooks-run-with-crysta).
bash tools/dev/build-local-crysta.sh app-with-crysta "$src"
prefix="$src/build/edi-local/prefix"

EDI_CRYSTA_PREFIX="$prefix" EDI_APP_TARGETS=edi_app bash tools/ci/app-build.sh
exec bash tools/ci/app-run.sh "$@"
