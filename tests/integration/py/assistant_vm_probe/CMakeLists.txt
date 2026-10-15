cmake_minimum_required(VERSION 3.24)
project(assistant_vm_resource_probe LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(EDI_BUILD_APP ON CACHE BOOL "" FORCE)
set(EDI_BUILD_BINDINGS OFF CACHE BOOL "" FORCE)
set(EDI_BUILD_ASSISTANT_NATIVE ON CACHE BOOL "" FORCE)
find_package(Qt6 REQUIRED COMPONENTS Core Gui Network Test Qml Quick QuickControls2 Graphs Quick3D Concurrent)
get_filename_component(EDI_SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/../../../.." ABSOLUTE)
add_subdirectory("${EDI_SOURCE}" edi)
qt_add_executable(assistant_vm_resource_probe probe.cpp)
set_target_properties(assistant_vm_resource_probe PROPERTIES AUTOMOC ON)
target_include_directories(assistant_vm_resource_probe PRIVATE
    "${EDI_SOURCE}/tests/integration/py/assistant_native_probe")
target_link_libraries(assistant_vm_resource_probe PRIVATE edi_app_module edi_app_moduleplugin
    edi_assistant_native edi_gui_style edi_gui_globals edi_gui_logic edi_gui_animations
    edi_gui_maintenance edi_gui_elements edi_gui_components Qt6::Test Qt6::Network)

# Separate files consumer; existing resource consumer retains its original public surface.
qt_add_executable(assistant_selected_vm_probe probe.cpp)
set_target_properties(assistant_selected_vm_probe PROPERTIES AUTOMOC ON)
target_compile_definitions(assistant_selected_vm_probe PRIVATE EDI_TEST_SELECTED_FILES=1)
target_include_directories(assistant_selected_vm_probe PRIVATE
    "${EDI_SOURCE}/tests/integration/py/assistant_native_probe")
target_link_libraries(assistant_selected_vm_probe PRIVATE edi_app_module edi_app_moduleplugin
    edi_assistant_native edi_gui_style edi_gui_globals edi_gui_logic edi_gui_animations
    edi_gui_maintenance edi_gui_elements edi_gui_components Qt6::Test Qt6::Network)

# PRIVATE proposed additional target in existing assistant_vm_probe/CMakeLists.txt.
# Existing resource/selected targets and their source remain byte-identical.
qt_add_executable(assistant_preferences_vm_probe preferences_probe.cpp)
set_target_properties(assistant_preferences_vm_probe PROPERTIES AUTOMOC ON)
target_include_directories(assistant_preferences_vm_probe PRIVATE
    "${EDI_SOURCE}/tests/integration/py/assistant_native_probe")
target_link_libraries(assistant_preferences_vm_probe PRIVATE edi_app_module edi_app_moduleplugin
    edi_assistant_native edi_gui_style edi_gui_globals edi_gui_logic edi_gui_animations
    edi_gui_maintenance edi_gui_elements edi_gui_components Qt6::Test Qt6::Network)
