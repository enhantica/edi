#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Build and run the command line against a local crysta checkout, for development only:
#
#   pixi run cli-with-crysta <crysta-checkout> [cli arguments]
#
# crysta's engine is built from the checkout as it is (tools/dev/build-local-crysta.sh, shared with
# app-with-crysta), and the CLI is built against it into build/cli, then run with the remaining arguments.
# The next plain `pixi run cli` builds against the pinned crysta SDK again. CI and releases always use the
# pinned SDK (ADR-0017), so this script refuses to run in CI. See docs/dev/local-crysta.md.
set -euo pipefail
cd "$(dirname "$0")/../.."
usage="usage: pixi run cli-with-crysta <crysta-checkout> [cli arguments]"
[ -z "${CI:-}" ] || { echo "cli-with-crysta: local development only; CI links the pinned crysta SDK" >&2; exit 1; }
[ $# -ge 1 ] || { echo "$usage" >&2; exit 1; }
src="$(cd "$1" 2>/dev/null && pwd)" || { echo "cli-with-crysta: no directory '$1'" >&2; exit 1; }
shift
bash tools/dev/build-local-crysta.sh cli-with-crysta "$src"
EDI_CRYSTA_PREFIX="$src/build/edi-local/prefix" bash tools/ci/cli-build.sh
exec bash tools/ci/cli-run.sh "$@"
