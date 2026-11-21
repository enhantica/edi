// SPDX-License-Identifier: BSD-3-Clause
// Imports a cryspy project file (.rcif) as an EasyDiffraction project (ADR-0099). cryspy writes CIF-like
// text: one data block per crystal and one per experiment, followed by its calculated output.

#include "cryspy_project.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <map>
#include <numeric>
#include <optional>
#include <array>
#include <set>
#include <sstream>

#include "edi/io.hpp"
#include "edi/model.hpp"
#include "edi/project_import.hpp"
#include "import_symmetry.hpp"

namespace edi {
namespace {
namespace fs = std::filesystem;
constexpr std::uintmax_t max_rcif_bytes = 64U * 1024U * 1024U;

[[noreturn]] void refuse(const std::string& message) { throw IoError(message); }

std::string lowercase(std::string text) {
    std::transform(text.begin(), text.end(), text.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return text;
}

struct Loop {
    std::vector<std::string> tags;
    std::vector<std::string> values;
    std::size_t rows() const { return tags.empty() ? 0 : values.size() / tags.size(); }
    std::optional<std::size_t> column(const std::string& tag) const {
        const auto found = std::find(tags.begin(), tags.end(), tag);
        if (found == tags.end()) return std::nullopt;
        return static_cast<std::size_t>(found - tags.begin());
    }
    const std::string& at(std::size_t row, std::size_t column) const { return values[row * tags.size() + column]; }
};

struct Block {
    std::string name;
    std::map<std::string, std::string> items;
    std::vector<Loop> loops;
    const Loop* loop_with(const std::string& tag) const {
        for (const auto& loop : loops) {
            if (loop.column(tag)) return &loop;
        }
        return nullptr;
    }
};

// cryspy's calculated output, which an import does not read. Its per-phase loops (`loop_<phase>`) can have
// ragged rows, so they are skipped without being checked.
bool output_tag(const std::string& tag) {
    for (const char* prefix : {"_pd_proc_", "_pd_peak_", "_refln_", "_inversed_hessian"}) {
        if (tag.starts_with(prefix)) return true;
    }
    return false;
}

std::vector<std::string> tokens_of(const std::string& line) {
    std::vector<std::string> out;
    std::size_t i = 0;
    while (i < line.size()) {
        while (i < line.size() && std::isspace(static_cast<unsigned char>(line[i]))) ++i;
        if (i >= line.size() || line[i] == '#') break;
        if (line[i] == '\'' || line[i] == '"') {
            const char quote = line[i];
            std::size_t end = i + 1;
            while (end < line.size() &&
                   !(line[end] == quote && (end + 1 == line.size() ||
                                            std::isspace(static_cast<unsigned char>(line[end + 1]))))) {
                ++end;
            }
            out.push_back(line.substr(i + 1, end - i - 1));
            i = end + 1;
        } else {
            std::size_t end = i;
            while (end < line.size() && !std::isspace(static_cast<unsigned char>(line[end]))) ++end;
            out.push_back(line.substr(i, end - i));
            i = end;
        }
    }
    return out;
}

std::vector<Block> parse(std::istream& input) {
    std::vector<Block> blocks;
    enum class State { none, item, tags, values, skipped };
    State state = State::none;
    std::string pending;
    Loop loop;
    const auto close_loop = [&] {
        if (state == State::tags || state == State::values) {
            const bool output = std::all_of(loop.tags.begin(), loop.tags.end(), output_tag);
            if (!output) {
                if (loop.values.size() % loop.tags.size() != 0) {
                    refuse("cryspy loop " + loop.tags.front() + " has an incomplete row");
                }
                blocks.back().loops.push_back(std::move(loop));
            }
        }
        loop = Loop{};
        if (state != State::item) state = State::none;
    };
    const auto value = [&](std::string text) {
        if (state == State::item) {
            blocks.back().items[pending] = std::move(text);
            state = State::none;
        } else if (state == State::tags || state == State::values) {
            loop.values.push_back(std::move(text));
            state = State::values;
        } else if (state != State::skipped) {
            refuse("cryspy project has a value with no item: " + text);
        }
    };
    std::string line;
    std::size_t number = 0;
    while (std::getline(input, line)) {
        ++number;
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.starts_with(';')) {  // a text field, read as one value and not used by the import
            while (std::getline(input, line) && !line.starts_with(';')) ++number;
            ++number;
            value("?");
            continue;
        }
        for (auto& token : tokens_of(line)) {
            const auto lower = lowercase(token);
            if (lower == "global_" || lower.starts_with("data_")) {
                close_loop();
                state = State::none;
                blocks.push_back(Block{lower == "global_" ? std::string() : token.substr(5), {}, {}});
            } else if (blocks.empty()) {
                refuse("cryspy project text starts before its first data block (line " + std::to_string(number) + ")");
            } else if (lower == "loop_") {
                close_loop();
                state = State::tags;
            } else if (lower.starts_with("loop_")) {
                close_loop();
                state = State::skipped;
            } else if (lower.starts_with('_') && state != State::item) {
                if (state == State::tags) {
                    loop.tags.push_back(lower);
                } else if (state == State::skipped && loop.values.empty()) {
                    loop.tags.push_back(lower);
                } else {
                    close_loop();
                    pending = lower;
                    state = State::item;
                }
            } else if (state == State::skipped) {
                loop.values.push_back(token);
            } else {
                value(token);
            }
        }
    }
    close_loop();
    if (state == State::item) refuse("cryspy item " + pending + " has no value");
    return blocks;
}

// A cryspy number: `1.23` is fixed, `1.23(4)` and `1.23()` are refined (cryspy's own reader, which also
// allows a constraint mark after the bracket).
Parameter number(const std::string& text, const std::string& what) {
    const auto bracket = text.find('(');
    const auto digits = text.substr(0, bracket);
    std::size_t used = 0;
    double value = 0;
    try {
        value = std::stod(digits, &used);
    } catch (const std::exception&) {
        used = 0;
    }
    if (used == 0 || used != digits.size() || !std::isfinite(value)) {
        refuse("cryspy " + what + " is not a number: '" + text + "'");
    }
    if (bracket != std::string::npos) {
        const auto close = text.find(')', bracket);
        if (close == std::string::npos) refuse("cryspy " + what + " has an unclosed bracket: '" + text + "'");
        if (close + 1 != text.size()) {
            refuse("cryspy " + what + " carries a constraint mark ('" + text + "'), which the import does not convert");
        }
    }
    return Parameter(value, std::nullopt, bracket != std::string::npos);
}

void set(Parameter& target, const Parameter& source) {
    target.value = source.value.get();
    target.free = source.free.get();
}

void set(OptionalParameter& target, const ParameterSpec& spec, const Parameter& source) {
    Parameter value = source;
    value.spec = &spec;
    target = value;
}

const std::string& item(const Block& block, const std::string& tag) {
    const auto found = block.items.find(tag);
    if (found == block.items.end()) refuse("cryspy block '" + block.name + "' has no " + tag);
    return found->second;
}

std::optional<std::string> optional_item(const Block& block, const std::string& tag) {
    const auto found = block.items.find(tag);
    if (found == block.items.end()) return std::nullopt;
    return found->second;
}

void only_known(const Block& block, const std::set<std::string>& items, const std::set<std::string>& loops) {
    for (const auto& [tag, value] : block.items) {
        if (!items.contains(tag) && !output_tag(tag)) {
            refuse("cryspy block '" + block.name + "' uses " + tag + ", which the import does not convert");
        }
    }
    for (const auto& loop : block.loops) {
        for (const auto& tag : loop.tags) {
            if (!loops.contains(tag)) {
                refuse("cryspy block '" + block.name + "' uses " + tag + ", which the import does not convert");
            }
        }
    }
}

std::string space_group_name(std::string text) {
    text.erase(std::remove_if(text.begin(), text.end(), [](unsigned char c) { return std::isspace(c); }), text.end());
    return lowercase(text);
}

void space_group(Structure& structure, const Block& block) {
    const auto name = space_group_name(item(block, "_space_group_name_h-m_alt"));
    const auto code = optional_item(block, "_space_group_it_coordinate_system_code");
    std::optional<SpaceGroupSettingName> chosen;
    for (const auto& setting : space_group_settings()) {
        if (space_group_name(setting.name_h_m) != name) continue;
        if (code ? setting.coord_system_code == *code : setting.setting == 0) {
            chosen = setting;
            break;
        }
    }
    if (!chosen && !code) chosen = detail::unambiguous_space_group_alias(item(block, "_space_group_name_h-m_alt"));
    if (!chosen) {
        refuse("cryspy space group '" + item(block, "_space_group_name_h-m_alt") + "'" +
               (code ? " with coordinate system code " + *code : std::string()) + " has no EasyDiffraction setting");
    }
    assign_space_group_setting(structure.space_group, *chosen, true);
}

Structure crystal(const Block& block) {
    only_known(block,
               {"_cell_length_a", "_cell_length_b", "_cell_length_c", "_cell_angle_alpha", "_cell_angle_beta",
                "_cell_angle_gamma", "_space_group_name_h-m_alt", "_space_group_it_coordinate_system_code",
                "_space_group_it_number"},
               {"_atom_site_label", "_atom_site_type_symbol", "_atom_site_fract_x", "_atom_site_fract_y",
                "_atom_site_fract_z", "_atom_site_occupancy", "_atom_site_adp_type", "_atom_site_b_iso_or_equiv",
                "_atom_site_u_iso_or_equiv", "_atom_site_multiplicity", "_atom_site_wyckoff_symbol"});
    Structure structure;
    structure.name = detail::imported_name(block.name, "phase_");
    space_group(structure, block);
    const auto cell = structure.cell.parameters();
    const char* cell_tags[] = {"_cell_length_a", "_cell_length_b", "_cell_length_c",
                               "_cell_angle_alpha", "_cell_angle_beta", "_cell_angle_gamma"};
    for (std::size_t i = 0; i < cell.size(); ++i) {
        set(*cell[i], number(item(block, cell_tags[i]), cell_tags[i]));
    }
    const Loop* atoms = block.loop_with("_atom_site_label");
    if (atoms == nullptr || atoms->rows() == 0) refuse("cryspy crystal '" + block.name + "' has no atom sites");
    const auto column = [&](const std::string& tag) {
        const auto found = atoms->column(tag);
        if (!found) refuse("cryspy crystal '" + block.name + "' has no " + tag);
        return *found;
    };
    for (std::size_t row = 0; row < atoms->rows(); ++row) {
        AtomSite site;
        const auto& label = atoms->at(row, column("_atom_site_label"));
        site.id = label;
        // cryspy reads only the element of an ion label for neutron scattering lengths.
        const auto& type = atoms->at(row, column("_atom_site_type_symbol"));
        site.type_symbol = type.substr(0, type.find_first_of("+-0123456789"));
        set(site.fract_x, number(atoms->at(row, column("_atom_site_fract_x")), "x of " + label));
        set(site.fract_y, number(atoms->at(row, column("_atom_site_fract_y")), "y of " + label));
        set(site.fract_z, number(atoms->at(row, column("_atom_site_fract_z")), "z of " + label));
        if (const auto occupancy = atoms->column("_atom_site_occupancy")) {
            set(site.occupancy, number(atoms->at(row, *occupancy), "occupancy of " + label));
        }
        const auto adp = atoms->column("_atom_site_adp_type");
        const auto kind = adp ? lowercase(atoms->at(row, *adp)) : std::string("biso");
        if (kind != "biso" && kind != "uiso") {
            refuse("cryspy atom " + label + " has ADP type " + atoms->at(row, *adp) +
                   ": the import converts isotropic displacements only");
        }
        const auto tag = kind == "biso" ? "_atom_site_b_iso_or_equiv" : "_atom_site_u_iso_or_equiv";
        site.adp_type = kind == "biso" ? "Biso" : "Uiso";
        if (const auto value = atoms->column(tag)) {
            set(site.adp_iso, number(atoms->at(row, *value), "displacement of " + label));
        }
        site.wyckoff_letter = detail::inferred_wyckoff_letter(structure, site);
        structure.atom_sites.push_back(site);
    }
    return structure;
}

bool true_flag(const Block& block, const std::string& tag, bool fallback) {
    const auto text = optional_item(block, tag);
    return text ? lowercase(*text) == "true" : fallback;
}

double fixed_number(const Block& block, const std::string& tag, double fallback) {
    const auto text = optional_item(block, tag);
    return text ? number(*text, tag).value.get() : fallback;
}

BraggPdExperiment powder(const Block& block, const std::vector<Structure>& structures, const WarningSink& warn) {
    only_known(block,
               {"_chi2_sum", "_chi2_diff", "_chi2_up", "_chi2_down", "_pd_instr_reflex_asymmetry_p1",
                "_pd_instr_reflex_asymmetry_p2", "_pd_instr_reflex_asymmetry_p3", "_pd_instr_reflex_asymmetry_p4",
                "_pd_instr_resolution_u", "_pd_instr_resolution_v", "_pd_instr_resolution_w",
                "_pd_instr_resolution_x", "_pd_instr_resolution_y", "_range_2theta_min", "_range_2theta_max",
                "_setup_wavelength", "_setup_field", "_setup_offset_2theta", "_setup_radiation", "_setup_k",
                "_setup_cthm"},
               {"_pd_meas_2theta", "_pd_meas_intensity", "_pd_meas_intensity_sigma", "_exclude_id",
                "_exclude_2theta_min", "_exclude_2theta_max", "_pd_background_2theta", "_pd_background_intensity",
                "_phase_label", "_phase_scale", "_phase_igsize"});
    const auto radiation = lowercase(optional_item(block, "_setup_radiation").value_or("neutrons"));
    if (radiation != "neutrons") {
        refuse("cryspy experiment '" + block.name + "' uses " + radiation + ": the import converts neutron data only");
    }
    if (fixed_number(block, "_setup_field", 0.) != 0.) {
        refuse("cryspy experiment '" + block.name + "' has a magnetic field: the import converts zero-field data only");
    }
    BraggPdExperiment experiment;
    experiment.name = detail::imported_name(block.name, "pd_");
    experiment.experiment_type.sample_form = SampleFormEnum::POWDER;
    experiment.experiment_type.beam_mode = BeamModeEnum::CONSTANT_WAVELENGTH;
    experiment.experiment_type.radiation_probe = RadiationProbeEnum::NEUTRON;
    experiment.experiment_type.scattering_type = ScatteringTypeEnum::BRAGG;
    experiment.neutron_scattering_length = "sears1992";
    set(experiment.instrument.setup_wavelength, spec::instrument_wavelength, number(item(block, "_setup_wavelength"), "wavelength"));
    if (const auto offset = optional_item(block, "_setup_offset_2theta")) {
        set(experiment.instrument.calib_twotheta_offset, spec::instrument_twotheta_offset, number(*offset, "2theta offset"));
    }

    // cryspy's peak is a Thompson-Cox-Hastings pseudo-Voigt with U, V, W in degrees squared and X, Y on tan and
    // 1/cos, the same widths as crysta's. crysta has Berar-Baldinozzi asymmetry only on the linearly mixed
    // pseudo-Voigt, which is the same peak when X and Y are zero (a Gaussian).
    const auto width = [&](const char* tag) {
        const auto text = optional_item(block, tag);
        return text ? number(*text, tag) : Parameter(0.);
    };
    const Parameter u = width("_pd_instr_resolution_u"), v = width("_pd_instr_resolution_v"),
                    w = width("_pd_instr_resolution_w"), x = width("_pd_instr_resolution_x"),
                    y = width("_pd_instr_resolution_y");
    std::array<Parameter, 4> asymmetry{width("_pd_instr_reflex_asymmetry_p1"),
                                       width("_pd_instr_reflex_asymmetry_p2"),
                                       width("_pd_instr_reflex_asymmetry_p3"),
                                       width("_pd_instr_reflex_asymmetry_p4")};
    const bool asymmetric = std::any_of(asymmetry.begin(), asymmetry.end(), [](const Parameter& p) {
        return p.value.get() != 0. || p.free.get();
    });
    const bool lorentzian = x.value.get() != 0. || x.free.get() || y.value.get() != 0. || y.free.get();
    auto& peak = experiment.peak;
    peak.cutoff_fwhm = 0.;  // cryspy computes every peak over the whole pattern
    peak.broad_gauss_u = u;
    peak.broad_gauss_v = v;
    peak.broad_gauss_w = w;
    if (asymmetric && !lorentzian) {
        peak.type = "cwl-pseudo-voigt-berar-baldinozzi";
        peak.mixing_eta_0 = Parameter(0.);
        peak.mixing_eta_1 = Parameter(0.);
        peak.asym_beba_a0 = asymmetry[0];
        peak.asym_beba_b0 = asymmetry[1];
        peak.asym_beba_a1 = asymmetry[2];
        peak.asym_beba_b1 = asymmetry[3];
    } else {
        peak.type = "cwl-tch-pseudo-voigt";
        peak.broad_lorentz_x = x;
        peak.broad_lorentz_y = y;
        if (asymmetric && warn) {
            warn("cryspy experiment '" + block.name +
                 "': the reflection asymmetry is left out, because EasyDiffraction has Berar-Baldinozzi asymmetry "
                 "only on the pseudo-Voigt without X and Y (ADR-0099)");
        }
    }
    canonicalize_peak_specs(peak);

    const Loop* phases = block.loop_with("_phase_label");
    if (phases == nullptr || phases->rows() == 0) refuse("cryspy experiment '" + block.name + "' links no phase");
    experiment.linked_structures.clear();
    for (std::size_t row = 0; row < phases->rows(); ++row) {
        const auto& label = phases->at(row, *phases->column("_phase_label"));
        const auto structure = std::find_if(structures.begin(), structures.end(), [&](const Structure& s) {
            return s.name.value() == detail::imported_name(label, "phase_");
        });
        if (structure == structures.end()) refuse("cryspy experiment '" + block.name + "' links unknown phase " + label);
        if (const auto size = phases->column("_phase_igsize")) {
            const auto ig = number(phases->at(row, *size), "igsize");
            if (ig.value.get() != 0. || ig.free.get()) {
                refuse("cryspy phase " + label + " has a Gaussian size term (igsize), which has no crysta counterpart");
            }
        }
        LinkedStructure link;
        link.structure_id = structure->name.value();
        const auto scale = phases->column("_phase_scale");
        set(link.scale, scale ? number(phases->at(row, *scale), "phase scale") : Parameter(1.));
        experiment.linked_structures.push_back(link);
    }

    const Loop* measured = block.loop_with("_pd_meas_2theta");
    if (measured == nullptr || measured->rows() < 2) refuse("cryspy experiment '" + block.name + "' has no measurements");
    const auto angle_column = *measured->column("_pd_meas_2theta");
    const auto intensity = measured->column("_pd_meas_intensity");
    const auto sigma = measured->column("_pd_meas_intensity_sigma");
    if (!intensity || !sigma) {
        refuse("cryspy experiment '" + block.name + "' needs measured intensities with their sigmas");
    }
    std::vector<double> grid, counts, sigmas;
    double previous = -1.;
    for (std::size_t row = 0; row < measured->rows(); ++row) {
        const double angle = number(measured->at(row, angle_column), "measured 2theta").value.get();
        const double s = number(measured->at(row, *sigma), "measured sigma").value.get();
        if (angle <= previous || angle >= 180. || s <= 0.) {
            refuse("cryspy experiment '" + block.name + "' needs ascending angles below 180 and positive sigmas");
        }
        previous = angle;
        grid.push_back(angle);
        counts.push_back(number(measured->at(row, *intensity), "measured intensity").value.get());
        sigmas.push_back(s);
    }
    // cryspy calculates only inside its range (both ends included); crysta keeps the rest of the grid excluded.
    const double low = fixed_number(block, "_range_2theta_min", grid.front());
    const double high = fixed_number(block, "_range_2theta_max", grid.back());
    const auto first = std::lower_bound(grid.begin(), grid.end(), low);
    const auto end = std::upper_bound(grid.begin(), grid.end(), high);
    if (end - first < 2) refuse("cryspy experiment '" + block.name + "' has fewer than two points in its range");
    if (first != grid.begin()) {
        ExcludedRegion below{grid.front(), std::midpoint(*(first - 1), *first)};
        below.id = "range-low";
        experiment.excluded_regions.push_back(below);
    }
    if (end != grid.end()) {
        ExcludedRegion above{std::midpoint(*(end - 1), *end), grid.back()};
        above.id = "range-high";
        experiment.excluded_regions.push_back(above);
    }
    if (const Loop* excluded = block.loop_with("_exclude_2theta_min")) {
        const auto id = excluded->column("_exclude_id");
        const auto from = excluded->column("_exclude_2theta_min");
        const auto to = excluded->column("_exclude_2theta_max");
        if (!to) refuse("cryspy experiment '" + block.name + "' has an excluded region without its end");
        for (std::size_t row = 0; row < excluded->rows(); ++row) {
            ExcludedRegion region{number(excluded->at(row, *from), "excluded start").value.get(),
                                  number(excluded->at(row, *to), "excluded end").value.get()};
            region.id = id ? detail::imported_name(excluded->at(row, *id), "region_") : "region-" + std::to_string(row + 1);
            experiment.excluded_regions.push_back(region);
        }
    }
    PdDataBase observations;
    observations.two_theta = std::move(grid);
    observations.intensity_meas = std::move(counts);
    observations.intensity_meas_su = std::move(sigmas);
    experiment.data = std::move(observations);

    const Loop* background = block.loop_with("_pd_background_2theta");
    if (background == nullptr || background->rows() == 0) {
        refuse("cryspy experiment '" + block.name + "' has no background points");
    }
    experiment.background_type = "line-segment";
    const auto level = background->column("_pd_background_intensity");
    if (!level) refuse("cryspy experiment '" + block.name + "' has background points without intensities");
    for (std::size_t row = 0; row < background->rows(); ++row) {
        auto point = std::make_shared<LineSegment>();
        point->id = std::to_string(row + 1);
        point->position =
            number(background->at(row, *background->column("_pd_background_2theta")), "background 2theta").value.get();
        set(point->intensity, number(background->at(row, *level), "background intensity"));
        experiment.background.push_back(point);
    }
    return experiment;
}

}  // namespace

Project load_cryspy_project(const std::string& path, const WarningSink& on_warning) {
    return reading_file(path, [&] {
        std::error_code error;
        const auto size = fs::file_size(path, error);
        if (error || size == 0 || size > max_rcif_bytes) refuse("Cannot read cryspy project '" + path + "'");
        std::ifstream input(path);
        if (!input) refuse("Cannot read cryspy project '" + path + "'");
        const auto blocks = parse(input);
        Project project = empty_project("cryspy_import", "");
        std::vector<Structure> structures;
        std::vector<const Block*> experiments;
        for (const auto& block : blocks) {
            if (block.name.empty()) continue;  // global_: cryspy's fit report
            if (block.items.contains("_cell_length_a")) {
                structures.push_back(crystal(block));
            } else if (block.items.contains("_setup_wavelength") && block.loop_with("_pd_meas_2theta")) {
                experiments.push_back(&block);
            } else {
                refuse("cryspy block '" + block.name +
                       "' is not a crystal or an unpolarised constant-wavelength powder experiment, which are what the "
                       "import converts");
            }
        }
        if (structures.empty() || experiments.empty()) {
            refuse("cryspy project '" + path + "' needs at least one crystal and one experiment");
        }
        for (const auto& structure : structures) add_loaded_structure(project, structure);
        for (const Block* block : experiments) add_loaded_experiment(project, powder(*block, structures, on_warning));
        project.fitting_mode = experiments.size() == 1 ? "single" : "joint";
        return project;
    });
}

}  // namespace edi
