// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <string>
#include <string_view>

// ADR-0016: the loader's reach into crysta's ONE identity decision — the identity-column table and
// the representable-id domain — defined in adapter.cpp, edi's one crysta
// contact (ADR-0003). core/src-private; never installed.

namespace edi::detail {

// The category a loop column's identity names, or nullptr when `tag` is not an identity column.
const char* identity_category(const std::string& tag);

// Refuses (std::invalid_argument) an identity value no writer can re-emit (crysta's domain).
void require_representable_id(const std::string& value, const std::string& category,
                              const std::string& where);

// Crysta's physical domains, so edi's readers admit exactly what the engine's calculation
// admits — the refusal text, or empty when admissible.
std::string cell_domain_message(double a, double b, double c, double alpha_deg, double beta_deg,
                                double gamma_deg);
std::string wavelength_domain_message(double wavelength);

}  // namespace edi::detail

namespace edi {
class Project;
}  // namespace edi

namespace edi::detail {

// ADR-0035 §7: the report's settings, checked by crysta's rules; each throws std::invalid_argument naming the item.
// `_report.<item>` with its decoded value, stated into `project`; an item the category does not have is refused.
void read_report_item(std::string_view item, const std::string& value, Project& project);
// `_correlation_chart.threshold`, `_pattern_chart.x_axis` and a `_report_file.format`, checked.
double read_correlation_threshold(const std::string& value);
std::string read_pattern_x_axis(const std::string& value);
std::string read_report_file_format(const std::string& value);

}  // namespace edi::detail
