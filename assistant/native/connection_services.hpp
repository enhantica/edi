// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include "chatgpt_connection.hpp"

namespace edi::assistant::native {
struct ProductionServices {
    NativeDependencies dependencies;
    std::function<void()> release_records;
};
ProductionServices production_services();
void validate_dependencies(const NativeDependencies& dependencies);
}
