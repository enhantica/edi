#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Run the already-built edi command line (`pixi run cli-run <arguments>`): no build, as app-run starts the
# app. `pixi run cli` builds first and then runs this, e.g. `pixi run cli fit docs/user/cli/<case>/project`.
set -euo pipefail
cd "$(dirname "$0")/../.."
cli=build/cli/cli/easydiffraction
[ -x "$cli" ] || [ ! -x "$cli.exe" ] || cli="$cli.exe"
if [ ! -x "$cli" ]; then
    echo "cli-run: $cli is not built - run 'pixi run cli-build' (or 'pixi run cli') first" >&2
    exit 1
fi
exec "$cli" "$@"
