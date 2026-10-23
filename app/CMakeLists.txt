# SPDX-License-Identifier: BSD-3-Clause
# The one edi QML app host (ADR-0009, ADR-0015): one QML module (`edi.app`) on one source tree, built
# for desktop now and WASM later (E07) from this host. The module is a static library so the host and
# the Qt Quick Test runner load exactly the same types, pages and engine setup.

set(QT_QML_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/qml)
include(${PROJECT_SOURCE_DIR}/cmake/EdiGuiBase.cmake)

# What the app tells its user about itself (ApplicationInfo): configured once, from git when available.
execute_process(COMMAND git -C ${PROJECT_SOURCE_DIR} describe --tags --always --dirty
                OUTPUT_VARIABLE EDI_APP_GIT_DESCRIBE OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET)
execute_process(COMMAND git -C ${PROJECT_SOURCE_DIR} log -1 --format=%cd --date=format:%d\ %b\ %Y
                OUTPUT_VARIABLE EDI_APP_GIT_DATE OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET)
set(EDI_APP_VERSION "${EDI_APP_GIT_DESCRIBE}" CACHE STRING "Version shown by the app")
if(EDI_APP_VERSION STREQUAL "")
    set(EDI_APP_VERSION "0.0.0+unknown")
endif()
set(EDI_APP_DATE "${EDI_APP_GIT_DATE}")
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
        src/example_list_model.hpp src/example_list_model.cpp
        src/engine_setup.hpp src/engine_setup.cpp
        src/demo_driver.hpp src/demo_driver.cpp
        src/test_observer.hpp src/test_observer.cpp
        src/web_page_hooks.hpp src/web_page_hooks.cpp
        src/project_editor.hpp
        src/row_table_model.hpp src/row_table_model.cpp
        src/parameter_item.hpp src/parameter_item.cpp
        src/parameter_registry.hpp src/parameter_registry.cpp
        src/option_list_model.hpp src/option_list_model.cpp
        src/block_text.hpp src/block_text.cpp
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
        src/web_files.hpp src/web_files.cpp
    QML_FILES
        qml/Main.qml
        qml/Components/AppDialog.qml
        qml/Components/AppPreferencesDialog.qml
        qml/Components/BlockSelector.qml
        qml/Components/CategoryGroup.qml
        qml/Components/DiagnosticsDialog.qml
        qml/Components/EmptyStateLabel.qml
        qml/Components/DataTable.qml
        qml/Components/DigitText.qml
        qml/Components/FitStatusItem.qml
        qml/Components/FitProgressBar.qml
        qml/Components/FitResultsDialog.qml
        qml/Components/ChartLegend.qml
        qml/Components/FigureColors.qml
        qml/Components/ChartToolButton.qml
        qml/Components/ChartToolbar.qml
        qml/Components/IconCell.qml
        qml/Components/IconLine.qml
        qml/Components/IconTabButton.qml
        qml/Components/MainAreaBlockSelector.qml
        qml/Components/NumberLabel.qml
        qml/Components/ParameterCell.qml
        qml/Components/ParameterField.qml
        qml/Components/ParameterGrid.qml
        qml/Components/PatternChart.qml
        qml/Components/ProjectPatternChart.qml
        qml/Components/EvolutionChart.qml
        qml/Components/ScanViewChart.qml
        qml/Components/CorrelationChart.qml
        qml/Components/SearchableComboBox.qml
        qml/Components/SelectedPatternBox.qml
        qml/Components/SelectedPatternLine.qml
        qml/Components/SelectorField.qml
        qml/Components/StatusBar.qml
        qml/Components/StatusBarItem.qml
        qml/Components/StructureScene.qml
        qml/Components/StructureToolbar.qml
        qml/Components/StructureView.qml
        qml/Components/TableRow.qml
        qml/Components/TextCell.qml
        qml/Components/TextTab.qml
        qml/Components/ToolbarComboBox.qml
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
        qml/Pages/Analysis/FittingGroup.qml
        qml/Pages/Analysis/FittingModeGroup.qml
        qml/Pages/Analysis/FreeHeaderMenu.qml
        qml/Pages/Analysis/JointFitGroup.qml
        qml/Pages/Analysis/MinimizerGroup.qml
        qml/Pages/Analysis/ParametersGroup.qml
        qml/Pages/Analysis/PatternUpdatesGroup.qml
        qml/Pages/Analysis/SequentialExtractGroup.qml
        qml/Pages/Analysis/SequentialFitGroup.qml
        qml/Pages/Experiment/AbsorptionGroup.qml
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
        qml/Pages/Home/HomePage.qml
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
)
target_include_directories(edi_app_module PUBLIC src ${CMAKE_CURRENT_BINARY_DIR})
target_link_libraries(edi_app_module
    PUBLIC Qt6::Quick Qt6::QuickControls2 Qt6::Graphs Qt6::Quick3D Qt6::Concurrent edi::core
    PRIVATE ${EDI_GUI_BASE_TARGETS} Qt6::CorePrivate)
