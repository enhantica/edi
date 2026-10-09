# SPDX-License-Identifier: BSD-3-Clause
# The gui-components base, consumed unmodified at a pinned commit (edi ADR-0015).
#
# gui-components ships its QML as a Python wheel, with no CMake build and qmldir `module` lines that do
# not match their import URIs, so edi fetches the pinned sources and declares its own QML modules under
# the upstream URIs from an explicit file list. Upstream files are never edited; the
# ones that need QtWebEngine, QtCharts, QtTest or QtMultimedia are left out (ADR-0006: WASM-clean).
#
# The pinned commit is fetched as GitHub's archive of it, checked against its SHA-256: a plain download
# with a timeout, where a git clone inside CMake could hang without a word. Offline builds point
# FETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS (EDI_GUI_COMPONENTS_SRC in tools/ci/app-build.sh) at a local copy:
# a git clone must be at the pinned commit with an unmodified src/ tree, and any other copy must hold
# exactly the pinned src/ files, or configuration stops.

include(FetchContent)

set(EDI_GUI_COMPONENTS_SHA 3897d339b60f5707bfe952fed59a20f73340e236)  # edi branch
set(EDI_GUI_COMPONENTS_ARCHIVE_SHA256 3aebde35ff5f714f83b5f76c03e4a54d40a84c196d766f020d6ce4eb683200e1)
# Every file under src/ at the pinned commit, as edi_gui_tree_sha256 below sums them.
set(EDI_GUI_COMPONENTS_SRC_SHA256 a7e0757c62cbbe0fdecb01a8b4b1abcb55eeae4354f16f1cc5155f422d1fd523)

if(NOT FETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS)
    message(STATUS "gui-components: fetching the pinned archive ${EDI_GUI_COMPONENTS_SHA} (8 MB, once per build tree)")
endif()
FetchContent_Declare(gui_components
    URL https://github.com/easyscience/gui-components/archive/${EDI_GUI_COMPONENTS_SHA}.tar.gz
    URL_HASH SHA256=${EDI_GUI_COMPONENTS_ARCHIVE_SHA256}
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE
    INACTIVITY_TIMEOUT 60
    TIMEOUT 600
    SOURCE_SUBDIR no-cmake-build  # upstream has no CMakeLists.txt; the modules are declared below
)
FetchContent_MakeAvailable(gui_components)

# The files under `dir`, each named with its SHA-256, summed in name order.
function(edi_gui_tree_sha256 dir out)
    file(GLOB_RECURSE files LIST_DIRECTORIES false RELATIVE "${dir}" "${dir}/*")
    list(SORT files)
    set(text "")
    foreach(file IN LISTS files)
        file(SHA256 "${dir}/${file}" hash)
        string(APPEND text "${file} ${hash}\n")
    endforeach()
    string(SHA256 sum "${text}")
    set(${out} ${sum} PARENT_SCOPE)
endfunction()

if(EXISTS "${gui_components_SOURCE_DIR}/.git")
    execute_process(
        COMMAND git -C ${gui_components_SOURCE_DIR} rev-parse HEAD
        OUTPUT_VARIABLE _edi_gui_sha OUTPUT_STRIP_TRAILING_WHITESPACE RESULT_VARIABLE _edi_gui_sha_rc)
    execute_process(
        COMMAND git -C ${gui_components_SOURCE_DIR} status --porcelain -- src
        OUTPUT_VARIABLE _edi_gui_dirty OUTPUT_STRIP_TRAILING_WHITESPACE)
    if(NOT _edi_gui_sha_rc EQUAL 0 OR NOT _edi_gui_sha STREQUAL EDI_GUI_COMPONENTS_SHA)
        message(FATAL_ERROR "gui-components at ${gui_components_SOURCE_DIR} is at '${_edi_gui_sha}', "
                            "not the pinned ${EDI_GUI_COMPONENTS_SHA}. "
                            "Run git -C ${gui_components_SOURCE_DIR} fetch origin edi, then "
                            "git -C ${gui_components_SOURCE_DIR} switch --detach ${EDI_GUI_COMPONENTS_SHA}, "
                            "or unset EDI_GUI_COMPONENTS_SRC to download the pinned archive.")
    endif()
    if(NOT _edi_gui_dirty STREQUAL "")
        message(FATAL_ERROR "gui-components at ${gui_components_SOURCE_DIR} has local changes under src/; "
                            "edi builds the pinned files unmodified")
    endif()
