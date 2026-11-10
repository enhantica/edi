// Visible  generator for the silicon fit's round-trip observed-pattern oracle.
//
// This executable links crysta directly and never touches edi's parser, adapter, forward model, or
// fit path.  The NCAF fixture supplies only the already-pinned WISH bank/profile geometry; the
// structure is replaced in memory with the known silicon F d -3 m origin-choice-2 model.  The
// target B_iso is anchored to the independent easydiffraction  refinement at 39ada82c
// (saved as 0.5315(43) A^2), not inferred from crysta's output.

#include <iomanip>
#include <iostream>
#include <map>
#include <string>
#include <utility>
#include <vector>

#include "crysta/model.hpp"
#include "crysta/pattern.hpp"
#include "crysta/scattering.hpp"
#include "crysta/symmetry.hpp"

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: direct_crysta_oracle COMPLETE_NCAF_PROJECT\n";
        return 2;
    }

    crysta::Project project = crysta::load_project(argv[1]);
    project.structure.space_group = crysta::resolve_space_group_by_hm_code("F d -3 m", "2");
    for (std::size_t index = 0; index < 3; ++index) {
        project.structure.cell.parameters[index].set_value(5.431);
        project.structure.cell.parameters[index].set_free(false);
    }
    for (std::size_t index = 3; index < 6; ++index) {
        project.structure.cell.parameters[index].set_value(90.0);
        project.structure.cell.parameters[index].set_free(false);
    }

    crysta::AtomSite silicon = project.structure.atom_sites.front();
    silicon.meta.site_id = "Si1";
    silicon.meta.type_symbol = "Si";
    silicon.meta.wyckoff_letter = "a";
    for (crysta::Parameter& coordinate : silicon.fract) {
        coordinate.set_value(0.125);
        coordinate.set_free(false);
    }
    silicon.occupancy.set_value(1.0);
    silicon.occupancy.set_free(false);
    silicon.adp_iso.set_value(0.5315);
    silicon.adp_iso.set_free(false);
    project.structure.atom_sites = {std::move(silicon)};

    std::vector<double> grid;
    grid.reserve(257);
    for (std::size_t index = 0; index < 257; ++index) {
        grid.push_back(15000.0 + 70000.0 * static_cast<double>(index) / 256.0);
    }
    const crysta::Experiment& experiment = project.experiment();
    const crysta::NeutronScattering scattering(std::map<std::string, double>{{"Si", 4.1491}});
    const std::vector<double> observed =
        crysta::compute_pattern(project, scattering, grid, experiment.bank_two_theta_deg,
                                experiment.cutoff_fwhm);

    std::cout << std::setprecision(17);
    for (std::size_t index = 0; index < grid.size(); ++index) {
        std::cout << grid[index] << ' ' << observed[index] << '\n';
    }
}
