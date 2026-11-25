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

# The selected SDK's exact source, always from an export: the pin's, or the candidate commit's out of
# CRYSTA_CONSUMER_SRC, whose checkout and untracked files are not read.
TREE="$ROOT/build/tsan"
if [ -n "${CRYSTA_SDK_DIR:-}" ]; then
    env -u CRYSTA_CONSUMER_SRC bash tools/ci/build-crysta.sh
    MANIFEST="$CRYSTA_SDK_DIR/share/crysta-sdk/manifest.json"
    SHA="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["source_sha"])' "$MANIFEST")"
    if ! git -C "${CRYSTA_CONSUMER_SRC:-}" cat-file -e "${SHA}^{commit}" 2>/dev/null; then
        echo "tsan-worker: the candidate SDK requires CRYSTA_CONSUMER_SRC, a crysta repository holding $SHA" >&2
        exit 1
    fi
    SRC="$TREE/source"
    rm -rf "$SRC"
    python tools/ci/crysta_source_export.py "$CRYSTA_CONSUMER_SRC" "$SHA" "$SRC"
else
    bash tools/ci/build-crysta.sh
    bash tools/ci/crysta-src.sh
    SRC="$ROOT/build/crysta-src"
    MANIFEST="$ROOT/build/crysta-prefix/share/crysta-sdk/manifest.json"
    SHA="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["source_sha"])' "$MANIFEST")"
fi
if ! python tools/ci/crysta_source_tree.py check "$SRC" "$MANIFEST"; then
    echo "tsan-worker: the source is not the tree the selected SDK ($SHA) was built from" >&2
    exit 1
fi
FLAGS="-fsanitize=thread -fno-omit-frame-pointer -g"

# A configure failure shows where it failed, not the message, which may quote crysta's source.
configure_failed() {
    echo "tsan-worker: crysta's configure failed (exit $1); its log has $(wc -l <"$TREE.configure.log") lines" >&2
    grep -aoE '^CMake Error at [^ ]+:[0-9]+ \([A-Za-z0-9_]+\):' "$TREE.configure.log" >&2 || true
    exit 1
}

# crysta under the sanitizer: rebuilt only when the selected source tree moves.
KEY="$(python tools/ci/crysta_source_tree.py id "$SRC") $SRC"
if [ "$(cat "$TREE/prefix/.crysta-tree" 2>/dev/null)" != "$KEY" ]; then
    rm -rf "$TREE/crysta" "$TREE/prefix"
    status=0
    # A compile error names its file, line and message without quoting the line.
    cmake -S "$SRC" -B "$TREE/crysta" -G Ninja --no-warn-unused-cli -DCMAKE_BUILD_TYPE=RelWithDebInfo \
        -DCRYSTA_CXX_PACKAGE=ON -DCMAKE_INSTALL_PREFIX="$TREE/prefix" \
        -DCMAKE_CXX_FLAGS="$FLAGS -fno-diagnostics-show-caret" -DCMAKE_EXE_LINKER_FLAGS=-fsanitize=thread \
        >"$TREE.configure.log" 2>&1 || status=$?
    [ "$status" -eq 0 ] || configure_failed "$status"
    cmake --build "$TREE/crysta" -j ${CMAKE_BUILD_PARALLEL_LEVEL:-}
    cmake --install "$TREE/crysta" >/dev/null
    printf '%s\n' "$KEY" >"$TREE/prefix/.crysta-tree"
fi

# edi's core, the probe and the negative control, in the same instrumented tree.
cmake -S tools/ci/tsan -B "$TREE/edi" -G Ninja --no-warn-unused-cli -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_PREFIX_PATH="$TREE/prefix" -DEDI_ROOT="$ROOT" \
    -DCMAKE_CXX_FLAGS="$FLAGS" -DCMAKE_EXE_LINKER_FLAGS=-fsanitize=thread >/dev/null
cmake --build "$TREE/edi" -j ${CMAKE_BUILD_PARALLEL_LEVEL:-}

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
