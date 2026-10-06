# Linked to the production app module; this is a headless observation host.
add_executable(scan_app_probe probe.cpp)
target_include_directories(scan_app_probe PRIVATE ${PROJECT_SOURCE_DIR}/app/src)
target_link_libraries(scan_app_probe PRIVATE edi_app_module edi_app_moduleplugin ${EDI_GUI_BASE_TARGETS})
target_compile_features(scan_app_probe PRIVATE cxx_std_20)
# Only the observer: SDK and production targets retain their declared release optimization.
target_compile_options(scan_app_probe PRIVATE -O0)
target_sources(scan_app_probe PRIVATE native_boundary.cpp io_faults.cpp ${SCAN_CONTRACT_NATIVE_OBJECT} ${SCAN_CONTRACT_NATIVE_FIT_OBJECT} ${SCAN_CONTRACT_NATIVE_READ_OBJECT})

add_subdirectory(reference)

set_target_properties(scan_app_probe PROPERTIES ENABLE_EXPORTS ON)
target_link_libraries(scan_app_probe PRIVATE ${CMAKE_DL_LIBS})
