#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# edi ci-local: mirror the ON-MERGE Linux leg of .github/workflows/ ci.yml — NOT the PR tier. The
# ruled contract is ci-local ≡ merge-Linux exactly; the named irreducible residual is the macOS legs
# (`core · macOS`, `cli-python · macOS`, `app · macOS`), which no local box can run. Keep this list
# in lockstep with the workflow's non-PR path (job names are
# `<area> · <platform>`):
#   lint            -> pixi run check + format-check
#   core · Linux    -> pixi run core-build + crysta-consumer + group-full (the FULL suite:
#                                                  tests/unit + tests/integration + tests/system
#                                                  and the C++ tier; group-quick on a pull request)
#   cli-python      -> pixi run cli-projects
#   notebooks       -> pixi run notebook-tests
#   docs            -> pixi run docs-build (strict)
#   app · Linux     -> pixi run app-verify
# plus the repo's own audit gates that run inside verify (per-pr-audit, generated-regions).
# The wall-clock wrapper (I6) is retired (no aggregate time gate; per-test tier bounds
# only).
set -euo pipefail
cd "$(dirname "$0")/../.."

echo "[ci-local] edi on-merge Linux leg (lockstep with .github/workflows/ci.yml non-PR path)"
# `merge-tasks` = the verify chain (verify IS the full chain). The
# two selections are now EQUAL (the P1.14 narrowing retired with the `heavy` marker), so this
# mirror differs from verify only in job composition, never in which tests run.
pixi run merge-tasks
echo "[ci-local] green — residual not covered locally: the macOS legs (core, cli-python, app · macOS)"
