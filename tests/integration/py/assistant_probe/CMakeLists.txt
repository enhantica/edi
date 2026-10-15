cmake_minimum_required(VERSION 3.24)
project(assistant_contract_probe LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(EDI_BUILD_APP OFF CACHE BOOL "" FORCE)
set(EDI_BUILD_BINDINGS OFF CACHE BOOL "" FORCE)
set(EDI_BUILD_ASSISTANT_NATIVE OFF CACHE BOOL "" FORCE)
get_filename_component(EDI_SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/../../../.." ABSOLUTE)
add_subdirectory("${EDI_SOURCE}" edi)
if(NOT TARGET assistant_contract_probe)
    add_executable(assistant_contract_probe probe.cpp)
    target_include_directories(assistant_contract_probe PRIVATE "${EDI_SOURCE}/core/src")
    target_link_libraries(assistant_contract_probe PRIVATE edi::core)
endif()

add_executable(assistant_fit_publication_probe fit_publication_probe.cpp)
target_include_directories(assistant_fit_publication_probe PRIVATE "${EDI_SOURCE}/core/src")
target_link_libraries(assistant_fit_publication_probe PRIVATE edi::core)

add_executable(assistant_terminal_retention_probe probe.cpp)
target_compile_definitions(assistant_terminal_retention_probe PRIVATE EDI_TEST_TERMINAL_RETENTION=1)
target_include_directories(assistant_terminal_retention_probe PRIVATE "${EDI_SOURCE}/core/src")
target_link_libraries(assistant_terminal_retention_probe PRIVATE edi::core)

add_executable(assistant_interruption_probe probe.cpp)
target_compile_definitions(assistant_interruption_probe PRIVATE EDI_TEST_ADMISSION_FAULT=1)
target_include_directories(assistant_interruption_probe PRIVATE "${EDI_SOURCE}/core/src")
target_link_libraries(assistant_interruption_probe PRIVATE edi::core)

add_executable(assistant_async_settlement_probe probe.cpp)
target_compile_definitions(assistant_async_settlement_probe PRIVATE EDI_TEST_ASYNC_SETTLEMENT=1)
target_include_directories(assistant_async_settlement_probe PRIVATE "${EDI_SOURCE}/core/src")
target_link_libraries(assistant_async_settlement_probe PRIVATE edi::core)

add_executable(assistant_recovery_boundaries_probe probe.cpp)
target_compile_definitions(assistant_recovery_boundaries_probe PRIVATE
    EDI_TEST_RECOVERY_BOUNDARIES=1 EDI_TEST_ASYNC_SETTLEMENT=1
    EDI_TEST_TERMINAL_RETENTION=1 EDI_TEST_ADMISSION_FAULT=1)
target_include_directories(assistant_recovery_boundaries_probe PRIVATE "${EDI_SOURCE}/core/src")
target_link_libraries(assistant_recovery_boundaries_probe PRIVATE edi::core)

add_executable(assistant_scope_retirement_probe probe.cpp)
target_compile_definitions(assistant_scope_retirement_probe PRIVATE
    EDI_TEST_RETIREMENT_OBSERVER=1 EDI_TEST_RECOVERY_BOUNDARIES=1
    EDI_TEST_ASYNC_SETTLEMENT=1 EDI_TEST_TERMINAL_RETENTION=1 EDI_TEST_ADMISSION_FAULT=1)
target_include_directories(assistant_scope_retirement_probe PRIVATE "${EDI_SOURCE}/core/src")
target_link_libraries(assistant_scope_retirement_probe PRIVATE edi::core)
