# SPDX-License-Identifier: BSD-3-Clause
# The one edi QML app host (ADR-0009, ADR-0015): one QML module (`edi.app`) on one source tree, built
# for desktop now and WASM later (E07) from this host. The module is a static library so the host and
# the Qt Quick Test runner load exactly the same types, pages and engine setup.

set(QT_QML_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/qml)
include(${PROJECT_SOURCE_DIR}/cmake/EdiGuiBase.cmake)

# The AI assistant is built into the desktop app and left out of the web kits (ADR-0023 §6): its C++, QML and
# resources are not compiled at all when the option is off, and nothing stands in for them.
if(EMSCRIPTEN)
    set(_edi_app_assistant_default OFF)
else()
    set(_edi_app_assistant_default ON)
endif()
option(EDI_APP_ASSISTANT "Build the AI assistant into the app (off for the web)" ${_edi_app_assistant_default})
if(EDI_APP_ASSISTANT)
    include(${PROJECT_SOURCE_DIR}/cmake/EdiAssistantMath.cmake)
    set(EDI_APP_ASSISTANT_SOURCES
        src/assistant_view_model.hpp src/assistant_view_model.cpp
        src/assistant_widget_input.hpp src/assistant_widget_input.cpp
        src/assistant_result.hpp src/assistant_result.cpp
        src/assistant_file_primitives.hpp src/assistant_file_primitives.cpp
        src/assistant_work_report.hpp src/assistant_work_report.cpp
        src/assistant_history.hpp src/assistant_history.cpp
        src/assistant_markdown.hpp src/assistant_markdown.cpp
        src/assistant_skill_import.hpp src/assistant_skill_import.cpp)
    set(EDI_APP_ASSISTANT_QML
        qml/Components/AssistantPanel.qml
        qml/Components/AssistantWorking.qml
        qml/Components/AssistantMessage.qml
        qml/Components/AssistantComposer.qml
        qml/Components/AssistantPlan.qml
        qml/Components/AssistantQuestion.qml
        qml/Components/AssistantTrial.qml
        qml/Components/AssistantSkillsDialog.qml
        qml/Components/AssistantConnectionDialog.qml)
    set(EDI_APP_ASSISTANT_RESOURCES resources/logo/AssistantWorking.svg resources/logo/AssistantSpinner.svg)
    set(EDI_APP_ASSISTANT_LICENCES ${PROJECT_SOURCE_DIR}/third_party/jkqtmathtext/LICENSE
                                   ${PROJECT_SOURCE_DIR}/third_party/jkqtmathtext/lib/jkqtmathtext/resources/xits/OFL.txt)
else()
    set(EDI_APP_ASSISTANT_SOURCES)
    set(EDI_APP_ASSISTANT_QML)
    set(EDI_APP_ASSISTANT_RESOURCES)
    set(EDI_APP_ASSISTANT_LICENCES)
endif()

# What the app tells its user about itself (ApplicationInfo). Its version and date come from git at every build, as the
# commit does, so a reused build folder never shows an old one (cmake/build_version.cmake).
set(EDI_RELEASE_VERSION "" CACHE STRING "Calendar version selected by release preparation")
set(EDI_APP_BUILD_VERSION_CPP "${CMAKE_CURRENT_BINARY_DIR}/edi_app_build_version.cpp")
set(EDI_APP_BUILD_VERSION_COMMAND "${CMAKE_COMMAND}" -DSOURCE_DIR=${PROJECT_SOURCE_DIR} -DOUT=${EDI_APP_BUILD_VERSION_CPP} -DRELEASE_VERSION=${EDI_RELEASE_VERSION}
                                  -P "${PROJECT_SOURCE_DIR}/cmake/build_version.cmake")
execute_process(COMMAND ${EDI_APP_BUILD_VERSION_COMMAND} COMMAND_ERROR_IS_FATAL ANY)
add_custom_target(edi_app_build_version
    COMMAND ${EDI_APP_BUILD_VERSION_COMMAND}
    BYPRODUCTS "${EDI_APP_BUILD_VERSION_CPP}"
    COMMENT "Embedding the version and date in the app")
# The crysta the app links, for the diagnostics view: its package version, and the commit its SDK manifest
# records (a local crysta build has no manifest).
find_package(crysta CONFIG QUIET)
set(EDI_APP_CRYSTA_VERSION "${crysta_VERSION}")
set(EDI_APP_CRYSTA_COMMIT "a local build (no SDK manifest)")
set(_edi_crysta_manifest "${crysta_DIR}/../../../share/crysta-sdk/manifest.json")
if(EXISTS "${_edi_crysta_manifest}")
    file(READ "${_edi_crysta_manifest}" _edi_crysta_manifest_text)
    string(JSON EDI_APP_CRYSTA_COMMIT ERROR_VARIABLE _edi_crysta_manifest_error GET "${_edi_crysta_manifest_text}" source_sha)
    if(_edi_crysta_manifest_error)
        set(EDI_APP_CRYSTA_COMMIT "unreadable SDK manifest")
    endif()
endif()
set(EDI_APP_SDK_SOURCE_KIND "unknown")
string(LENGTH "${EDI_APP_CRYSTA_COMMIT}" _edi_sdk_source_length)
if(_edi_sdk_source_length EQUAL 40 AND EDI_APP_CRYSTA_COMMIT MATCHES "^[0-9a-f]+$")
    set(EDI_APP_SDK_SOURCE_KIND "manifest")
elseif(EDI_APP_CRYSTA_COMMIT STREQUAL "a local build (no SDK manifest)")
    set(EDI_APP_SDK_SOURCE_KIND "local_without_manifest")
endif()
configure_file(src/app_build_info.hpp.in ${CMAKE_CURRENT_BINARY_DIR}/app_build_info.hpp @ONLY)

