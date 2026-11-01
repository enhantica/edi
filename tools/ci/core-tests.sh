#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# The nightly-only cohort is declared once, alongside the other execution groups.
set -euo pipefail
set --
if [ "${EDI_RUN_NIGHTLY_ONLY:-false}" != true ]; then
  nightly="$(python -c 'import json; print("\n".join(json.load(open("tests/test-groups.json"))["groups"]["nightly-only"]["paths"]))')"
  [ -n "$nightly" ] || { echo "core-tests: the nightly-only group names no files" >&2; exit 2; }
  while IFS= read -r path; do set -- "$@" "--ignore=$path"; done <<< "$nightly"
fi
exec python -m pytest tests/unit tests/integration --ignore=tests/integration/app -q "$@"
