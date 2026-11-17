# SPDX-License-Identifier: BSD-3-Clause
# The warning sets for edi's own C++, the same as crysta's, and EDI_WERROR to make them errors (edi ADR-0093). They go on
# each hand-written source file, not on the targets, so Qt's generated sources, nanobind's sources and the code under
# third_party/ build as before.
option(EDI_WERROR "Treat warnings in edi's own C++ as errors" OFF)
if(MSVC)
    set(EDI_WARNINGS /W4)
    set(EDI_BASE_WARNINGS /W4)
else()
    set(EDI_WARNINGS -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wold-style-cast -Wcast-align
        -Wnull-dereference -Woverloaded-virtual -Wdouble-promotion)
    # GCC's -Wshadow=local leaves out a constructor parameter named as its member; Clang only has plain -Wshadow.
    if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
        list(APPEND EDI_WARNINGS -Wshadow=local)
    else()
        list(APPEND EDI_WARNINGS -Wshadow)
    endif()
    # The Python bindings, like crysta's, take the base set: nanobind's headers are not system headers there.
    set(EDI_BASE_WARNINGS -Wall -Wextra -Wpedantic)
endif()
if(EDI_WERROR)
    if(MSVC)
        list(APPEND EDI_WARNINGS /WX)
        list(APPEND EDI_BASE_WARNINGS /WX)
    else()
        list(APPEND EDI_WARNINGS -Werror)
        list(APPEND EDI_BASE_WARNINGS -Werror)
    endif()
endif()

# Applies the warnings to every C++ source of the TARGETS under edi's own directories (core, cli, lib, app, assistant),
# leaving out the hidden test tiers and third_party/. BASE takes the base set. QT marks targets built on Qt: there GCC
# reports -Wnull-dereference after inlining Qt's smart pointers and containers, on paths the code has already checked,
# so it is off on GCC; Clang keeps it, and clang-tidy's analyzer checks null dereferences on every path.
function(edi_apply_warnings)
    cmake_parse_arguments(PARSE_ARGV 0 arg "QT;BASE" "" "TARGETS")
    if(arg_BASE)
        set(warnings ${EDI_BASE_WARNINGS})
    else()
        set(warnings ${EDI_WARNINGS})
    endif()
    if(arg_QT AND CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
        list(APPEND warnings -Wno-null-dereference)
    endif()
    set(own "^${PROJECT_SOURCE_DIR}/(core|cli|lib|app|assistant)/")
    set(skip "^${PROJECT_SOURCE_DIR}/(core/third_party|third_party)/")
    foreach(target IN LISTS arg_TARGETS)
        if(NOT TARGET ${target})
            continue()
        endif()
        get_target_property(directory ${target} SOURCE_DIR)
        get_target_property(sources ${target} SOURCES)
        foreach(source IN LISTS sources)
            if(NOT source MATCHES "\\.cpp$" OR source MATCHES "^\\$<")
                continue()
            endif()
            cmake_path(ABSOLUTE_PATH source BASE_DIRECTORY ${directory} NORMALIZE OUTPUT_VARIABLE path)
            if(NOT path MATCHES "${own}" OR path MATCHES "${skip}")
                continue()
            endif()
            set_source_files_properties(${path} TARGET_DIRECTORY ${target} PROPERTIES COMPILE_OPTIONS "${warnings}")
        endforeach()
    endforeach()
endfunction()
