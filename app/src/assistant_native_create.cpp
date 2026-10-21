// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_native_create.hpp"
#include "background_input.hpp"
#include "assistant_recipe_refusal.hpp"
#include "../../core/src/assistant_parameter_edits.hpp"
#include "edi/assistant_files.hpp"
#include "edi/assistant_limits.hpp"
#include "edi/selectors.hpp"
#include "edi/symmetry.hpp"
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
QJsonObject native_cwl_recipe_schema(bool include_profiles) {
    const Object shortText{{"type", "string"}, {"minLength", 1}, {"maxLength", static_cast<int>(Limits::id_bytes)}};
    const Object num{{"type", "number"}};
    Array profiles;
    if(include_profiles)edi::visit_supported_peak_profiles(edi::BeamModeEnum::CONSTANT_WAVELENGTH,
        [&](const std::string& token){profiles.append(QString::fromStdString(token));});
    Object profile = shortText;
    profile["enum"] = profiles;
    profile["description"] = "Use one exact supported CW profile token from this enum, not a prose label or guessed spelling";

    const auto pairs = [&](const char* first, const char* second, int minimum) {
        return Object{{"type", "array"}, {"minItems", minimum}, {"maxItems", static_cast<int>(Limits::stream_items)},
            {"items", shape({{first, num}, {second, num}}, {first, second})}};
    };
    auto background = pairs("position", "intensity", 2);
    background["description"] = "Direct array of exact position/intensity rows; no anchors wrapper. Setup intensities start fixed implicitly. Retain desired source refinement flags separately for authorized grouped Analysis after setup.";
    auto background_point = background.value("items").toObject();
    background_point["description"] = "Exactly position and intensity numbers. No free, id, uncertainty or other keys; standalone edit_background has a separate explicit free field.";
    background["items"] = background_point;
    return shape({{"project_name", shortText}, {"description", Object{{"type", "string"}, {"maxLength", static_cast<int>(Limits::context_bytes)}}},
        {"experiment_name", shortText}, {"sample_form", Object{{"type", "string"}, {"enum", Array{"powder"}}}},
        {"beam_mode", Object{{"type", "string"}, {"enum", Array{"constant wavelength"}}}},
        {"radiation_probe", Object{{"type", "string"}, {"enum", Array{"neutron"}}}},
        {"scattering_type", Object{{"type", "string"}, {"enum", Array{"bragg"}}}},
        {"peak_profile", profile}, {"wavelength", num}, {"zero_offset", num}, {"phase_scale", num},
        {"background", background}, {"exclusions", pairs("first", "second", 0)},
        {"initial_parameters", Object{{"type", "array"}, {"minItems", 0}, {"maxItems", static_cast<int>(Limits::stream_items)},
            {"items", shape({{"path", shortText}, {"value", num}}, {"path", "value"})}}}},
        {"project_name", "description", "experiment_name", "sample_form", "beam_mode", "radiation_probe", "scattering_type",
            "peak_profile", "wavelength", "zero_offset", "phase_scale", "background", "exclusions", "initial_parameters"});
}
QJsonObject native_mapped_structure_schema() {
    const Object token{{"type","string"},{"minLength",1},{"maxLength",static_cast<int>(Limits::id_bytes)}};
    const Object optional{{"type","string"},{"maxLength",static_cast<int>(Limits::id_bytes)}};
    const Object num{{"type","number"}};
    const auto rows=[](Object item) {return Object{{"type","array"},{"minItems",1},
        {"maxItems",static_cast<int>(Limits::stream_items)},{"items",item}};};
    const auto iso=shape({{"id",token},{"adp_type",Object{{"enum",Array{"Biso","Uiso"}}}},{"adp_iso",num}},
        {"id","adp_type","adp_iso"});
    const auto aniso=shape({{"id",token},{"adp_type",Object{{"enum",Array{"Bani","Uani","beta"}}}},
        {"adp_11",num},{"adp_22",num},{"adp_33",num},{"adp_12",num},{"adp_13",num},{"adp_23",num}},
        {"id","adp_type","adp_11","adp_22","adp_33","adp_12","adp_13","adp_23"});
    auto schema = shape({{"name",token},{"space_group",shape({{"name_h_m",token},{"coord_system_code",optional}},
        {"name_h_m","coord_system_code"})},
        {"cell",shape({{"length_a",num},{"length_b",num},{"length_c",num},{"angle_alpha",num},
            {"angle_beta",num},{"angle_gamma",num}},
            {"length_a","length_b","length_c","angle_alpha","angle_beta","angle_gamma"})},
        {"atom_sites",rows(shape({{"id",token},{"type_symbol",token},{"wyckoff_letter",optional},
            {"fract_x",num},{"fract_y",num},{"fract_z",num},{"occupancy",num}},
            {"id","type_symbol","wyckoff_letter","fract_x","fract_y","fract_z","occupancy"}))},
        {"atom_site_adps",rows(Object{{"oneOf",Array{iso,aniso}}})}},
        {"name","space_group","cell","atom_sites","atom_site_adps"});
    schema["description"] = "Complete closed target in this exact schema: space_group uses name_h_m and coord_system_code; cell uses length_a/length_b/length_c and angle_alpha/angle_beta/angle_gamma; atom_sites and atom_site_adps use matching id, and isotropic ADPs use adp_type with adp_iso. Do not substitute name_hm/setting, a/b/c, label or b_iso. A mapped_structure refusal does not establish setup completion; inspect current state and correct the schema before a fresh call. No permissive aliases or generated CIF are needed.";
    return schema;
}
namespace {
// The complete typed input adapter owns no live app object or copied default
// factory. Original constructors attach every Parameter spec and ItemVec owns
// the actual memberships. Expected dependent values are checked after final
// overrides/relations below, never forced through a dependent setter.
edi::Structure mapped_structure(const Object& source) {
    constexpr auto field=RecipeField::MappedStructure;
    exact(source,{"name","space_group","cell","atom_sites","atom_site_adps"},field);
    const auto token=[&](const Object& object,const char* key,bool empty=false) {
        const auto value=object.value(key);
        if(!value.isString())throw RecipeRefusal(field,RecipeReason::TextRequired);
        const auto input=value.toString();
        if((!empty && input.trimmed().isEmpty()) || std::any_of(input.cbegin(),input.cend(),[](QChar c){return c.unicode()<32 || c.unicode()==127;}))throw RecipeRefusal(field,RecipeReason::InvalidText);
        if(input.size()>static_cast<qsizetype>(Limits::id_bytes))throw RecipeRefusal(field,RecipeReason::TextCapacity);
        const auto bytes=input.toUtf8();
        if(bytes.size()>static_cast<qsizetype>(Limits::id_bytes) || QString::fromUtf8(bytes)!=input)
            throw RecipeRefusal(field,RecipeReason::InvalidText);
        return bytes.toStdString();
    };
    const auto object=[&](const Object& parent,const char* key) {
        if(!parent.value(key).isObject())throw RecipeRefusal(field,RecipeReason::ObjectRequired);
        return parent.value(key).toObject();
    };
    const auto finite=[&](const Object& parent,const char* key) {
        const auto value=parent.value(key);
        if(!value.isDouble() || !std::isfinite(value.toDouble()))throw RecipeRefusal(field,RecipeReason::FiniteNumber);
        return value.toDouble();
    };
    const auto list=[&](const char* key) {
        const auto value=source.value(key);
        if(!value.isArray())throw RecipeRefusal(field,RecipeReason::ArrayRequired);
        const auto rows=value.toArray();
        if(rows.isEmpty())throw RecipeRefusal(field,RecipeReason::MinimumItems,1);
        if(rows.size()>static_cast<qsizetype>(Limits::stream_items))throw RecipeRefusal(field,RecipeReason::MaximumItems,static_cast<int>(Limits::stream_items));
        return rows;
    };
    edi::Structure result;result.name=token(source,"name");
    if(!edi::persistable_name(result.name.value()))throw RecipeRefusal(field,RecipeReason::InvalidText);
    const auto group=object(source,"space_group");exact(group,{"name_h_m","coord_system_code"},field);
    const auto hm=token(group,"name_h_m"), code=token(group,"coord_system_code",true);
    auto setting=edi::space_group_setting_for_name(hm);
    if(!setting)throw RecipeRefusal(field,RecipeReason::InvalidText);
    if(!code.empty())setting=edi::space_group_setting_for_code(setting->it_number,code);
    if(!setting || !edi::same_space_group_name(hm,setting->name_h_m))throw RecipeRefusal(field,RecipeReason::InvalidText);
    edi::Edit::space_group_setting(result.space_group,*setting,false)();
    const auto cell=object(source,"cell");exact(cell,{"length_a","length_b","length_c","angle_alpha","angle_beta","angle_gamma"},field);
    const char* cell_keys[]={"length_a","length_b","length_c","angle_alpha","angle_beta","angle_gamma"};
    auto cell_values=result.cell.parameters();
    for(std::size_t i=0;i<cell_values.size();++i)edi::assign_value(*cell_values[i],finite(cell,cell_keys[i]));
    const auto sites=list("atom_sites"), adps=list("atom_site_adps");
    if(sites.size()!=adps.size())throw RecipeRefusal(field,RecipeReason::Fields);
    for(const auto& value:sites) {
        if(!value.isObject())throw RecipeRefusal(field,RecipeReason::ObjectRequired);
        const auto row=value.toObject();exact(row,{"id","type_symbol","wyckoff_letter","fract_x","fract_y","fract_z","occupancy"},field);
        auto site=std::make_shared<edi::AtomSite>();site->id=token(row,"id");site->type_symbol=token(row,"type_symbol");site->wyckoff_letter=token(row,"wyckoff_letter",true);
        const char* keys[]={"fract_x","fract_y","fract_z","occupancy"};auto parameters=site->parameters();
        for(std::size_t i=0;i<4;++i)edi::assign_value(*parameters[i],finite(row,keys[i]));
        result.atom_sites.push_back(std::move(site)); // original ItemVec rejects duplicate keys
    }
    for(qsizetype index=0;index<adps.size();++index) {
        const auto value=adps.at(index);
        if(!value.isObject())throw RecipeRefusal(field,RecipeReason::ObjectRequired);
        const auto row=value.toObject();const auto id=token(row,"id"),type=token(row,"adp_type");
        if(!edi::is_adp_type(type))throw RecipeRefusal(field,RecipeReason::Fields);
        for(qsizetype before=0;before<index;++before)if(adps.at(before).toObject().value("id")==row.value("id"))
            throw RecipeRefusal(field,RecipeReason::Fields);
        edi::AtomSite* site=nullptr;for(const auto& candidate:result.atom_sites)if(candidate->id.value()==id)site=candidate.get();
        if(!site)throw RecipeRefusal(field,RecipeReason::Fields);
        if(!edi::is_anisotropic_adp_type(type)) {
            exact(row,{"id","adp_type","adp_iso"},field);
            edi::Edit::adp_type(result,*site,type)();edi::assign_value(site->adp_iso,finite(row,"adp_iso"));
        } else {
            exact(row,{"id","adp_type","adp_11","adp_22","adp_33","adp_12","adp_13","adp_23"},field);
            edi::Edit::adp_type(result,*site,type)();
            edi::AtomSiteAniso* tensor=nullptr;for(const auto& candidate:result.atom_site_aniso)if(candidate->id.value()==id)tensor=candidate.get();
            if(!tensor)throw RecipeRefusal(field,RecipeReason::Fields);
            const char* keys[]={"adp_11","adp_22","adp_33","adp_12","adp_13","adp_23"};auto parameters=tensor->parameters();
            for(std::size_t i=0;i<parameters.size();++i)edi::assign_value(*parameters[i],finite(row,keys[i]));
        }
    }
    return result;
}
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
    bool offered=false;
    edi::visit_supported_peak_profiles(edi::BeamModeEnum::CONSTANT_WAVELENGTH,
        [&](const std::string& token){offered=offered || token==result.peak_profile;});
    if (!offered)
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
                                             const NativeCwlRecipe& recipe, const Object& mapped) {
    using Limits = edi::assistant::Limits;
    if ((cif.empty() && mapped.isEmpty()) || (!cif.empty() && !mapped.isEmpty()) || cif.size() > edi::assistant::SelectedFileLimits::file_bytes ||
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
    auto structure = mapped.isEmpty() ? edi::structure_from_edi_text(cif) : mapped_structure(mapped);
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
    if(!mapped.isEmpty()) {
        const auto check=[](const edi::Parameter& parameter,double requested) {
            if(parameter.dependence!=edi::Dependence::Independent && parameter.value.get()!=requested)
                throw RecipeRefusal(RecipeField::MappedStructure,RecipeReason::DependentTarget);
        };
        auto& target=*candidate.project.structures[0];
        const auto cell=mapped.value("cell").toObject();const char* cell_keys[]={"length_a","length_b","length_c","angle_alpha","angle_beta","angle_gamma"};
        const auto cell_fields=target.cell.parameters();
        for(std::size_t i=0;i<cell_fields.size();++i)check(*cell_fields[i],cell.value(cell_keys[i]).toDouble());
        const auto sites=mapped.value("atom_sites").toArray();
        for(qsizetype i=0;i<sites.size();++i) {
            const auto row=sites.at(i).toObject();auto& site=*target.atom_sites[static_cast<std::size_t>(i)];
            const char* keys[]={"fract_x","fract_y","fract_z","occupancy"};const auto fields=site.parameters();
            for(std::size_t j=0;j<4;++j)check(*fields[j],row.value(keys[j]).toDouble());
        }
        for(const auto& value:mapped.value("atom_site_adps").toArray()) {
            const auto row=value.toObject();const auto id=row.value("id").toString().toStdString();
            if(!edi::is_anisotropic_adp_type(row.value("adp_type").toString().toStdString())) {
                for(const auto& site:target.atom_sites)if(site->id.value()==id)check(site->adp_iso,row.value("adp_iso").toDouble());
            } else for(const auto& tensor:target.atom_site_aniso)if(tensor->id.value()==id) {
                const char* keys[]={"adp_11","adp_22","adp_33","adp_12","adp_13","adp_23"};const auto fields=tensor->parameters();
                for(std::size_t j=0;j<fields.size();++j)check(*fields[j],row.value(keys[j]).toDouble());
            }
        }
    }
    return candidate;
}
} // namespace edi_app
