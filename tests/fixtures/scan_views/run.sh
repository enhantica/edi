#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$root"
export CONDA_PREFIX="$root/.pixi/envs/app"
export PATH="$CONDA_PREFIX/bin:$PATH"
export QSG_RENDER_LOOP=basic
unset QT_QUICK_BACKEND QT_QPA_PLATFORM
source tools/ci/app-platform.sh
app_capture_platform scan-content
"$@"
