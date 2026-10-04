#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Fetch — never build — the source of the crysta edi links: edi's tests read crysta's fitting corpus and
# reference source at exactly the commit the pinned SDK was built from, and the SDK carries neither. The
# commit is the linked prefix's `.crysta-sha` (tools/ci/build-crysta.sh); the tree lands in
# build/crysta-src with that sha recorded. The consumer configuration (CRYSTA_SDK_DIR) reads its source
# from CRYSTA_CONSUMER_SRC instead, so nothing is fetched for it.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
[ -z "${CRYSTA_SDK_DIR:-}" ] || exit 0
# Build/crysta-src is checked out and cleaned under edi's producer lock (tools/ci/producer-lock.sh).
. "$ROOT/tools/ci/producer-lock.sh"; edi_producer_lock "$ROOT"
SHA="$(cat "$ROOT/build/crysta-prefix/.crysta-sha" 2>/dev/null)" \
  || { echo "ERROR: build/crysta-prefix/.crysta-sha is missing — run tools/ci/build-crysta.sh first" >&2; exit 1; }
SRC="$ROOT/build/crysta-src"
if [ "$(cat "$SRC/CRYSTA_SOURCE_SHA" 2>/dev/null)" = "$SHA" ] && [ "$(git -C "$SRC" rev-parse HEAD 2>/dev/null)" = "$SHA" ]; then
  exit 0
fi
# shellcheck source=tools/ci/crysta-source.sh
. "$ROOT/tools/ci/crysta-source.sh"
[ -d "$SRC/.git" ] || git init -q "$SRC"
if ! git -C "$SRC" cat-file -e "${SHA}^{commit}" 2>/dev/null; then
  crysta_remote "fetch" -C "$SRC" fetch -q --depth 1 "$(crysta_url)" "$SHA" \
    || { echo "ERROR: crysta $SHA (the pinned SDK's source) could not be fetched:" >&2; _crysta_redact "$CRYSTA_REMOTE_OUT" >&2; echo >&2; exit 1; }
fi
git -C "$SRC" checkout -qf --detach "$SHA"
git -C "$SRC" clean -qfdx
printf '%s\n' "$SHA" >"$SRC/CRYSTA_SOURCE_SHA"
echo "crysta-source: $SHA (fetched for the corpus and reference readers; never built)"
