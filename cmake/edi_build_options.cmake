# SPDX-License-Identifier: BSD-3-Clause
# Shared native compiler policy, also exercised before full installer builds (ADR-0071).
if(MSVC)
    add_compile_options(/bigobj
        "$<$<COMPILE_LANGUAGE:CXX>:/utf-8>"
        "$<$<COMPILE_LANGUAGE:CXX>:/EHsc>"
        "$<$<COMPILE_LANGUAGE:CXX>:/Zc:ternary>")
endif()
if(WIN32)
    add_compile_definitions(NOMINMAX)
endif()
