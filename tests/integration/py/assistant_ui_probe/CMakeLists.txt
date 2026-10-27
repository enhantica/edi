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

# Same kit, same core adapter and doctest main; only the existing owner-thread
# worker/preview translation units differ. Do not whole-archive edi_core here:
# its ordinary worker objects must not replace these actual mode-1 objects.
find_package(doctest CONFIG REQUIRED)
add_library(assistant_owner_preview_objects OBJECT
    "${EDI_SOURCE}/core/src/worker.cpp"
    "${EDI_SOURCE}/core/src/live_preview.cpp"
    "${EDI_SOURCE}/tests/unit/cpp/test_e11_t5_preview_admission.cpp")
target_compile_features(assistant_owner_preview_objects PRIVATE cxx_std_20)
target_compile_definitions(assistant_owner_preview_objects PRIVATE EDI_WORKER_OWNER_THREAD=1)
target_include_directories(assistant_owner_preview_objects PRIVATE
    "${EDI_SOURCE}/core/include" "${EDI_SOURCE}/core/src")
target_link_libraries(assistant_owner_preview_objects PRIVATE
    crysta::crysta Threads::Threads doctest::doctest)
add_executable(assistant_owner_preview_probe EXCLUDE_FROM_ALL
    "${EDI_SOURCE}/tools/probes/edi_tests_main.cpp"
    $<TARGET_OBJECTS:assistant_owner_preview_objects>)
target_link_libraries(assistant_owner_preview_probe PRIVATE edi::core doctest::doctest)
