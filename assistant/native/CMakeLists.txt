# SPDX-License-Identifier: BSD-3-Clause
find_package(Qt6 REQUIRED COMPONENTS Core Gui Network)
find_package(OpenSSL REQUIRED)
add_library(edi_assistant_native STATIC chatgpt_connection.cpp connection_services.cpp)
target_include_directories(edi_assistant_native PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}
    PRIVATE ${PROJECT_SOURCE_DIR}/third_party/jwt-cpp/include ${PROJECT_SOURCE_DIR}/core/src)
target_link_libraries(edi_assistant_native PUBLIC edi::core Qt6::Core Qt6::Gui Qt6::Network PRIVATE OpenSSL::Crypto)
target_compile_features(edi_assistant_native PUBLIC cxx_std_20)
