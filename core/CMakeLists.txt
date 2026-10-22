# SPDX-License-Identifier: BSD-3-Clause
# edi product core (ADR-0009): the C++ home for all product logic. Qt-free. From it holds the
# user-facing model + the crysta adapter (the only engine contact, public API only — ADR-0003). The
# adapter's edi-only logic — identity paths + label resolution, the canonical source encoding, the
# refinement boundary checks / bounds / write-back — lives in its own TUs on edi's side of the ADR-0003
# line (core/src-private headers, the adapter_test_access.hpp shape), so the unit tier can reach it
# without the engine; adapter.cpp keeps everything that holds a crysta type.
find_package(crysta CONFIG REQUIRED GLOBAL)  # shared native consumers also use imported targets

add_library(edi_core STATIC
    src/version.cpp
    src/adapter.cpp
    src/canonical_encoding.cpp
    src/parameter_paths.cpp
    src/fit_policy.cpp
    src/io.cpp
    src/validation.cpp
    src/report.cpp
    src/json.cpp
    src/assistant.cpp
    src/assistant_skills.cpp
    ${CMAKE_CURRENT_BINARY_DIR}/assistant_skills_data.cpp
    src/assistant_stream.cpp
    src/report_model.cpp
    src/report_json.cpp
    src/report_html.cpp
    src/report_save.cpp
    src/palette.cpp
    src/category_title.cpp
    src/duration_text.cpp
    src/correlation_matrix.cpp
    src/parameter_symbol.cpp
    src/su_text.cpp
    src/selectors.cpp
    src/worker.cpp
    src/live_preview.cpp
    src/fit_job.cpp
    src/presentation.cpp
    src/structure_scene.cpp
    ${CMAKE_CURRENT_BINARY_DIR}/element_styles_data.cpp
    ${CMAKE_CURRENT_BINARY_DIR}/report_js_data.cpp
    ${CMAKE_CURRENT_BINARY_DIR}/openai_capabilities_data.cpp
    ${CMAKE_CURRENT_BINARY_DIR}/palette_data.cpp
)
add_library(edi::core ALIAS edi_core)

# ADR-0022: the element table (data/elements/element-styles.tsv, PROVENANCE.md beside it) is embedded in
# the core as a string, so no runtime file lookup exists; element_style_table() parses it once. A change
# to the file reconfigures.
set(EDI_ELEMENT_STYLES_TSV ${PROJECT_SOURCE_DIR}/data/elements/element-styles.tsv)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${EDI_ELEMENT_STYLES_TSV})
file(READ ${EDI_ELEMENT_STYLES_TSV} EDI_ELEMENT_STYLES)
configure_file(src/element_styles_data.cpp.in ${CMAKE_CURRENT_BINARY_DIR}/element_styles_data.cpp @ONLY)

# The colour palettes (data/palettes, PROVENANCE.md beside them) are embedded the same way, one per edi::ColourScheme
# in its order; a change reconfigures.
set(EDI_PALETTES coast garden peaceful fog-forest sage okabe-ito paul-tol-bright paul-tol-muted tableau observable
    carbon dark2 petroff vivid nord solarized catppuccin apple)
set(EDI_PALETTE_TABLES "")
foreach(scheme IN LISTS EDI_PALETTES)
    set(palette_tsv ${PROJECT_SOURCE_DIR}/data/palettes/${scheme}.tsv)
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${palette_tsv})
    file(READ ${palette_tsv} palette)
    string(APPEND EDI_PALETTE_TABLES "    R\"edi_palette(${palette})edi_palette\",\n")
endforeach()
configure_file(src/palette_data.cpp.in ${CMAKE_CURRENT_BINARY_DIR}/palette_data.cpp @ONLY)

# ADR-0036: the HTML report's script (data/report/report.js) is embedded the same way, so every surface writes the same
# file with no lookup; a change to the script reconfigures.
set(EDI_REPORT_JS_FILE ${PROJECT_SOURCE_DIR}/data/report/report.js)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${EDI_REPORT_JS_FILE})
file(READ ${EDI_REPORT_JS_FILE} EDI_REPORT_JS)
configure_file(src/report_js_data.cpp.in ${CMAKE_CURRENT_BINARY_DIR}/report_js_data.cpp @ONLY)

set(EDI_OPENAI_CAPABILITIES_FILE ${PROJECT_SOURCE_DIR}/data/assistant/openai-capabilities.json)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${EDI_OPENAI_CAPABILITIES_FILE})
file(READ ${EDI_OPENAI_CAPABILITIES_FILE} EDI_OPENAI_CAPABILITIES)
configure_file(src/openai_capabilities_data.cpp.in ${CMAKE_CURRENT_BINARY_DIR}/openai_capabilities_data.cpp @ONLY)