else()
    edi_gui_tree_sha256("${gui_components_SOURCE_DIR}/src" _edi_gui_tree)
    if(NOT _edi_gui_tree STREQUAL EDI_GUI_COMPONENTS_SRC_SHA256)
        message(FATAL_ERROR "gui-components at ${gui_components_SOURCE_DIR} does not hold the pinned "
                            "${EDI_GUI_COMPONENTS_SHA} src/ files unmodified")
    endif()
endif()

set(EDI_GUI_BASE_DIR ${gui_components_SOURCE_DIR}/src/EasyApplication)

# One base module: its QML types, singletons and JavaScript files, all read from the pinned tree, except
# the names in REPLACED, which edi builds from app/qml/Base/<subdir>/ in their place (Style/Fonts for edi's font set,
# Components/ListView for Qt selection-model initialization; ADR-0015 §10, ADR-0028).
function(edi_gui_base_module target uri subdir)
    cmake_parse_arguments(ARG "" "" "TYPES;SINGLETONS;SCRIPTS;REPLACED" ${ARGN})
    set(files)
    foreach(name IN LISTS ARG_TYPES ARG_SINGLETONS)
        if(name IN_LIST ARG_REPLACED)
            set(path "${PROJECT_SOURCE_DIR}/app/qml/Base/${subdir}/${name}.qml")
        else()
            set(path "${EDI_GUI_BASE_DIR}/${subdir}/${name}.qml")
        endif()
        set_source_files_properties("${path}" PROPERTIES QT_RESOURCE_ALIAS "${name}.qml")
        if(name IN_LIST ARG_SINGLETONS)
            set_source_files_properties("${path}" PROPERTIES QT_QML_SINGLETON_TYPE TRUE)
        endif()
        list(APPEND files "${path}")
    endforeach()
    # The base's QML reaches its scripts through the module's qmldir (`EaLogic.Utils.…`), as the
    # upstream qmldir declares them, so each keeps its qmldir entry. Upstream ships them without
    # `.pragma library` and edi builds them unmodified, so every importing document evaluates its own
    # copy, exactly as in the upstream module; stating the entry is what Qt asks for that choice.
    foreach(name IN LISTS ARG_SCRIPTS)
        set(path "${EDI_GUI_BASE_DIR}/${subdir}/${name}.js")
        set_source_files_properties("${path}" PROPERTIES QT_RESOURCE_ALIAS "${name}.js"
                                                         QT_QML_SKIP_QMLDIR_ENTRY FALSE)
        list(APPEND files "${path}")
    endforeach()
    qt_add_library(${target} STATIC)
    qt_add_qml_module(${target}
        URI ${uri}
        VERSION 1.0
        NO_PLUGIN
        QML_FILES ${files}
    )
endfunction()

edi_gui_base_module(edi_gui_style EasyApplication.Gui.Style Gui/Style
    SINGLETONS Colors Fonts Sizes Times
    REPLACED Fonts)
edi_gui_base_module(edi_gui_globals EasyApplication.Gui.Globals Gui/Globals
    SINGLETONS Vars)
# Left out of Logic: Plotting.js, used only by the base's Charts, which edi does not build.
edi_gui_base_module(edi_gui_logic EasyApplication.Gui.Logic Gui/Logic
    SCRIPTS ProjectConfig Translate Utils)
edi_gui_base_module(edi_gui_animations EasyApplication.Gui.Animations Gui/Animations
    TYPES ColorReset ThemeChange TranslationChange)
edi_gui_base_module(edi_gui_maintenance EasyApplication.Logic.Maintenance Logic/Maintenance
    TYPES Updater)
