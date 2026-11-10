#include <array>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "crysta/model.hpp"
#include "crysta/parameter.hpp"

namespace {

bool first_parameter = true;
bool first_metadata = true;

std::string json_escape(const std::string& text) {
    std::string escaped;
    for (const char character : text) {
        switch (character) {
            case '\\':
                escaped += "\\\\";
                break;
            case '"':
                escaped += "\\\"";
                break;
            case '\n':
                escaped += "\\n";
                break;
            default:
                escaped += character;
        }
    }
    return escaped;
}

void separator(bool& first) {
    if (!first) {
        std::cout << ',';
    }
    first = false;
}

void parameter(const std::string& path, const crysta::Parameter& value) {
    separator(first_parameter);
    std::cout << "\n    [\"" << json_escape(path) << "\"," << std::setprecision(17)
              << value.value() << ',' << value.esd << ',' << (value.free() ? "true" : "false")
              << ']';
}

void metadata_string(const std::string& path, const std::string& value) {
    separator(first_metadata);
    std::cout << "\n    \"" << json_escape(path) << "\":\"" << json_escape(value) << '"';
}

void metadata_number(const std::string& path, double value) {
    separator(first_metadata);
    std::cout << "\n    \"" << json_escape(path) << "\":" << std::setprecision(17) << value;
}

void metadata_regions(const std::string& path,
                      const std::vector<std::pair<double, double>>& regions) {
    separator(first_metadata);
    std::cout << "\n    \"" << json_escape(path) << "\":[";
    for (std::size_t index = 0; index < regions.size(); ++index) {
        if (index != 0) {
            std::cout << ',';
        }
        std::cout << '[' << std::setprecision(17) << regions[index].first << ','
                  << regions[index].second << ']';
    }
    std::cout << ']';
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        throw std::invalid_argument("usage: crysta_snapshot PROJECT_DIRECTORY");
    }

    const crysta::Project project = crysta::load_project(argv[1]);
    constexpr std::array<const char*, 6> cell_names = {
        "length_a", "length_b", "length_c", "angle_alpha", "angle_beta", "angle_gamma"};
    constexpr std::array<const char*, 3> fract_names = {"fract_x", "fract_y", "fract_z"};
    constexpr std::array<const char*, 14> peak_names = {
        "rise_alpha_0", "rise_alpha_1", "decay_beta_0", "decay_beta_1",
        "broad_gauss_sigma_0", "broad_gauss_sigma_1", "broad_gauss_sigma_2",
        "broad_gauss_size", "broad_gauss_strain", "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1", "broad_lorentz_gamma_2", "broad_lorentz_size",
        "broad_lorentz_strain"};
    constexpr std::array<const char*, 3> instrument_names = {
        "calib_d_to_tof_offset", "calib_d_to_tof_linear", "calib_d_to_tof_quadratic"};

    std::cout << "{\n  \"parameters\":[";
    for (std::size_t index = 0; index < cell_names.size(); ++index) {
        parameter("structure.cell." + std::string(cell_names[index]),
                  project.structure.cell.parameters.at(index));
    }
    for (const crysta::AtomSite& site : project.structure.atom_sites) {
        const std::string prefix = "structure.atom_sites[" + site.meta.site_id + "].";
        for (std::size_t index = 0; index < fract_names.size(); ++index) {
            parameter(prefix + fract_names[index], site.fract[index]);
        }
        parameter(prefix + "occupancy", site.occupancy);
        parameter(prefix + "adp_iso", site.adp_iso);
    }
    for (const crysta::Experiment& experiment : project.experiments) {
        const std::string prefix = "experiments[" + experiment.name + "].";
        for (std::size_t index = 0; index < peak_names.size(); ++index) {
            parameter(prefix + "peak." + peak_names[index], experiment.peak.at(index));
        }
        for (std::size_t index = 0; index < instrument_names.size(); ++index) {
            parameter(prefix + "instrument." + instrument_names[index],
                      experiment.instrument.at(index));
        }
        parameter(prefix + "linked_structure.scale", experiment.scale);
        for (std::size_t index = 0; index < experiment.background.size(); ++index) {
            parameter(prefix + "background." + std::to_string(index) + ".intensity",
                      experiment.background[index].intensity);
        }
    }
    std::cout << "\n  ],\n  \"metadata\":{";
    metadata_string("analysis.fitting_mode", project.fitting_mode);
    metadata_string("structure.space_group.name_h_m",
                    project.structure.space_group.hermann_mauguin);
    for (const crysta::AtomSite& site : project.structure.atom_sites) {
        const std::string prefix = "structure.atom_sites[" + site.meta.site_id + "].";
        metadata_string(prefix + "type_symbol", site.meta.type_symbol);
        metadata_string(prefix + "wyckoff_letter", site.meta.wyckoff_letter);
    }
    for (const crysta::Experiment& experiment : project.experiments) {
        const std::string prefix = "experiments[" + experiment.name + "].";
        metadata_string(prefix + "peak.type", experiment.peak_type);
        metadata_number(prefix + "instrument.setup_twotheta_bank", experiment.bank_two_theta_deg);
        metadata_number(prefix + "peak.cutoff_fwhm", experiment.cutoff_fwhm);
        metadata_number(prefix + "dataset_weight", experiment.dataset_weight);
        metadata_number(prefix + "background.count",
                        static_cast<double>(experiment.background.size()));
        metadata_regions(prefix + "excluded_regions", experiment.excluded_regions);
        for (std::size_t index = 0; index < experiment.background.size(); ++index) {
            metadata_number(prefix + "background." + std::to_string(index) + ".position",
                            experiment.background[index].position);
        }
    }
    std::cout << "\n  }\n}\n";
}
