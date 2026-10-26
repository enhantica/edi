// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <optional>
#include <string>
#include <string_view>
#include <vector>

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

// The current `.edi` name `tag` reads as by crysta's dictionary: an older `.edi` spelling's, and with `every_name` (a
// structure or experiment block) any name an item lists, `.edi` or CIF, in either notation; else `tag` itself.
std::string current_edi_name(const std::string& tag, bool every_name);

// The one-row category (`_peak`, `_cell`) whose item `tag` names by crysta's dictionary, by any of its names; empty for
// an item of a loop category or a name no item lists. Such an item written as a loop column is refused.
std::string one_row_category(const std::string& tag);

// The site types whose own names include `tag`, an ADP name that spells its item for those types only
// (`_atom_site_U_iso_or_equiv`: Uiso and Uani); empty for a name every type shares (crysta ADR-0103 §1).
std::vector<std::string> name_variants(const std::string& tag);

// Returns unless `tags`, the names a structure or experiment text spells as edi's reader reads
// them, are a CIF's by crysta's rule; crysta throws std::invalid_argument for a CIF, as reading
// CIF files is not supported yet.
void refuse_cif_names(const std::vector<std::string>& tags);

// A project's structure files by crysta's rule, sorted: each `.edi` in `folder`; any other file is
// passed over.
std::vector<std::string> project_structure_files(const std::string& folder);
// A project's experiment files by the same rule.
std::vector<std::string> project_experiment_files(const std::string& folder);

}  // namespace edi::detail

namespace edi {
class Project;
}  // namespace edi

namespace edi::detail {

// ADR-0036 §7: the report's settings, checked by crysta's rules; each throws std::invalid_argument naming the item.
// `_report.<item>` with its decoded value, stated into `project`; an item the category does not have is refused.
void read_report_item(std::string_view item, const std::string& value, Project& project);
// `_correlation_chart.threshold`, `_pattern_chart.x_axis` and a `_report_file.format`, checked.
double read_correlation_threshold(const std::string& value);
// A single crystal's `_reflns.threshold_sigma`/`_refine_ls.threshold_sigma` (`tag`) and `_reflns.threshold_basis`,
// checked by crysta's rules (edi ADR-0050).
double read_threshold_sigma(const std::string& value, const char* tag);
std::string read_threshold_basis(const std::string& value);
std::string read_pattern_x_axis(const std::string& value);
std::string read_report_file_format(const std::string& value);

}  // namespace edi::detail
