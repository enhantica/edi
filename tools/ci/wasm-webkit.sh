#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# WebKit for the browser checks' route test (tests/system/manual/web_parallel_routes.mjs, edi ADR-0023): the
# Playwright driver locked in tests/fixtures/web_parallel/package-lock.json and the WebKit build it pins, in the
# toolchain cache, reinstalled only when the lock changes. Run by wasm-toolchain.sh.
#
# WebKit also needs system libraries. Where the runner allows sudo (the hosted CI runners), Playwright installs them
# with the system's package manager; elsewhere the ones the system lacks are unpacked from the system's own packages
# beside WebKit's libraries, without root.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=tools/ci/wasm-env.sh
. "$ROOT/tools/ci/wasm-env.sh"

FIXTURE="$ROOT/tests/fixtures/web_parallel"
PW="$(wasm_playwright_dir)"
NODE_BIN="$(echo "$EDI_WASM_TOOLCHAIN/emsdk-$EDI_WASM_EMSDK"/node/*/bin)"
export PATH="$NODE_BIN:$PATH" PLAYWRIGHT_BROWSERS_PATH="$PW/browsers"
CLI="$PW/node_modules/playwright-core/cli.js"

lock_id="$(sha256sum "$FIXTURE/package-lock.json" | cut -c1-64)"
if [ "$(cat "$PW/.edi-installed" 2>/dev/null)" != "$lock_id" ]; then
  rm -rf "$PW"
  mkdir -p "$PW"
  cp "$FIXTURE/package.json" "$FIXTURE/package-lock.json" "$PW/"
  (cd "$PW" && npm ci --no-audit --no-fund >/dev/null)
  node "$CLI" install webkit >/dev/null
  printf '%s\n' "$lock_id" >"$PW/.edi-installed"
fi

# The system libraries WebKit lacks, as Playwright's own host check names them (it re-checks on every install).
missing_libraries() {
  node "$CLI" install webkit 2>&1 | sed -n 's/^║[[:space:]]*\(lib[^[:space:]]*\.so[^[:space:]]*\)[[:space:]]*║$/\1/p' | sort -u
}

missing="$(missing_libraries)"
if [ -n "$missing" ]; then
  if sudo -n true 2>/dev/null; then
    node "$CLI" install-deps webkit >/dev/null
  else
    # The system's packages for WebKit, as Playwright names them, and the packages they depend on, downloaded and
    # unpacked without installing; only the missing libraries are copied beside WebKit's own.
    packages="$(node "$CLI" install-deps --dry-run webkit 2>/dev/null |
      sed -n 's/.*--no-install-recommends \([^"]*\).*/\1/p' | tr ' ' '\n' | grep -v '^$' | sort -u)"
    unpacked="$(mktemp -d)"
    mkdir -p "$unpacked/debs"
    (
      cd "$unpacked/debs"
      for package in $packages; do apt-get download "$package" >/dev/null 2>&1 || true; done
      depends="$(for deb in ./*.deb; do dpkg-deb -f "$deb" Depends 2>/dev/null; done |
        tr ',' '\n' | sed 's/[(|].*//; s/[[:space:]]//g' | grep -v '^$' | sort -u)"
      for package in $depends; do
        ls "${package}"_*.deb >/dev/null 2>&1 || apt-get download "$package" >/dev/null 2>&1 || true
      done
    )
    for deb in "$unpacked"/debs/*.deb; do
      [ -f "$deb" ] && dpkg -x "$deb" "$unpacked/root"
    done
    for library in $missing; do
      found="$(find "$unpacked/root" -name "$library" | head -n 1)"
      if [ -n "$found" ]; then
        for dir in "$PLAYWRIGHT_BROWSERS_PATH"/webkit-*/minibrowser-*/lib; do
          cp -L "$found" "$dir/"
        done
      fi
    done
    rm -rf "$unpacked"
  fi
  still="$(missing_libraries)"
  if [ -n "$still" ]; then
    echo "wasm-webkit: WebKit still lacks system libraries: $(echo "$still" | tr '\n' ' ')" >&2
    exit 1
  fi
fi
echo "wasm-webkit: Playwright $(node -p "require('$PW/node_modules/playwright-core/package.json').version") and its WebKit in $PW"
