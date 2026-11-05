// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <string_view>

#include "assistant_json.hpp"
#include "assistant_skill_resources.hpp"

namespace edi::assistant::detail {
J skill_catalog(std::string_view selected, bool has_selected_files, const J& tools);
J skill_context(std::string_view selected, const J& tools,
                std::uint64_t limit = Limits::context_bytes);
}  // namespace edi::assistant::detail
