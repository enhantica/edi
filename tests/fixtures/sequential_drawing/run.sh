#!/usr/bin/env bash
# Run one authored actor on the same real OpenGL platform as the application.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)
source "$root/tools/ci/app-platform.sh"
app_capture_platform sequential-drawing
export QSG_RENDER_LOOP=basic
unset QT_QUICK_BACKEND
"$@"
