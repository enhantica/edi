cmake_minimum_required(VERSION 3.24)
project(native_dialogs LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_AUTOMOC ON)
find_package(Qt6 REQUIRED COMPONENTS Core Gui Qml Widgets Test)
get_filename_component(EDI_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../.." ABSOLUTE)
add_executable(native_dialog_probe probe.cpp
    "${EDI_ROOT}/app/src/native_dialog.cpp" "${EDI_ROOT}/app/src/native_dialog.hpp"
    "${EDI_ROOT}/app/src/native_dialog_helper.cpp")
target_include_directories(native_dialog_probe PRIVATE "${EDI_ROOT}/app/src")
target_link_libraries(native_dialog_probe PRIVATE Qt6::Core Qt6::Gui Qt6::Qml Qt6::Widgets Qt6::Test)
