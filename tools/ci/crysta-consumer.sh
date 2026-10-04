#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Zero-Python installed-consumer gate: prove the pinned, installed crysta::crysta package is consumable
# by a FRESH C++-only project — `find_package(crysta)` + link + run a real public call — with
# Python/Python3 discovery DISABLED, so the proof cannot lean on edi's Python/nanobind env. The current
# `core-build` configures the whole edi tree with EDI_BUILD_BINDINGS=ON in a Python env, so it does not
# prove this; this gate does.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$ROOT/tools/ci/crysta-consumer"
BUILD="$ROOT/build/crysta-consumer"

# Review-8 F3 + review-9 F3: this gate proves the CONFIGURATION actually selected, by the
# SAME precedence verification.py and lib/edi/__init__.py use — an explicit EDI_EXTENSION_DIR
# names the artifact outright and outranks the explicit consumer selector
# EDI_USE_CONSUMER_BUILD (CRYSTA_CONSUMER_SRC is the build-time source path and never
# selects a configuration at runtime); an extension dir this script cannot map to a known
# configuration is REFUSED rather than silently proven as the ordinary one (proving source A
# while the selected artifact contains B is the exact defect). The consumer-contract build has
# its own prefix and linked stamp and, by design, no float source record.
CONFIGURATION=""
if [ -n "${EDI_EXTENSION_DIR:-}" ]; then
  # Review-10 F3: resolve the COMPLETE selected artifact directory FIRST — physically, the way
  # the importer and the verification label do — and only then classify it. Discarding the
  # last component before resolving let a symlink inside one configuration select the OTHER
  # artifact while this gate proved the unselected source.
  EXT_DIR="$(cd "$EDI_EXTENSION_DIR" 2>/dev/null && pwd -P)" || EXT_DIR=""
  ORDINARY_EXT="$(cd "$ROOT/build/ci/python/edi" 2>/dev/null && pwd -P)" || ORDINARY_EXT=""
  CONSUMER_EXT="$(cd "$ROOT/build/ci-consumer/python/edi" 2>/dev/null && pwd -P)" || CONSUMER_EXT=""
  if [ -n "$EXT_DIR" ] && [ -n "$ORDINARY_EXT" ] && [ "$EXT_DIR" = "$ORDINARY_EXT" ]; then
    CONFIGURATION="ordinary"
  elif [ -n "$EXT_DIR" ] && [ -n "$CONSUMER_EXT" ] && [ "$EXT_DIR" = "$CONSUMER_EXT" ]; then
    CONFIGURATION="consumer"
  else
    echo "ERROR: EDI_EXTENSION_DIR=$EDI_EXTENSION_DIR resolves to '${EXT_DIR:-<unresolvable>}', which this gate cannot reconcile with a known build configuration (expected the resolved <repo>/build/ci/python/edi or <repo>/build/ci-consumer/python/edi) — refusing rather than proving a different artifact's source" >&2
    exit 1
  fi
elif [ -n "${EDI_USE_CONSUMER_BUILD:-}" ] \
  || [ "${CRYSTA_CONSUMER_SRC:-}" = "hidden-surface-control" ] \
  || { [ -n "${CRYSTA_CONSUMER_SRC:-}" ] && [ -f "${CRYSTA_CONSUMER_SRC}/CMakeLists.txt" ]; }; then
  # The explicit selector, the hidden control's exact literal (exempt BY NAME), or a source
  # path carrying the source-tree witness CMakeLists.txt — never any other bare truthy string,
  # which used to select a possibly stale ci-consumer artifact. ONE definition, shared
  # verbatim by all four selection sites: lib/edi/__init__.py,
  # verification._consumer_source_selects, python_surface_superset.resolve_prefix and here.
  CONFIGURATION="consumer"
else
  CONFIGURATION="ordinary"
