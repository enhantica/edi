#include <doctest/doctest.h>

#include <array>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <numbers>
#include <string>
#include <vector>

#include "edi/io.hpp"
#include "edi/model.hpp"

namespace {
struct ScratchProject {
    std::filesystem::path path =
        std::filesystem::temp_directory_path() /
        ("edi-hex-cell-" +
         std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));

    ScratchProject() {
        std::filesystem::create_directories(path / "analysis");
        std::filesystem::create_directory(path / "structures");
        std::filesystem::create_directory(path / "experiments");
    }
    ~ScratchProject() { std::filesystem::remove_all(path); }
};

void write_hexagonal_project(const std::filesystem::path& path) {
    std::ofstream(path / "project.edi")
        << "_edi.schema_version 3\n_metadata.name long-hexagonal-cell\n";
    std::ofstream(path / "analysis/analysis.edi")
        << "_edi.schema_version 3\n_fitting_mode.type single\n_minimizer.max_iterations 8\n";
    std::ofstream(path / "structures/phase.edi") << R"(data_phase
_edi.schema_version 3
_cell.length_a 5.90
_cell.length_b 5.90
_cell.length_c 32.2
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 120
_space_group.name_h_m "P 6"
_space_group.coord_system_code h
loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.wyckoff_letter
_atom_site.adp_type
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
A Fe a Biso 0 0 0 1 0.30
)";
    std::ofstream measured(path / "experiments/bank.edi");
    measured << R"(data_bank
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.radiation_probe neutron
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0
_peak.broad_gauss_v 0
_peak.broad_gauss_w 0.15
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0
_peak.cutoff_fwhm 5
_instrument.setup_wavelength 1.54
_instrument.calib_twotheta_offset 0
loop_
_linked_structure.structure_id
_linked_structure.scale
phase 0.7()
loop_
_data.two_theta
_data.intensity_meas
_data.intensity_meas_su
)";
    // Put a smooth observed peak around the independently located 004 reflection.
    const double center = 360.0 / std::numbers::pi * std::asin(1.54 * 4 / (2 * 32.2));
    for (int step = 0; step <= 80; ++step) {
        const double theta = 10.0 + static_cast<double>(step) / 20;
        const double offset = (theta - center) / .28;
        measured << theta << ' ' << 4 + 25 * std::exp(-offset * offset) << " 1\n";
    }
}
}  // namespace

TEST_CASE("The 32.2 Angstrom hexagonal cell loads and fits measured data") {
    const ScratchProject scratch;
    write_hexagonal_project(scratch.path);
    std::vector<std::string> warnings;
    auto project = edi::load_project(scratch.path.string(),
                                     [&](const std::string& warning) { warnings.push_back(warning); });
    const auto cell_lengths = [&] {
        const auto& cell = project.structures[0]->cell;
        return std::array{cell.length_a.value.get(), cell.length_b.value.get(),
                          cell.length_c.value.get()};
    };
    const std::array expected{5.90, 5.90, 32.2};
    CHECK_MESSAGE(cell_lengths() == expected,
                  "The loader preserves all three independently declared hexagonal lengths");
    for (const auto& warning : warnings) {
        CHECK_MESSAGE(warning.find("cell.length_c") == std::string::npos,
                      "A 32.2 Angstrom length is ordinary valid cell data");
    }
    const auto result = project.fit();
    REQUIRE_MESSAGE(result.values.size() == 1,
                    "The measured long-cell fit solves the one declared free scale");
    CHECK_MESSAGE(std::isfinite(result.reduced_chi_square), "The fit returns finite residuals");
    CHECK_MESSAGE(std::isfinite(result.values.begin()->second), "The fitted value is finite");
    CHECK_MESSAGE(cell_lengths() == expected, "Fitting keeps the long fixed cell unchanged");
}
