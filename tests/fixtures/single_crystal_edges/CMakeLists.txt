# A prebuilt public-model observer: pytest consumes this, never compiles a second core.
add_executable(single_crystal_edge_probe probe.cpp)
target_compile_features(single_crystal_edge_probe PRIVATE cxx_std_20)
file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/probe.cpp" edge_source_sha)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS probe.cpp)
target_compile_definitions(single_crystal_edge_probe PRIVATE EDGE_SOURCE_SHA="${edge_source_sha}")
target_compile_definitions(single_crystal_edge_probe PRIVATE EDGE_EDI)
target_link_libraries(single_crystal_edge_probe PRIVATE edi_core)

# The parser boundary shares the existing public-model preparation target.
add_executable(serialized_admission_probe ../serialized_admission/probe.cpp)
target_compile_features(serialized_admission_probe PRIVATE cxx_std_20)
file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/../serialized_admission/probe.cpp" admission_source_sha)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ../serialized_admission/probe.cpp)
target_compile_definitions(serialized_admission_probe PRIVATE
    SERIALIZED_OBSERVER_SHA="${admission_source_sha}")
target_compile_definitions(serialized_admission_probe PRIVATE SERIALIZED_EDI)
target_link_libraries(serialized_admission_probe PRIVATE edi_core)
add_dependencies(single_crystal_edge_probe serialized_admission_probe)
