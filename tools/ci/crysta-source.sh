#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# The crysta commit edi builds (edi ADR-0083): pixi.toml's CRYSTA_COMMIT. Run directly it prints that
# sha, and in CI also writes `sha=<sha>` to $GITHUB_OUTPUT for the jobs that key on it.
#
#   bash tools/ci/crysta-source.sh    -> the pinned sha
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SHA="$(python3 "$ROOT/tools/ci/crysta_sdk.py" pins "$ROOT/pixi.toml")"
echo "$SHA"
[ -z "${GITHUB_OUTPUT:-}" ] || echo "sha=$SHA" >>"$GITHUB_OUTPUT"
