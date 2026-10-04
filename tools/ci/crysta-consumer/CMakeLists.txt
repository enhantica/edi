# SPDX-License-Identifier: BSD-3-Clause
# Standalone zero-Python consumer of the installed crysta::crysta package. A fresh C++-only project —
# no edi, no Python — that `find_package(crysta)` and links + calls the public API, proving the pinned
# installed package is consumable on its own. Built by tools/ci/crysta-consumer.sh with Python
# discovery disabled.
cmake_minimum_required(VERSION 3.21)
project(crysta_consumer LANGUAGES CXX)

find_package(crysta CONFIG REQUIRED)

add_executable(crysta_consumer main.cpp)
target_compile_features(crysta_consumer PRIVATE cxx_std_20)  # crysta public headers use C++20
target_link_libraries(crysta_consumer PRIVATE crysta::crysta)
