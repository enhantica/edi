#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Runs moc for every target of the app's build tree. clang-tidy reads the compile commands of every app source, test
# runners included, and a source that includes its own `.moc` cannot be read until that file exists; app-build builds
# only some of the targets.
set -euo pipefail
cd "$(dirname "$0")/../.."
[ -f build/app/build.ninja ] || { echo "app-moc: build/app is not configured; run app-build first" >&2; exit 1; }
mapfile -t targets < <(ninja -C build/app -t targets all | grep -o '^[A-Za-z0-9_]*_autogen:' | tr -d ':' | sort -u)
[ "${#targets[@]}" -gt 0 ] || { echo "app-moc: build/app has no moc targets" >&2; exit 1; }
cmake --build build/app --target "${targets[@]}"
