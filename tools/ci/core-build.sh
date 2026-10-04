#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Configure + build the edi C++ core (Release). From the core links crysta::crysta, so first acquire
# the pinned crysta SDK as a CMake package at build/crysta-prefix (ADR-0003, ADR-0017), then
# configure edi with that prefix on CMAKE_PREFIX_PATH. Skips cleanly while no CMake tree exists, so
# CI stays green on the pre-code skeleton.
set -euo pipefail
if [ -f CMakeLists.txt ]; then SRC=.; elif [ -f core/CMakeLists.txt ]; then SRC=core; else
  echo "no CMake tree yet — skeleton pass"; exit 0
fi
ROOT="$(pwd)"

# ⛔ ONE PRODUCER AT A TIME. The crysta prefix and the edi build dir are SHARED mutable state: two
# concurrent builds interleave their writes into the same tree, and the loser observes a
# half-installed prefix — a failure that reads as a source defect and is not reproducible. A
# pytest worker that shells out to this script is exactly that second producer. `flock` serialises
# them: the second waits rather than corrupting the first, and the wait is bounded so a stale
# holder fails loudly instead of hanging the gate forever. A pytest WORKER may not enter the
# producer at all. Serialising would only make the second worker wait for a build it must not have
# started: the suite's job is to consume the built artifact, not to produce it, and a worker that
# builds races every other worker's imports. Refused by name so the cause is legible instead of
# surfacing as a corrupt-prefix import error.
if [ -n "${PYTEST_XDIST_WORKER:-}" ]; then
  echo "REFUSING: pytest worker ${PYTEST_XDIST_WORKER} may not enter the shared core build." >&2
  echo "The core is built once, before the suite runs; a worker that builds races every other" >&2
  echo "worker's imports against a half-installed prefix. Run 'pixi run core-build' first." >&2
  exit 1
fi
# CRYSTA_SDK_DIR builds build/ci-consumer, which every runtime reader selects only by the ONE consumer selector
# (lib/edi/__init__.py, verification, python_surface_superset, crysta-consumer.sh), so a candidate build without
# it would be followed by an import of the ordinary build/ci. Refused before any write.
if [ -n "${CRYSTA_SDK_DIR:-}" ] && ! { [ -n "${EDI_USE_CONSUMER_BUILD:-}" ] \
  || [ "${CRYSTA_CONSUMER_SRC:-}" = "hidden-surface-control" ] \
  || { [ -n "${CRYSTA_CONSUMER_SRC:-}" ] && [ -f "${CRYSTA_CONSUMER_SRC}/CMakeLists.txt" ]; }; }; then
  echo "REFUSING: CRYSTA_SDK_DIR builds build/ci-consumer, which no runtime reader selects without EDI_USE_CONSUMER_BUILD or CRYSTA_CONSUMER_SRC (the SDK's source tree)" >&2
  exit 1
fi

# `.lock.d`, not `.lock`: the OLD flock implementation left a regular FILE at the bare path,
# and `mkdir` can never succeed against one — a checkout carrying that legacy file would wait
# out the whole deadline and then refuse, forever. Measured on this box, in both repos. A
# distinct directory-shaped path makes the migration inert instead of fatal.
BUILD_LOCK="$ROOT/build/.core-build.lock.d"
mkdir -p "$(dirname "$BUILD_LOCK")"
# The lock is `mkdir`, NOT `flock`, and it is NOT taken via `exec`. Two defects were fused here:
# `flock` is util-linux and macOS ships none (conda-forge has no osx-arm64 flock either, so it
# cannot be pinned the way bash and coreutils were) — so `command -v flock` failed on the macOS
# leg and the lock VANISHED, with no else branch and no message. And `exec` REPLACES this shell,
# so nothing downstream could ever have reported it. `mkdir` is atomic on POSIX and needs no
# re-exec, which is what makes the failure sayable at all.
BUILD_LOCK_WAIT_S="${EDI_CORE_BUILD_LOCK_WAIT_S:-1800}"
_waited=0
until mkdir "$BUILD_LOCK" 2>/dev/null; do
  if [ "$_waited" -ge "$BUILD_LOCK_WAIT_S" ]; then
    echo "REFUSING: another core build has held $BUILD_LOCK for ${BUILD_LOCK_WAIT_S}s." >&2
    echo "Two concurrent builds interleave writes into one prefix and the loser observes a" >&2
    echo "half-installed tree. If no build is running, an earlier one was killed: remove" >&2
    echo "$BUILD_LOCK." >&2
    exit 1
  fi
  sleep 1
  _waited=$((_waited + 1))
done
# Released on ANY exit, so an ordinary run never leaves it behind; a killed run does, and the
# bounded wait above then refuses loudly by name rather than hanging the gate forever.
trap 'rm -f "$BUILD_LOCK/owner"; rmdir "$BUILD_LOCK" 2>/dev/null || true' EXIT
# Build-crysta.sh below runs inside THIS acquisition — a token only this holder wrote, never a path
export EDI_PRODUCER_LOCK_HELD="$$.$RANDOM.$RANDOM"; printf '%s\n' "$EDI_PRODUCER_LOCK_HELD" >"$BUILD_LOCK/owner"
# Acquire crysta as a CMake package, inside this producer lock: the pinned SDK (ADR-0017), or
# CRYSTA_SDK_DIR's candidate. Needs the crysta link deps in the env (eigen/sleef/openmp) — see pixi.toml.
bash tools/ci/build-crysta.sh
# The linked commit's corpus and reference source for edi's tests (fetched, never built).
bash tools/ci/crysta-src.sh
# A consumer job restores the artifact `native · <platform>` built once for this run, each bound field
# and every restored byte checked against it, and compiles nothing.
if [ "${EDI_NATIVE_ARTIFACT:-}" = 1 ]; then
  python tools/ci/edi_native.py restore; exit $?  # never exec: the EXIT trap releases the lock
fi
# In the crysta->edi consumer-contract direction the crysta package is the candidate SDK in its own
# prefix, so edi configures against THAT prefix and into its own build tree. Keeping the two apart is
# what lets a consumer run and edi's own pinned build coexist in one checkout without either
# invalidating the other.
if [ -n "${CRYSTA_SDK_DIR:-}" ]; then
  CRYSTA_PREFIX="$ROOT/build/crysta-consumer-prefix"
  EDI_BUILD_DIR=build/ci-consumer
else
  CRYSTA_PREFIX="$ROOT/build/crysta-prefix"
  EDI_BUILD_DIR=build/ci
fi
# The declared deployment target on every configure, as for crysta above, so edi's objects and
# its link agree with the crysta objects they link.
cmake -S "$SRC" -B "$EDI_BUILD_DIR" -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="$CRYSTA_PREFIX" \
  -DCMAKE_OSX_DEPLOYMENT_TARGET="${MACOSX_DEPLOYMENT_TARGET:-}"
cmake --build "$EDI_BUILD_DIR" -j
# Further targets in this same tree, under this lock (the C++ tier's edi_tests).
[ -z "${EDI_CORE_TARGETS:-}" ] || cmake --build "$EDI_BUILD_DIR" --target ${EDI_CORE_TARGETS} -j
# Review-7 F7: tie provenance to the edi artifact actually LINKED. The prefix stamp and source
# record are mutable across resolves; this record names the crysta the just-built edi contains,
# and downstream consumers select it instead of re-reading whatever a later resolve left behind.
cp "$CRYSTA_PREFIX/.crysta-sha" "$EDI_BUILD_DIR/.crysta-linked-sha"
