# SPDX-License-Identifier: BSD-3-Clause
cmake_minimum_required(VERSION 3.21)

# edi — one C++/CMake project builds the product core, the CLI, and (option-gated) the one
# QML app host (ADR-0002/0009). `core` + `cli` are Qt-free and build in the default pixi env
# (`pixi run core-build`); the app host is built only when EDI_BUILD_APP=ON and Qt6 is
# present. The app surface waits on gui-components G01–G04 (ADR-0005 / D4), so E01 does not
# build it — this is reviewable scaffolding that activates at E04 (desktop) / E07 (WASM).
project(edi LANGUAGES CXX)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_subdirectory(core)
add_subdirectory(cli)

# The thin nanobind Python bindings over the core (ADR-0009). Build-time deps: Python + nanobind.
option(EDI_BUILD_BINDINGS "Build the nanobind Python bindings (_edi, emitted per configuration)" ON)
if(EDI_BUILD_BINDINGS)
    add_subdirectory(lib)
endif()

# The one QML app host — desktop + WASM targets from one source tree (ADR-0006/0009/0015).
# Off by default: the default pixi environment is Qt-free; the `app` environment builds it
# (`pixi run -e app app-build`, tools/ci/app-build.sh). A C++ host only.
option(EDI_BUILD_APP "Build the Qt/QML app host; needs Qt6" OFF)
if(EDI_BUILD_APP)
    # CorePrivate: the project archive (app/src/web_files.cpp); the browser build also reads the browser's files
    # through GuiPrivate's header. Qt warns that a private module ties the build to its Qt version: edi pins that
    # version exactly (ADR-0023 §5), so the warning is off.
    set(QT_NO_PRIVATE_MODULE_WARNING ON)
    find_package(Qt6 REQUIRED COMPONENTS Gui Qml Quick QuickControls2 QuickTest Graphs Quick3D CorePrivate Concurrent)
    if(EMSCRIPTEN)
        find_package(Qt6 REQUIRED COMPONENTS GuiPrivate)
    endif()
    qt_standard_project_setup(REQUIRES 6.8)
    qt_policy(SET QTP0004 NEW)  # a qmldir per QML subdirectory, so tooling resolves pages in subfolders
    add_subdirectory(app)
endif()
