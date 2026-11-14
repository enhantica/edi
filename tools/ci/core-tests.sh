#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# The nightly-only and weekly-only cohorts are declared once, alongside the other execution groups.
set -euo pipefail
command=(python -m pytest tests/unit tests/integration --ignore=tests/integration/app -q)
leave_out() {
  local paths
  paths="$(python -c 'import json, sys; sys.stdout.reconfigure(newline="\n"); print("\n".join(json.load(open("tests/test-groups.json"))["groups"][sys.argv[1]]["paths"]))' "$1")"
  [ -n "$paths" ] || { echo "core-tests: the $1 group names no files" >&2; exit 2; }
  while IFS= read -r path; do command+=("--ignore=$path"); done <<< "$paths"
}
if [ "${EDI_RUN_NIGHTLY_ONLY:-false}" != true ]; then leave_out nightly-only; fi
if [ "${EDI_RUN_WEEKLY_ONLY:-false}" != true ]; then leave_out weekly-only; fi
exec "${command[@]}" "$@"
