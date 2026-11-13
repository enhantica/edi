// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <cstddef>
#include <optional>
#include <string>

namespace edi::detail {
std::string scan_progress_heading(const std::string& project_name, bool sequential,
                                  std::optional<int> total_files, bool resumed, std::size_t columns);
std::string scan_progress_row(int completed, std::optional<int> total_files,
                              double elapsed_seconds, int measured_completed, int ok_count,
                              int fail_count, double reduced_chi_square, std::size_t columns);
std::string scan_progress_rewrite(const std::string& line, std::size_t previous_width,
                                  std::size_t columns);
}  // namespace edi::detail