# Left out of Elements: RemoteController (QtTest + QtMultimedia; the original's tutorial driver), and
# SplashScreen: edi opens without a startup window (owner, 2026-09-28).
edi_gui_base_module(edi_gui_elements EasyApplication.Gui.Elements Gui/Elements
    TYPES AppBarTabButton ApplicationWindow Button CheckBox CheckIndicator ComboBox CursorDelegate
          Dialog DialogButtonBox GroupBox GroupButton GroupColumn GroupRow Label LinkedImage Menu
          MenuItem ParamComboBox Parameter ParamTextField RadioButton RemotePointer RunningLabel
          ScrollBar ScrollIndicator SideBarButton Slider SliderHandle SpinBox StatusBar
          StatusBarItem TabBar TabButton TextArea TextField TextInput ToolButton ToolTip ToolTipShadow
    REPLACED ParamTextField)
# Left out of Components: BasicReport (QtWebEngine), GuideWindow and GuideWindowContainer (they need a
# host `Gui.Globals` module), JsonListModel (the dict/JSON model edi does not use).
edi_gui_base_module(edi_gui_components EasyApplication.Gui.Components Gui/Components
    TYPES AboutDialog ApplicationWindow AppBarCentralTabs AppBarLeftButtons AppBarRightButtons
          ContentPage ContentArea MainContent SideBar SideBarColumn PreferencesDialog
          ProjectDescriptionDialog ListView ListViewHeader ListViewDelegate ListViewTextInput
          TableView TableViewHeader TableViewDelegate TableViewLabel
          TableViewAdvancedLabel TableViewTwoRowsAdvancedLabel TableViewParameter TableViewCheckBox
          TableViewComboBox TableViewButton TableViewLabelControl TableViewTextInput
    REPLACED ListView TableViewParameter)

# The fonts edi's Style/Fonts.qml (app/qml/Base/Gui/Style) loads, placed where its
# `Qt.resolvedUrl("../Resources/Fonts")` looks: the base's own faces edi keeps, and edi's (ADR-0015 §10).
set(EDI_GUI_BASE_FONTS
    "PT_Sans/PTSans-Regular.ttf" "PT_Sans/PTSans-Bold.ttf" "PT_Mono/PTMono-Regular.ttf"
    "Encode_Sans/EncodeSans-Regular.ttf"
    "FontAwesome/Font Awesome 5 Free-Solid-900.otf")
set(_edi_gui_font_files)
foreach(font IN LISTS EDI_GUI_BASE_FONTS)
    list(APPEND _edi_gui_font_files "${EDI_GUI_BASE_DIR}/Gui/Resources/Fonts/${font}")
endforeach()
qt_add_resources(edi_gui_style "edi_gui_base_fonts"
    PREFIX "/qt/qml/EasyApplication/Gui/Resources/Fonts"
    BASE "${EDI_GUI_BASE_DIR}/Gui/Resources/Fonts"
    FILES ${_edi_gui_font_files})
# edi's faces, with their licences beside them in app/resources/fonts: Noto Sans and Noto Sans Mono for every
# character PT Sans and PT Mono lack, Noto Sans Light for the large placeholder text, Baloo 2 for the wordmark.
qt_add_resources(edi_gui_style "edi_fonts"
    PREFIX "/qt/qml/EasyApplication/Gui/Resources/Fonts"
    BASE "${PROJECT_SOURCE_DIR}/app/resources/fonts"
    FILES "${PROJECT_SOURCE_DIR}/app/resources/fonts/Noto_Sans/NotoSans-Regular.ttf"
          "${PROJECT_SOURCE_DIR}/app/resources/fonts/Noto_Sans/NotoSans-Light.ttf"
          "${PROJECT_SOURCE_DIR}/app/resources/fonts/Noto_Sans_Mono/NotoSansMono-Regular.ttf"
          "${PROJECT_SOURCE_DIR}/app/resources/fonts/Baloo_2/Baloo2-Regular.ttf"
          "${PROJECT_SOURCE_DIR}/app/resources/fonts/Baloo_2/Baloo2-SemiBold.ttf")

set(EDI_GUI_BASE_TARGETS edi_gui_style edi_gui_globals edi_gui_logic edi_gui_animations
    edi_gui_maintenance edi_gui_elements edi_gui_components)
