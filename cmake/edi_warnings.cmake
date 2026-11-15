# SPDX-License-Identifier: BSD-3-Clause
# The warning set for edi's own C++, the same as crysta's for its core, and EDI_WERROR to make it an error (edi
# ADR-0089). It goes on each hand-written source file, not on the targets, so Qt's generated sources and the code under
# third_party/ build as before.
option(EDI_WERROR "Treat warnings in edi's own C++ as errors" OFF)
if(MSVC)
    set(EDI_WARNINGS /W4)
else()
    set(EDI_WARNINGS -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wold-style-cast -Wcast-align
        -Wnull-dereference -Woverloaded-virtual -Wdouble-promotion)
    # GCC's -Wshadow=local leaves out a constructor parameter named as its member; Clang only has plain -Wshadow.
    if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
        list(APPEND EDI_WARNINGS -Wshadow=local)
    else()
        list(APPEND EDI_WARNINGS -Wshadow)
    endif()
endif()
if(EDI_WERROR)
    if(MSVC)
        list(APPEND EDI_WARNINGS /WX)
    else()
        list(APPEND EDI_WARNINGS -Werror)
    endif()
endif()

# Applies EDI_WARNINGS to every C++ source of the given targets that lives in this repository: not generated in the
# build tree, not under third_party/, and not in the hidden test tiers.
function(edi_apply_warnings)
    set(skip "^(${CMAKE_BINARY_DIR}|${PROJECT_SOURCE_DIR}/third_party|${PROJECT_SOURCE_DIR}/core/third_party|${PROJECT_SOURCE_DIR}/tests/(unit|integration|system))/")
    foreach(target IN LISTS ARGN)
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
            if(path MATCHES "${skip}")
                continue()
            endif()
            set_source_files_properties(${path} TARGET_DIRECTORY ${target} PROPERTIES COMPILE_OPTIONS "${EDI_WARNINGS}")
        endforeach()
    endforeach()
endfunction()
