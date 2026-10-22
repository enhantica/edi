// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <array>
#include <stdexcept>
#include <string_view>
namespace edi_app {
// Canonical mapped-schema description shared by offered schema/refusal (ADR-0041).
inline constexpr std::string_view mapped_structure_guidance = "Use the offered create_cwl_project mapped_structure schema as authority, not staged skill files or workspace searches. Required root keys: name, space_group, cell, atom_sites, atom_site_adps. space_group requires name_h_m and coord_system_code. cell requires length_a, length_b, length_c, angle_alpha, angle_beta, angle_gamma. Every atom_sites row requires id, type_symbol, wyckoff_letter, fract_x, fract_y, fract_z, occupancy. Every atom_site_adps row requires id and adp_type: Biso/Uiso requires adp_iso; Bani/Uani/beta requires adp_11, adp_22, adp_33, adp_12, adp_13, adp_23. Both arrays must be nonempty, with unique matching IDs and one ADP row per site. Include every required key even where the schema permits an empty string. Obtain scientific values from admitted source/current evidence; never guess Wyckoff letters. No extra keys or substitute spellings are admitted. A mapped_structure refusal is not setup completion: inspect current state and correct the complete shape only within unchanged input/owner authority after a proved prewrite refusal; never replay partial/uncertain work or generate a CIF.";
static_assert([] {
    for(unsigned char c:mapped_structure_guidance)
        if(c<0x20 || c>0x7e || c=='"' || c=='\\')return false;
    return true;
}());
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
