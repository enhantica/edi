#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# pytest wrapper for the pre-code skeleton: exit code 5 ("no tests collected")
# passes; anything else is authoritative. The gate tightens automatically the
# moment the first real test lands.
set -uo pipefail
pytest "$@"
ec=$?
if [ "$ec" -eq 5 ]; then
  echo "pytest: no tests collected yet — skeleton pass"
  exit 0
fi
exit "$ec"
