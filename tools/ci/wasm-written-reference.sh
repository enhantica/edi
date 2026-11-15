#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Capture the ordinary native Save counterpart without replacing the independent raw anchors.
# Both browser check owners use this prerequisite (ADR-0023).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
OUT="${1:?the reference directory}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
module_sha="$(python -c 'import hashlib, pathlib, edi; print(hashlib.sha256(pathlib.Path(edi._edi.__file__).read_bytes()).hexdigest())')"
commit="$(git rev-parse HEAD)"
for case in lbco ncaf; do
  python -m tests.fixtures.e04_t11_wasm.written capture --root "$ROOT" --case "$case" \
    --reference "$OUT/$case" --module-sha256 "$module_sha" --build-commit "$commit"
done