# ADR0042: package-relative skills are immutable product resources, not runtime paths.
set(EDI_SKILL_ROOT ${PROJECT_SOURCE_DIR}/data/assistant/skills)
set(EDI_SKILL_INDEX_FILE ${EDI_SKILL_ROOT}/index.json)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${EDI_SKILL_INDEX_FILE})
file(READ ${EDI_SKILL_INDEX_FILE} EDI_SKILL_INDEX)
string(FIND "${EDI_SKILL_INDEX}" ")edi_skill\"" EDI_SKILL_INDEX_DELIMITER)
if(NOT EDI_SKILL_INDEX_DELIMITER EQUAL -1)
    message(FATAL_ERROR "Bundled skill index contains its reserved embedding delimiter")
endif()
string(JSON EDI_SKILL_COUNT LENGTH "${EDI_SKILL_INDEX}" skills)
if(EDI_SKILL_COUNT LESS 1)
    message(FATAL_ERROR "The bundled skill catalog must not be empty")
endif()
set(EDI_SKILL_RESOURCES "")
math(EXPR EDI_SKILL_LAST "${EDI_SKILL_COUNT} - 1")
foreach(EDI_SKILL_N RANGE ${EDI_SKILL_LAST})
    string(JSON EDI_SKILL_ID GET "${EDI_SKILL_INDEX}" skills ${EDI_SKILL_N} id)
    string(JSON EDI_SKILL_PATH GET "${EDI_SKILL_INDEX}" skills ${EDI_SKILL_N} path)
    string(JSON EDI_SKILL_HASH GET "${EDI_SKILL_INDEX}" skills ${EDI_SKILL_N} sha256)
    if(NOT EDI_SKILL_ID MATCHES "^[a-z][a-z0-9-]*$" OR NOT EDI_SKILL_PATH STREQUAL "${EDI_SKILL_ID}/SKILL.md")
        message(FATAL_ERROR "Invalid package-relative bundled skill identity/path")
    endif()
    set(EDI_SKILL_FILE ${EDI_SKILL_ROOT}/${EDI_SKILL_PATH})
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${EDI_SKILL_FILE})
    file(SHA256 ${EDI_SKILL_FILE} EDI_SKILL_ACTUAL_HASH)
    if(NOT EDI_SKILL_HASH STREQUAL EDI_SKILL_ACTUAL_HASH)
        message(FATAL_ERROR "Bundled skill content differs from its declared SHA256")
    endif()
    file(READ ${EDI_SKILL_FILE} EDI_SKILL_CONTENT)
    string(FIND "${EDI_SKILL_CONTENT}" ")edi_skill\"" EDI_SKILL_DELIMITER)
    if(NOT EDI_SKILL_DELIMITER EQUAL -1)
        message(FATAL_ERROR "Bundled skill contains its reserved embedding delimiter")
    endif()
    string(APPEND EDI_SKILL_RESOURCES "        {R\"edi_skill(${EDI_SKILL_ID})edi_skill\", R\"edi_skill(${EDI_SKILL_ACTUAL_HASH})edi_skill\", R\"edi_skill(${EDI_SKILL_CONTENT})edi_skill\"},\n")
endforeach()
configure_file(src/assistant_skills_data.cpp.in ${CMAKE_CURRENT_BINARY_DIR}/assistant_skills_data.cpp @ONLY)


target_include_directories(edi_core
    PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)
# crysta's public headers use C++20 (e.g. <numbers>), so the core (which consumes them through the
# adapter) compiles as C++20; the edi model surface itself stays plain value types.
target_compile_features(edi_core PUBLIC cxx_std_20)
# ADR-0020: the calculation worker runs one std::thread.
find_package(Threads REQUIRED)
target_link_libraries(edi_core PUBLIC crysta::crysta Threads::Threads)
# ADR-0023: the single-thread WebAssembly build runs the worker's jobs on the owner thread instead
# (tools/ci/wasm-build.sh sets it there; worker.cpp refuses an unthreaded Emscripten build without it).
option(EDI_WORKER_OWNER_THREAD "Run the calculation worker's jobs on the owner thread, with no thread" OFF)
target_compile_definitions(edi_core PUBLIC EDI_WORKER_OWNER_THREAD=$<BOOL:${EDI_WORKER_OWNER_THREAD}>)

