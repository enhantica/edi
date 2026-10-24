// SPDX-License-Identifier: BSD-3-Clause
#include <string_view>
#include <utility>

#include "edi/categories.hpp"

namespace edi {

const char* category_title(std::string_view id) {
    // The original's group names where a category matches one; a loop's title is plural, as it names its rows
    // (edi ADR-0017 §3).
    static constexpr std::pair<std::string_view, const char*> kTitles[] = {
        {"metadata", "Project"},
        {"space_group", "Space group"},
        {"cell", "Cell"},
        {"atom_site", "Atom sites"},
        {"atom_site_aniso", "Atomic displacement"},  // owner, 2026-10-06
        {"scattering_length", "Scattering lengths"},
        {"experiment_type", "Experiment type"},
        {"data", "Measured data"},  // owner, 2026-09-29
        {"data_range", "Calculation range"},
        {"instrument", "Instrument"},
        {"peak", "Peak profile"},
        {"background", "Background"},
        {"linked_structure", "Linked structures"},
        {"excluded_region", "Excluded regions"},  // owner, 2026-10-04
        {"absorption", "Absorption"},
        {"extinction", "Extinction"},
        {"preferred_orientation", "Preferred orientations"},
        {"scattering_source", "Scattering source"},
        {"refln", "Reflections"},
        {"minimizer", "Minimizer"},
        {"refine_ls", "Fitted reflections"},
        {"fitting_mode", "Fitting mode"},
        {"alias", "Aliases"},
        {"constraint", "Constraints"},
        {"joint_fit", "Joint-fit weights"},
        {"sequential_fit", "Sequential fit"},
        {"sequential_fit_extract", "Scan extraction rules"},
        {"fit_parameter", "Fit start values"},
    };
    for (const auto& [key, title] : kTitles) {
        if (key == id) {
            return title;
        }
    }
    return "";
}

}  // namespace edi
