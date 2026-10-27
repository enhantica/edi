cmake_minimum_required(VERSION 3.24)
if(EMSCRIPTEN)
    return()
endif()
if(NOT TARGET edi_app_module)
    message(FATAL_ERROR "Add the acceptance directory after the real app in its ordinary root configure")
endif()
get_filename_component(EDI_SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/../../../.." ABSOLUTE)
find_package(Qt6 REQUIRED COMPONENTS QuickTest Test Network)
get_directory_property(_edi_test_gui_targets DIRECTORY "${EDI_SOURCE}/app"
                       DEFINITION EDI_GUI_BASE_TARGETS)
if(NOT _edi_test_gui_targets)
    message(FATAL_ERROR "The real app must provide its current GUI targets to its acceptance host")
endif()
qt_add_executable(assistant_real_owner_probe probe.cpp)
set_target_properties(assistant_real_owner_probe PROPERTIES AUTOMOC ON)
target_include_directories(assistant_real_owner_probe PRIVATE
    "${EDI_SOURCE}/tests/integration/py/assistant_native_probe")
target_link_libraries(assistant_real_owner_probe PRIVATE edi_app_module edi_app_moduleplugin
    edi_assistant_native ${_edi_test_gui_targets} Qt6::QuickTest Qt6::Test Qt6::Network)
if(NOT EMSCRIPTEN)
    target_link_libraries(assistant_real_owner_probe PRIVATE
        "$<LINK_LIBRARY:WHOLE_ARCHIVE,crysta::process_defaults>")
endif()
