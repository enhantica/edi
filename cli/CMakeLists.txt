# SPDX-License-Identifier: BSD-3-Clause
# edi CLI (ADR-0007): the `easydiffraction` console binary — C++, Python-free, Qt-free, a
# thin main() over the product core (ADR-0009). Builds in the default (Qt-free) pixi env
# alongside the core.
add_executable(easydiffraction
    main.cpp
)
target_link_libraries(easydiffraction PRIVATE edi::core)
target_compile_features(easydiffraction PRIVATE cxx_std_17)

# The CLI carries edi's licence and the notice of each third-party component it ships, as DEPENDENCIES.md lists for
# it (cli/licence-files.txt, written by tools/licences/sync.py): beside the executable after every build, and installed
# with it, so a CLI copied or installed from either place brings its notices.
file(STRINGS ${CMAKE_CURRENT_SOURCE_DIR}/licence-files.txt EDI_CLI_LICENCE_NAMES)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/licence-files.txt)
set(EDI_CLI_LICENCE_FILES)
foreach(name IN LISTS EDI_CLI_LICENCE_NAMES)
    list(APPEND EDI_CLI_LICENCE_FILES ${PROJECT_SOURCE_DIR}/licenses/${name})
endforeach()
add_custom_command(TARGET easydiffraction POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different ${PROJECT_SOURCE_DIR}/LICENSE $<TARGET_FILE_DIR:easydiffraction>/LICENSE
    COMMAND ${CMAKE_COMMAND} -E make_directory $<TARGET_FILE_DIR:easydiffraction>/licenses
    COMMAND ${CMAKE_COMMAND} -E copy_if_different ${EDI_CLI_LICENCE_FILES} $<TARGET_FILE_DIR:easydiffraction>/licenses/
    VERBATIM)
# The app's build installs the desktop app alone, so the CLI is installed only from a build without it.
if(NOT EDI_BUILD_APP)
    include(GNUInstallDirs)
    install(TARGETS easydiffraction RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
    install(FILES ${PROJECT_SOURCE_DIR}/LICENSE DESTINATION ${CMAKE_INSTALL_DOCDIR})
    install(FILES ${EDI_CLI_LICENCE_FILES} DESTINATION ${CMAKE_INSTALL_DOCDIR}/licenses)
endif()
