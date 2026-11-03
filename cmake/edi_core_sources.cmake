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

    list(APPEND sources
        ${CMAKE_CURRENT_BINARY_DIR}/element_styles_data.cpp
        ${CMAKE_CURRENT_BINARY_DIR}/report_js_data.cpp
        ${CMAKE_CURRENT_BINARY_DIR}/palette_data.cpp
        ${CMAKE_CURRENT_BINARY_DIR}/colour_map_data.cpp
    )
    set(${out} ${sources} PARENT_SCOPE)
endfunction()
