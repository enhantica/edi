add_executable(plain_data_probe probe.cpp)
target_include_directories(plain_data_probe PRIVATE ${PROJECT_SOURCE_DIR}/app/src)
target_link_libraries(plain_data_probe PRIVATE edi_app_module edi_app_moduleplugin ${EDI_GUI_BASE_TARGETS})
target_compile_features(plain_data_probe PRIVATE cxx_std_20)

# The SDK bootstrap belongs to executables, never their shared/core interfaces.
if(NOT EMSCRIPTEN)
    target_link_libraries(plain_data_probe PRIVATE "$<LINK_LIBRARY:WHOLE_ARCHIVE,crysta::process_defaults>")
endif()