# Test-only C++ probe: inspects the edi -> crysta conversion through the private
# `edi::detail` seam (src/adapter_test_access.hpp) rather than a public API. Built as a default target so
# `pixi run core-build` emits build/ci/core/e02_adapter_probe for the hidden pytest to run; ONLY this
# target gets core/src on its include path, so the seam header stays out of core/include + installation.
add_executable(e02_adapter_probe ${PROJECT_SOURCE_DIR}/tests/unit/cpp/e02_adapter_probe.cpp)
target_link_libraries(e02_adapter_probe PRIVATE edi_core)
target_include_directories(e02_adapter_probe PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)

# Test-only C++ probe: proves the `.edi` numeric grammar is locale-INDEPENDENT by parsing the
# pinned token corpus under an injected comma-decimal locale, which needs no system locale data and
# therefore runs on every platform. Same shape as the probe above — a default target so
# `pixi run core-build` emits build/ci/core/c09_t8_locale_probe for the hidden pytest to run.
add_executable(c09_t8_locale_probe ${PROJECT_SOURCE_DIR}/tests/unit/cpp/c09_t8_locale_probe.cpp)
target_link_libraries(c09_t8_locale_probe PRIVATE edi_core)
target_include_directories(c09_t8_locale_probe PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)

# Test-only C++ probe: the V1/e.s.d. internal probe formerly cmake-compiled AD-HOC inside a
# session fixture (~18 s per suite run, and a second mutable build tree). Same shape as the
# probes above - a default target so `pixi run core-build` emits
# build/ci/core/c09_t7_internal_probe for the pytest to run.
add_executable(c09_t7_internal_probe ${PROJECT_SOURCE_DIR}/tests/unit/cpp/c09_t7_internal_probe.cpp)
target_link_libraries(c09_t7_internal_probe PRIVATE edi_core)
target_include_directories(c09_t7_internal_probe PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)

# Each latency probe carries the commit it was built from (`-dirty` when tracked files differed) as bytes
# tools/ci/latency_bank.py reads from the executable it is about to run, so a bank row names the revision the timed
# binary was built from; regenerated on every build, as lib's stamp.
if(EXISTS ${PROJECT_SOURCE_DIR}/tests/unit/cpp/e04_t9_latency_probe.cpp
   OR EXISTS ${PROJECT_SOURCE_DIR}/tests/unit/cpp/e04_t10_latency_probe.cpp)
    set(EDI_PROBE_BUILD_COMMIT_CPP "${CMAKE_BINARY_DIR}/edi_probe_build_commit.cpp")
    execute_process(COMMAND "${CMAKE_COMMAND}" -DSOURCE_DIR=${PROJECT_SOURCE_DIR} -DOUT=${EDI_PROBE_BUILD_COMMIT_CPP}
                            -DMARKER=ON -DMARK_DIRTY=ON -P "${PROJECT_SOURCE_DIR}/cmake/build_commit.cmake")
    add_custom_target(edi_probe_build_commit
        COMMAND "${CMAKE_COMMAND}" -DSOURCE_DIR=${PROJECT_SOURCE_DIR} -DOUT=${EDI_PROBE_BUILD_COMMIT_CPP}
                -DMARKER=ON -DMARK_DIRTY=ON -P "${PROJECT_SOURCE_DIR}/cmake/build_commit.cmake"
        BYPRODUCTS "${EDI_PROBE_BUILD_COMMIT_CPP}"
        COMMENT "Embedding the source commit in the latency probes")
endif()

# Test-only C++ probe (edi ADR-0020 §5): the latency measurement with its own oracle, the tests
# lane's, which the ratchet gate runs once and `pixi run latency-bank` runs ten times. Same shape as
# the probes above; guarded, so the instrument and the probe can land in either order.
if(EXISTS ${PROJECT_SOURCE_DIR}/tests/unit/cpp/e04_t9_latency_probe.cpp)
    add_executable(e04_t9_latency_probe ${PROJECT_SOURCE_DIR}/tests/unit/cpp/e04_t9_latency_probe.cpp
                   "${EDI_PROBE_BUILD_COMMIT_CPP}")
    add_dependencies(e04_t9_latency_probe edi_probe_build_commit)
    target_link_libraries(e04_t9_latency_probe PRIVATE edi_core)
    target_include_directories(e04_t9_latency_probe PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src
                                                            ${PROJECT_SOURCE_DIR}/tests/fixtures)
endif()