# Singletons are marked before the module is declared: qt_add_qml_module reads the property then.
set_source_files_properties(qml/Globals/AppState.qml qml/Globals/FactorText.qml qml/Globals/FieldTitles.qml qml/Globals/FitOutcomes.qml qml/Globals/NumberText.qml qml/Globals/ParameterNames.qml
                            qml/Globals/Preferences.qml qml/Globals/RecentProjects.qml qml/Globals/SideBarGroups.qml qml/Globals/TypedInput.qml
                            qml/Style/AppColors.qml qml/Style/AppSizes.qml PROPERTIES QT_QML_SINGLETON_TYPE TRUE)
qt_add_library(edi_app_module STATIC)
qt_add_qml_module(edi_app_module
    URI edi.app
    VERSION 1.0
    # The chart controller's series properties are Qt Graphs types, and the structure view's instance
    # tables and mesh are Qt Quick 3D types: the module names both dependencies so that its type record
    # resolves them.
    DEPENDENCIES QtGraphs QtQuick3D
    SOURCES
        src/app_info.hpp src/app_info.cpp
        src/assistant_message_presentation.hpp
        src/assistant_values.hpp
        src/assistant_panel_presentation.hpp
        src/assistant_data.hpp
        src/assistant_data_summary.hpp
        ${EDI_APP_ASSISTANT_SOURCES}
        src/example_list_model.hpp src/example_list_model.cpp
        src/engine_setup.hpp src/engine_setup.cpp
        src/demo_driver.hpp src/demo_driver.cpp src/demo_documentation.cpp
        src/run_log.hpp src/run_log.cpp
        src/item_locator.hpp src/item_locator.cpp
        src/view_rows.hpp src/view_rows.cpp
        src/user_action_log.hpp src/user_action_log.cpp
        src/build_version.hpp
        src/desktop_updates.hpp src/desktop_updates.cpp
        src/test_observer.hpp src/test_observer.cpp
        src/web_page_hooks.hpp src/web_page_hooks.cpp
        src/project_editor.hpp
        src/row_table_model.hpp src/row_table_model.cpp
        src/parameter_item.hpp src/parameter_item.cpp
        src/parameter_registry.hpp src/parameter_registry.cpp
        src/option_list_model.hpp src/option_list_model.cpp
        src/block_text.hpp src/block_text.cpp
        src/edi_text_highlighter.hpp src/edi_text_highlighter.cpp
        src/generated_category.hpp src/generated_category.cpp
        src/category_list_model.hpp src/category_list_model.cpp
        src/structure_view_model.hpp src/structure_view_model.cpp
        src/structure_view_options.hpp src/structure_view_options.cpp
        src/structure_instances.hpp src/structure_instances.cpp
        src/shared_site_geometry.hpp src/shared_site_geometry.cpp
        src/structure_label_layer.hpp src/structure_label_layer.cpp
        src/structure_view_controller.hpp src/structure_view_controller.cpp
        src/experiment_models.hpp src/experiment_models.cpp
        src/pattern_model.hpp src/pattern_model.cpp
        src/pattern_chart_controller.hpp src/pattern_chart_controller.cpp
        src/chart_models.hpp src/chart_models.cpp
        src/measured_layer.hpp src/measured_layer.cpp
        src/evolution_view_model.hpp src/evolution_view_model.cpp
        src/scan_view_model.hpp src/scan_view_model.cpp
        src/scan_layer.hpp src/scan_layer.cpp
        src/scan_lines.hpp src/scan_lines.cpp
        src/rendering_info.hpp src/rendering_info.cpp
        src/correlation_view_model.hpp src/correlation_view_model.cpp
        src/scan_session.hpp src/scan_session.cpp
        src/experiment_view_model.hpp src/experiment_view_model.cpp
        src/analysis_view_model.hpp src/analysis_view_model.cpp
        src/fit_view_model.hpp src/fit_view_model.cpp
        src/parameter_table_model.hpp src/parameter_table_model.cpp
        src/report_view_model.hpp src/report_view_model.cpp
        src/report_pdf.hpp src/report_pdf.cpp
        src/project_view_model.hpp src/project_view_model.cpp
        src/session.hpp src/session.cpp
        src/online_sources.hpp src/online_sources.cpp
        src/online_search.hpp src/online_search.cpp
        src/online_values.hpp
        src/online_fetch.hpp src/online_fetch.cpp
        src/collection_examples.hpp src/collection_examples.cpp
        src/web_files.hpp src/web_files.cpp
        src/web_storage.hpp src/web_storage.cpp
    QML_FILES
        qml/Main.qml
        feedback/Payload.js
        qml/Components/AppDialog.qml
        qml/Components/AppPreferencesDialog.qml
        qml/Components/LoadMenuHeader.qml
        qml/Components/LoadMenuItem.qml
        qml/Components/OnlineLoadDialog.qml
        ${EDI_APP_ASSISTANT_QML}
        qml/Components/BlockSelector.qml
        qml/Components/ChoiceRadioButton.qml
        qml/Components/CategoryGroup.qml
        qml/Components/SideBarGroup.qml
        qml/Components/PerformanceGroup.qml
        qml/Components/ComboCell.qml
        qml/Components/CrashDialog.qml
        qml/Components/DiagnosticsDialog.qml
        qml/Components/FeedbackDialog.qml
        qml/Components/EmptyStateLabel.qml
        qml/Components/DataTable.qml
        qml/Components/DigitText.qml
        qml/Components/FitStatusItem.qml
        qml/Components/FitProgressBar.qml
        qml/Components/FitResultsDialog.qml
        qml/Components/ChartLegend.qml
        qml/Components/ChartTheme.qml
        qml/Components/FigureColors.qml
        qml/Components/HeaderLabel.qml
        qml/Components/ChartToolButton.qml
        qml/Components/ChartToolbar.qml
        qml/Components/ColourMapBar.qml
        qml/Components/ColourMapComboBox.qml
        qml/Components/IconCell.qml
        qml/Components/IconLine.qml
        qml/Components/IconTabButton.qml
        qml/Components/MainAreaBlockSelector.qml
        qml/Components/NumberLabel.qml
        qml/Components/ParameterCell.qml
        qml/Components/ParameterField.qml
        qml/Components/ParameterGrid.qml
        qml/Components/PaletteStrip.qml
        qml/Components/PatternChart.qml
        qml/Components/ProjectPatternChart.qml
        qml/Components/EvolutionChart.qml
        qml/Components/ScanViewChart.qml
        qml/Components/SingleCrystalChart.qml
        qml/Components/SingleCrystalTable.qml
        qml/Components/CorrelationChart.qml
        qml/Components/SearchableComboBox.qml
        qml/Components/SelectedPatternLine.qml
        qml/Components/SelectorField.qml
        qml/Components/StatusBar.qml
        qml/Components/ExampleCell.qml
        qml/Components/ExampleFilters.qml
        qml/Components/IconLink.qml
        qml/Components/AssistantDownloadLink.qml
        qml/Components/StatusBarButton.qml
        qml/Components/StatusBarFitButton.qml
        qml/Components/StatusBarItem.qml
        qml/Components/StructureScene.qml
        qml/Components/StructureToolbar.qml
        qml/Components/StructureView.qml
        qml/Components/TableRow.qml
        qml/Components/TextCell.qml
        qml/Components/GeneratedGroup.qml
        qml/Components/MultiLineField.qml
        qml/Components/TextTab.qml
        qml/Components/TutorialPanel.qml
        qml/Components/TutorialControls.qml
        qml/Components/WhatsNewDialog.qml
        qml/Components/UpdateButton.qml
        qml/Components/ToolbarComboBox.qml
        qml/Components/ToolbarLines.qml
        qml/Components/ValueField.qml
        qml/Components/WarningToolTip.qml
        qml/Components/WarningsDialog.qml
        qml/Components/Wordmark.qml
        qml/Components/WordmarkWithVersion.qml
        qml/Components/WorkflowPage.qml
        qml/Components/WorkflowTabButton.qml
        qml/Globals/AppState.qml
        qml/Globals/FactorText.qml
        qml/Globals/FieldTitles.qml
        qml/Globals/FitOutcomes.qml
        qml/Globals/NumberText.qml
        qml/Globals/ParameterNames.qml
        qml/Globals/Preferences.qml
        qml/Globals/RecentProjects.qml
        qml/Globals/SideBarGroups.qml
        qml/Globals/TypedInput.qml
        qml/Pages/Analysis/AliasesGroup.qml
        qml/Pages/Analysis/AnalysisPage.qml
        qml/Pages/Analysis/ConstraintsGroup.qml
        qml/Pages/Analysis/FitStartGroup.qml
        qml/Pages/Analysis/FittingModeGroup.qml
        qml/Pages/Analysis/FreeHeaderMenu.qml
        qml/Pages/Analysis/JointFitGroup.qml
        qml/Pages/Analysis/MinimizerGroup.qml
        qml/Pages/Analysis/ParametersGroup.qml
        qml/Pages/Analysis/PatternUpdatesGroup.qml
        qml/Pages/Analysis/RefinementGroup.qml
        qml/Pages/Analysis/SequentialExtractGroup.qml
        qml/Pages/Analysis/SequentialFitGroup.qml
        qml/Pages/Analysis/ShownParametersGroup.qml
        qml/Pages/Experiment/AbsorptionGroup.qml
        qml/Pages/Experiment/ExtinctionGroup.qml
        qml/Pages/Experiment/ObservedThresholdRow.qml
        qml/Pages/Experiment/BackgroundGroup.qml
        qml/Pages/Experiment/ExcludedRegionsGroup.qml
        qml/Pages/Experiment/ExperimentPage.qml
        qml/Pages/Experiment/ExperimentTypeGroup.qml
        qml/Pages/Experiment/ExperimentsGroup.qml
        qml/Pages/Experiment/InstrumentGroup.qml
        qml/Pages/Experiment/LinkedStructureGroup.qml
        qml/Pages/Experiment/MeasuredRangeGroup.qml
        qml/Pages/Experiment/PeakExtrasGroup.qml
        qml/Pages/Experiment/BackgroundExtrasGroup.qml
        qml/Pages/Experiment/PeakGroup.qml
        qml/Pages/Experiment/PreferredOrientationGroup.qml
        qml/Pages/Experiment/ReflectionsGroup.qml
        qml/Pages/Experiment/ScatteringSourceGroup.qml
        qml/Pages/Home/AboutDialog.qml
        qml/Pages/Home/CitationDialog.qml
        qml/Pages/Home/HomePage.qml
        qml/Pages/Home/TutorialsDialog.qml
        qml/Pages/Project/BlockNames.qml
        qml/Pages/Project/DescriptionRow.qml
        qml/Pages/Project/DescriptionTab.qml
        qml/Pages/Project/ExamplesGroup.qml
        qml/Pages/Project/GetStartedGroup.qml
        qml/Pages/Project/ProjectPage.qml
        qml/Pages/Project/RecentProjectsGroup.qml
        qml/Pages/Project/StandardUncertaintiesGroup.qml
        qml/Pages/Report/ContentsGroup.qml
        qml/Pages/Report/ExportGroup.qml
        qml/Pages/Report/ReportCorrelations.qml
        qml/Pages/Report/ReportPage.qml
        qml/Pages/Report/ReportPreview.qml
        qml/Pages/Report/ReportTable.qml
        qml/Pages/Structure/AppearanceGroup.qml
        qml/Pages/Structure/AtomSiteAdpGroup.qml
        qml/Pages/Structure/AtomSiteMomentGroup.qml
        qml/Pages/Structure/MagneticFormFactorsGroup.qml
        qml/Pages/Structure/MagneticSpaceGroupGroup.qml
        qml/Pages/Structure/PropagationVectorsGroup.qml
        qml/Pages/Structure/AtomSitesGroup.qml
        qml/Pages/Structure/CellGroup.qml
        qml/Pages/Structure/ScatteringLengthsGroup.qml
        qml/Pages/Structure/SpaceGroupGroup.qml
        qml/Pages/Structure/StructurePage.qml
        qml/Pages/Structure/StructuresGroup.qml
        qml/Style/AppColors.qml
        qml/Style/AppSizes.qml
    RESOURCES
        resources/logo/App.svg
        ${EDI_APP_ASSISTANT_RESOURCES}
)
target_compile_definitions(edi_app_module PUBLIC EDI_APP_ASSISTANT=$<IF:$<BOOL:${EDI_APP_ASSISTANT}>,1,0>)
target_sources(edi_app_module PRIVATE "${EDI_APP_BUILD_VERSION_CPP}")
add_dependencies(edi_app_module edi_app_build_version)
# The Stacked view's line shader (edi ADR-0041), compiled for every graphics API Qt Quick runs on.
qt_add_shaders(edi_app_module "edi_scan_shaders" PREFIX "/edi" FILES shaders/scan_line.vert shaders/scan_line.frag)
target_include_directories(edi_app_module PUBLIC src ${CMAKE_CURRENT_BINARY_DIR})
target_compile_definitions(edi_app_module PUBLIC QT_MESSAGELOGCONTEXT)  # file and line in the run log (ADR-0062)
target_link_libraries(edi_app_module
    PUBLIC Qt6::Quick Qt6::QuickControls2 Qt6::Graphs Qt6::Quick3D Qt6::Concurrent Qt6::Network edi::core
    PRIVATE ${EDI_GUI_BASE_TARGETS} Qt6::CorePrivate Qt6::QuickPrivate Qt6::QmlModelsPrivate)
