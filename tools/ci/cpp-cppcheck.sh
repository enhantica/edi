#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# cppcheck over edi's own C++ (edi ADR-0093); any finding is an error. It reads the compile commands of the app's build
# tree and, for the Python bindings, the core's, so it sees Qt's and crysta's headers and the build's macros as the
# compiler does. returnByReference is off: it asks Qt-style getters to return their implicitly shared members (QString,
# QStringList) by reference, where a copy is a reference count.
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
check() {
    cppcheck --project="$1/compile_commands.json" "${@:2}" --enable=warning,performance,portability \
        --error-exitcode=1 --inline-suppr --suppress=missingIncludeSystem --suppress=returnByReference --quiet \
        "${deferred[@]}" -j "${EDI_CPPCHECK_JOBS:-4}"
}
status=0
# Qt's macros (emit, signals, slots) only for the code built on Qt: the core has a function named emit.
check build/app --file-filter="$root/core/src/*" --file-filter="$root/cli/*" || status=$?
# cppcheck does not read Qt's headers (system headers), so a QPointer member returned as a raw pointer looks like an
# integer to it, and moc's include guard looks unmet in the generated .moc files.
check build/app --library=qt --suppress=CastIntegerToAddressAtReturn --suppress="preprocessorErrorDirective:*_autogen*" \
    --file-filter="$root/app/*" --file-filter="$root/assistant/native/*" || status=$?
# The bindings include nanobind's and Python's headers as system headers, which cppcheck's project import does not
# read; without them it misreads nanobind's types. It checks them against a copy of the compile commands where those
# two are ordinary include paths.
mkdir -p build/ci/cppcheck
sed -E 's#-isystem ([^ "]*(nanobind/include|include/python3[^ "/]*))#-I\1#g' build/ci/compile_commands.json \
    > build/ci/cppcheck/compile_commands.json
check build/ci/cppcheck --file-filter="$root/lib/src/*" --suppress="preprocessorErrorDirective:*/python3*" || status=$?
exit "$status"
