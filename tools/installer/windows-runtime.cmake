# SPDX-License-Identifier: BSD-3-Clause

# A staged executable and a prefix DLL can resolve the same runtime by different paths.
function(edi_choose_runtime_copy name output)
    set(selected "")
    set(digest "")
    foreach(candidate IN LISTS ARGN)
        file(SHA256 "${candidate}" candidate_digest)
        if(digest AND NOT digest STREQUAL candidate_digest)
            message(FATAL_ERROR "Different Windows runtime copies found for ${name}: ${ARGN}")
        endif()
        set(digest "${candidate_digest}")
        cmake_path(IS_PREFIX STAGE "${candidate}" NORMALIZE in_stage)
        if(NOT selected OR in_stage)
            set(selected "${candidate}")
        endif()
    endforeach()
    set("${output}" "${selected}" PARENT_SCOPE)
endfunction()

# Allow the byte comparison to be exercised without running the Windows scanner.
if(NOT CMAKE_SCRIPT_MODE_FILE STREQUAL CMAKE_CURRENT_LIST_FILE)
    return()
endif()
if(POLICY CMP0207)
    cmake_policy(SET CMP0207 NEW)
endif()
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
    CONFLICTING_DEPENDENCIES_PREFIX conflicts
    RESOLVED_DEPENDENCIES_VAR dependencies
    UNRESOLVED_DEPENDENCIES_VAR missing)
if(missing)
    message(FATAL_ERROR "Unresolved Windows runtime dependencies: ${missing}")
endif()
foreach(name IN LISTS conflicts_FILENAMES)
    edi_choose_runtime_copy("${name}" selected ${conflicts_${name}})
    list(APPEND dependencies "${selected}")
endforeach()
foreach(dependency IN LISTS dependencies)
    cmake_path(IS_PREFIX STAGE "${dependency}" NORMALIZE already_staged)
    if(NOT already_staged)
        file(INSTALL "${dependency}" DESTINATION "${STAGE}/bin" TYPE SHARED_LIBRARY)
    endif()
endforeach()
