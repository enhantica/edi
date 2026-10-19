cmake_minimum_required(VERSION 3.24)
project(assistant_consent_probe LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(EDI_BUILD_APP ON CACHE BOOL "" FORCE)
set(EDI_BUILD_BINDINGS OFF CACHE BOOL "" FORCE)
set(EDI_BUILD_ASSISTANT_NATIVE ON CACHE BOOL "" FORCE)
find_package(Qt6 REQUIRED COMPONENTS Core Gui Network Test Qml Quick QuickControls2 Graphs Quick3D Concurrent)
get_filename_component(EDI_SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/../../../.." ABSOLUTE)
add_subdirectory("${EDI_SOURCE}" edi)
qt_add_executable(assistant_consent_probe probe.cpp)
set_target_properties(assistant_consent_probe PROPERTIES AUTOMOC ON)
target_include_directories(assistant_consent_probe PRIVATE
    "${EDI_SOURCE}/tests/integration/py/assistant_native_probe")
target_link_libraries(assistant_consent_probe PRIVATE edi_app_module edi_app_moduleplugin
    edi_assistant_native edi_gui_style edi_gui_globals edi_gui_logic edi_gui_animations
    edi_gui_maintenance edi_gui_elements edi_gui_components Qt6::Test Qt6::Network)

# The SDK bootstrap belongs to executables, never their shared/core interfaces.
if(NOT EMSCRIPTEN)
    target_link_libraries(assistant_consent_probe PRIVATE "$<LINK_LIBRARY:WHOLE_ARCHIVE,crysta::process_defaults>")
endif()
