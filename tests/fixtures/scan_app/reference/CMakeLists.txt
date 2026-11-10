# The actual public Python binding sources, linked to the same installed SDK.
find_package(crysta CONFIG REQUIRED)
find_package(Python 3.12 COMPONENTS Interpreter Development.Module Development.SABIModule REQUIRED)
execute_process(COMMAND ${Python_EXECUTABLE} -m nanobind --cmake_dir
                OUTPUT_VARIABLE nanobind_ROOT OUTPUT_STRIP_TRAILING_WHITESPACE
                COMMAND_ERROR_IS_FATAL ANY)
find_package(nanobind CONFIG REQUIRED)
set(binding_sources crysta_ext bind_partype bind_parameter bind_enumeration bind_symmetry
    bind_model bind_scattering bind_tof_profile bind_pattern bind_residual bind_fit bind_validation)
set(binding_paths)
foreach(name IN LISTS binding_sources)
    list(APPEND binding_paths "${SCAN_CONTRACT_ENGINE_SOURCE}/src/bindings/${name}.cpp")
endforeach()
nanobind_add_module(scan_reference STABLE_ABI NB_STATIC ${binding_paths})
set_target_properties(scan_reference PROPERTIES OUTPUT_NAME "_crysta"
                      LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/package/crysta")
target_link_libraries(scan_reference PRIVATE crysta::crysta)
target_include_directories(scan_reference PRIVATE "${SCAN_CONTRACT_ENGINE_SOURCE}/src")
file(COPY "${SCAN_CONTRACT_ENGINE_SOURCE}/lib/crysta/" DESTINATION "${CMAKE_CURRENT_BINARY_DIR}/package/crysta")

file(GENERATE OUTPUT "${CMAKE_BINARY_DIR}/scan-reference-sdk.txt"
     CONTENT "$<TARGET_FILE:crysta::crysta>\n$<TARGET_PROPERTY:crysta::crysta,INTERFACE_INCLUDE_DIRECTORIES>")
