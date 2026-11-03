// SPDX-License-Identifier: BSD-3-Clause
#pragma once

namespace edi_app {

// The version (git describe) and the commit date the app shows, written at every build (cmake/build_version.cmake).
const char* app_version() noexcept;
const char* app_date() noexcept;

}  // namespace edi_app
