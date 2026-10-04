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

#include <cstddef>
#include <map>
#include <string>
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
                         std::optional<Parameter>& field) {
    if (field.has_value()) {
        fields.push_back({name, &*field, true});
    }
}

inline void add_if_shown(std::vector<CategoryField>& fields, const char* name, Parameter& field,
                         bool declared) {
    if (declared || field.free) {
        fields.push_back({name, &field, declared});
    }
}

}  // namespace detail

// The peak category's parameter fields and asymmetry subheading for the experiment's profile.
inline Category peak_category(ExperimentBase& experiment) {
    Category category{"peak"};
    PeakBase& peak = experiment.peak;
    const bool constant_wavelength = experiment.effective_beam_mode() == BeamModeEnum::CONSTANT_WAVELENGTH;
    const std::string profile = peak.type.value_or(constant_wavelength ? "cwl-pseudo-voigt" : "tof-jorgensen");
    if (constant_wavelength) {
        detail::add_optional(category.fields, "broad_gauss_u", peak.broad_gauss_u);
        detail::add_optional(category.fields, "broad_gauss_v", peak.broad_gauss_v);
        detail::add_optional(category.fields, "broad_gauss_w", peak.broad_gauss_w);
        detail::add_optional(category.fields, "broad_lorentz_x", peak.broad_lorentz_x);
        detail::add_optional(category.fields, "broad_lorentz_y", peak.broad_lorentz_y);
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
                                 detail::tof_profile_declares(profile, name));
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

// An experiment's categories in page order (§2b (iii)).
inline std::vector<Category> experiment_categories(ExperimentBase& experiment) {
    const bool constant_wavelength = experiment.effective_beam_mode() == BeamModeEnum::CONSTANT_WAVELENGTH;
    std::vector<Category> categories;
    categories.push_back({"experiment_type"});
    if (experiment.data.has_value()) {  // D-h: the measured range, or the declared grid
        Category data{experiment.calculation_only ? "data_range" : "data"};
        data.rows = experiment.data->intensity_meas.size();
        categories.push_back(data);
    }
    categories.push_back(instrument_category(experiment));
    categories.push_back(peak_category(experiment));
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
    Category linked{"linked_structure", true, 1};
    linked.fields.push_back({"scale", &experiment.linked_structure.scale, true});
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
    // The file's reflections, read-only: shown when the file carried them.
    if (experiment.carried_reflections.has_value()) {
        categories.push_back({"refln", true, experiment.carried_reflections->rows.size()});
    }
    return categories;
}

// A structure's categories in page order (§2b (ii)); ADP columns belong to atom_site (§15.6).
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
    categories.push_back({"scattering_length", true, structure.scattering_lengths_fm.size()});
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
// the `_alias.parameter_unique_name` spelling), in the slot walk's order. Defined beside the walk (io.cpp).
struct NamedParameter {
    std::string unique_name;
    const Parameter* parameter = nullptr;
};
std::vector<NamedParameter> named_parameters(const Project& project);

// The same walk over a project being written: each refinable parameter by its unique name.
struct NamedSlot {
    std::string unique_name;
    Parameter* parameter = nullptr;
};
std::vector<NamedSlot> named_slots(Project& project);

// The analysis categories shown (D-i): the minimizer and the fitting mode always; the scan declaration
// in a scan mode. Every loop the block writes is shown as its own category ("loop in .edi — table in
// gui"): the joint weights always (the writer writes them in every mode; admitted in joint mode only),
// the scan extraction rules and the fit start state when there are any.
inline std::vector<Category> analysis_categories(const Project& project) {
    std::vector<Category> categories{{"minimizer"}, {"fitting_mode"}};
    // The declared aliases and constraints, in diffraction-lib's analysis order.
    if (!project.aliases.empty()) {
        categories.push_back({"alias", true, project.aliases.size()});
    }
    if (!project.constraints.empty()) {
        categories.push_back({"constraint", true, project.constraints.size()});
    }
    Category joint{"joint_fit", true, project.experiments.size()};
    joint.admitted = project.fitting_mode == "joint";
    categories.push_back(joint);
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

}  // namespace edi

#endif  // EDI_CATEGORIES_HPP
