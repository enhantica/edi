# SPDX-License-Identifier: BSD-3-Clause
# ADR-0020 §3: the ThreadSanitizer tree. edi's core is compiled here itself, with the sanitizer,
# against a crysta built from the pinned source with it too (tools/ci/tsan-worker.sh) — the
# prebuilt SDK is not instrumented, and a race inside it would go unseen. Never part of the
# product build.
cmake_minimum_required(VERSION 3.24)
project(edi_tsan CXX)
find_package(crysta CONFIG REQUIRED)
find_package(Threads REQUIRED)
file(GLOB EDI_CORE_SOURCES ${EDI_ROOT}/core/src/*.cpp)
add_library(edi_core_tsan STATIC ${EDI_CORE_SOURCES})
target_compile_features(edi_core_tsan PUBLIC cxx_std_20)
target_include_directories(edi_core_tsan PUBLIC ${EDI_ROOT}/core/include ${EDI_ROOT}/core/src
                                                ${EDI_ROOT}/tests/fixtures)
target_link_libraries(edi_core_tsan PUBLIC crysta::crysta Threads::Threads)

# The scenario: the tests lane's probe (hidden tier), run by tsan-worker.sh.
add_executable(e04_t9_tsan_probe ${EDI_ROOT}/tests/unit/cpp/e04_t9_tsan_probe.cpp)
target_link_libraries(e04_t9_tsan_probe PRIVATE edi_core_tsan)

# The negative control: a deliberate data race, which the sanitizer must report. A tree that
# reports nothing here is not instrumented, and its silence on the probe would mean nothing.
add_executable(tsan_control control.cpp)
target_compile_features(tsan_control PRIVATE cxx_std_20)
target_link_libraries(tsan_control PRIVATE Threads::Threads)
