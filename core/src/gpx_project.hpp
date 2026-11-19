// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <string_view>

#include "json.hpp"

namespace edi::gpx {
json::Value decode_project(std::string_view bytes, const std::string& filename);
}  // namespace edi::gpx
