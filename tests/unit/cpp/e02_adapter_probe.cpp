#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "adapter_test_access.hpp"
#include "crysta/recompute.hpp"
#include "crysta/residual.hpp"
#include "crysta/scattering.hpp"
#include "crysta/symmetry.hpp"
#include "edi/io.hpp"
#include "edi/model.hpp"

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << message << '\n';
        std::exit(1);
    }
}

void require_parameter(const crysta::Parameter& actual, double value, double esd, bool free,
                       const char* message) {
    require(actual.value() == value, message);
    require(actual.uncertainty() == esd, message);
    require(actual.free() == free, message);
}

std::uint64_t maximum_stamp(const std::vector<crysta::Clock>& clocks) {
    std::uint64_t result = 0;
    for (const auto& clock : clocks) result = std::max(result, clock.stamp());
    return result;
}

void require_absorption_uses_public_value_cache_behavior(const edi::Project& source) {
    edi::BraggPdExperiment experiment = source.experiment();
    experiment.absorption.abscor1 = edi::Parameter(0.0);
    experiment.absorption.abscor2 = edi::Parameter(0.0);
    experiment.absorption.type = "cylinder";
    experiment.peak.type = "tof-jorgensen-von-dreele";
    crysta::Structure structure(edi::detail::to_crysta_cell(source.structure().cell),
                                crysta::resolve_space_group(
                                    source.structure().space_group.name_h_m),
                                edi::detail::to_crysta_atom_sites(source.structure().atom_sites));
    crysta::Project project(std::move(structure), edi::detail::to_crysta_experiment(experiment));
    const crysta::NeutronScattering scattering =
        source.structure().scattering_lengths_fm.empty()
            ? crysta::load_neutron_scattering()
            : crysta::NeutronScattering(source.structure().scattering_lengths_fm);
    std::vector<double> grid(257);
    for (std::size_t i = 0; i < grid.size(); ++i) {
        grid[i] = 18000.0 + (76000.0 - 18000.0) * static_cast<double>(i) /
                               static_cast<double>(grid.size() - 1);
    }
    crysta::CachedForwardModel forward(project, scattering, grid,
                                       experiment.instrument.setup_twotheta_bank.value,
                                       experiment.peak.cutoff_fwhm);
    const auto baseline = forward.evaluate();
    require(forward.rebuilds() == 1, "absorption baseline rebuild count");
    const std::uint64_t stamp_before = maximum_stamp(forward.structural_clocks());
    project.experiment().absorption.at(0).set_value(0.05);
    const std::uint64_t stamp_after = maximum_stamp(forward.structural_clocks());
    require(stamp_after == stamp_before, "absorption must not click a value-cache structural stamp");
    const auto changed = forward.evaluate();
    require(forward.rebuilds() == 1, "absorption must add zero value-cache rebuilds");
    double maximum_relative_change = 0.0;
    for (std::size_t i = 0; i < baseline.size(); ++i) {
        const double denominator = std::max(std::abs(baseline[i]), 1.0e-300);
        maximum_relative_change =
            std::max(maximum_relative_change, std::abs(changed[i] - baseline[i]) / denominator);
    }
    require(maximum_relative_change > 1.0e-6, "non-zero absorption edit must change the pattern");
}

