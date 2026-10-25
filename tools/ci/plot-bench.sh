#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# The plotting benchmark (app/tools/plot_bench.cpp, edi ADR-0041): every way of feeding Qt Graphs on the Stacked and
# Pattern charts' workloads, logged as it runs, its table written to build/plot-bench/<machine>-<platform>-<renderer>.tsv.
# On Linux without a display it draws on the UI test's X server (Mesa llvmpipe); elsewhere on the desktop, whose window
# must stay visible. Arguments go to the benchmark (--routes <route,...>, --workloads <name,...>, --out <file>), e.g.
# pixi run -e app plot-bench -- --workloads pattern.
set -euo pipefail
cd "$(dirname "$0")/../.."
if [ "$(uname -s)" = Linux ] && [ -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
    source tools/ci/app-platform.sh
    app_capture_platform plot-bench
fi
# pixi passes a leading "--" through.
[ "${1:-}" = "--" ] && shift
build/app/app/edi_app_plot_bench "$@"
