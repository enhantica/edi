#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# ADR-0020 §3: the two-thread witness. The calculation worker calculates on a snapshot while the
# owner thread uses the live project, with no global lock around crysta. This gate runs that
# scenario — the tests lane's probe — under ThreadSanitizer, with crysta built from the pinned
# source and edi's core both instrumented, and requires that nothing is reported.
#
# The prebuilt SDK cannot serve: it is not instrumented, so a race inside crysta would go unseen.
# crysta is therefore compiled here, once per pinned source, into build/tsan — the one place edi
# compiles crysta, and never part of the product build.
#
# Linux only: one platform witnesses the sharing, and macOS's sanitizer runtime is not in the pinned
# toolchain. OMP_NUM_THREADS=1: libgomp is not instrumented and would report its own team; the race
# under test is between the worker thread and the owner thread, not inside an OpenMP region.
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT="$(pwd)"

if [ "$(uname -s)" != "Linux" ]; then
    echo "tsan-worker: Linux only — not run on $(uname -s)"
    exit 0
fi
PROBE=tests/unit/cpp/e04_t9_tsan_probe.cpp
if [ ! -f "$PROBE" ]; then
    echo "tsan-worker: $PROBE is missing — the gate has no scenario to run" >&2
    exit 1
fi

# The pinned SDK's source, at the commit the linked prefix was built from.
bash tools/ci/build-crysta.sh
bash tools/ci/crysta-src.sh
SRC="$ROOT/build/crysta-src"
SHA="$(cat "$SRC/CRYSTA_SOURCE_SHA")"
TREE="$ROOT/build/tsan"
FLAGS="-fsanitize=thread -fno-omit-frame-pointer -g"

# crysta under the sanitizer: rebuilt only when the pinned source moves.
if [ "$(cat "$TREE/prefix/.crysta-sha" 2>/dev/null)" != "$SHA" ]; then
    rm -rf "$TREE/crysta" "$TREE/prefix"
    cmake -S "$SRC" -B "$TREE/crysta" -G Ninja --no-warn-unused-cli -DCMAKE_BUILD_TYPE=RelWithDebInfo \
        -DCRYSTA_CXX_PACKAGE=ON -DCMAKE_INSTALL_PREFIX="$TREE/prefix" \
        -DCMAKE_CXX_FLAGS="$FLAGS" -DCMAKE_EXE_LINKER_FLAGS=-fsanitize=thread >"$TREE.configure.log" 2>&1 \
        || { cat "$TREE.configure.log" >&2; exit 1; }
    cmake --build "$TREE/crysta" -j
    cmake --install "$TREE/crysta" >/dev/null
    printf '%s\n' "$SHA" >"$TREE/prefix/.crysta-sha"
fi

# edi's core, the probe and the negative control, in the same instrumented tree.
cmake -S tools/ci/tsan -B "$TREE/edi" -G Ninja --no-warn-unused-cli -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_PREFIX_PATH="$TREE/prefix" -DEDI_ROOT="$ROOT" \
    -DCMAKE_CXX_FLAGS="$FLAGS" -DCMAKE_EXE_LINKER_FLAGS=-fsanitize=thread >/dev/null
cmake --build "$TREE/edi" -j

export OMP_NUM_THREADS=1
export TSAN_OPTIONS="exitcode=66 ${TSAN_OPTIONS:-}"

# The control first: the sanitizer must report the deliberate race, or its silence means nothing.
control_status=0
"$TREE/edi/tsan_control" >"$TREE/control.log" 2>&1 || control_status=$?
if [ "$control_status" -ne 66 ] || ! grep -q "WARNING: ThreadSanitizer: data race" "$TREE/control.log"; then
    echo "tsan-worker: the negative control reported no data race (exit $control_status) — this tree" >&2
    echo "is not instrumented, so a clean probe run would prove nothing" >&2
    exit 1
fi

log="$TREE/tsan-worker.log"
status=0
"$TREE/edi/e04_t9_tsan_probe" >"$log" 2>&1 || status=$?
cat "$log"
reports=$(grep -c "WARNING: ThreadSanitizer" "$log" || true)
if [ "$status" -ne 0 ] || [ "$reports" -ne 0 ]; then
    echo "tsan-worker: the probe exited $status with $reports ThreadSanitizer report(s)" >&2
    exit 1
fi
echo "tsan-worker: no ThreadSanitizer report (crysta $SHA and edi's core, both instrumented; control reported)"
