// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <string>

namespace edi {
class Project;

Project load_gsas_project(const std::string& path);
}  // namespace edi
