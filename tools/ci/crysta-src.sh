#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# crysta's source at the built commit, for the corpus and reference readers and the web build, which the
# SDK does not carry (edi ADR-0083): exported from the crysta checkout in CRYSTA_SRC, which CI's crysta-source
# action makes and a desk names. Never fetched here.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
[ -z "${CRYSTA_SDK_DIR:-}" ] || exit 0
. "$ROOT/tools/ci/producer-lock.sh"; edi_producer_lock "$ROOT"
SHA="$(cat "$ROOT/build/crysta-prefix/.crysta-sha" 2>/dev/null)" \
  || { echo "ERROR: build/crysta-prefix/.crysta-sha is missing — run tools/ci/build-crysta.sh first" >&2; exit 1; }
SRC="$ROOT/build/crysta-src"
MANIFEST="$ROOT/build/crysta-prefix/share/crysta-sdk/manifest.json"
# An export is kept only while its files are still the SDK's tree; Windows keeps neither modes nor links, so there the
# recorded commit decides.
is_sdk_tree() { case "$(uname -s)" in MINGW* | MSYS* | CYGWIN*) return 0 ;; esac
  python3 "$ROOT/tools/ci/crysta_source_tree.py" check "$SRC" "$MANIFEST"; }
require_sdk_tree() {
  is_sdk_tree && return 0
  echo "ERROR: the exported crysta source is not the tree the SDK at $SHA was built from" >&2
  rm -rf "$SRC"
  exit 1
}
[ "$(cat "$SRC/CRYSTA_SOURCE_SHA" 2>/dev/null)" = "$SHA" ] && is_sdk_tree && exit 0
rm -rf "$SRC"
if [ -n "${CRYSTA_SRC:-}" ] && git -C "$CRYSTA_SRC" cat-file -e "${SHA}^{commit}" 2>/dev/null; then
  python3 "$ROOT/tools/ci/crysta_source_export.py" "$CRYSTA_SRC" "$SHA" "$SRC"
  require_sdk_tree
  python3 "$ROOT/tools/ci/crysta_source_receipt.py" "$CRYSTA_SRC" "$SHA" "$SRC/runner-source-objects.json"
else
  echo "ERROR: crysta $SHA's source is not in CRYSTA_SRC (a crysta checkout holding it)" >&2
  exit 1
fi
printf '%s\n' "$SHA" >"$SRC/CRYSTA_SOURCE_SHA"
echo "crysta-source: $SHA (for the corpus and reference readers and the web build; never built here)"
