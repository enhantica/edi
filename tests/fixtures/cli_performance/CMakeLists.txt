add_executable(edi_cli_performance_observer
    "${PROJECT_SOURCE_DIR}/cli/main.cpp"
    "${PROJECT_SOURCE_DIR}/cli/downloads.cpp"
    "${PROJECT_SOURCE_DIR}/cli/transport.cpp"
    observer.cpp)
target_link_libraries(edi_cli_performance_observer PRIVATE edi_core)
target_compile_features(edi_cli_performance_observer PRIVATE cxx_std_20)
if(WIN32)
    target_link_libraries(edi_cli_performance_observer PRIVATE winhttp)
else()
    target_link_libraries(edi_cli_performance_observer PRIVATE ${CMAKE_DL_LIBS})
endif()
