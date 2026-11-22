// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <string>

#include "edi/io.hpp"

namespace edi {

Project load_gsas_project(const std::string& path, const WarningSink& on_warning = {});
}  // namespace edi
