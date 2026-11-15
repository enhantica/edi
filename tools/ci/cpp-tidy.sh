#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# clang-tidy, the Clang Static Analyzer among its checks, over edi's own C++ (edi ADR-0089), with .clang-tidy's checks
# and any finding an error. It reads the compile commands of the app's build tree, so run app-build first; the Python
# bindings, which that tree leaves out, come from the core's tree (core-build).
set -euo pipefail
cd "$(dirname "$0")/../.."
root="$(pwd)"
own="^$root/(core|cli|lib|app|assistant)/"
status=0
for tree in build/app build/ci; do
    if [ ! -f "$tree/compile_commands.json" ]; then
        echo "cpp-tidy: $tree/compile_commands.json is missing; build that tree first (app-build, core-build)" >&2
        exit 1
    fi
done
# Each file once: the bindings from the core's tree, everything else from the app's.
run-clang-tidy -quiet -p build/app -j "${EDI_TIDY_JOBS:-4}" -header-filter="$own" -warnings-as-errors='*' \
    -extra-arg=-Wno-unknown-warning-option "$own(core/src|cli|app|assistant/native)/.*\.cpp$" || status=$?
run-clang-tidy -quiet -p build/ci -j "${EDI_TIDY_JOBS:-4}" -header-filter="$own" -warnings-as-errors='*' \
    -extra-arg=-Wno-unknown-warning-option "$own(lib/src)/.*\.cpp$" || status=$?
exit "$status"
