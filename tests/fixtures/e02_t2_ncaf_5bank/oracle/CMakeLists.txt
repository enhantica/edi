cmake_minimum_required(VERSION 3.26)
project(edi_e02_t2_crysta_oracle LANGUAGES CXX)

find_package(crysta CONFIG REQUIRED)

add_executable(crysta_snapshot crysta_snapshot.cpp)
target_link_libraries(crysta_snapshot PRIVATE crysta::crysta)
target_compile_features(crysta_snapshot PRIVATE cxx_std_20)
