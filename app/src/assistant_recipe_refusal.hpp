// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <array>
#include <stdexcept>
#include <string_view>
namespace edi_app {
// Closed app-owned recipe identifiers, never provider text or exception what().
enum class RecipeField { Recipe, ProjectName, Description, ExperimentName, SampleForm,
    BeamMode, RadiationProbe, ScatteringType, PeakProfile, Wavelength, ZeroOffset,
    PhaseScale, Background, Exclusions, InitialParameters, Position, Intensity,
    First, Second, Path, Value, MappedStructure };
enum class RecipeReason { Fields, TextRequired, TextCapacity, InvalidText, FiniteNumber,
    ArrayRequired, MinimumItems, MaximumItems, ObjectRequired, SupportedProfile, DependentTarget };
inline constexpr std::array<const char*,22> recipe_fields{{"recipe","project_name","description",
    "experiment_name","sample_form","beam_mode","radiation_probe","scattering_type",
    "peak_profile","wavelength","zero_offset","phase_scale","background","exclusions",
    "initial_parameters","position","intensity","first","second","path","value","mapped_structure"}};
inline constexpr std::array<const char*,11> recipe_reasons{{"missing_or_unsupported_fields",
    "nonempty_text_required","text_capacity","invalid_text","finite_number_required",
    "array_required","minimum_items","maximum_items","object_required","supported_profile_required","dependent_target_mismatch"}};
inline RecipeField recipe_field(std::string_view key) {
    for(std::size_t i=0;i<recipe_fields.size();++i)if(key==recipe_fields[i])return static_cast<RecipeField>(i);
    throw std::logic_error("Native recipe field mapping is unavailable");
}
class RecipeRefusal final : public std::invalid_argument {
public:
    RecipeRefusal(RecipeField field,RecipeReason reason,int bound=0)
        : std::invalid_argument("The native creation recipe is invalid"),field_(field),reason_(reason),bound_(bound) {}
    RecipeField field() const noexcept { return field_; }
    RecipeReason reason() const noexcept { return reason_; }
    int bound() const noexcept { return bound_; }
private:
    RecipeField field_;
    RecipeReason reason_;
    int bound_;
};
} // namespace edi_app
