#include <crysta/model.hpp>
#include <crysta/pattern.hpp>
#include <crysta/reflections.hpp>
#include <crysta/scattering.hpp>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << message << '\n';
        std::exit(1);
    }
}

std::vector<double> tof_grid() {
    std::vector<double> grid;
    grid.reserve(257);
    for (std::size_t index = 0; index < 257; ++index) {
        grid.push_back(15000.0 + 70000.0 * static_cast<double>(index) / 256.0);
    }
    return grid;
}

}  // namespace

int main(int argc, char** argv) {
    require(argc == 2, "usage: crysta-reference <NCAF project directory>");
    const crysta::Project project = crysta::load_project(argv[1]);
    const crysta::Experiment& experiment = project.experiment();
    const crysta::NeutronScattering scattering = crysta::load_neutron_scattering();
    const std::vector<double> grid = tof_grid();
    const std::vector<double> pattern = crysta::compute_pattern(
        project, scattering, grid, experiment.bank_two_theta_deg, experiment.cutoff_fwhm);
    const std::vector<crysta::ReflectionRow> reflections =
        crysta::compute_reflections(project, scattering, grid);
    require(!reflections.empty(), "direct crysta reference returned no reflections");

    std::cout << std::setprecision(17);
    for (const double value : pattern) {
        std::cout << "P " << value << '\n';
    }
    for (const crysta::ReflectionRow& row : reflections) {
        std::cout << "R " << row.h << ' ' << row.k << ' ' << row.l << ' ' << row.d << ' '
                  << row.f_squared << '\n';
    }
    return 0;
}
