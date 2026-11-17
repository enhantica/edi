#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# clang-tidy, the Clang Static Analyzer among its checks, over edi's own C++ (edi ADR-0093), with .clang-tidy's checks
# and any finding an error. It reads the compile commands of the app's build tree, so run app-build first; the Python
# bindings, which that tree leaves out, come from the core's tree (core-build).
set -euo pipefail
cd "$(dirname "$0")/../.."
root="$(pwd)"
own="^$root/(core|cli|lib|app|assistant)/"
# The files tools/ci/static-checks-deferred.txt lists are skipped, as sources and as headers. A list of comments only
# skips nothing; a list that cannot be read stops the check rather than checking with no list.
list=tools/ci/static-checks-deferred.txt
[ -r "$list" ] || { echo "cpp-tidy: cannot read $list" >&2; exit 1; }
deferred="$({ grep -v '^#' "$list" || [ $? -eq 1 ]; } | sed 's/[.]/\\./g' | paste -sd '|' -)"
skip="^$root/(${deferred:-^})$"
status=0
for tree in build/app build/ci; do
    if [ ! -f "$tree/compile_commands.json" ]; then
        echo "cpp-tidy: $tree/compile_commands.json is missing; build that tree first (app-build, core-build)" >&2
        exit 1
    fi
done
# Each file once: the bindings from the core's tree, everything else from the app's.
run-clang-tidy -quiet -p build/app -j "${EDI_TIDY_JOBS:-4}" -header-filter="$own" -exclude-header-filter="$skip" \
    -warnings-as-errors='*' -extra-arg=-Wno-unknown-warning-option \
    "^$root/(?!(${deferred:-^})$)(core/src|cli|app|assistant/native)/.*\.cpp$" || status=$?
run-clang-tidy -quiet -p build/ci -j "${EDI_TIDY_JOBS:-4}" -header-filter="$own" -exclude-header-filter="$skip" \
    -warnings-as-errors='*' -extra-arg=-Wno-unknown-warning-option "^$root/lib/src/.*\.cpp$" || status=$?
exit "$status"