if(EMSCRIPTEN)
    target_link_libraries(edi_app_module PRIVATE Qt6::GuiPrivate)
endif()

# The Examples: the user-facing projects of edi's CLI registry (`user-facing: true`), in registry order, each
# with its scan data (a scan's datasets are browsed in the app). Every other registered project is a test
# fixture, and verification projects stay CLI projects only (ADR-0031). Configuration fails when the registry
# and the project directories disagree.
set(_cli ${PROJECT_SOURCE_DIR}/docs/user/cli)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${_cli}/projects.yml)
file(STRINGS ${_cli}/projects.yml _registry_lines REGEX "^  - id: |^    user-facing: ")
set(_registered_ids)
set(EDI_APP_EXAMPLE_IDS)
foreach(line IN LISTS _registry_lines)
    if(line MATCHES "^  - id: *(.+)$")
        set(id ${CMAKE_MATCH_1})
        if(NOT IS_DIRECTORY ${_cli}/${id}/project)
            message(FATAL_ERROR "docs/user/cli/projects.yml lists '${id}', which has no docs/user/cli/${id}/project/")
        endif()
        list(APPEND _registered_ids ${id})
    elseif(line MATCHES "^    user-facing: *true$")
        list(APPEND EDI_APP_EXAMPLE_IDS ${id})
    endif()
endforeach()
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
    if(_purpose STREQUAL "verification")
        list(REMOVE_ITEM EDI_APP_EXAMPLE_IDS ${id})
    elseif(NOT _purpose STREQUAL "refinement" AND NOT _purpose STREQUAL "simulation")
        message(FATAL_ERROR "Example '${id}' has purpose '${_purpose}', not refinement, simulation or verification")
    endif()
endforeach()
function(edi_app_bundle_examples root)
    foreach(id IN LISTS ARGN)
        file(GLOB_RECURSE files CONFIGURE_DEPENDS ${root}/${id}/project/*)
        qt_add_resources(edi_app_module "edi_example_${id}" PREFIX "/edi/examples" BASE ${root} FILES ${files})
    endforeach()
endfunction()
edi_app_bundle_examples(${_cli} ${EDI_APP_EXAMPLE_IDS})
qt_add_resources(edi_app_module "edi_example_metadata" PREFIX "/edi/examples"
                 BASE ${CMAKE_CURRENT_SOURCE_DIR}/examples FILES ${CMAKE_CURRENT_SOURCE_DIR}/examples/metadata.json)
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
    ${PROJECT_SOURCE_DIR}/DEPENDENCIES.md ${PROJECT_SOURCE_DIR}/app/DISTRIBUTION-LICENSE.md)
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
target_link_libraries(edi_app PRIVATE edi_app_module edi_app_moduleplugin ${EDI_GUI_BASE_TARGETS})
set_target_properties(edi_app PROPERTIES MACOSX_BUNDLE FALSE WIN32_EXECUTABLE TRUE)
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
target_link_libraries(edi_app_tests PRIVATE edi_app_module edi_app_moduleplugin ${EDI_GUI_BASE_TARGETS}
                                            Qt6::QuickTest)
# The demo and the test observers open test projects the app does not bundle from the source tree (ADR-0048).
set_source_files_properties(src/demo_driver.cpp PROPERTIES
                            COMPILE_DEFINITIONS "EDI_CLI_PROJECTS_DIR=\"${PROJECT_SOURCE_DIR}/docs/user/cli\"")
target_compile_definitions(edi_app_tests PRIVATE
    QUICK_TEST_SOURCE_DIR="${PROJECT_SOURCE_DIR}/tests/unit/app")
set_target_properties(edi_app_tests PROPERTIES AUTOMOC ON WIN32_EXECUTABLE FALSE MACOSX_BUNDLE FALSE)

include(GNUInstallDirs)
install(TARGETS edi_app RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
install(FILES ${EDI_APP_LICENCE_FILES} DESTINATION ${CMAKE_INSTALL_DOCDIR})
