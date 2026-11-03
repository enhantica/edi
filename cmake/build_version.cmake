# SPDX-License-Identifier: BSD-3-Clause
# The version and date the app shows (ApplicationInfo), from git at every build as the commit is (build_commit.cmake),
# so a build folder reused across commits shows the current ones. `SOURCE_DIR` and `OUT` come from the caller; the file
# is rewritten only when a value changes.
execute_process(
    COMMAND git -C "${SOURCE_DIR}" describe --tags --always --dirty
    OUTPUT_VARIABLE _version
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET)
execute_process(
    COMMAND git -C "${SOURCE_DIR}" log -1 "--format=%cd" "--date=format:%d %b %Y"
    OUTPUT_VARIABLE _date
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET)
if(_version STREQUAL "")
    set(_version "0.0.0+unknown")
endif()
set(_content "// The version and date the app shows (cmake/build_version.cmake).
namespace edi_app {
const char* app_version() noexcept { return \"${_version}\"; }
const char* app_date() noexcept { return \"${_date}\"; }
}  // namespace edi_app
")
set(_current "")
if(EXISTS "${OUT}")
    file(READ "${OUT}" _current)
endif()
if(NOT _current STREQUAL _content)
    file(WRITE "${OUT}" "${_content}")
endif()