find_package(Qt6QmlPrivate REQUIRED)
target_link_libraries(edi_app_module PRIVATE Qt6::QmlPrivate)
if(EDI_APP_ASSISTANT)
    # The assistant's math rendering; nothing else draws formulas, so a build without the assistant has no math library.
    target_link_libraries(edi_app_module PRIVATE EdiMath::JKQTMathTextEdi)
    target_compile_definitions(edi_app_module PRIVATE EDI_HAS_NATIVE_MATH=1)
endif()
if(EMSCRIPTEN)
    target_link_libraries(edi_app_module PRIVATE Qt6::GuiPrivate)
endif()

# The Examples: the user-facing projects of edi's CLI registry (`user-facing: true`) and its declared app-only
# ones (`app-only: <reason>`, ADR-0048), in registry order, each with its scan data (a scan's datasets are
# browsed in the app). Every other registered project is a test fixture, and verification projects stay CLI
# projects only (ADR-0031). Configuration fails when the registry and the project directories disagree.
set(_cli ${PROJECT_SOURCE_DIR}/docs/user/cli)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${_cli}/projects.yml)
file(STRINGS ${_cli}/projects.yml _registry_lines
     REGEX "^  - id: |^    user-facing: |^    app-only: |^    verification: ")
set(_registered_ids)
set(EDI_APP_EXAMPLE_IDS)
set(_verification_ids)
foreach(line IN LISTS _registry_lines)
    if(line MATCHES "^  - id: *(.+)$")
        set(id ${CMAKE_MATCH_1})
        if(NOT IS_DIRECTORY ${_cli}/${id}/project)
            message(FATAL_ERROR "docs/user/cli/projects.yml lists '${id}', which has no docs/user/cli/${id}/project/")
        endif()
        list(APPEND _registered_ids ${id})
    elseif(line MATCHES "^    user-facing: *true$" OR line MATCHES "^    app-only: ")
        list(APPEND EDI_APP_EXAMPLE_IDS ${id})
    elseif(line MATCHES "^    verification: *true$")
        list(APPEND _verification_ids ${id})
    endif()
