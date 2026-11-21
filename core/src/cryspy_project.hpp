// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <string>

#include "edi/io.hpp"

namespace edi {
// A cryspy .rcif project as a new, unsaved project (ADR-0099); the import base names and checks it.
Project load_cryspy_project(const std::string& path, const WarningSink& on_warning = {});
}  // namespace edi
