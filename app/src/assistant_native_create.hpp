// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include "edi/io.hpp"
#include <QJsonObject>
#include <string>
#include <utility>
#include <vector>
namespace edi_app {
// App-private composition input. The caller must obtain text/path from the
// genuine request's immutable selected-file IDs, never a model-supplied path.
struct NativeCwlRecipe {
    std::string project_name, description, experiment_name;
    edi::ExperimentTypeTokens type;
    std::string peak_profile;
    double wavelength = 0, zero_offset = 0, phase_scale = 0;
    std::vector<std::pair<double, double>> background, exclusions;
    std::vector<std::pair<std::string, double>> initial_parameters;
};
// The generic runtime must supply an explicit typed recipe. No host instrument,
// wavelength/profile/background/chemical choices are silently invented here.
QJsonObject native_cwl_recipe_schema();
NativeCwlRecipe parse_native_cwl_recipe(const QJsonObject& recipe);
struct NativeCwlCandidate {
    edi::Project project;
    std::size_t points = 0, skipped = 0, nonpositive = 0, duplicates = 0, reordered = 0, derived_sigma = 0;
};
// Prepares a new owned candidate only. No app adoption, fit, original mutation,
// save, provider action or permission expansion occurs here.
NativeCwlCandidate prepare_native_cwl_project(const std::string& selected_cif_text,
                                             const std::string& selected_measurement_snapshot,
                                             const NativeCwlRecipe& recipe);
} // namespace edi_app
