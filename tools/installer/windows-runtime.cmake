# SPDX-License-Identifier: BSD-3-Clause
if(NOT WIN32 OR NOT IS_DIRECTORY "${STAGE}/bin" OR NOT IS_DIRECTORY "${PREFIX}/Library/bin")
    message(FATAL_ERROR "Windows runtime deployment requires a staged app and its build prefix")
endif()
file(GLOB_RECURSE modules "${STAGE}/*.dll")
list(FILTER modules EXCLUDE REGEX "/libexec/edi/codex/")
file(GET_RUNTIME_DEPENDENCIES
    EXECUTABLES "${STAGE}/bin/edi_app.exe" "${STAGE}/bin/edi_assistant_guard.exe"
    LIBRARIES ${modules}
    DIRECTORIES "${STAGE}/bin" "${PREFIX}/Library/bin"
    PRE_EXCLUDE_REGEXES "^[Aa][Pp][Ii]-[Mm][Ss]-" "^[Ee][Xx][Tt]-[Mm][Ss]-"
    POST_EXCLUDE_REGEXES "[/\\\\][Ww][Ii][Nn][Dd][Oo][Ww][Ss][/\\\\][Ss][Yy][Ss][Tt][Ee][Mm]32[/\\\\]"
    RESOLVED_DEPENDENCIES_VAR dependencies
    UNRESOLVED_DEPENDENCIES_VAR missing)
if(missing)
    message(FATAL_ERROR "Unresolved Windows runtime dependencies: ${missing}")
endif()
foreach(dependency IN LISTS dependencies)
    cmake_path(IS_PREFIX STAGE "${dependency}" NORMALIZE already_staged)
    if(NOT already_staged)
        file(INSTALL "${dependency}" DESTINATION "${STAGE}/bin" TYPE SHARED_LIBRARY)
    endif()
endforeach()
