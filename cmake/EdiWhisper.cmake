# SPDX-License-Identifier: BSD-3-Clause
# Voice input's speech recogniser (ADR-0107): whisper.cpp at a pinned release, built here as a static, CPU-only library
# for the desktop app. The release archive is checked against its SHA-256. Offline builds point
# FETCHCONTENT_SOURCE_DIR_WHISPER (EDI_WHISPER_SRC in tools/ci/app-build.sh) at an unpacked copy of the same release.
if(EMSCRIPTEN)
    return()
endif()
include(FetchContent)

set(EDI_WHISPER_VERSION 1.9.6)
set(EDI_WHISPER_ARCHIVE_SHA256 7ab15dc88022d2425ad94dcffd8abbf1b6d7018089b4e48d6b40780738e0b445)

FetchContent_Declare(whisper
    URL https://github.com/ggml-org/whisper.cpp/archive/refs/tags/v${EDI_WHISPER_VERSION}.tar.gz
    URL_HASH SHA256=${EDI_WHISPER_ARCHIVE_SHA256}
    DOWNLOAD_EXTRACT_TIMESTAMP FALSE
    INACTIVITY_TIMEOUT 60
    TIMEOUT 600)

function(edi_whisper_targets)
    # whisper.cpp asks for CMake 3.5, so its option() calls would drop these settings without the newer policy.
    set(CMAKE_POLICY_DEFAULT_CMP0077 NEW)
    set(BUILD_SHARED_LIBS OFF)
    set(WHISPER_BUILD_TESTS OFF)
    set(WHISPER_BUILD_EXAMPLES OFF)
    set(WHISPER_BUILD_SERVER OFF)
    set(WHISPER_ALL_WARNINGS OFF)
    set(WHISPER_CURL OFF)
    set(WHISPER_SDL2 OFF)
    set(WHISPER_COREML OFF)
    set(WHISPER_OPENVINO OFF)
    set(GGML_ALL_WARNINGS OFF)
    set(GGML_CCACHE OFF)
    # An installer runs on other machines than the one that built it: no -march=native, and on x86-64 the AVX2
    # generation (ADR-0107). Apple silicon gets NEON and Accelerate from ggml's defaults.
    set(GGML_NATIVE OFF)
    if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|AMD64|amd64)$")
        set(GGML_SSE42 ON)
        set(GGML_AVX ON)
        set(GGML_AVX2 ON)
        set(GGML_BMI2 ON)
        set(GGML_FMA ON)
        set(GGML_F16C ON)
    endif()
    # CPU only: ggml's own thread pool, no OpenMP runtime to ship, no GPU backend.
    set(GGML_OPENMP OFF)
    set(GGML_METAL OFF)
    set(GGML_CUDA OFF)
    set(GGML_VULKAN OFF)
    set(GGML_BACKEND_DL OFF)
    FetchContent_MakeAvailable(whisper)
    # Only what the app links is built, and whisper's headers do not take edi's warning set.
    set_property(DIRECTORY "${whisper_SOURCE_DIR}" PROPERTY EXCLUDE_FROM_ALL TRUE)
    foreach(target whisper ggml ggml-base ggml-cpu)
        if(TARGET ${target})
            get_target_property(includes ${target} INTERFACE_INCLUDE_DIRECTORIES)
            if(includes)
                set_target_properties(${target} PROPERTIES INTERFACE_SYSTEM_INCLUDE_DIRECTORIES "${includes}")
            endif()
        endif()
    endforeach()
endfunction()
edi_whisper_targets()
