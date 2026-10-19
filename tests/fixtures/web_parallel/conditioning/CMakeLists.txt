cmake_minimum_required(VERSION 3.25)
project(native_conditioning LANGUAGES CXX)
find_package(crysta CONFIG REQUIRED)
add_executable(native_conditioning capture.cpp)
target_compile_features(native_conditioning PRIVATE cxx_std_20)
target_link_libraries(native_conditioning PRIVATE crysta::crysta)

# The SDK bootstrap belongs to executables, never their shared/core interfaces.
if(NOT EMSCRIPTEN)
    target_link_libraries(native_conditioning PRIVATE "$<LINK_LIBRARY:WHOLE_ARCHIVE,crysta::process_defaults>")
endif()