# Test-only C++ probe (ADR-0022): the structure scene's presentation and update latency (V1, V2), the
# tests lane's, which `pixi run latency-bank` runs beside probe. The same shape and the same guard as.
if(EXISTS ${PROJECT_SOURCE_DIR}/tests/unit/cpp/e04_t10_latency_probe.cpp)
    add_executable(e04_t10_latency_probe ${PROJECT_SOURCE_DIR}/tests/unit/cpp/e04_t10_latency_probe.cpp
                   "${EDI_PROBE_BUILD_COMMIT_CPP}")
    add_dependencies(e04_t10_latency_probe edi_probe_build_commit)
    target_link_libraries(e04_t10_latency_probe PRIVATE edi_core)
    target_include_directories(e04_t10_latency_probe PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src
                                                             ${PROJECT_SOURCE_DIR}/tests/fixtures)
endif()

# Direct, constructed-value coverage of the presentation contract. The percent-change rule has edge
# cases a live refinement will never produce — a zero start, a non-finite operand, either side of
# the 0.05 % blanking threshold — so they are exercised on constructed values instead. A default
# target, so `pixi run core-build` emits it next to the other probes. Non-hidden and
# implementation-lane-owned: it asserts the contract report.hpp documents.
add_executable(report_format_probe ${PROJECT_SOURCE_DIR}/tools/probes/report_format_probe.cpp)
target_link_libraries(report_format_probe PRIVATE edi_core)

# --- The C++ unit tier ---------------------------------------------- ONE doctest
# binary, EXCLUDE_FROM_ALL (crysta's crysta_tests precedent): it is built by
# `pixi run cpp-test` and by the coverage instrument, never by `core-build` — the probes
# above are default targets because pytest runs them, whereas this tier is its own gate and
# must not tax every core build.
#
# The cases come from tests/unit/cpp/test_*.cpp. The `test_` prefix is what separates them
# from the standalone probes beside them (`*_probe.cpp`, `*_reference.cpp`), each of which
# carries its own main and therefore cannot link into this binary. CONFIGURE_DEPENDS so a
# newly added case re-globs on the next build rather than needing an edit here — the cases
# are hidden-surface (tests/hidden-surface.txt denies tests/unit/cpp/**) and thus authored by
# the test lane, while this instrument is implementation-lane-owned; a glob keeps the two
# from having to touch one file.
find_package(doctest CONFIG QUIET)
set(EDI_TEST_SOURCES "")
if(doctest_FOUND)
    file(GLOB EDI_TEST_SOURCES CONFIGURE_DEPENDS
        ${PROJECT_SOURCE_DIR}/tests/unit/cpp/test_*.cpp)
endif()
if(EDI_TEST_SOURCES)
    add_executable(edi_tests EXCLUDE_FROM_ALL
        ${PROJECT_SOURCE_DIR}/tools/probes/edi_tests_main.cpp
        ${EDI_TEST_SOURCES})
    target_link_libraries(edi_tests PRIVATE "$<LINK_LIBRARY:WHOLE_ARCHIVE,edi_core>" doctest::doctest)
    # Same private seam access the probes get, so a unit case can reach edi::detail; and the visible
    # fixtures (the stress dataset's generator is a header there).
    target_include_directories(edi_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src
                                                 ${PROJECT_SOURCE_DIR}/tests/fixtures)
    enable_testing()
    add_test(NAME edi_unit COMMAND edi_tests)
endif()
# Whether the target exists is decided HERE and recorded for the scripts to read, so CMake
# stays the single derivation. The alternative — having cpp-test.sh re-glob, or parse the
# generator's target list — either duplicates this logic or hardcodes one generator's output
# format (the Makefile `... target` shape silently matches nothing under Ninja).
list(LENGTH EDI_TEST_SOURCES EDI_TEST_CASE_FILES)
file(WRITE ${CMAKE_BINARY_DIR}/edi_tests_case_files.txt "${EDI_TEST_CASE_FILES}\n")

if(EXISTS ${PROJECT_SOURCE_DIR}/tests/integration/py/assistant_probe/probe.cpp)
    add_executable(assistant_contract_probe ${PROJECT_SOURCE_DIR}/tests/integration/py/assistant_probe/probe.cpp)
    target_include_directories(assistant_contract_probe PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)
    target_link_libraries(assistant_contract_probe PRIVATE edi::core)
endif()

# The SDK bootstrap belongs to executables, never their shared/core interfaces.
if(NOT EMSCRIPTEN)
    foreach(_edi_engine_executable IN ITEMS
        e02_adapter_probe
        c09_t8_locale_probe
        c09_t7_internal_probe
        e04_t9_latency_probe
        e04_t10_latency_probe
        report_format_probe
        edi_tests
        assistant_contract_probe)
        if(TARGET ${_edi_engine_executable})
            target_link_libraries(${_edi_engine_executable} PRIVATE "$<LINK_LIBRARY:WHOLE_ARCHIVE,crysta::process_defaults>")
        endif()
    endforeach()
    unset(_edi_engine_executable)
endif()
