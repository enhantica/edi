cmake_minimum_required(VERSION 3.24)
project(parameter_notation_gate LANGUAGES CXX)
find_package(crysta CONFIG REQUIRED)
find_package(doctest CONFIG REQUIRED)
add_executable(notation_probe
    "${EDI_ROOT}/tools/probes/edi_tests_main.cpp"
    "${EDI_ROOT}/tests/unit/cpp/test_report_format.cpp"
    "${EDI_ROOT}/tests/unit/cpp/test_dictionary_parameter_table.cpp")
target_compile_features(notation_probe PRIVATE cxx_std_20)
target_include_directories(notation_probe PRIVATE "${EDI_ROOT}/core/include")
target_link_libraries(notation_probe PRIVATE "${EDI_CORE_LIBRARY}" crysta::crysta doctest::doctest)
