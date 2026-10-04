# SPDX-License-Identifier: BSD-3-Clause
# The gui-components base, consumed unmodified at a pinned commit (edi ADR-0015).
#
# gui-components ships its QML as a Python wheel, with no CMake build and qmldir `module` lines that do
# not match their import URIs, so edi fetches the pinned sources and declares its own QML modules under
# the upstream URIs from an explicit file list. Upstream files are never edited or copied into edi; the
# ones that need QtWebEngine, QtCharts, QtTest or QtMultimedia are left out (ADR-0006: WASM-clean).
#
# Offline builds point FETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS at a local clone; that clone must be at the
# pinned commit with an unmodified src/ tree, or configuration stops.

include(FetchContent)

set(EDI_GUI_COMPONENTS_SHA a573a9695e53a0807de197785e12f9facd06da05)  # tag v0.9.1

FetchContent_Declare(gui_components
    GIT_REPOSITORY https://github.com/easyscience/gui-components.git
    GIT_TAG ${EDI_GUI_COMPONENTS_SHA}
    SOURCE_SUBDIR no-cmake-build  # upstream has no CMakeLists.txt; the modules are declared below
)
FetchContent_MakeAvailable(gui_components)

execute_process(
    COMMAND git -C ${gui_components_SOURCE_DIR} rev-parse HEAD
    OUTPUT_VARIABLE _edi_gui_sha OUTPUT_STRIP_TRAILING_WHITESPACE RESULT_VARIABLE _edi_gui_sha_rc)
execute_process(
    COMMAND git -C ${gui_components_SOURCE_DIR} status --porcelain -- src
    OUTPUT_VARIABLE _edi_gui_dirty OUTPUT_STRIP_TRAILING_WHITESPACE)
if(NOT _edi_gui_sha_rc EQUAL 0 OR NOT _edi_gui_sha STREQUAL EDI_GUI_COMPONENTS_SHA)
    message(FATAL_ERROR "gui-components at ${gui_components_SOURCE_DIR} is at '${_edi_gui_sha}', "
                        "not the pinned ${EDI_GUI_COMPONENTS_SHA}")
endif()
if(NOT _edi_gui_dirty STREQUAL "")
    message(FATAL_ERROR "gui-components at ${gui_components_SOURCE_DIR} has local changes under src/; "
                        "edi builds the pinned files unmodified")
endif()

set(EDI_GUI_BASE_DIR ${gui_components_SOURCE_DIR}/src/EasyApplication)

# One base module: its QML types, singletons and JavaScript files, all read from the pinned tree, except
# the names in REPLACED, which edi builds from app/qml/Base/<subdir>/ in their place (only Style/Fonts:
# the font set is edi's own, ADR-0015 §10).
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
          StatusBarItem TabBar TabButton TextArea TextField TextInput ToolButton ToolTip ToolTipShadow)
# Left out of Components: BasicReport (QtWebEngine), GuideWindow and GuideWindowContainer (they need a
# host `Gui.Globals` module), JsonListModel (the dict/JSON model edi does not use).
edi_gui_base_module(edi_gui_components EasyApplication.Gui.Components Gui/Components
    TYPES AboutDialog ApplicationWindow AppBarCentralTabs AppBarLeftButtons AppBarRightButtons
          ContentPage ContentArea MainContent SideBar SideBarColumn PreferencesDialog
          ProjectDescriptionDialog TableView TableViewHeader TableViewDelegate TableViewLabel
          TableViewAdvancedLabel TableViewTwoRowsAdvancedLabel TableViewParameter TableViewCheckBox
          TableViewComboBox TableViewButton TableViewLabelControl TableViewTextInput)

# The fonts edi's Style/Fonts.qml (app/qml/Base/Gui/Style) loads, placed where its
# `Qt.resolvedUrl("../Resources/Fonts")` looks: the base's own faces edi keeps, and edi's (ADR-0015 §10).
set(EDI_GUI_BASE_FONTS
    "PT_Sans/PTSans-Regular.ttf" "PT_Sans/PTSans-Bold.ttf" "PT_Mono/PTMono-Regular.ttf"
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
