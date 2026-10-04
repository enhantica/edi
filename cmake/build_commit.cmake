# SPDX-License-Identifier: BSD-3-Clause Embed the git commit the build was made from: a runtime
# witness must be able to prove which source it measured. Runs at EVERY build (a custom target
# with no OUTPUT), so the embedded value follows HEAD; the file is rewritten only when the value
# changes, so an unchanged HEAD does not relink. Mirrors crysta's cmake/build_commit.cmake.
# `SOURCE_DIR` and `OUT` come from the caller. With `MARKER` the file holds the commit as a marker
# string an executable carries, instead of `edi::build_commit()`. With `MARK_DIRTY` (the app test
# runner and the latency probes, whose measurements the latency bank attributes to a revision) a
# build made while tracked files differ from HEAD is stamped `<sha>-dirty`, which names no
# revision.
execute_process(
    COMMAND git -C "${SOURCE_DIR}" rev-parse HEAD
    OUTPUT_VARIABLE _commit
    OUTPUT_STRIP_TRAILING_WHITESPACE
    RESULT_VARIABLE _rc)
if(NOT _rc EQUAL 0 OR _commit STREQUAL "")
    set(_commit "unknown")
elseif(MARK_DIRTY)
    execute_process(
        COMMAND git -C "${SOURCE_DIR}" status --porcelain --untracked-files=no
        OUTPUT_VARIABLE _changed
        RESULT_VARIABLE _rc)
    if(NOT _rc EQUAL 0)
        set(_commit "unknown")
    elseif(NOT _changed STREQUAL "")
        string(APPEND _commit "-dirty")
    endif()
endif()
if(MARKER)
    # The commit as bytes in the executable, which a reader finds without running it and without
    # trusting a caller's tag; kept through the linker's garbage collection (`retain` on ELF,
    # `used` on Mach-O).
    set(_content "// The commit this executable was built from (cmake/build_commit.cmake, MARKER).
#if defined(__ELF__)
#define EDI_KEEP __attribute__((used, retain))
#else
#define EDI_KEEP __attribute__((used))
#endif
extern \"C\" EDI_KEEP const char edi_build_commit_marker[] = \"edi-build-commit:${_commit}\\n\";
")
else()
    set(_content "#include \"edi/version.hpp\"
namespace edi {
const char* build_commit() noexcept { return \"${_commit}\"; }
}  // namespace edi
")
endif()
set(_current "")
if(EXISTS "${OUT}")
    file(READ "${OUT}" _current)
endif()
if(NOT _current STREQUAL _content)
    file(WRITE "${OUT}" "${_content}")
endif()
