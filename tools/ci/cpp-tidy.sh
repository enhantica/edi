#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# clang-tidy, the Clang Static Analyzer among its checks, over edi's own C++ (edi ADR-0093), with .clang-tidy's checks
# and any finding an error. It reads the compile commands of the app's build tree, so run app-build first; the Python
# bindings, which that tree leaves out, come from the core's tree (core-build).
#
#   cpp-tidy.sh           every file the selection below gives
#   cpp-tidy.sh <k>/<n>   part k of n: every n-th of those files, from the k-th (CI's `static · <platform> · k/n`)
#   cpp-tidy.sh list      those files as units (tools/ci/static_checks.py), without running clang-tidy
#   cpp-tidy.sh capture   every file, keeping run-clang-tidy's output and both databases in build/static-capture
#
# A run writes the units of the files run-clang-tidy reports it ran to build/static/processed/clang-tidy.txt (capture:
# build/static-capture), and `list` writes build/static/list/clang-tidy.txt; CI's `static · <platform>` joins them.
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
mode="${1:-all}"
static_checks() { python3 tools/ci/static_checks.py "$@"; }
case "$mode" in
    all) out=build/static/processed header="part 1/1" ;;
    capture) out=build/static-capture header="part 1/1" ;;
    list) out=build/static/list header=full ;;
    *)
        static_checks part "$mode" 0 </dev/null || { echo "usage: cpp-tidy.sh [<k>/<n> | list | capture]" >&2; exit 2; }
        out=build/static/processed header="part $mode"
        ;;
esac
report="$out/clang-tidy.txt"
mkdir -p "$out"
rm -f "$out"/clang-tidy-*.log
printf '%s\n' "$header" >"$report"
# The parts count the files across both calls, in their order.
taken=0
# One run-clang-tidy call on a database and the regex of its files, or this mode's share of it. A part always names
# its files, since run-clang-tidy given none takes every file of the database.
tidy() {
    local call="$1" tree="$2" pattern="$3" selected log s=0
    local patterns=("$pattern")
    selected="$(static_checks select "$root" "$tree" clang-tidy "$pattern")" || return 1
    case "$mode" in
        list) static_checks units "$root" clang-tidy "$call" "$tree" <<<"$selected" >>"$report" || return 1; return 0 ;;
        all | capture) ;;
        *)
            mapfile -t patterns < <(static_checks part "$mode" "$taken" <<<"$selected" | static_checks regexes)
            taken=$((taken + $(grep -c . <<<"$selected" || true)))
            [ "${#patterns[@]}" -gt 0 ] || return 0
            ;;
    esac
    log="$out/clang-tidy-$call.log"
    run-clang-tidy -quiet -p "$tree" -j "${EDI_TIDY_JOBS:-4}" -header-filter="$own" -exclude-header-filter="$skip" \
        -warnings-as-errors='*' -extra-arg=-Wno-unknown-warning-option "${patterns[@]}" 2>&1 | tee "$log" || s=$?
    static_checks processed "$root" clang-tidy "$call" "$tree" "$log" >>"$report" || return 1
    return "$s"
}
# Each file once: the bindings from the core's tree, everything else from the app's.
tidy app build/app "^$root/(?!(${deferred:-^})$)(core/src|cli|app|assistant/native)/.*\.cpp$" || status=$?
tidy bindings build/ci "^$root/lib/src/.*\.cpp$" || status=$?
if [ "$mode" = list ]; then
    cat "$report"
else
    echo "cpp-tidy: $(grep -c '^clang-tidy ' "$report" || true) compile commands of the files it ran, in $report"
fi
if [ "$mode" = capture ]; then
    for tree in build/app build/ci; do
        mkdir -p "$out/databases/$tree"
        cp "$tree/compile_commands.json" "$out/databases/$tree/"
    done
    {
        echo "root $root"
        echo "commit $(git rev-parse HEAD)"
        echo "clang-tidy $(clang-tidy --version | tr -s '\n ' ' ')"
    } >"$out/capture-clang-tidy.txt"
fi
exit "$status"
