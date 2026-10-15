// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <span>
#include <string_view>
#include "assistant_json.hpp"

namespace edi::assistant::detail {
// Immutable bytes are bonded to the strict manifest by CMake file(SHA256).
// No runtime path, fetch, public provider service or mutable resource cache.
struct SkillResource { std::string_view id, sha256, content; };
std::string_view skill_index_data();
std::span<const SkillResource> skill_resource_data();
J skill_catalog(std::string_view selected, bool has_selected_files, const J& tools);
J skill_context(std::string_view selected, const J& tools);
}
