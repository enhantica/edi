#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# app-build.sh's stale-toolchain recovery: seed build/app with the state a build under another environment
# leaves — a build identity that is not this one, and a CMake cache naming a C++ compiler that does not exist
# — then build the host. app-build must configure build/app fresh and succeed. Without the identity key the
# configure fails: "The CMAKE_CXX_COMPILER ... is not a full path to an existing compiler tool". CI runs it as
# the last step of each app job when app-build.sh changed (it is a second full build); the checkout starts
# from a clean tree and so never meets a stale build/app otherwise. It uses an existing build/app and never
# builds one first (note 20).
set -euo pipefail
cd "$(dirname "$0")/../.."
cache=build/app/CMakeCache.txt
if [ ! -f "$cache" ]; then
    echo "app-build-recovery: build/app has no CMake cache - run 'pixi run -e app app-build' first" >&2
    exit 1
fi
stale=/nonexistent/stale-toolchain/c++
echo "stale" > build/app/.edi-app-build-key
sed -i.stale "s|^CMAKE_CXX_COMPILER:.*|CMAKE_CXX_COMPILER:FILEPATH=$stale|" "$cache"
grep -qx "CMAKE_CXX_COMPILER:FILEPATH=$stale" "$cache" || {
    echo "app-build-recovery: could not seed the stale compiler into $cache" >&2
    exit 1
}
log=build/app-build-recovery.log
EDI_APP_TARGETS=edi_app bash tools/ci/app-build.sh 2>&1 | tee "$log"
if ! grep -q 'app-build: build identity changed' "$log"; then
    echo "app-build-recovery: app-build reused the stale build/app" >&2
    exit 1
fi
compiler=$(sed -n 's/^CMAKE_CXX_COMPILER:[A-Z]*=//p' "$cache")
if [ "$compiler" = "$stale" ] || [ ! -x "$compiler" ]; then
    echo "app-build-recovery: build/app still names '$compiler' as its C++ compiler" >&2
    exit 1
fi
echo "app-build-recovery: a stale build/app was configured fresh; its C++ compiler is $compiler"
