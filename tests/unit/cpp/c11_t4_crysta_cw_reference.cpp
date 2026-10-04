#include <crysta/model.hpp>
#include <crysta/pattern.hpp>
#include <crysta/scattering.hpp>

#include <exception>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

int main(int argc, char** argv) {
    if (argc < 3) {
        std::cerr << "usage: -crysta-reference classify|pattern <project> [grid ...]\n";
        return 2;
    }

    try {
        const std::string mode = argv[1];
        const crysta::Project project = crysta::load_project(argv[2]);
        if (mode == "classify") {
            if (argc != 3) {
                std::cerr << "classify takes no grid values\n";
                return 2;
            }
            return 0;
        }
        if (mode != "pattern" || argc < 4) {
            std::cerr << "pattern requires at least one grid value\n";
            return 2;
        }

        std::vector<double> grid;
        grid.reserve(static_cast<std::size_t>(argc - 3));
        for (int index = 3; index < argc; ++index) {
            grid.push_back(std::stod(argv[index]));
        }
        const crysta::Experiment& experiment = project.experiment();
        const std::vector<double> pattern =
            crysta::compute_pattern(project, crysta::load_neutron_scattering(), grid,
                                    experiment.bank_two_theta_deg, experiment.cutoff_fwhm);
        std::cout << std::setprecision(17);
        for (const double value : pattern) {
            std::cout << value << '\n';
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
