// SPDX-License-Identifier: BSD-3-Clause
// The doctest entry point for edi's C++ unit tier.
//
// Deliberately the ONLY translation unit that defines main: the tier's cases live in
// tests/unit/cpp/test_*.cpp and are compiled into the same `edi_tests` binary (see
// core/CMakeLists.txt). Keeping the entry point here — beside report_format_probe.cpp,
// the established home for implementation-lane-owned C++ test-side source — keeps it out
// of the repo-declared hidden surface (tests/hidden-surface.txt denies tests/unit/cpp/**),
// so the instrument and the cases it runs stay in separate lanes exactly as the Python
// hidden gates do.
#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include <doctest/doctest.h>
