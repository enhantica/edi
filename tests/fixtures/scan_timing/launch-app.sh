#!/usr/bin/env bash
set -euo pipefail
platform_script="$1"
shift
source "$platform_script"
unset QT_QPA_PLATFORM
app_capture_platform 'Scan timing observer'
"$@"
