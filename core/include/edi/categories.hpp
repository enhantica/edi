// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_CATEGORIES_HPP
#define EDI_CATEGORIES_HPP

// The `.edi` categories a block shows, in page order, and the fields each shows. Presence follows
// the block's type (diffraction-lib's category Compatibility, with edi's declared divergences
// D-a…D-k) or what the block carries; the shown fields come from the per-profile table below — never
// from the model's storage walks, which also hold the inert coefficients of the other beam mode (a
// CW experiment stores the fourteen TOF peak terms). A field outside its profile's set is hidden
// while fixed and shown, marked, while free (I15). A field symmetry fixes or ties to another is
// shown and marked not refinable (edi ADR-0019): a page shows it disabled, with its implied value.
// So is a field a declared constraint sets (ADR-0024), from the dependence crysta marks it with.

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <map>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "edi/model.hpp"
#include "edi/symmetry.hpp"

namespace edi {

struct CategoryField {
    std::string name;                // the `.edi` item name, e.g. "broad_gauss_u"
    Parameter* parameter = nullptr;  // the model field
    bool used_by_profile = true;     // false: outside the profile's set, shown because it is free
    bool refinable = true;           // false: symmetry fixes it or ties it to another parameter
};

struct Category {
    std::string id;                          // the `.edi` tag prefix, e.g. "peak"
    bool is_loop = false;
    std::size_t rows = 0;                    // loop rows (0 for a scalar category)
    std::vector<CategoryField> fields;       // parameter fields in `.edi` order
    std::vector<CategoryField> asymmetry;    // peak only: the `_peak.asym_*` subheading
    bool admitted = true;                    // false: shown only because the block carries it
};

namespace detail {

// A field crysta marks dependent (symmetry or a declared constraint, ADR-0024) is not refinable,
// whichever category shows it.
inline void mark_dependents(std::vector<Category>& categories) {
    for (Category& category : categories) {
        for (std::vector<CategoryField>* fields : {&category.fields, &category.asymmetry}) {
            for (CategoryField& field : *fields) {
                if (field.parameter != nullptr && field.parameter->dependence != Dependence::Independent) {
                    field.refinable = false;
                }
            }
        }
    }
}

// The TOF peak coefficients in the crysta writer's `.edi` order, and their storage.
inline std::vector<std::pair<const char*, Parameter PeakBase::*>> tof_peak_fields() {
    return {{"rise_alpha_0", &PeakBase::rise_alpha_0},
            {"rise_alpha_1", &PeakBase::rise_alpha_1},
            {"decay_beta_0", &PeakBase::decay_beta_0},
            {"decay_beta_1", &PeakBase::decay_beta_1},
            {"broad_gauss_sigma_0", &PeakBase::broad_gauss_sigma_0},
            {"broad_gauss_sigma_1", &PeakBase::broad_gauss_sigma_1},
            {"broad_gauss_sigma_2", &PeakBase::broad_gauss_sigma_2},
            {"broad_gauss_size", &PeakBase::broad_gauss_size},
            {"broad_gauss_strain", &PeakBase::broad_gauss_strain},
            {"broad_lorentz_gamma_0", &PeakBase::broad_lorentz_gamma_0},
            {"broad_lorentz_gamma_1", &PeakBase::broad_lorentz_gamma_1},
            {"broad_lorentz_gamma_2", &PeakBase::broad_lorentz_gamma_2},
            {"broad_lorentz_size", &PeakBase::broad_lorentz_size},
            {"broad_lorentz_strain", &PeakBase::broad_lorentz_strain}};
}

// Which TOF coefficients each profile declares (diffraction-lib 0ffba46f peak/tof.py: Jorgensen =
// Gaussian + back-to-back; Jorgensen-Von Dreele adds the Lorentzian; pseudo-Voigt = Gaussian +
// Lorentzian, no back-to-back).
inline bool tof_profile_declares(const std::string& profile, const std::string& field) {
    const bool back_to_back = field.rfind("rise_alpha", 0) == 0 || field.rfind("decay_beta", 0) == 0;
    const bool lorentzian = field.rfind("broad_lorentz", 0) == 0;
    if (profile == "tof-jorgensen") {
        return !lorentzian;
    }
    if (profile == "tof-pseudo-voigt") {
        return !back_to_back;
    }
    return true;  // tof-jorgensen-von-dreele and registered extensions: every coefficient
}

inline void add_optional(std::vector<CategoryField>& fields, const char* name,
                         OptionalParameter& field) {
    if (field.has_value()) {
        fields.push_back({name, &*field, true});
    }
}

// `carried`: listed whether shown or not, a value the experiment carries (the Analysis table's inventory, edi
// ADR-0053).
inline void add_if_shown(std::vector<CategoryField>& fields, const char* name, Parameter& field,
                         bool declared, bool carried = false) {
    if (declared || field.free || carried) {
        fields.push_back({name, &field, declared});
    }
}

}  // namespace detail

// The peak category's parameter fields and asymmetry subheading for the experiment's profile. With `every_carried`
// a time-of-flight experiment lists the coefficients its profile does not use too, as the Analysis table does
// (edi ADR-0053); the Experiment page shows those only while free.
inline Category peak_category(ExperimentBase& experiment, bool every_carried = false) {
    Category category{"peak"};
    PeakBase& peak = experiment.peak;
    const bool constant_wavelength = experiment.effective_beam_mode() == BeamModeEnum::CONSTANT_WAVELENGTH;
    const std::string profile = effective_peak_type(experiment);
    if (constant_wavelength) {
        detail::add_optional(category.fields, "broad_gauss_u", peak.broad_gauss_u);
        detail::add_optional(category.fields, "broad_gauss_v", peak.broad_gauss_v);
        detail::add_optional(category.fields, "broad_gauss_w", peak.broad_gauss_w);
        detail::add_optional(category.fields, "broad_lorentz_x", peak.broad_lorentz_x);
        detail::add_optional(category.fields, "broad_lorentz_y", peak.broad_lorentz_y);
        detail::add_optional(category.fields, "mixing_eta_0", peak.mixing_eta_0);
        detail::add_optional(category.fields, "mixing_eta_1", peak.mixing_eta_1);
        detail::add_optional(category.asymmetry, "asym_fcj_1", peak.asym_fcj_1);
        detail::add_optional(category.asymmetry, "asym_fcj_2", peak.asym_fcj_2);
        detail::add_optional(category.asymmetry, "asym_beba_a0", peak.asym_beba_a0);
        detail::add_optional(category.asymmetry, "asym_beba_b0", peak.asym_beba_b0);
        detail::add_optional(category.asymmetry, "asym_beba_a1", peak.asym_beba_a1);
        detail::add_optional(category.asymmetry, "asym_beba_b1", peak.asym_beba_b1);
        detail::add_optional(category.asymmetry, "asym_beba_limit", peak.asym_beba_limit);
        for (const auto& [name, member] : detail::tof_peak_fields()) {  // inert on CW: only if free
            detail::add_if_shown(category.fields, name, peak.*member, false);
        }
    } else {
        for (const auto& [name, member] : detail::tof_peak_fields()) {
            detail::add_if_shown(category.fields, name, peak.*member,
                                 detail::tof_profile_declares(profile, name), every_carried);
        }
    }
    return category;
}

// The instrument category: CW the wavelength, 2θ offset and the declared line shifts; TOF the bank angle
// and d→TOF terms.
inline Category instrument_category(ExperimentBase& experiment) {
    Category category{"instrument"};
    InstrumentBase& instrument = experiment.instrument;
    const bool constant_wavelength = experiment.effective_beam_mode() == BeamModeEnum::CONSTANT_WAVELENGTH;
    if (constant_wavelength) {
        detail::add_optional(category.fields, "setup_wavelength", instrument.setup_wavelength);
        detail::add_optional(category.fields, "calib_twotheta_offset", instrument.calib_twotheta_offset);
        // Line shifts, when declared (the row holds all four).
        detail::add_optional(category.fields, "calib_sample_displacement", instrument.calib_sample_displacement);
        detail::add_optional(category.fields, "calib_sample_transparency", instrument.calib_sample_transparency);
        // The X-ray monochromator polarization, when the experiment carries it.
        detail::add_optional(category.fields, "setup_polarization_coefficient",
                             instrument.setup_polarization_coefficient);
        detail::add_optional(category.fields, "setup_monochromator_twotheta",
                             instrument.setup_monochromator_twotheta);
        // The X-ray K-alpha doublet, when the experiment carries it.
        detail::add_optional(category.fields, "setup_wavelength_2", instrument.setup_wavelength_2);
        detail::add_optional(category.fields, "setup_wavelength_2_to_1_ratio",
                             instrument.setup_wavelength_2_to_1_ratio);
    }
    const std::pair<const char*, Parameter InstrumentBase::*> tof[] = {
        {"setup_twotheta_bank", &InstrumentBase::setup_twotheta_bank},
        {"calib_d_to_tof_offset", &InstrumentBase::calib_d_to_tof_offset},
        {"calib_d_to_tof_linear", &InstrumentBase::calib_d_to_tof_linear},
        {"calib_d_to_tof_quadratic", &InstrumentBase::calib_d_to_tof_quadratic},
        {"calib_d_to_tof_reciprocal", &InstrumentBase::calib_d_to_tof_reciprocal}};
    for (const auto& [name, member] : tof) {
        detail::add_if_shown(category.fields, name, instrument.*member, !constant_wavelength);
    }
    return category;
}

// The absorption category: the fields its family carries (the model engages exactly those).
inline Category absorption_category(ExperimentBase& experiment) {
    Category category{"absorption"};
    detail::add_optional(category.fields, "abscor1", experiment.absorption.abscor1);
    detail::add_optional(category.fields, "abscor2", experiment.absorption.abscor2);
    detail::add_optional(category.fields, "mu_r", experiment.absorption.mu_r);
    return category;
}

namespace detail {
// Whether a save writes an experiment's calculation, as crysta's writer decides it (writes_computed): its calculation
// current, with a value for every reflection of a single crystal and no infinite value anywhere. A powder whose
// calculation range is declared (`_data_range`) is written as that declaration, without the calculation.
inline bool writes_calculation(const ExperimentBase& experiment) {
    const auto infinite = [](const auto& column) {
        return std::any_of(column.begin(), column.end(), [](double value) { return std::isinf(value); });
    };
    if (experiment.reflections.has_value()) {
        const ReflnDataBase& reflections = *experiment.reflections;
        return !reflections.intensity_calc.empty() && reflections.intensity_calc.size() == reflections.size() &&
               experiment.computed_current() && !infinite(reflections.intensity_calc) &&
               !infinite(reflections.d_spacing) && !infinite(reflections.sin_theta_over_lambda);
    }
    if (!experiment.data.has_value() || experiment.data->intensity_calc.empty() || experiment.calculation_only ||
        !experiment.computed_current()) {
        return false;
    }
    const PdDataBase& data = *experiment.data;
    const PowderReflnDataBase& refln = experiment.refln;
    return !infinite(data.d_spacing) && !infinite(data.intensity_calc) && !infinite(data.intensity_bkg) &&
           !infinite(data.component_intensities_net) &&
           !infinite(data.component_intensities_magnetic) && !infinite(data.component_intensities_nuclear) && !infinite(data.residual) && !infinite(refln.d_spacing) &&
           !infinite(refln.sin_theta_over_lambda) && !infinite(refln.f_calc) && !infinite(refln.f_squared_calc) &&
           !infinite(refln.position);
}
}  // namespace detail

// An experiment's categories in page order (§2b (iii)); `every_carried` as for peak_category.
inline std::vector<Category> experiment_categories(ExperimentBase& experiment, bool every_carried = false) {
    const bool constant_wavelength = experiment.effective_beam_mode() == BeamModeEnum::CONSTANT_WAVELENGTH;
    std::vector<Category> categories;
    categories.push_back({"experiment_type"});
    if (experiment.reflections.has_value()) {
        // A single crystal: no profile, background, excluded regions or absorption; its extinction
        // instead.
        // Its wavelength at constant wavelength. At time of flight, which reads none, the category holds no
        // parameter: the app's Instrument group shows the reflections' wavelength band.
        categories.push_back(experiment.effective_beam_mode() == BeamModeEnum::CONSTANT_WAVELENGTH
                                 ? instrument_category(experiment)
                                 : Category{"instrument"});
        Category extinction{"extinction"};
        detail::add_optional(extinction.fields, "crystal_radius", experiment.extinction.crystal_radius);
        detail::add_optional(extinction.fields, "domain_radius", experiment.extinction.domain_radius);
        detail::add_optional(extinction.fields, "mosaic_spread", experiment.extinction.mosaic_spread);
        detail::add_optional(extinction.fields, "coefficient", experiment.extinction.coefficient);
        detail::add_optional(extinction.fields, "coefficient_11", experiment.extinction.coefficient_11);
        detail::add_optional(extinction.fields, "coefficient_22", experiment.extinction.coefficient_22);
        detail::add_optional(extinction.fields, "coefficient_33", experiment.extinction.coefficient_33);
        detail::add_optional(extinction.fields, "coefficient_12", experiment.extinction.coefficient_12);
        detail::add_optional(extinction.fields, "coefficient_13", experiment.extinction.coefficient_13);
        detail::add_optional(extinction.fields, "coefficient_23", experiment.extinction.coefficient_23);
        categories.push_back(extinction);
        Category linked{"linked_structure", true, experiment.linked_structures.size()};
        for (const auto& link : experiment.linked_structures) {
            linked.fields.push_back({"scale", &link->scale, true});
        }
        categories.push_back(linked);
        categories.push_back({"scattering_source"});
        categories.push_back({"refln", true, experiment.reflections->size()});
        detail::mark_dependents(categories);
        return categories;
    }
    if (experiment.data.has_value()) {  // D-h: the measured range, or the declared grid
        Category data{experiment.calculation_only ? "data_range" : "data"};
        data.rows = experiment.data->intensity_meas.size();
        categories.push_back(data);
    }
    categories.push_back(instrument_category(experiment));
    categories.push_back(peak_category(experiment, every_carried));
    // The declared model's rows — the line-segment points, or a polynomial or Chebyshev model's
    // terms.
    if (experiment.background_type == "line-segment") {
        Category background{"background", true, experiment.background.size()};
        for (std::size_t i = 0; i < experiment.background.size(); ++i) {
            background.fields.push_back({"intensity", &experiment.background[i]->intensity, true});
        }
        categories.push_back(background);
    } else {
        Category background{"background", true, experiment.background_terms.size()};
        for (std::size_t i = 0; i < experiment.background_terms.size(); ++i) {
            background.fields.push_back({"coef", &experiment.background_terms[i]->coef, true});
        }
        categories.push_back(background);
    }
    // One row per linked structure (phase), each with its scale.
    Category linked{"linked_structure", true, experiment.linked_structures.size()};
    for (const auto& link : experiment.linked_structures) {
        linked.fields.push_back({"scale", &link->scale, true});
    }
    categories.push_back(linked);
    categories.push_back({"excluded_region", true, experiment.excluded_regions.size()});
    categories.push_back(absorption_category(experiment));
    // D-b: admitted for constant wavelength only; a carried row is shown on any mode.
    if (constant_wavelength || !experiment.preferred_orientation.empty()) {
        Category texture{"preferred_orientation", true, experiment.preferred_orientation.size()};
        texture.admitted = constant_wavelength;
        for (const auto& row : experiment.preferred_orientation) {
            texture.fields.push_back({"march_r", &row->march_r, true});
            texture.fields.push_back({"march_random_fract", &row->march_random_fract, true});
        }
        categories.push_back(texture);
    }
    categories.push_back({"scattering_source"});
    // The file's reflections, read-only: the calculation's while a save writes it, else those the file carried.
    if (detail::writes_calculation(experiment)) {
        if (experiment.refln.size() > 0) {
            categories.push_back({"refln", true, experiment.refln.size()});
        }
    } else if (experiment.carried_reflections.has_value()) {
        categories.push_back({"refln", true, experiment.carried_reflections->rows.size()});
    }
    detail::mark_dependents(categories);
    return categories;
}

// A structure's categories in page order (§2b (ii)).
inline std::vector<Category> structure_categories(Structure& structure) {
    std::vector<Category> categories;
    categories.push_back({"space_group"});
    // The cell and the coordinates are refinable where the space group leaves them independent.
    std::map<const Parameter*, bool> independent;
    for (const ParameterTie& tie : structure_ties(structure)) {
        independent.emplace(tie.parameter, tie.kind == TieKind::Independent);
    }
    const auto refinable = [&independent](const Parameter* parameter) {
        const auto found = independent.find(parameter);
        return found == independent.end() || found->second;  // no tie row: not a symmetry quantity
    };
    Category cell{"cell"};
    const char* cell_names[] = {"length_a", "length_b", "length_c", "angle_alpha", "angle_beta", "angle_gamma"};
    const std::vector<Parameter*> cell_parameters = structure.cell.parameters();
    for (std::size_t i = 0; i < cell_parameters.size(); ++i) {
        cell.fields.push_back({cell_names[i], cell_parameters[i], true, refinable(cell_parameters[i])});
    }
    categories.push_back(cell);
    Category sites{"atom_site", true, structure.atom_sites.size()};
    for (const auto& site : structure.atom_sites) {
        const char* names[] = {"fract_x", "fract_y", "fract_z", "occupancy", "adp_iso"};
        const std::vector<Parameter*> parameters = site->parameters();
        for (std::size_t i = 0; i < parameters.size(); ++i) {
            sites.fields.push_back({names[i], parameters[i], true, refinable(parameters[i])});
        }
    }
    categories.push_back(sites);
    // The anisotropic sites' tensors, a loop of its own (diffraction-lib's atom_site_aniso): a
    // component symmetry ties to the others is not refinable.
    Category aniso{"atom_site_aniso", true, structure.atom_site_aniso.size()};
    for (const auto& tensor : structure.atom_site_aniso) {
        const char* names[] = {"adp_11", "adp_22", "adp_33", "adp_12", "adp_13", "adp_23"};
        const std::vector<Parameter*> parameters = tensor->parameters();
        for (std::size_t i = 0; i < parameters.size(); ++i) {
            aniso.fields.push_back({names[i], parameters[i], true, refinable(parameters[i])});
        }
    }
    categories.push_back(aniso);
    categories.push_back({"scattering_length", true, structure.scattering_lengths_fm.size()});
    // The magnetic description (edi ADR-0070), for a structure that has one: crysta reads and
    // writes it, so each category shows its rows as the file holds them.
    const MagneticDescription& magnetic = structure.magnetic;
    if (!magnetic.empty() || !structure.atom_site_moment.empty()) {
        categories.push_back({"space_group_magn"});
        categories.push_back({"parent_space_group"});
        categories.push_back({"parent_propagation_vector", true, magnetic.propagation_vectors.size()});
        categories.push_back({"space_group_symop_magn_operation", true, magnetic.operations.size()});
        if (!magnetic.centerings.empty()) {
            categories.push_back({"space_group_symop_magn_centering", true, magnetic.centerings.size()});
        }
        Category moments{"atom_site_moment", true, structure.atom_site_moment.size()};
        for (const auto& moment : structure.atom_site_moment) {
            const char* names[] = {"crystalaxis_x", "crystalaxis_y", "crystalaxis_z"};
            const std::vector<Parameter*> parameters = moment->parameters();
            for (std::size_t i = 0; i < parameters.size(); ++i) {
                moments.fields.push_back({names[i], parameters[i], true, refinable(parameters[i])});
            }
        }
        categories.push_back(moments);
        Category form_factors{"magnetic_form_factor", true, structure.magnetic_form_factors.size()};
        for (const auto& row : structure.magnetic_form_factors) {
            const char* names[] = {"j2_coefficient", "j4_coefficient", "j6_coefficient"};
            const std::vector<Parameter*> parameters = row->parameters();
            for (std::size_t i = 0; i < parameters.size(); ++i) {
                form_factors.fields.push_back({names[i], parameters[i], true, refinable(parameters[i])});
            }
        }
        categories.push_back(form_factors);
    }
    detail::mark_dependents(categories);
    return categories;
}

// One `_fit_parameter` row: a parameter's persisted pre-fit start state, by the loop's
// `.edi` id, in the writer's order. Defined beside the writer's own slot walk (io.cpp).
struct FitStartRow {
    std::string id;
    const Parameter* parameter = nullptr;
};
std::vector<FitStartRow> fit_start_rows(const Project& project);

// A refinable parameter by its diffraction-lib unique name (`<datablock>.<category>[.<entry>].<name>`,
// the `_alias.parameter_unique_name` spelling), in the slot walk's order: the parameters a new alias
// can name. A dependent is left out, since its relation sets it. Defined beside the walk (io.cpp).
struct NamedParameter {
    std::string unique_name;
    const Parameter* parameter = nullptr;
};
std::vector<NamedParameter> named_parameters(const Project& project);
// One exact member, formatted only by the FIRST writer slot walk. Callers own
// this preparation bound through the lookup and output ownership transfer.
std::size_t named_parameter_preparation_bytes(std::size_t maximum_name_bytes);
std::optional<std::string> named_parameter(const Project& project,const Parameter* member,std::size_t maximum_name_bytes);

// The dependents (each parameter a relation sets), by unique name, in the slot walk's order.
std::vector<NamedParameter> named_dependents(const Project& project);

// The same walk over a project being written: each refinable parameter by its unique name.
struct NamedSlot {
    std::string unique_name;
    Parameter* parameter = nullptr;
};
std::vector<NamedSlot> named_slots(Project& project);

// The analysis categories shown (D-i): the minimizer and the fitting mode always; the scan declaration
// in a scan mode. Every loop the block writes is shown as its own category ("loop in .edi — table in
// gui"): the aliases and the constraints always (the first of each is added from its table), the joint
// weights in joint mode only, as they are written (the owner, 2026-10-11), the scan extraction rules and
// the fit start state when there are any.
inline std::vector<Category> analysis_categories(const Project& project) {
    std::vector<Category> categories{{"minimizer"}, {"fitting_mode"}};
    // A single crystal's fit cutoff (edi ADR-0050).
    if (std::any_of(project.experiments.begin(), project.experiments.end(),
                    [](const auto& experiment) { return experiment->reflections.has_value(); })) {
        categories.push_back({"refine_ls"});
    }
    // The declared aliases and constraints, in diffraction-lib's analysis order, empty when there are none.
    categories.push_back({"alias", true, project.aliases.size()});
    categories.push_back({"constraint", true, project.constraints.size()});
    if (project.fitting_mode == "joint") {
        categories.push_back({"joint_fit", true, project.experiments.size()});
    }
    if (is_scan_fitting_mode(project.fitting_mode)) {
        categories.push_back({"sequential_fit"});
    }
    if (!project.sequential_fit.extract.empty()) {
        categories.push_back({"sequential_fit_extract", true, project.sequential_fit.extract.size()});
    }
    if (const std::size_t starts = fit_start_rows(project).size(); starts > 0) {
        categories.push_back({"fit_parameter", true, starts});
    }
    return categories;
}

// The project block's one category.
inline std::vector<Category> project_categories(const Project&) { return {{"metadata"}}; }

// The categories a block's file holds only while its calculation is current, with their rows, by the rule the save
// follows (the adapter's save_project): a structure's when its geometry is current, an experiment's when its
// calculation is. A save writes them after calculating; these are read from the model, so a list of the file's
// categories needs no save. Empty while nothing is current.
inline std::vector<Category> calculated_categories(const Structure& structure) {
    if (!structure.geometry_current()) {
        return {};
    }
    // The writer writes the symmetry operators and the expanded sites always, a structure without sites with no rows,
    // and the bonds only when there is one in the cutoffs (crysta's write_geometry).
    const StructureGeometry& geometry = structure.geometry;
    std::vector<Category> categories{{"atom_sites_cartn_transform"},
                                     {"space_group_symop", true, geometry.space_group_symop.size()},
                                     {"expanded_atom_site", true, geometry.expanded_atom_sites.size()}};
    if (geometry.geom_bond.size() > 0) {
        categories.push_back({"geom_bond", true, geometry.geom_bond.size()});
    }
    if (geometry.expanded_atom_site_moments.size() > 0) {
        categories.push_back({"expanded_atom_site_moment", true, geometry.expanded_atom_site_moments.size()});
    }
    return categories;
}

inline std::vector<Category> calculated_categories(const ExperimentBase& experiment) {
    if (!detail::writes_calculation(experiment)) {
        return {};
    }
    if (experiment.reflections.has_value()) {  // the single crystal's agreement and its observed-reflection counts
        return {{"refine_ls"}, {"reflns"}};
    }
    // A powder's reflections are its designed group's (experiment_categories). Each structure's curve is written with
    // two structures or more: a single one's is the calculated pattern less the background, already in the file.
    if (experiment.data->component_order.size() >= 2) {
        return {{"pd_calc", true, experiment.data->intensity_calc.size()}, {"pd_calc_overall"}};
    }
    return {};
}

}  // namespace edi

#endif  // EDI_CATEGORIES_HPP
