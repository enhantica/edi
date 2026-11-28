#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# cppcheck over edi's own C++ (edi ADR-0093); any finding is an error. It reads the compile commands of the app's build
# tree and, for the Python bindings, the core's, so it sees Qt's and crysta's headers and the build's macros as the
# compiler does. returnByReference is off: it asks Qt-style getters to return their implicitly shared members (QString,
# QStringList) by reference, where a copy is a reference count.
#
#   cpp-cppcheck.sh           the three calls below
#   cpp-cppcheck.sh <k>/<n>   part k of n (CI's `static · <platform> · k/n`): part 1 makes the three calls whole
#   cpp-cppcheck.sh list      the files they take as units (tools/ci/static_checks.py), without running cppcheck
#   cpp-cppcheck.sh capture   the three calls, keeping cppcheck's output and the databases in build/static-capture
#
# cppcheck runs without --quiet, so it names each file as it starts it; a run writes the units of those files to
# build/static/processed/cppcheck.txt (capture: build/static-capture), and `list` writes build/static/list/cppcheck.txt;
# CI's `static · <platform>` joins them.
set -euo pipefail
cd "$(dirname "$0")/../.."
root="$(pwd)"
for tree in build/app build/ci; do
    if [ ! -f "$tree/compile_commands.json" ]; then
        echo "cpp-cppcheck: $tree/compile_commands.json is missing; build that tree first (app-build, core-build)" >&2
        exit 1
    fi
done
# The files tools/ci/static-checks-deferred.txt lists are skipped, findings in them included. A list of comments only
# skips nothing; a list that cannot be read stops the check rather than checking with no list.
list=tools/ci/static-checks-deferred.txt
[ -r "$list" ] || { echo "cpp-cppcheck: cannot read $list" >&2; exit 1; }
deferred=()
while read -r path; do
    [ -n "$path" ] && deferred+=("--suppress=*:$path")
done < <(grep -v '^#' "$list" || [ $? -eq 1 ])
mode="${1:-all}"
static_checks() { python3 tools/ci/static_checks.py "$@"; }
case "$mode" in
    all) out=build/static/processed header="part 1/1" ;;
    capture) out=build/static-capture header="part 1/1" ;;
    list) out=build/static/list header=full ;;
    *)
        usage="usage: cpp-cppcheck.sh [<k>/<n> | list | capture]"
        static_checks part "$mode" 0 </dev/null || { echo "$usage" >&2; exit 2; }
        out=build/static/processed header="part $mode"
        ;;
esac
report="$out/cppcheck.txt"
mkdir -p "$out"
rm -f "$out"/cppcheck-*.log
printf '%s\n' "$header" >"$report"
# One cppcheck call, named for the report, or what this mode makes of it. Its arguments other than -j are recorded.
check() {
    local call="$1" log s=0
    local args=(--project="$2/compile_commands.json" "${@:3}" "--enable=warning,performance,portability"
        --error-exitcode=1 --inline-suppr --suppress=missingIncludeSystem --suppress=returnByReference
        "${deferred[@]}")
    case "$mode" in
        list)
            static_checks select "$root" "$2" cppcheck "${args[@]}" |
                static_checks units "$root" cppcheck "$call" "$2" >>"$report" || return 1
            return 0
            ;;
        all | capture | 1/*) ;;
        *) return 0 ;;
    esac
    log="$out/cppcheck-$call.log"
    cppcheck "${args[@]}" -j "${EDI_CPPCHECK_JOBS:-4}" 2>&1 | tee "$log" || s=$?
    static_checks processed "$root" cppcheck "$call" "$2" "$log" "${args[@]}" >>"$report" || return 1
    return "$s"
}
status=0
# Qt's macros (emit, signals, slots) only for the code built on Qt: the core has a function named emit.
check core build/app --file-filter="$root/core/src/*" --file-filter="$root/cli/*" || status=$?
# cppcheck does not read Qt's headers (system headers), so a QPointer member returned as a raw pointer looks like an
# integer to it, and moc's include guard looks unmet in the generated .moc files.
check qt build/app --library=qt --suppress=CastIntegerToAddressAtReturn --suppress="preprocessorErrorDirective:*_autogen*" \
    --file-filter="$root/app/*" --file-filter="$root/assistant/native/*" || status=$?
# The bindings include nanobind's and Python's headers as system headers, which cppcheck's project import does not
# read; without them it misreads nanobind's types. It checks them against a copy of the compile commands where those
# two are ordinary include paths.
mkdir -p build/ci/cppcheck
sed -E 's#-isystem ([^ "]*(nanobind/include|include/python3[^ "/]*))#-I\1#g' build/ci/compile_commands.json \
    > build/ci/cppcheck/compile_commands.json
check bindings build/ci/cppcheck --file-filter="$root/lib/src/*" --suppress="preprocessorErrorDirective:*/python3*" \
    || status=$?
if [ "$mode" = list ]; then
    cat "$report"
else
    echo "cpp-cppcheck: $(grep -c '^cppcheck ' "$report" || true) compile commands of the files it checked, in $report"
fi
if [ "$mode" = capture ]; then
    for tree in build/app build/ci build/ci/cppcheck; do
        mkdir -p "$out/databases/$tree"
        cp "$tree/compile_commands.json" "$out/databases/$tree/"
    done
    {
        echo "root $root"
        echo "commit $(git rev-parse HEAD)"
        echo "cppcheck $(cppcheck --version)"
    } >"$out/capture-cppcheck.txt"
fi
exit "$status"
