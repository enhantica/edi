# Linked to the production app module; this is a headless observation host.
add_executable(scan_app_probe probe.cpp)
target_include_directories(scan_app_probe PRIVATE ${PROJECT_SOURCE_DIR}/app/src)
target_link_libraries(scan_app_probe PRIVATE edi_app_module edi_app_moduleplugin ${EDI_GUI_BASE_TARGETS})
target_compile_features(scan_app_probe PRIVATE cxx_std_20)
if(DEFINED SCAN_CONTRACT_ENGINE_SOURCE)
    target_sources(scan_app_probe PRIVATE observed_engine.cpp)
    target_include_directories(scan_app_probe PRIVATE "${SCAN_CONTRACT_ENGINE_SOURCE}/src")
endif()
