// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_native_create.hpp"
#include "background_input.hpp"
#include "assistant_recipe_refusal.hpp"
#include "../../core/src/assistant_parameter_edits.hpp"
#include "edi/assistant_files.hpp"
#include "edi/assistant_limits.hpp"
#include "edi/selectors.hpp"
#include <cmath>
#include <algorithm>
#include <QJsonArray>
#include <QSet>
#include <stdexcept>
namespace edi_app {
namespace {
using Object = QJsonObject;
using Array = QJsonArray;
using Limits = edi::assistant::Limits;
Object shape(Object properties, Array required) {
    return {{"type", "object"}, {"properties", properties}, {"required", required}, {"additionalProperties", false}};
}
void exact(const Object& value, const QSet<QString>& keys, RecipeField field = RecipeField::Recipe) {
    if (value.size() != keys.size()) throw RecipeRefusal(field, RecipeReason::Fields);
    for (auto i = value.constBegin(); i != value.constEnd(); ++i) if (!keys.contains(i.key())) throw RecipeRefusal(field, RecipeReason::Fields);
}
std::string text(const Object& value, const char* key, quint64 limit, bool empty = false) {
    const auto field = value.value(key);
    if (!field.isString() || (!empty && field.toString().trimmed().isEmpty())) throw RecipeRefusal(recipe_field(key), RecipeReason::TextRequired);
    if (static_cast<quint64>(field.toString().size()) > limit) throw RecipeRefusal(recipe_field(key), RecipeReason::TextCapacity);
    const auto bytes = field.toString().toUtf8();
    if (static_cast<quint64>(bytes.size()) > limit) throw RecipeRefusal(recipe_field(key), RecipeReason::TextCapacity);
    if (bytes.contains('\0')) throw RecipeRefusal(recipe_field(key), RecipeReason::InvalidText);
    return bytes.toStdString();
}
double number(const Object& value, const char* key) {
    const auto field = value.value(key);
    if (!field.isDouble() || !std::isfinite(field.toDouble())) throw RecipeRefusal(recipe_field(key), RecipeReason::FiniteNumber);
    return field.toDouble();
}
Array array(const Object& value, const char* key, int minimum) {
    const auto field = value.value(key);
    if (!field.isArray()) throw RecipeRefusal(recipe_field(key), RecipeReason::ArrayRequired);
    if (field.toArray().size() < minimum) throw RecipeRefusal(recipe_field(key), RecipeReason::MinimumItems, minimum);
    if (field.toArray().size() > static_cast<qsizetype>(Limits::stream_items))
        throw RecipeRefusal(recipe_field(key), RecipeReason::MaximumItems, static_cast<int>(Limits::stream_items));
    return field.toArray();
}
}
QJsonObject native_cwl_recipe_schema() {
    const Object shortText{{"type", "string"}, {"minLength", 1}, {"maxLength", static_cast<int>(Limits::id_bytes)}};
    const Object num{{"type", "number"}};
    Array profiles;
    for (const auto& token : edi::supported_peak_profiles(edi::BeamModeEnum::CONSTANT_WAVELENGTH))
        profiles.append(QString::fromStdString(token));
    Object profile = shortText;
    profile["enum"] = profiles;
    profile["description"] = "Use one exact supported CW profile token from this enum, not a prose label or guessed spelling";

    const auto pairs = [&](const char* first, const char* second, int minimum) {
        return Object{{"type", "array"}, {"minItems", minimum}, {"maxItems", static_cast<int>(Limits::stream_items)},
            {"items", shape({{first, num}, {second, num}}, {first, second})}};
    };
    return shape({{"project_name", shortText}, {"description", Object{{"type", "string"}, {"maxLength", static_cast<int>(Limits::context_bytes)}}},
        {"experiment_name", shortText}, {"sample_form", Object{{"type", "string"}, {"enum", Array{"powder"}}}},
        {"beam_mode", Object{{"type", "string"}, {"enum", Array{"constant wavelength"}}}},
        {"radiation_probe", Object{{"type", "string"}, {"enum", Array{"neutron"}}}},
        {"scattering_type", Object{{"type", "string"}, {"enum", Array{"bragg"}}}},
        {"peak_profile", profile}, {"wavelength", num}, {"zero_offset", num}, {"phase_scale", num},
        {"background", pairs("position", "intensity", 2)}, {"exclusions", pairs("first", "second", 0)},
        {"initial_parameters", Object{{"type", "array"}, {"minItems", 0}, {"maxItems", static_cast<int>(Limits::stream_items)},
            {"items", shape({{"path", shortText}, {"value", num}}, {"path", "value"})}}}},
        {"project_name", "description", "experiment_name", "sample_form", "beam_mode", "radiation_probe", "scattering_type",
            "peak_profile", "wavelength", "zero_offset", "phase_scale", "background", "exclusions", "initial_parameters"});
}
NativeCwlRecipe parse_native_cwl_recipe(const Object& recipe) {
    exact(recipe, {"project_name", "description", "experiment_name", "sample_form", "beam_mode", "radiation_probe", "scattering_type",
        "peak_profile", "wavelength", "zero_offset", "phase_scale", "background", "exclusions", "initial_parameters"});
    NativeCwlRecipe result;
    result.project_name = text(recipe, "project_name", Limits::id_bytes);
    result.description = text(recipe, "description", Limits::context_bytes, true);
    result.experiment_name = text(recipe, "experiment_name", Limits::id_bytes);
    result.type.sample_form = text(recipe, "sample_form", Limits::id_bytes);
    result.type.beam_mode = text(recipe, "beam_mode", Limits::id_bytes);
    result.type.radiation_probe = text(recipe, "radiation_probe", Limits::id_bytes);
    result.type.scattering_type = text(recipe, "scattering_type", Limits::id_bytes);
    result.peak_profile = text(recipe, "peak_profile", Limits::id_bytes);
    const auto profiles = edi::supported_peak_profiles(edi::BeamModeEnum::CONSTANT_WAVELENGTH);
    if (std::find(profiles.begin(), profiles.end(), result.peak_profile) == profiles.end())
        throw RecipeRefusal(RecipeField::PeakProfile, RecipeReason::SupportedProfile);

    result.wavelength = number(recipe, "wavelength"); result.zero_offset = number(recipe, "zero_offset"); result.phase_scale = number(recipe, "phase_scale");
    for (const auto& entry : array(recipe, "background", 2)) {
        if (!entry.isObject()) throw RecipeRefusal(RecipeField::Background, RecipeReason::ObjectRequired);
        const auto row = entry.toObject(); exact(row, {"position", "intensity"}, RecipeField::Background);
        result.background.emplace_back(number(row, "position"), number(row, "intensity"));
    }
    for (const auto& entry : array(recipe, "exclusions", 0)) {
        if (!entry.isObject()) throw RecipeRefusal(RecipeField::Exclusions, RecipeReason::ObjectRequired);
        const auto row = entry.toObject(); exact(row, {"first", "second"}, RecipeField::Exclusions);
        result.exclusions.emplace_back(number(row, "first"), number(row, "second"));
    }
    for (const auto& entry : array(recipe, "initial_parameters", 0)) {
        if (!entry.isObject()) throw RecipeRefusal(RecipeField::InitialParameters, RecipeReason::ObjectRequired);
        const auto row = entry.toObject(); exact(row, {"path", "value"}, RecipeField::InitialParameters);
        result.initial_parameters.emplace_back(text(row, "path", Limits::id_bytes), number(row, "value"));
    }
    return result;
}
NativeCwlCandidate prepare_native_cwl_project(const std::string& cif, const std::string& data,
                                             const NativeCwlRecipe& recipe) {
    using Limits = edi::assistant::Limits;
    if (cif.empty() || cif.size() > edi::assistant::SelectedFileLimits::file_bytes ||
        recipe.project_name.size() > Limits::id_bytes || recipe.experiment_name.size() > Limits::id_bytes ||
        recipe.description.size() > Limits::context_bytes || recipe.peak_profile.size() > Limits::id_bytes ||
        recipe.background.size() > Limits::stream_items || recipe.exclusions.size() > Limits::stream_items ||
        recipe.initial_parameters.size() > Limits::stream_items)
        throw std::length_error("Native creation inputs exceed their existing limits");
    if (recipe.type.sample_form != "powder" || recipe.type.beam_mode != "constant wavelength" ||
        recipe.type.radiation_probe != "neutron" || recipe.type.scattering_type != "bragg")
        throw edi::IoError("This native creation slice supports an explicit powder/CW/neutron/Bragg recipe only");
    if (!std::isfinite(recipe.wavelength) || recipe.wavelength <= 0 || !std::isfinite(recipe.zero_offset) ||
        !std::isfinite(recipe.phase_scale) || recipe.phase_scale <= 0 || recipe.background.size() < 2)
        throw edi::IoError("Supply actual wavelength, zero, positive phase scale and line-segment background anchors");
    NativeCwlCandidate candidate;
    candidate.project = edi::empty_project(recipe.project_name, recipe.description);
    // Existing classic-CIF/dot vocabulary reader owns space group/site/ADP and
    // optional-Wyckoff normalization. No new crystallographic parser or matcher.
    auto structure = edi::structure_from_edi_text(cif);
    const auto phase = structure.name.value();
    edi::Edit::add_structure(candidate.project, std::move(structure))();
    auto experiment = edi::simulation_experiment(recipe.experiment_name, recipe.type, phase);
    edi::select_peak_profile(experiment, recipe.peak_profile);
    if (!experiment.instrument.setup_wavelength || !experiment.instrument.calib_twotheta_offset)
        throw edi::IoError("The explicit recipe did not create the required CW instrument slots");
    edi::assign_value(*experiment.instrument.setup_wavelength, recipe.wavelength);
    edi::assign_value(*experiment.instrument.calib_twotheta_offset, recipe.zero_offset);
    if (experiment.linked_structures.size() != 1) throw edi::IoError("The recipe does not identify exactly one phase");
    edi::assign_value(experiment.linked_structures[0]->scale, recipe.phase_scale);
    edi::select_background_type(experiment, "line-segment");
    experiment.background.clear();
    double previous = -INFINITY;
    for (const auto& [position, intensity] : recipe.background) {
        if (!std::isfinite(position) || !std::isfinite(intensity) || position <= previous)
            throw edi::IoError("Background anchors must have finite, strictly increasing positions");
        edi::LineSegment point; point.position = position;
        point.id = background_append_input(experiment).id;
        edi::assign_value(point.intensity, intensity); experiment.background.push_back(std::make_shared<edi::LineSegment>(point));
        previous = position;
    }
    experiment.excluded_regions.clear();
    for (const auto& [first, second] : recipe.exclusions) {
        if (!std::isfinite(first) || !std::isfinite(second) || first > second)
            throw edi::IoError("Exclusion limits must be finite ordered pairs");
        edi::ExcludedRegion region(first, second); region.id = std::to_string(experiment.excluded_regions.size() + 1);
        experiment.excluded_regions.push_back(std::make_shared<edi::ExcludedRegion>(region));
    }
    // The one native plain-data reader owns filtering, sorting, sigma and range.
    // Its actual diagnostics accompany the candidate; no observations/weights
    // are invented or adjusted to improve a fit.
    auto measured = edi::experiment_with_plain_data(experiment, data, false);
    candidate.points = measured.points; candidate.skipped = measured.skipped;
    candidate.nonpositive = measured.nonpositive; candidate.duplicates = measured.duplicates;
    candidate.reordered = measured.reordered; candidate.derived_sigma = measured.derived;
    edi::Edit::create_experiment(candidate.project, std::move(measured.experiment))();
    if (!recipe.initial_parameters.empty())
        edi::assistant::detail::prepare_parameter_edit(candidate.project, recipe.initial_parameters)();
    // Match the original visible AutoIDs action AFTER values that name the
    // ordinary Add IDs. The normal candidate remains one atomic transaction.
    auto& background_owner=*candidate.project.experiments[0];
    auto ids=edi::position_point_ids(background_owner);
    for(const auto& id:ids)if(id.size()>Limits::id_bytes)
        throw std::length_error("Position-derived IDs exceed their original admitted capacity");
    edi::Edit::background_point_ids(background_owner,std::move(ids))();
    edi::complete_relations(candidate.project);
    return candidate;
}
} // namespace edi_app
