#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Start the already-built edi app (`pixi run -e app app-run`): no build, no crysta resolve, no network.
# Arguments go to the app, e.g. `--demo <dir>` (the scripted click-through that saves one image per page
# state, then exits). `pixi run -e app app` builds first and then runs this.
set -euo pipefail
cd "$(dirname "$0")/../.."
app=build/app/app/edi_app
if [ ! -x "$app" ]; then
    echo "app-run: $app is not built - run 'pixi run -e app app-build' (or 'pixi run -e app app') first" >&2
    exit 1
fi
exec "$app" "$@"
