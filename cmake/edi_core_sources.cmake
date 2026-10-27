# SPDX-License-Identifier: BSD-3-Clause
# The core's sources, for the product build (core/CMakeLists.txt) and the ThreadSanitizer tree (tools/ci/tsan), so
# both compile the same files: the ones in core/src and the data tables embedded in it, generated into the calling
# directory's build tree. `root` is edi's source root; the list is returned in `out`.
function(edi_core_sources root out)
    set(sources
        ${root}/core/src/version.cpp
        ${root}/core/src/adapter.cpp
        ${root}/core/src/canonical_encoding.cpp
        ${root}/core/src/parameter_paths.cpp
        ${root}/core/src/fit_policy.cpp
        ${root}/core/src/io.cpp
        ${root}/core/src/validation.cpp
        ${root}/core/src/report.cpp
        ${root}/core/src/json.cpp
        ${root}/core/src/assistant.cpp
        ${root}/core/src/assistant_skills.cpp
        ${root}/core/src/assistant_stream.cpp
        ${CMAKE_CURRENT_BINARY_DIR}/assistant_skills_data.cpp
        ${CMAKE_CURRENT_BINARY_DIR}/openai_capabilities_data.cpp
        ${root}/core/src/report_model.cpp
        ${root}/core/src/report_json.cpp
        ${root}/core/src/report_html.cpp
        ${root}/core/src/report_save.cpp
        ${root}/core/src/palette.cpp
        ${root}/core/src/display.cpp
        ${root}/core/src/duration_text.cpp
        ${root}/core/src/correlation_matrix.cpp
        ${root}/core/src/su_text.cpp
        ${root}/core/src/selectors.cpp
        ${root}/core/src/worker.cpp
        ${root}/core/src/live_preview.cpp
        ${root}/core/src/fit_job.cpp
        ${root}/core/src/presentation.cpp
        ${root}/core/src/structure_scene.cpp
        ${root}/core/src/scan_views.cpp
        ${root}/core/src/project_archive.cpp
        ${root}/core/third_party/miniz/miniz.c
    )

    # ADR-0022: the element table (data/elements/element-styles.tsv, PROVENANCE.md beside it) is embedded in the core
    # as a string, so no runtime file lookup exists; element_style_table() parses it once. A change to the file
    # reconfigures.
    set(EDI_ELEMENT_STYLES_TSV ${root}/data/elements/element-styles.tsv)
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${EDI_ELEMENT_STYLES_TSV})
    file(READ ${EDI_ELEMENT_STYLES_TSV} EDI_ELEMENT_STYLES)
    configure_file(${root}/core/src/element_styles_data.cpp.in ${CMAKE_CURRENT_BINARY_DIR}/element_styles_data.cpp
                   @ONLY)

    # The figure palettes (data/palettes, PROVENANCE.md beside them) are embedded the same way, one per
    # edi::ColourScheme in its order; a change reconfigures.
    set(EDI_PALETTES earth classic soft natural colour-blind-safe)
    set(EDI_PALETTE_TABLES "")
    foreach(scheme IN LISTS EDI_PALETTES)
        set(palette_tsv ${root}/data/palettes/${scheme}.tsv)
        set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${palette_tsv})
        file(READ ${palette_tsv} palette)
        string(APPEND EDI_PALETTE_TABLES "    R\"edi_palette(${palette})edi_palette\",\n")
    endforeach()
    configure_file(${root}/core/src/palette_data.cpp.in ${CMAKE_CURRENT_BINARY_DIR}/palette_data.cpp @ONLY)

    # ADR-0041: the scan views' colour maps (data/colormaps, PROVENANCE.md beside them), embedded the same way, in
    # edi::ScanColourMap's order after Blue-Red, which the core mixes itself.
    set(EDI_COLOUR_MAPS viridis batlow inferno lapaz greys)
    set(EDI_COLOUR_MAP_TABLES "")
    set(EDI_COLOUR_MAP_NAMES "")
    list(LENGTH EDI_COLOUR_MAPS EDI_COLOUR_MAP_COUNT)
    foreach(map IN LISTS EDI_COLOUR_MAPS)
        set(map_tsv ${root}/data/colormaps/${map}.tsv)
        set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${map_tsv})
        file(READ ${map_tsv} colour_map)
        string(APPEND EDI_COLOUR_MAP_TABLES "    R\"edi_colour_map(${colour_map})edi_colour_map\",\n")
        string(APPEND EDI_COLOUR_MAP_NAMES "    \"${map}\",\n")
    endforeach()
    configure_file(${root}/core/src/colour_map_data.cpp.in ${CMAKE_CURRENT_BINARY_DIR}/colour_map_data.cpp @ONLY)

    # ADR-0036: the HTML report's script (data/report/report.js) is embedded the same way, so every surface writes
    # the same file with no lookup; a change to the script reconfigures.
    set(EDI_REPORT_JS_FILE ${root}/data/report/report.js)
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${EDI_REPORT_JS_FILE})
    file(READ ${EDI_REPORT_JS_FILE} EDI_REPORT_JS)
    configure_file(${root}/core/src/report_js_data.cpp.in ${CMAKE_CURRENT_BINARY_DIR}/report_js_data.cpp @ONLY)

    set(EDI_OPENAI_CAPABILITIES_FILE ${root}/data/assistant/openai-capabilities.json)
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${EDI_OPENAI_CAPABILITIES_FILE})
    file(READ ${EDI_OPENAI_CAPABILITIES_FILE} EDI_OPENAI_CAPABILITIES)
    configure_file(${root}/core/src/openai_capabilities_data.cpp.in ${CMAKE_CURRENT_BINARY_DIR}/openai_capabilities_data.cpp @ONLY)

    # ADR0057: package-relative skills are immutable product resources, not runtime paths.
    set(EDI_SKILL_ROOT ${root}/data/assistant/skills)
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
    configure_file(${root}/core/src/assistant_skills_data.cpp.in ${CMAKE_CURRENT_BINARY_DIR}/assistant_skills_data.cpp @ONLY)

    list(APPEND sources
        ${CMAKE_CURRENT_BINARY_DIR}/element_styles_data.cpp
        ${CMAKE_CURRENT_BINARY_DIR}/report_js_data.cpp
        ${CMAKE_CURRENT_BINARY_DIR}/palette_data.cpp
        ${CMAKE_CURRENT_BINARY_DIR}/colour_map_data.cpp
    )
    set(${out} ${sources} PARENT_SCOPE)
endfunction()
