# A prebuilt public-model observer: pytest consumes this, never compiles a second core.
add_executable(single_crystal_edge_probe probe.cpp)
target_compile_features(single_crystal_edge_probe PRIVATE cxx_std_20)
file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/probe.cpp" edge_source_sha)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS probe.cpp)
target_compile_definitions(single_crystal_edge_probe PRIVATE EDGE_SOURCE_SHA="${edge_source_sha}")
target_compile_definitions(single_crystal_edge_probe PRIVATE EDGE_EDI)
target_link_libraries(single_crystal_edge_probe PRIVATE edi_core)
