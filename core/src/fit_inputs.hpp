// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <iomanip>
#include <locale>
#include <sstream>
#include <vector>
#include "edi/model.hpp"

namespace edi::detail {
struct FitInputs {
    std::vector<std::uint64_t> identities;
    std::string settings;
};

inline FitInputs inputs_of(Project& project) {
    FitInputs inputs;
    for (const Parameter* parameter : project.parameters()) {
        inputs.identities.push_back(parameter->value.written());
        inputs.identities.push_back(parameter->uncertainty.written());
        inputs.identities.push_back(parameter->free.written());
        inputs.identities.push_back(parameter->start_value.written());
        inputs.identities.push_back(parameter->start_uncertainty.written());
    }
    std::ostringstream settings;
    settings.imbue(std::locale::classic());
    settings << std::setprecision(17) << project.fitting_mode << '\x1f' << project.descent << '\x1f'
             << project.minimizer_max_iterations << '\x1f' << project.minimizer_chi_square_tolerance << '\x1f'
             << (project.minimizer_type.has_value() ? "T" + *project.minimizer_type : std::string("-"));
    for (const auto& experiment : project.experiments) {
        settings << '\x1f' << experiment->dataset_weight;
    }
    inputs.settings = settings.str();
    return inputs;
}

inline bool operator!=(const FitInputs& a, const FitInputs& b) {
    return a.identities != b.identities || a.settings != b.settings;
}

}  // namespace edi::detail
