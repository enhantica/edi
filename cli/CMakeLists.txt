# SPDX-License-Identifier: BSD-3-Clause
# edi CLI (ADR-0007): the `easydiffraction` console binary — C++, Python-free, Qt-free, a
# thin main() over the product core (ADR-0009). Builds in the default (Qt-free) pixi env
# alongside the core.
add_executable(easydiffraction
    main.cpp
)
target_link_libraries(easydiffraction PRIVATE edi::core)
target_compile_features(easydiffraction PRIVATE cxx_std_17)