fi
if [ "$CONFIGURATION" = "consumer" ]; then
  PREFIX="$ROOT/build/crysta-consumer-prefix"
  LINKED="$ROOT/build/ci-consumer/.crysta-linked-sha"
  RECORD=""
else
  PREFIX="$ROOT/build/crysta-prefix"
  LINKED="$ROOT/build/ci/.crysta-linked-sha"
  RECORD="$ROOT/build/crysta-src/CRYSTA_SOURCE_SHA"
fi

# Review-7 F7: ONE crysta source per verification unit. This gate proves the package core-build
# already resolved, installed and LINKED into edi — it never re-resolves the float, which could
# overwrite the source records with a newer main while the already-linked edi still contains the
# older engine (crysta is a static library). It SELECTS the unit's matching records for the
# chosen configuration and refuses on absence or disagreement.
STAMP="$PREFIX/.crysta-sha"
for f in $RECORD "$STAMP" "$LINKED"; do
  [ -f "$f" ] || { echo "ERROR: $f missing — run 'pixi run core-build' first (same configuration); this gate consumes that unit's crysta, it never resolves its own" >&2; exit 1; }
done
PREFIX_SHA="$(cat "$STAMP")"; LINKED_SHA="$(cat "$LINKED")"
if [ "$PREFIX_SHA" != "$LINKED_SHA" ]; then
  echo "ERROR: crysta records disagree (prefix $PREFIX_SHA, linked $LINKED_SHA) — rerun 'pixi run core-build' so one source flows through the whole unit" >&2
  exit 1
fi
if [ -n "$RECORD" ]; then
  SRC_SHA="$(cat "$RECORD")"
  if [ "$SRC_SHA" != "$PREFIX_SHA" ]; then
    echo "ERROR: crysta source records disagree (source $SRC_SHA, prefix $PREFIX_SHA, linked $LINKED_SHA) — rerun 'pixi run core-build' so one source flows through the whole unit" >&2
    exit 1
  fi
fi
# A stale consumer artifact must not follow a changed live source. When the consumer
# configuration is explicitly selected and the build-time source path names a real tree, the
# tree's current commit must be the one this artifact was linked with — a mismatch names both
# rather than proving a crysta that was never built into the unit.
if [ "$CONFIGURATION" = "consumer" ] && [ -n "${CRYSTA_CONSUMER_SRC:-}" ] \
  && [ -f "${CRYSTA_CONSUMER_SRC}/CMakeLists.txt" ]; then
  LIVE_SHA="$(git -C "$CRYSTA_CONSUMER_SRC" rev-parse HEAD 2>/dev/null || true)"
  if [ -n "$LIVE_SHA" ] && [ "$LIVE_SHA" != "$LINKED_SHA" ]; then
    echo "ERROR: the consumer artifact was linked with stale crysta source $LINKED_SHA but the live source $CRYSTA_CONSUMER_SRC is now at $LIVE_SHA — rerun 'pixi run core-build' so the unit proves the crysta actually built" >&2
    exit 1
  fi
fi
echo "crysta-consumer: proving the unit's linked crysta $PREFIX_SHA ($CONFIGURATION configuration)"

# Configure the standalone consumer with Python discovery disabled — a fresh C++-only project.
rm -rf "$BUILD"
# --no-warn-unused-cli: the disable-Python flags are intentionally belt-and-suspenders; when the consumer
# + crysta config never look for Python at all, CMake reports them "unused" — which is the point.
cmake -S "$SRC" -B "$BUILD" -G Ninja --no-warn-unused-cli -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="$PREFIX" \
  -DCMAKE_DISABLE_FIND_PACKAGE_Python=ON \
  -DCMAKE_DISABLE_FIND_PACKAGE_Python2=ON \
  -DCMAKE_DISABLE_FIND_PACKAGE_Python3=ON
cmake --build "$BUILD" -j
"$BUILD/crysta_consumer"
echo "crysta zero-Python installed-consumer gate: PASS"
