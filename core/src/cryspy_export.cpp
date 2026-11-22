// SPDX-License-Identifier: BSD-3-Clause
// A copy of a project as one cryspy .rcif file (ADR-0099): the reverse of the cryspy import, for the models both
// programs share. Anything else is refused by name rather than written approximately or left out.

#include <algorithm>
#include <cctype>
#include <cmath>
#include <filesystem>
#include <format>
#include <fstream>
#include <locale>
#include <set>
#include <sstream>

#include "cryspy_project.hpp"
#include "edi/display.hpp"
#include "edi/model.hpp"
#include "edi/project_archive.hpp"

namespace edi {
namespace {
namespace fs = std::filesystem;

[[noreturn]] void unsupported(const std::string& message) { throw IoError("cryspy export: " + message); }

std::string lowercase(std::string text) {
    std::transform(text.begin(), text.end(), text.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return text;
}

// A number that is not a parameter (a measured point, a range limit): its shortest spelling that reads back as the
// same double, so neighbouring grid points never collapse into one.
std::string plain(double value, const std::string& what) {
    if (!std::isfinite(value)) unsupported(what + " is not a finite number");
    return std::format("{}", value);
}

// A text value as one token cryspy's reader keeps whole. That reader (pycifstar) cuts a line at its first `#`, even
// inside quotes, and treats every quote character as an opening or closing quote, so a value holding `#`, `'` or `"`
// cannot be written at all and is refused by name. Otherwise the value is quoted when it would read as syntax (a tag,
// a reserved word, the unknown or inapplicable mark, a text field) or holds a space.
std::string value_token(const std::string& text, const std::string& what) {
    if (text.find_first_of("#'\"\n\r") != std::string::npos) {
        unsupported(what + " '" + text + "' holds a character cryspy cannot read in a value (#, a quote or a line break)");
    }
    const auto lower = lowercase(text);
    const bool reserved = lower.starts_with("data_") || lower.starts_with("loop_") || lower.starts_with("save_") ||
                          lower.starts_with("global_") || lower.starts_with("stop_") || lower == "." || lower == "?";
    const bool needs_quotes =
        text.empty() || reserved || std::string("_$;[]").find(text.front()) != std::string::npos ||
        std::any_of(text.begin(), text.end(), [](unsigned char c) { return std::isspace(c); });
    return needs_quotes ? "'" + text + "'" : text;
}

// A cryspy block name: data_ followed by a token without spaces.
std::string block_name(const std::string& name) {
    if (name.empty() || name.find_first_of("#'\"") != std::string::npos ||
        std::any_of(name.begin(), name.end(), [](unsigned char c) { return std::isspace(c); })) {
        unsupported("the name '" + name + "' cannot name a cryspy block");
    }
    return name;
}

// Parameters spelled as the native save spells them (its exact-cell and all-exact exceptions included), with cryspy's
// bracket: a plain number is fixed, `v()` is free without an s.u., and `v(n)` is free with the s.u. as whole digits of
// the value's last decimal, which is the only form cryspy's reader keeps.
class Numbers {
public:
    explicit Numbers(const Project& project)
        : project_(project), spelling_(save_spelling(project)), rule_(project.su_rule) {}

    std::string operator()(const Parameter& parameter, const std::string& what) const {
        const double value = parameter.value.get();
        if (!std::isfinite(value)) unsupported(what + " is not a finite number");
        const auto text = file_text(parameter, rule_, written_exactly(spelling_, project_, parameter));
        if (!parameter.free.get()) return text.value;
        const auto su = parameter.uncertainty.get();
        if (!su || *su == 0.) return text.value + "()";
        if (!std::isfinite(*su) || *su < 0.) unsupported(what + " has an s.u. that is not a finite positive number");
        if (text.value.find_first_of("eE") != std::string::npos) {
            unsupported(what + " (" + text.value + ") needs an exponent, which cryspy's s.u. bracket cannot follow");
        }
        const auto point = text.value.find('.');
        const int decimals = point == std::string::npos ? 0 : static_cast<int>(text.value.size() - point - 1);
        // The s.u. in units of the value's last decimal, rounded up as an s.u. is.
        const double units = std::ceil(*su * std::pow(10.0, decimals) * (1 - 1e-12));
        if (units < 1 || units > 1e9) {
            unsupported(what + " has the s.u. " + std::format("{}", *su) + ", which cryspy cannot write against " +
                        text.value);
        }
        return text.value + "(" + std::format("{}", static_cast<long long>(units)) + ")";
    }
    std::string operator()(const OptionalParameter& parameter, const std::string& what) const {
        return parameter ? (*this)(*parameter, what) : std::string("0");
    }

private:
    const Project& project_;
    SaveSpelling spelling_;
    std::string rule_;
};

bool zero(const OptionalParameter& parameter) {
    return !parameter || (parameter->value.get() == 0. && !parameter->free.get());
}

// What cryspy's project holds and the export writes; every other active term is refused by name, never dropped.
void admit_structure(const Structure& structure) {
    const auto where = "structure " + structure.name.value() + ": ";
    if (!structure.magnetic.get().empty() || !structure.atom_site_moment.empty() ||
        !structure.magnetic_form_factors.empty()) {
        unsupported(where + "magnetic order is not part of the cryspy export");
    }
    if (!structure.scattering_lengths_fm.get().empty()) {
        unsupported(where + "custom neutron scattering lengths have no place in a cryspy project");
    }
    if (!structure.atom_site_aniso.empty()) {
        unsupported(where + "anisotropic displacements are not part of the cryspy export");
    }
    if (structure.atom_sites.empty()) unsupported(where + "it has no atom sites");
}

void admit_experiment(const BraggPdExperiment& experiment, const Project& project) {
    const auto where = "experiment " + experiment.name.value() + ": ";
    const auto refuse = [&](const std::string& what) { unsupported(where + what); };
    if (experiment.experiment_type.effective_sample_form() != SampleFormEnum::POWDER ||
        experiment.experiment_type.effective_scattering_type() != ScatteringTypeEnum::BRAGG ||
        experiment.effective_beam_mode() != BeamModeEnum::CONSTANT_WAVELENGTH ||
        experiment.experiment_type.effective_radiation_probe() != RadiationProbeEnum::NEUTRON) {
        refuse("the cryspy export writes constant-wavelength neutron powder diffraction only");
    }
    const auto& instrument = experiment.instrument;
    if (!instrument.setup_wavelength || !(instrument.setup_wavelength->value.get() > 0.)) {
        refuse("it needs a positive wavelength");
    }
    if (!zero(instrument.calib_sample_displacement)) refuse("cryspy has no sample displacement");
    if (!zero(instrument.calib_sample_transparency)) refuse("cryspy has no sample transparency");
    if (!zero(instrument.setup_wavelength_2_to_1_ratio)) refuse("cryspy has no second wavelength");
    if (!zero(instrument.setup_polarization_coefficient)) refuse("cryspy has no polarization correction here");
    if (experiment.absorption.type.value_or("none") != "none" || !zero(experiment.absorption.mu_r) ||
        !zero(experiment.absorption.abscor1)) {
        refuse("cryspy has no absorption correction");
    }
    if (!experiment.preferred_orientation.empty()) refuse("cryspy's powder experiment has no preferred orientation");
    if (experiment.extinction.type.value_or("none") != "none") refuse("cryspy's powder experiment has no extinction");
    if (project.experiments.size() > 1 && experiment.dataset_weight != 1.0) {
        refuse("cryspy weighs every experiment of a joint fit equally");
    }
    const auto& peak = experiment.peak;
    const std::string type = peak.type.value_or("cwl-tch-pseudo-voigt");
    if (type == "cwl-pseudo-voigt-berar-baldinozzi") {
        if (!zero(peak.mixing_eta_0) || !zero(peak.mixing_eta_1)) {
            refuse("cryspy's Bérar–Baldinozzi peak is a Gaussian; the pseudo-Voigt mixing must be zero and fixed");
        }
        if (peak.asym_beba_limit && peak.asym_beba_limit->value.get() < 180.) {
            refuse("cryspy applies the Bérar–Baldinozzi asymmetry at every angle; the angular limit must be 180");
        }
    } else if (type != "cwl-tch-pseudo-voigt") {
        refuse("the peak profile " + type + " has no cryspy counterpart; cryspy has the Thompson-Cox-Hastings "
               "pseudo-Voigt and its Gaussian with Bérar–Baldinozzi asymmetry");
    }
    if (experiment.background_type != "line-segment" || experiment.background.empty()) {
        refuse("cryspy's background is a set of line-segment points");
    }
    std::size_t linked = 0;
    for (const auto& link : experiment.linked_structures) {
        if (!link->enabled.get()) continue;
        const auto& id = link->structure_id.value();
        if (std::none_of(project.structures.begin(), project.structures.end(),
                         [&](const auto& structure) { return structure->name.value() == id; })) {
            refuse("it links the structure " + id + ", which the project does not have");
        }
        ++linked;
    }
    if (linked == 0) refuse("no structure is linked");
    if (!experiment.data) unsupported(where + "cryspy needs measured intensities with their sigmas");
    const auto& data = *experiment.data;
    const auto& x = data.axis();
    const auto& y = data.intensity_meas.get();
    const auto& sigma = data.intensity_meas_su.get();
    if (x.size() < 2 || y.size() != x.size() || sigma.size() != x.size()) {
        refuse("cryspy needs measured intensities with their sigmas");
    }
    for (std::size_t i = 0; i < x.size(); ++i) {
        if (!std::isfinite(x[i]) || !std::isfinite(y[i]) || !std::isfinite(sigma[i]) || !(sigma[i] > 0.) ||
            x[i] >= 180. || (i > 0 && !(x[i] > x[i - 1]))) {
            refuse("measured point " + std::to_string(i + 1) +
                   " is not a finite point of an ascending grid below 180 degrees with a positive sigma");
        }
    }
}

void admit_project(const Project& project) {
    if (project.structures.empty() || project.experiments.empty()) {
        unsupported("a cryspy project needs at least one structure and one experiment");
    }
    if (!project.constraints.empty()) {
        unsupported("the project's parameter constraints have no cryspy counterpart");
    }
    if (project.sequential_fit.declared()) unsupported("a sequential fit setup has no cryspy counterpart");
    std::set<std::string> names;
    for (const auto& structure : project.structures) {
        admit_structure(*structure);
        if (!names.insert(lowercase(structure->name.value())).second) {
            unsupported("two blocks would be named " + structure->name.value());
        }
    }
    for (const auto& experiment : project.experiments) {
        admit_experiment(*experiment, project);
        if (!names.insert(lowercase(experiment->name.value())).second) {
            unsupported("two blocks would be named " + experiment->name.value());
        }
    }
}

void write_crystal(std::ostream& out, const Structure& structure, const Numbers& number) {
    const auto name = structure.name.value();
    out << "data_" << block_name(name) << "\n\n";
    const auto& group = structure.space_group;
    out << "_space_group_name_H-M_alt " << value_token(group.name_h_m.value(), "the space group of " + name) << "\n";
    if (!group.coord_system_code.value().empty()) {
        out << "_space_group_IT_coordinate_system_code "
            << value_token(group.coord_system_code.value(), "the setting of " + name) << "\n";
    }
    const char* cell_tags[] = {"_cell_length_a",    "_cell_length_b",   "_cell_length_c",
                               "_cell_angle_alpha", "_cell_angle_beta", "_cell_angle_gamma"};
    const auto cell = const_cast<Structure&>(structure).cell.parameters();
    for (std::size_t i = 0; i < cell.size(); ++i) {
        out << cell_tags[i] << " " << number(*cell[i], std::string(cell_tags[i]) + " of " + name) << "\n";
    }
    out << "\nloop_\n_atom_site_label\n_atom_site_type_symbol\n_atom_site_fract_x\n_atom_site_fract_y\n"
           "_atom_site_fract_z\n_atom_site_occupancy\n_atom_site_adp_type\n_atom_site_B_iso_or_equiv\n"
           "_atom_site_U_iso_or_equiv\n";
    for (const auto& site : structure.atom_sites) {
        const auto id = site->id.value();
        const auto type = site->adp_type.value();
        if (type != "Biso" && type != "Uiso") {
            unsupported(std::format("atom {} of {} has {} displacements; the cryspy export writes isotropic ones", id,
                                    name, type));
        }
        const bool b = type == "Biso";
        const auto what = std::format("atom {} of {}", id, name);
        out << value_token(id, "the label of " + what) << " "
            << value_token(site->type_symbol.value(), "the type of " + what) << " "
            << number(site->fract_x, "x of " + what) << " " << number(site->fract_y, "y of " + what) << " "
            << number(site->fract_z, "z of " + what) << " " << number(site->occupancy, "occupancy of " + what)
            << " " << (b ? "Biso" : "Uiso") << " "
            << (b ? number(site->adp_iso, "B of " + what) : std::string("0")) << " "
            << (b ? std::string("0") : number(site->adp_iso, "U of " + what)) << "\n";
    }
    out << "\n";
}

void write_powder(std::ostream& out, const BraggPdExperiment& experiment, const Numbers& number) {
    const auto name = experiment.name.value();
    const auto of = [&](const std::string& what) { return what + " of " + name; };
    if (!experiment.data) unsupported("experiment " + name + " has no measured data");
    const auto& data = *experiment.data;
    const auto& peak = experiment.peak;
    const bool beba = peak.type.value_or("cwl-tch-pseudo-voigt") == "cwl-pseudo-voigt-berar-baldinozzi";
    const auto& instrument = experiment.instrument;
    out << "data_" << block_name(name) << "\n\n"
        << "_setup_radiation neutrons\n"
        << "_setup_wavelength " << number(instrument.setup_wavelength, of("the wavelength")) << "\n"
        << "_setup_field 0\n"
        << "_setup_offset_2theta " << number(instrument.calib_twotheta_offset, of("the 2theta offset")) << "\n\n"
        << "_pd_instr_resolution_U " << number(peak.broad_gauss_u, of("U")) << "\n"
        << "_pd_instr_resolution_V " << number(peak.broad_gauss_v, of("V")) << "\n"
        << "_pd_instr_resolution_W " << number(peak.broad_gauss_w, of("W")) << "\n"
        << "_pd_instr_resolution_X " << (beba ? std::string("0") : number(peak.broad_lorentz_x, of("X"))) << "\n"
        << "_pd_instr_resolution_Y " << (beba ? std::string("0") : number(peak.broad_lorentz_y, of("Y"))) << "\n";
    if (beba) {
        out << "_pd_instr_reflex_asymmetry_p1 " << number(peak.asym_beba_a0, of("asymmetry A0")) << "\n"
            << "_pd_instr_reflex_asymmetry_p2 " << number(peak.asym_beba_b0, of("asymmetry B0")) << "\n"
            << "_pd_instr_reflex_asymmetry_p3 " << number(peak.asym_beba_a1, of("asymmetry A1")) << "\n"
            << "_pd_instr_reflex_asymmetry_p4 " << number(peak.asym_beba_b1, of("asymmetry B1")) << "\n";
    }
    const auto& x = data.axis();
    out << "\n_range_2theta_min " << plain(x.front(), of("the first point")) << "\n_range_2theta_max "
        << plain(x.back(), of("the last point")) << "\n";

    out << "\nloop_\n_phase_label\n_phase_scale\n_phase_igsize\n";
    for (const auto& link : experiment.linked_structures) {
        if (!link->enabled.get()) continue;
        const auto& id = link->structure_id.value();
        out << value_token(id, of("the phase link")) << " " << number(link->scale, of("the scale of " + id))
            << " 0\n";
    }

    if (!experiment.excluded_regions.empty()) {
        out << "\nloop_\n_exclude_id\n_exclude_2theta_min\n_exclude_2theta_max\n";
        for (const auto& region : experiment.excluded_regions) {
            const auto id = region->id.value();
            out << value_token(id, of("the excluded region id")) << " "
                << plain(region->first.get(), of("excluded region " + id)) << " "
                << plain(region->second.get(), of("excluded region " + id)) << "\n";
        }
    }

    out << "\nloop_\n_pd_background_2theta\n_pd_background_intensity\n";
    for (const auto& point : experiment.background) {
        out << plain(point->position.get(), of("a background point")) << " "
            << number(point->intensity, of("background point " + point->id.value())) << "\n";
    }

    out << "\nloop_\n_pd_meas_2theta\n_pd_meas_intensity\n_pd_meas_intensity_sigma\n";
    const auto& y = data.intensity_meas.get();
    const auto& sigma = data.intensity_meas_su.get();
    for (std::size_t i = 0; i < x.size(); ++i) {
        const auto what = of("measured point " + std::to_string(i + 1));
        out << plain(x[i], what) << " " << plain(y[i], what) << " " << plain(sigma[i], what) << "\n";
    }
    out << "\n";
}

}  // namespace

std::string export_cryspy_project(const Project& project, const std::string& directory) {
    // Everything is checked and written to text before the directory is created.
    admit_project(project);
    const Numbers number(project);
    std::ostringstream text;
    text.imbue(std::locale::classic());
    text << "# Exported by EasyDiffraction\n\n";
    for (const auto& structure : project.structures) write_crystal(text, *structure, number);
    for (const auto& experiment : project.experiments) write_powder(text, *experiment, number);

    const auto destination = fs::absolute(directory).lexically_normal();
    if (destination.filename().empty() || fs::exists(destination)) {
        unsupported("choose a new output directory");
    }
    const auto stage = detail::fresh_archive_directory_at("cryspy", destination.parent_path().string());
    try {
        const auto output = fs::path(stage) / "export";
        fs::create_directory(output);
        std::ofstream out(output / "project.rcif");
        out << text.str();
        out.close();
        if (!out) unsupported("cannot write project.rcif");
        detail::publish_fresh_project_path(output.string(), destination.string());
        remove_archive_directory(stage);
    } catch (...) {
        remove_archive_directory(stage);
        throw;
    }
    return (destination / "project.rcif").string();
}

}  // namespace edi
