#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# cppcheck over edi's own C++ (edi ADR-0089); any finding is an error. Qt's macros come from cppcheck's Qt library.
set -euo pipefail
cd "$(dirname "$0")/../.."
cppcheck --enable=warning,performance,portability --std=c++20 --language=c++ --library=qt --error-exitcode=1 \
    --inline-suppr --suppress=missingIncludeSystem --quiet -j "${EDI_CPPCHECK_JOBS:-4}" \
    -I core/include -I core/src -I app/src -I assistant/native \
    core/src cli lib/src app/src app/main.cpp app/tools app/tests assistant/native