endforeach()
# A verification project stays a CLI project (ADR-0031): the registry marks it.
if(_verification_ids)
    list(REMOVE_ITEM EDI_APP_EXAMPLE_IDS ${_verification_ids})
endif()
file(GLOB _cli_entries LIST_DIRECTORIES true RELATIVE ${_cli} CONFIGURE_DEPENDS ${_cli}/*)
foreach(entry IN LISTS _cli_entries)
    if(IS_DIRECTORY ${_cli}/${entry} AND NOT entry IN_LIST _registered_ids)
        message(FATAL_ERROR "docs/user/cli/${entry}/ is not listed in docs/user/cli/projects.yml")
    endif()
endforeach()
# Metadata belongs to the app presentation; the CLI registry retains its execution contract.
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/examples/metadata.json" _example_metadata)
string(JSON _metadata_schema GET "${_example_metadata}" schema)
if(NOT _metadata_schema EQUAL 1)
    message(FATAL_ERROR "Unsupported example metadata schema")
endif()
foreach(id IN LISTS EDI_APP_EXAMPLE_IDS)
    string(JSON _purpose ERROR_VARIABLE _metadata_error GET "${_example_metadata}" examples "${id}" values purpose 0)
    if(_metadata_error)
        message(FATAL_ERROR "Example '${id}' has no app metadata")
    endif()
    if(NOT _purpose STREQUAL "refinement" AND NOT _purpose STREQUAL "simulation")
        message(FATAL_ERROR "Example '${id}' has purpose '${_purpose}', not refinement or simulation")
    endif()
endforeach()
# The example projects themselves are not bundled: the app downloads them from the data collections (ADR-0068);
# only the catalogue (metadata, tags, the id list) is.
qt_add_resources(edi_app_module "edi_tutorials" PREFIX "/edi/tutorials"
                 BASE ${CMAKE_CURRENT_SOURCE_DIR}/tutorials FILES tutorials/manifest.json tutorials/tour.json)
# The tutorials' two input files (tutorials/files) are not bundled either: the session fetches them from the
# collection, which `build_collection.py populate` writes them into.
qt_add_resources(edi_app_module "edi_documentation_script" PREFIX "/edi/docs"
                 BASE ${CMAKE_CURRENT_SOURCE_DIR}/docs FILES docs/y2o3-spodi.js)
qt_add_resources(edi_app_module "edi_example_metadata" PREFIX "/edi/examples"
                 BASE ${CMAKE_CURRENT_SOURCE_DIR}/examples FILES ${CMAKE_CURRENT_SOURCE_DIR}/examples/metadata.json
                 ${CMAKE_CURRENT_SOURCE_DIR}/examples/tags.json)
list(JOIN EDI_APP_EXAMPLE_IDS "\n" _index)
file(CONFIGURE OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/examples/index.txt CONTENT "${_index}\n")
qt_add_resources(edi_app_module "edi_example_index" PREFIX "/edi/examples"
                 BASE ${CMAKE_CURRENT_BINARY_DIR}/examples FILES ${CMAKE_CURRENT_BINARY_DIR}/examples/index.txt)

# The licences: the app's (COPYING, GPL-3.0, and its notice app/DISTRIBUTION-LICENSE.md), the source code's (LICENSE),
# the third-party notices and DEPENDENCIES.md, whose column for this build About's third-party table lists. They are in the app's
# resources at their repository paths for the About window (qrc:/COPYING, qrc:/app/DISTRIBUTION-LICENSE.md,
# ...), beside the built app, and installed with it.
set(EDI_APP_LICENCE_FILES
    ${PROJECT_SOURCE_DIR}/COPYING ${PROJECT_SOURCE_DIR}/LICENSE ${PROJECT_SOURCE_DIR}/THIRD-PARTY-NOTICES
    ${PROJECT_SOURCE_DIR}/DEPENDENCIES.md ${PROJECT_SOURCE_DIR}/app/DISTRIBUTION-LICENSE.md
    ${EDI_APP_ASSISTANT_LICENCES})
# How to cite (Home), read from the repository's one citation file.
qt_add_resources(edi_app_module "edi_citation" PREFIX "/" BASE ${PROJECT_SOURCE_DIR} FILES ${PROJECT_SOURCE_DIR}/CITATION.cff)
# What's new: the docs site's dated page, the one place the changes are written.
qt_add_resources(edi_app_module "edi_changelog" PREFIX "/edi" BASE ${PROJECT_SOURCE_DIR}/website/surfaces/docs
                 FILES ${PROJECT_SOURCE_DIR}/website/surfaces/docs/changelog.md)
# Stored uncompressed, so the texts stay readable in the binary itself as well.
qt_add_resources(edi_app_module "edi_licences" PREFIX "/" BASE ${PROJECT_SOURCE_DIR}
                 OPTIONS --no-compress FILES ${EDI_APP_LICENCE_FILES})
foreach(file IN LISTS EDI_APP_LICENCE_FILES)
    get_filename_component(name ${file} NAME)
    configure_file(${file} ${CMAKE_CURRENT_BINARY_DIR}/${name} COPYONLY)
endforeach()

# The HTML report's chart libraries (ADR-0036), which a saved report carries when asked: in the desktop app's resources
# at qrc:/edi/report/vendor/; the browser build fetches them from its site instead (wasm-pack.sh), so its download
# does not grow.
if(NOT EMSCRIPTEN)
    file(GLOB EDI_REPORT_VENDOR CONFIGURE_DEPENDS ${PROJECT_SOURCE_DIR}/data/report/vendor/*.js)
    qt_add_resources(edi_app_module "edi_report_vendor" PREFIX "/edi" BASE ${PROJECT_SOURCE_DIR}/data
                     FILES ${EDI_REPORT_VENDOR})
endif()

qt_add_executable(edi_app main.cpp)
target_link_libraries(edi_app PRIVATE edi_app_module edi_app_moduleplugin ${EDI_GUI_BASE_TARGETS} Qt6::Svg)
set_target_properties(edi_app PROPERTIES MACOSX_BUNDLE FALSE WIN32_EXECUTABLE TRUE)
if(WIN32)
    enable_language(RC)
    file(GENERATE OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/edi-app-icon.rc"
        CONTENT "1 ICON \"${CMAKE_CURRENT_SOURCE_DIR}/resources/logo/App.ico\"\n")
    target_sources(edi_app PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/edi-app-icon.rc")
endif()
# ADR-0023: the browser build's stacks. A fit runs crysta on the calculation worker's thread, which Emscripten sizes
# at 64 KiB by default, or, in the single-thread build, on the main thread, which Qt sizes at 5 MiB; both get 8 MiB.
# Qt's own STACK_SIZE is an interface link option, placed after the target's, and Emscripten takes the last value:
# so the main stack goes with the libraries, which the link line places after every option.
if(EMSCRIPTEN)
    target_link_libraries(edi_app PRIVATE "-sSTACK_SIZE=8MB")
    if(QT_FEATURE_thread)
        target_link_options(edi_app PRIVATE -sDEFAULT_PTHREAD_STACK_SIZE=8MB)
    endif()
    # ADR-0030: the page's files live in WasmFS, so a worker reads and writes them on its own thread instead of
    # waiting for the page's. FORCE_FILESYSTEM keeps the JavaScript FS calls the folder upload uses (mkdirTree,
    # writeFile); the stubs stand in for the socket library a WasmFS link leaves out.
    target_sources(edi_app PRIVATE src/wasmfs_socket_stubs.cpp)
    target_link_options(edi_app PRIVATE -sWASMFS -sFORCE_FILESYSTEM)
endif()

# The measured-layer benchmark (edi ADR-0017 §15): test tooling, never part of the host. It reads the
# stress dataset's generator from the visible fixtures.
qt_add_executable(edi_app_chart_bench tools/chart_bench.cpp)
qt_add_resources(edi_app_chart_bench "edi_chart_bench" PREFIX "/edi/bench" BASE tools FILES tools/ChartBench.qml)
target_include_directories(edi_app_chart_bench PRIVATE ${PROJECT_SOURCE_DIR}/tests/fixtures)
target_link_libraries(edi_app_chart_bench PRIVATE edi_app_module edi_app_moduleplugin ${EDI_GUI_BASE_TARGETS})
set_target_properties(edi_app_chart_bench PROPERTIES WIN32_EXECUTABLE FALSE MACOSX_BUNDLE FALSE)

# The scan views' renderer benchmark (edi ADR-0041): test tooling, never part of the host.
qt_add_executable(edi_app_scan_bench tools/scan_bench.cpp)
qt_add_resources(edi_app_scan_bench "edi_scan_bench" PREFIX "/edi/bench" BASE tools FILES tools/ScanBench.qml)
target_link_libraries(edi_app_scan_bench PRIVATE edi_app_module edi_app_moduleplugin ${EDI_GUI_BASE_TARGETS})
set_target_properties(edi_app_scan_bench PROPERTIES WIN32_EXECUTABLE FALSE MACOSX_BUNDLE FALSE)

# The plotting benchmark (edi ADR-0041): every way of feeding Qt Graphs on the Stacked and Pattern charts' workloads.
# Test tooling, never part of the host.
qt_add_executable(edi_app_plot_bench tools/plot_bench.cpp)
qt_add_resources(edi_app_plot_bench "edi_plot_bench" PREFIX "/edi/bench" BASE tools FILES tools/PlotBench.qml)
target_link_libraries(edi_app_plot_bench PRIVATE edi_app_module edi_app_moduleplugin ${EDI_GUI_BASE_TARGETS})
set_target_properties(edi_app_plot_bench PROPERTIES WIN32_EXECUTABLE FALSE MACOSX_BUNDLE FALSE)

# The page-image comparator: test tooling, QtGui only, never part of the host.
qt_add_executable(edi_app_ui_compare tools/ui_compare.cpp)
target_link_libraries(edi_app_ui_compare PRIVATE Qt6::Gui)
set_target_properties(edi_app_ui_compare PROPERTIES WIN32_EXECUTABLE FALSE MACOSX_BUNDLE FALSE)

# The Qt Quick Test runner: the hidden tier's tst_*.qml cases, with its test_*.cpp support sources
# compiled in, over the same edi.app module and engine setup the host uses. The cases are the tests
# lane's; a glob keeps the two lanes off one file. Never linked into edi_app.
file(GLOB EDI_APP_TEST_SUPPORT CONFIGURE_DEPENDS ${PROJECT_SOURCE_DIR}/tests/unit/app/test_*.cpp)
# The runner prints the commit it was built from (`<sha>-dirty` when tracked files differed), so the latency
# bank attributes the frame times it prints to a revision; regenerated on every build, as lib's.
set(EDI_APP_BUILD_COMMIT_CPP "${CMAKE_BINARY_DIR}/edi_app_build_commit.cpp")
execute_process(COMMAND "${CMAKE_COMMAND}" -DSOURCE_DIR=${PROJECT_SOURCE_DIR} -DOUT=${EDI_APP_BUILD_COMMIT_CPP}
                        -DMARK_DIRTY=ON -P "${PROJECT_SOURCE_DIR}/cmake/build_commit.cmake")
add_custom_target(edi_app_build_commit
    COMMAND "${CMAKE_COMMAND}" -DSOURCE_DIR=${PROJECT_SOURCE_DIR} -DOUT=${EDI_APP_BUILD_COMMIT_CPP}
            -DMARK_DIRTY=ON -P "${PROJECT_SOURCE_DIR}/cmake/build_commit.cmake"
    BYPRODUCTS "${EDI_APP_BUILD_COMMIT_CPP}"
    COMMENT "Embedding the source commit in the app and its test runner")
qt_add_executable(edi_app_tests ${CMAKE_CURRENT_SOURCE_DIR}/tests/app_tests_main.cpp ${EDI_APP_TEST_SUPPORT}
                  "${EDI_APP_BUILD_COMMIT_CPP}")
add_dependencies(edi_app_tests edi_app_build_commit)
# The app names it too: its test observers report the build they observe.
target_sources(edi_app PRIVATE "${EDI_APP_BUILD_COMMIT_CPP}")
add_dependencies(edi_app edi_app_build_commit)
# And carries it as bytes (MARKER), which a receipt reads from the binary without running it, as the latency probes do.
set(EDI_APP_BUILD_MARKER_CPP "${CMAKE_BINARY_DIR}/edi_app_build_marker.cpp")
execute_process(COMMAND "${CMAKE_COMMAND}" -DSOURCE_DIR=${PROJECT_SOURCE_DIR} -DOUT=${EDI_APP_BUILD_MARKER_CPP}
                        -DMARKER=ON -DMARK_DIRTY=ON -P "${PROJECT_SOURCE_DIR}/cmake/build_commit.cmake")
add_custom_target(edi_app_build_marker
    COMMAND "${CMAKE_COMMAND}" -DSOURCE_DIR=${PROJECT_SOURCE_DIR} -DOUT=${EDI_APP_BUILD_MARKER_CPP}
            -DMARKER=ON -DMARK_DIRTY=ON -P "${PROJECT_SOURCE_DIR}/cmake/build_commit.cmake"
    BYPRODUCTS "${EDI_APP_BUILD_MARKER_CPP}"
    COMMENT "Embedding the source commit in the app as bytes")
target_sources(edi_app PRIVATE "${EDI_APP_BUILD_MARKER_CPP}")
add_dependencies(edi_app edi_app_build_marker)
target_link_libraries(edi_app_tests PRIVATE edi_app_module edi_app_moduleplugin ${EDI_GUI_BASE_TARGETS}
                                            Qt6::QuickTest Qt6::QmlPrivate)
# The demo and the test observers open test projects the app does not bundle from the source tree (ADR-0048).
set_source_files_properties(src/demo_driver.cpp src/demo_documentation.cpp PROPERTIES
                            COMPILE_DEFINITIONS "EDI_CLI_PROJECTS_DIR=\"${PROJECT_SOURCE_DIR}/docs/user/cli\"")
target_compile_definitions(edi_app_tests PRIVATE
    QUICK_TEST_SOURCE_DIR="${PROJECT_SOURCE_DIR}/tests/unit/app")
set_target_properties(edi_app_tests PROPERTIES AUTOMOC ON WIN32_EXECUTABLE FALSE MACOSX_BUNDLE FALSE)

include(GNUInstallDirs)
option(EDI_DEPLOY_APP "Install a self-contained desktop application" OFF)
if(EDI_DEPLOY_APP AND APPLE)
    set(app_icon resources/logo/App.icns)
    target_sources(edi_app PRIVATE "${app_icon}")
    set_source_files_properties("${app_icon}" PROPERTIES MACOSX_PACKAGE_LOCATION Resources)
    set_target_properties(edi_app PROPERTIES MACOSX_BUNDLE_ICON_FILE App.icns)
    set_target_properties(edi_app PROPERTIES MACOSX_BUNDLE TRUE OUTPUT_NAME EasyDiffraction
        MACOSX_BUNDLE_GUI_IDENTIFIER org.easyscience.easydiffraction
        MACOSX_BUNDLE_BUNDLE_NAME EasyDiffraction)
    set(CMAKE_INSTALL_BINDIR EasyDiffraction.app/Contents/MacOS)
    set(CMAKE_INSTALL_LIBEXECDIR EasyDiffraction.app/Contents/libexec)
    set(CMAKE_INSTALL_DOCDIR EasyDiffraction.app/Contents/Resources/licenses)
endif()
if(EDI_DEPLOY_APP AND UNIX AND NOT APPLE)
    set_target_properties(edi_app PROPERTIES INSTALL_RPATH "$ORIGIN/../lib")
endif()
install(TARGETS edi_app BUNDLE DESTINATION . COMPONENT desktop RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
        COMPONENT desktop)
if(NOT EMSCRIPTEN)
    option(EDI_INSTALLER_CALENDAR_PREVIEW "Build an installer preview without stable release history" OFF)
    target_compile_definitions(edi_app PRIVATE EDI_INSTALLER_CALENDAR_PREVIEW=$<BOOL:${EDI_INSTALLER_CALENDAR_PREVIEW}>)
    target_sources(edi_app PRIVATE src/installer_smoke.cpp)
    set(smoke_project "${PROJECT_SOURCE_DIR}/docs/user/cli/pd-neut-cwl_lab6-11b-echidna_basic/project")
    file(GLOB_RECURSE smoke_files CONFIGURE_DEPENDS "${smoke_project}/*")
    qt_add_resources(edi_app installer_smoke PREFIX /edi/installer-smoke
        BASE "${smoke_project}" FILES ${smoke_files})
endif()
install(FILES ${EDI_APP_LICENCE_FILES} DESTINATION ${CMAKE_INSTALL_DOCDIR} COMPONENT desktop)

if(TARGET edi_assistant_native AND EDI_APP_ASSISTANT)
    target_link_libraries(edi_app_module PRIVATE edi_assistant_native)
    # C++ observers include Session's native interface, as the real Main probe does.
    target_link_libraries(edi_app_tests PRIVATE edi_assistant_native)
endif()
if(NOT EMSCRIPTEN)
    target_sources(edi_app_module PRIVATE src/codex_agent.hpp src/codex_agent.cpp
        src/assistant_native_tools.hpp src/assistant_native_tools.cpp
        src/assistant_native_create.hpp src/assistant_native_create.cpp)
    file(GLOB_RECURSE EDI_RUNTIME_SKILL_FILES CONFIGURE_DEPENDS
         ${PROJECT_SOURCE_DIR}/data/assistant/skills/*)
    qt_add_resources(edi_app_module edi_runtime_skills PREFIX "/edi/assistant/skills"
        BASE ${PROJECT_SOURCE_DIR}/data/assistant/skills FILES ${EDI_RUNTIME_SKILL_FILES})
    include(${PROJECT_SOURCE_DIR}/cmake/assistant_runtime.cmake)
    edi_bundle_assistant_runtime()
endif()
# Read-only documentation export, using the same linked dictionary as the app (ADR-0061).
if(NOT EMSCRIPTEN)
    qt_add_executable(edi_doc_metadata ${PROJECT_SOURCE_DIR}/tools/docs/reference-metadata.cpp)
    target_link_libraries(edi_doc_metadata PRIVATE edi::core Qt6::Core)
    set_target_properties(edi_doc_metadata PROPERTIES EXCLUDE_FROM_ALL TRUE WIN32_EXECUTABLE FALSE MACOSX_BUNDLE FALSE)
endif()

qt_add_executable(edi_trial_lock_tests tests/trial_lock_tests.cpp)
target_link_libraries(edi_trial_lock_tests PRIVATE edi_app_module edi_app_moduleplugin ${EDI_GUI_BASE_TARGETS} Qt6::QuickTest)
target_compile_definitions(edi_trial_lock_tests PRIVATE EDI_SOURCE_DIR="${PROJECT_SOURCE_DIR}")
target_sources(edi_trial_lock_tests PRIVATE "${EDI_APP_BUILD_COMMIT_CPP}")
add_dependencies(edi_trial_lock_tests edi_app_build_commit)
set_target_properties(edi_trial_lock_tests PROPERTIES AUTOMOC ON WIN32_EXECUTABLE FALSE MACOSX_BUNDLE FALSE)
if(TARGET edi_assistant_native)
    target_link_libraries(edi_trial_lock_tests PRIVATE edi_assistant_native)
endif()

qt_add_executable(edi_assistant_ui_tests tests/assistant_ui_tests.cpp)
target_link_libraries(edi_assistant_ui_tests PRIVATE edi_app_module edi_app_moduleplugin ${EDI_GUI_BASE_TARGETS} Qt6::QuickTest)
target_compile_definitions(edi_assistant_ui_tests PRIVATE EDI_SOURCE_DIR="${PROJECT_SOURCE_DIR}")
target_sources(edi_assistant_ui_tests PRIVATE "${EDI_APP_BUILD_COMMIT_CPP}")
add_dependencies(edi_assistant_ui_tests edi_app_build_commit)
set_target_properties(edi_assistant_ui_tests PROPERTIES AUTOMOC ON WIN32_EXECUTABLE FALSE MACOSX_BUNDLE FALSE)
if(TARGET edi_assistant_native)
    target_link_libraries(edi_assistant_ui_tests PRIVATE edi_assistant_native)
endif()

if(NOT EMSCRIPTEN)
    qt_add_executable(edi_assistant_guard tools/assistant_guard.cpp)
    target_link_libraries(edi_assistant_guard PRIVATE Qt6::Core)
    set_target_properties(edi_assistant_guard PROPERTIES WIN32_EXECUTABLE FALSE MACOSX_BUNDLE FALSE)
    add_dependencies(edi_app_module edi_assistant_guard)
    add_dependencies(edi_app edi_assistant_guard)
    add_dependencies(edi_app_tests edi_assistant_guard)
    qt_add_executable(edi_assistant_lifetime_host tests/assistant_lifetime_host.cpp)
    target_link_libraries(edi_assistant_lifetime_host PRIVATE edi_app_module edi_app_moduleplugin ${EDI_GUI_BASE_TARGETS})
    if(TARGET edi_assistant_native)
        target_link_libraries(edi_assistant_lifetime_host PRIVATE edi_assistant_native)
    endif()
    qt_add_executable(edi_assistant_lifetime_fixture tests/fixtures/assistant_lifetime_server.cpp)
    target_link_libraries(edi_assistant_lifetime_fixture PRIVATE Qt6::Core)
    target_sources(edi_assistant_lifetime_host PRIVATE "${EDI_APP_BUILD_COMMIT_CPP}")
    add_dependencies(edi_assistant_lifetime_host edi_app_build_commit)
    add_dependencies(edi_assistant_lifetime_host edi_assistant_guard edi_assistant_lifetime_fixture)
    if(EDI_DEPLOY_APP AND UNIX AND NOT APPLE)
        set_target_properties(edi_assistant_guard PROPERTIES INSTALL_RPATH "$ORIGIN/../lib")
    endif()
    install(TARGETS edi_assistant_guard RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR} COMPONENT desktop)
endif()

if(EDI_DEPLOY_APP)
    if(EMSCRIPTEN)
        message(FATAL_ERROR "Desktop deployment cannot target WebAssembly")
    endif()
    set(edi_deploy_filters)
    if(UNIX AND NOT APPLE)
        list(APPEND edi_deploy_filters POST_EXCLUDE_REGEXES "^/lib/" "^/lib64/" "^/usr/lib/"
            INCLUDE_PLUGINS qoffscreen qwayland)
    endif()
    qt_generate_deploy_qml_app_script(TARGET edi_app OUTPUT_SCRIPT edi_deploy_script ${edi_deploy_filters})
    install(SCRIPT ${edi_deploy_script} COMPONENT desktop)
    edi_install_assistant_runtime("${EDI_ASSISTANT_RUNTIME_INSTALL_CHECK}" "${EDI_ASSISTANT_RUNTIME_INSTALL_ROOT}")
endif()

set(EDI_RELEASE_HISTORY "${PROJECT_SOURCE_DIR}/data/releases.json" CACHE FILEPATH "Release history selected by release preparation")
set_source_files_properties("${EDI_RELEASE_HISTORY}" PROPERTIES QT_RESOURCE_ALIAS releases.json)
qt_add_resources(edi_app_module edi_release_history PREFIX "/edi"
    BASE "${PROJECT_SOURCE_DIR}/data"
    FILES "${PROJECT_SOURCE_DIR}/data/distribution.json" "${EDI_RELEASE_HISTORY}")

qt_add_executable(edi_desktop_update_tests EXCLUDE_FROM_ALL tests/desktop_update_tests.cpp)
target_link_libraries(edi_desktop_update_tests PRIVATE edi_app_module edi_app_moduleplugin ${EDI_GUI_BASE_TARGETS} Qt6::QuickTest)
target_sources(edi_desktop_update_tests PRIVATE "${EDI_APP_BUILD_COMMIT_CPP}")
add_dependencies(edi_desktop_update_tests edi_app_build_commit)
set_target_properties(edi_desktop_update_tests PROPERTIES AUTOMOC ON WIN32_EXECUTABLE FALSE MACOSX_BUNDLE FALSE)
if(TARGET edi_assistant_native)
    target_link_libraries(edi_desktop_update_tests PRIVATE edi_assistant_native)
endif()