//  review-11 F1: this default-built native probe is run by the system tier in a
// subprocess. A null edit-record dereference must fail that one case, never the pytest suite.
int require_moved_from_project_reuse(const std::string& mode, const std::string& fixture) {
    edi::Project source = edi::load_project(fixture);
    const edi::Project valid = edi::load_project(fixture);
    const auto restore_and_calculate = [&](bool copy_whole_project) {
        if (copy_whole_project) {
            source = valid;
        } else {
            source.structures = valid.structures;
            source.experiments = valid.experiments;
        }
        require(source.experiment().data.has_value(),
                " moved-from reuse control must restore a measured data node");
        source.note_edit();
        source.calculate();
        require(!source.experiment().data->intensity_calc.empty(),
                " moved-from reuse must publish a calculated data column");
    };
    if (mode == "construct-copy" || mode == "construct-collections") {
        edi::Project destination(std::move(source));
        restore_and_calculate(mode == "construct-copy");
        return 0;
    }
    if (mode == "assign-copy" || mode == "assign-collections") {
        edi::Project destination;
        destination = std::move(source);
        restore_and_calculate(mode == "assign-copy");
        return 0;
    }
    return 2;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc == 4 && std::string(argv[1]) == "--move-reuse") {
        return require_moved_from_project_reuse(argv[2], argv[3]);
    }
    edi::Cell cell;
    cell.length_a = {7.1, 0.01, true};
    cell.length_b = {8.2, 0.02, false};
    cell.length_c = {9.3, 0.03, true};
    cell.angle_alpha = {78.5, 0.04, false};
    cell.angle_beta = {91.25, 0.05, true};
    cell.angle_gamma = {103.75, 0.06, false};
    const crysta::Cell converted_cell = edi::detail::to_crysta_cell(cell);
    require(converted_cell.parameters.size() == 6, "cell parameter count");
    const double cell_values[] = {7.1, 8.2, 9.3, 78.5, 91.25, 103.75};
    for (std::size_t i = 0; i < converted_cell.parameters.size(); ++i) {
        require_parameter(converted_cell.parameters[i], cell_values[i], 0.01 * (i + 1), i % 2 == 0,
                          "cell value/esd/free mapping");
    }

    edi::AtomSite atom;
    atom.id = "Na1";
    atom.type_symbol = "Na";
    atom.wyckoff_letter = "a";
    atom.fract_x = {0.137, 0.007, true};
    atom.fract_y = {0.281, 0.008, false};
    atom.fract_z = {0.419, 0.009, true};
    atom.occupancy = {0.73, 0.01, false};
    atom.adp_iso = {1.27, 0.02, true};
    edi::ItemVec<edi::AtomSite> atoms;
    atoms.push_back(std::move(atom));
    const auto sites = edi::detail::to_crysta_atom_sites(atoms);
    require(sites.size() == 1, "atom-site count");
    require(sites[0].site_id == "Na1", "atom label");
    require(sites[0].type_symbol == "Na", "atom element");
    require_parameter(sites[0].fract[0], 0.137, 0.007, true, "fract_x mapping");
    require_parameter(sites[0].fract[1], 0.281, 0.008, false, "fract_y mapping");
    require_parameter(sites[0].fract[2], 0.419, 0.009, true, "fract_z mapping");
    require_parameter(sites[0].occupancy, 0.73, 0.01, false, "occupancy mapping");
    require_parameter(sites[0].adp_iso, 1.27, 0.02, true, "Biso mapping");

    edi::BraggPdExperiment experiment;
    experiment.peak.rise_alpha_0 = {1.0, 0.01, true};
    experiment.peak.rise_alpha_1 = {2.0, 0.02, false};
    experiment.peak.decay_beta_0 = {3.0, 0.03, true};
    experiment.peak.decay_beta_1 = {4.0, 0.04, false};
    experiment.peak.broad_gauss_sigma_0 = {5.0, 0.05, true};
    experiment.peak.broad_gauss_sigma_1 = {6.0, 0.06, false};
    experiment.peak.broad_gauss_sigma_2 = {14.2, 0.31, true};
    experiment.peak.broad_gauss_size = {8.0, 0.08, false};
    experiment.peak.broad_gauss_strain = {9.0, 0.09, true};
    experiment.peak.broad_lorentz_gamma_0 = {10.0, 0.10, false};
    experiment.peak.broad_lorentz_gamma_1 = {11.0, 0.11, true};
    experiment.peak.broad_lorentz_gamma_2 = {12.0, 0.12, false};
    experiment.peak.broad_lorentz_size = {13.0, 0.13, true};
    experiment.peak.broad_lorentz_strain = {14.0, 0.14, false};
    experiment.instrument.calib_d_to_tof_offset = {-11.3, 0.15, true};
    experiment.instrument.calib_d_to_tof_linear = {20123.4, 0.16, false};
    experiment.instrument.calib_d_to_tof_quadratic = {-1.375, 0.17, true};
    experiment.linked_structure.scale = {1.7, 0.18, false};
    experiment.instrument.setup_twotheta_bank.value = 137.2;
    experiment.peak.cutoff_fwhm = 17.5;
    edi::LineSegment background;
    background.position = 10000.0;
    background.intensity = {2.0, 0.19, true};
    experiment.background.push_back(std::move(background));

    const crysta::BraggPdExperiment converted = edi::detail::to_crysta_experiment(experiment);
    require(converted.peak.size() == 14, "peak parameter count");
    require(converted.instrument.size() == 3 || converted.instrument.size() == 4,
            "instrument parameter count across pinned/current crysta");
    require_parameter(converted.peak[6], 14.2, 0.31, true, "sigma2 mapping");
    require_parameter(converted.instrument[0], -11.3, 0.15, true, "zero mapping");
    require_parameter(converted.instrument[1], 20123.4, 0.16, false, "dtt1 mapping");
    require_parameter(converted.instrument[2], -1.375, 0.17, true, "dtt2 mapping");
    if (converted.instrument.size() == 4) {
        require_parameter(converted.instrument[3], 0.0, 0.0, false, "fixed reciprocal mapping");
    }
    require_parameter(converted.scale, 1.7, 0.18, false, "scale mapping");
    require(converted.background.size() == 1, "background count");
    require(converted.background[0].position == 10000.0, "background position");
    require_parameter(converted.background[0].intensity, 2.0, 0.19, true,
                      "background intensity mapping");
    require(converted.setup_twotheta_bank == 137.2, "bank angle mapping");
    require(converted.cutoff_fwhm == 17.5, "cutoff mapping");
    require(argc == 2, "expected the one-bank fixture directory");
    const edi::Project source = edi::load_project(argv[1]);
    require_absorption_uses_public_value_cache_behavior(source);
    return 0;
}
