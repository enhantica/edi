add_executable(scan_timing_observer observer.cpp)
target_include_directories(scan_timing_observer PRIVATE ${PROJECT_SOURCE_DIR}/app/src)
target_link_libraries(scan_timing_observer PRIVATE edi_app_module edi_app_moduleplugin ${EDI_GUI_BASE_TARGETS})
target_compile_features(scan_timing_observer PRIVATE cxx_std_20)

# The SDK bootstrap belongs to executables, never their shared/core interfaces.
if(NOT EMSCRIPTEN)
    target_link_libraries(scan_timing_observer PRIVATE "$<LINK_LIBRARY:WHOLE_ARCHIVE,crysta::process_defaults>")
endif()
