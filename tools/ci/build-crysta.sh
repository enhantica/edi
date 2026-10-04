#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Acquire crysta as a CMake package: the pinned, prebuilt C++ SDK crysta's CI built and tested (edi
# ADR-0017). No path compiles crysta.
#
# The pin is pixi.toml's CRYSTA_SDK_TAG / CRYSTA_SDK_SHA256 for this platform. tools/ci/crysta_sdk.py
# reuses build/crysta-sdk/<sha>-<platform>/ when its recorded sha256 matches the pin, else downloads the
# release asset over the REST API (curl; no `gh` on the CI fleet), verifies the sha256, unpacks it and
# checks its toolchain fingerprint against this environment's pixi.lock (I25), refusing before anything
# configures. It prints the provenance line the CI evidence binds:
#   crysta: using SDK build-<sha> tree <tree> sha256 <h> platform <p>
#
# The prefix every consumer reads (build/crysta-prefix, suffixed per pixi environment as before) is a
# link to the SDK, and `.crysta-sha` in it records the SDK's source commit. (The corpus and reference
# source edi's tests read, which the SDK does not carry, are fetched by tools/ci/crysta-src.sh.)
#
#   CRYSTA_SDK_DIR       an unpacked SDK to use instead of the pin: crysta's edi-verification candidate
#                        or a diagnostic. Same fingerprint check; its own prefix
#                        (build/crysta-consumer-prefix) so the pinned records are never touched. The
#                        consumer configuration's source (corpus, reference) is CRYSTA_CONSUMER_SRC,
#                        which must then be the SDK's source tree at its commit.
#   CRYSTA_CONSUMER_SRC  refused without CRYSTA_SDK_DIR: a crysta working tree is never compiled here.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"   # edi repo root
cd "$ROOT"
# One prefix per pixi environment; the default keeps the unsuffixed paths every core consumer reads,
# and app-build.sh derives the same suffix (keep in step).
ENV_NAME="${PIXI_ENVIRONMENT_NAME:-$(basename "${CONDA_PREFIX:-default}")}"
case "$ENV_NAME" in default | "") ENV_SUFFIX="" ;; *) ENV_SUFFIX="-$ENV_NAME" ;; esac
# Seam 12: the one platform mapping in this script — the pixi platform the task runs on (PIXI_PLATFORM; the app
# environment's linux-64-app is linux-64), else the runner's labels, else the host.
case "${PIXI_PLATFORM:-${RUNNER_OS:-$(uname -s)}-${RUNNER_ARCH:-$(uname -m)}}" in
  linux-64 | linux-64-app | Linux-X64 | Linux-x86_64) PLATFORM=linux-64 ;;
  osx-arm64 | macOS-ARM64 | Darwin-arm64) PLATFORM=osx-arm64 ;;
  *) echo "ERROR: no crysta SDK is built for ${PIXI_PLATFORM:-$(uname -s)-$(uname -m)} (edi ADR-0017: linux-64, osx-arm64)" >&2; exit 1 ;;
esac

# The prefix is shared mutable state: a pytest worker never writes it (core-build's lock covers its callers).
[ -z "${PYTEST_XDIST_WORKER:-}" ] || { echo "REFUSING: pytest worker ${PYTEST_XDIST_WORKER} may not write the crysta prefix" >&2; exit 1; }
# The prefix and the SDK cache are written under edi's producer lock (tools/ci/producer-lock.sh).
. "$ROOT/tools/ci/producer-lock.sh"; edi_producer_lock "$ROOT"
if [ -n "${CRYSTA_SDK_DIR:-}" ]; then
  PREFIX="$ROOT/build/crysta-consumer-prefix$ENV_SUFFIX"
  OUT="$(python tools/ci/crysta_sdk.py check --sdk "$CRYSTA_SDK_DIR" --platform "$PLATFORM")"
elif [ -n "${CRYSTA_CONSUMER_SRC:-}" ]; then
  echo "ERROR: CRYSTA_CONSUMER_SRC=$CRYSTA_CONSUMER_SRC without CRYSTA_SDK_DIR — edi never compiles crysta (ADR-0017); pack an SDK (crysta: pixi run -e cpp-ci sdk-pack) and set CRYSTA_SDK_DIR" >&2
  exit 1
else
  PREFIX="$ROOT/build/crysta-prefix$ENV_SUFFIX"
  OUT="$(python tools/ci/crysta_sdk.py fetch --platform "$PLATFORM")"
fi
# ONE provenance line per CI job (RUNNER_TEMP is job-scoped) — a later call linking the same SDK is silent, one
# linking a different SDK logs again, so a contradiction stays two lines the reader refuses.
LINE="${OUT%%$'\n'*}" SEEN="${RUNNER_TEMP:+$RUNNER_TEMP/crysta-sdk-line}"   # crysta: using SDK build-<sha> tree <tree> ...
if [ -z "$SEEN" ] || [ "$(cat "$SEEN" 2>/dev/null)" != "$LINE" ]; then echo "$LINE"; [ -z "$SEEN" ] || printf '%s\n' "$LINE" >"$SEEN"; fi
SDK="${OUT##*$'\n'}"
SHA="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["source_sha"])' "$SDK/share/crysta-sdk/manifest.json")"
# The prefix is edi's own directory linking the SDK's top-level entries, so the SDK itself — a cache entry,
# or a caller's CRYSTA_SDK_DIR — is never written; `.crysta-sha` records the SDK's source commit here.
# F02: a prefix already linking exactly this SDK is left as it is — a reader building against it is never disturbed.
want="$(for e in "$SDK"/*; do printf '%s %s\n' "$(basename "$e")" "$e"; done; echo "$SHA")"
have="$(cd "$PREFIX" 2>/dev/null && for f in *; do printf '%s %s\n' "$f" "$(readlink "$f")"; done; cat .crysta-sha 2>/dev/null)" || have=""
if [ "$want" != "$have" ]; then
  rm -rf "$PREFIX" && mkdir -p "$PREFIX"
  for entry in "$SDK"/*; do ln -s "$entry" "$PREFIX/$(basename "$entry")"; done
  printf '%s\n' "$SHA" >"$PREFIX/.crysta-sha"
fi

if [ -n "${CRYSTA_SDK_DIR:-}" ] && [ -n "${CRYSTA_CONSUMER_SRC:-}" ]; then
  # The consumer configuration's source (corpus, reference) is the caller's tree: the SDK's own commit.
  live="$(git -C "$CRYSTA_CONSUMER_SRC" rev-parse HEAD 2>/dev/null || echo none)"
  [ "$live" = "$SHA" ] || { echo "ERROR: CRYSTA_CONSUMER_SRC is at $live but the SDK was built from $SHA" >&2; exit 1; }
fi
echo "crysta::crysta ($SHA) from the SDK at $SDK, linked as $PREFIX"
