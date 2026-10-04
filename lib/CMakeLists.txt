# SPDX-License-Identifier: BSD-3-Clause
# edi Python bindings (ADR-0009): the thin nanobind module `_edi` over edi_core, emitted into the
# lib/edi package so the editable `import edi` resolves it. Build-time deps: Python + nanobind.
find_package(Python 3.10 COMPONENTS Interpreter Development.Module REQUIRED)
execute_process(
    COMMAND "${Python_EXECUTABLE}" -m nanobind --cmake_dir
    OUTPUT_VARIABLE NB_CMAKE_DIR OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
list(APPEND CMAKE_PREFIX_PATH "${NB_CMAKE_DIR}")
find_package(nanobind CONFIG REQUIRED)

# Embed the git HEAD the module was built from — regenerated on every build; the module carries
# it as `__build_commit__` (crysta's pattern).
set(EDI_BUILD_COMMIT_CPP "${CMAKE_BINARY_DIR}/edi_build_commit.cpp")
execute_process(COMMAND "${CMAKE_COMMAND}" -DSOURCE_DIR=${CMAKE_SOURCE_DIR}
                        -DOUT=${EDI_BUILD_COMMIT_CPP} -P "${CMAKE_SOURCE_DIR}/cmake/build_commit.cmake")
add_custom_target(edi_build_commit
    COMMAND "${CMAKE_COMMAND}" -DSOURCE_DIR=${CMAKE_SOURCE_DIR}
            -DOUT=${EDI_BUILD_COMMIT_CPP} -P "${CMAKE_SOURCE_DIR}/cmake/build_commit.cmake"
    BYPRODUCTS "${EDI_BUILD_COMMIT_CPP}"
    COMMENT "Embedding the source commit")

nanobind_add_module(_edi STABLE_ABI src/bindings.cpp "${EDI_BUILD_COMMIT_CPP}")
add_dependencies(_edi edi_build_commit)
target_link_libraries(_edi PRIVATE edi::core)
# Emit the module PER CONFIGURATION into the build tree — six configurations sharing the one
# source-tree lib/edi artifact relinked stale objects over one another, so runtime evidence
# could not name the configuration it came from. lib/edi/__init__.py resolves the
# configuration (EDI_EXTENSION_DIR, else the core-build.sh selection) and refuses a stray
# source-tree artifact.
set_target_properties(_edi PROPERTIES LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/python/edi")
