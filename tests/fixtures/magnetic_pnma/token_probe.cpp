#define EDI_PROBE
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>

#include "crysta/magnetic.hpp"
#ifdef EDI_PROBE
#include "edi/io.hpp"
#include "edi/model.hpp"
#include "edi/symmetry.hpp"
namespace product = edi;
#else
#include "crysta/analysis.hpp"
#include "crysta/model.hpp"
namespace product = crysta;
#endif
int main(int argc, char** argv) {
    if (argc != 5) return 64;
    try {
        const bool factory = std::string(argv[1]) == "factory";
        auto model = product::load_project(factory ? argv[4] : argv[2]);
        if (std::string(argv[1]) == "factory") {
            std::ifstream stream(std::filesystem::path(argv[2]) / "structures/cosio.edi");
            std::string source{std::istreambuf_iterator<char>(stream), {}};
#ifdef EDI_PROBE
            const auto structure =
                product::structure_from_edi_text(source, "magnetic token witness");
#else
            const auto structure = product::structure_from_edi_text(source);
#endif
            model.structure() = structure;
        }
#ifdef EDI_PROBE
        edi::complete_atom_site_moments(model.structure());
        std::cout << "STAGE completion\n";
        model.calculate();
#else
        product::calculate_project(model);
#endif
#ifdef EDI_PROBE
        (void)crysta::parent_asymmetric_sites(model.structure().magnetic->parent,
                                              std::vector<std::array<double, 3>>{{0, 0, 0}},
                                              std::vector<std::string>{"Ho"});
#else
        (void)crysta::parent_asymmetric_sites(model.structure());
#endif
        std::cout << "STAGE calculate-and-parent-view\n";
#ifdef EDI_PROBE
        if (!model.structure().atom_site_moment.empty()) {
            model.structure().atom_site_moment[0]->crystalaxis_x.free = true;
            (void)model.fit({}, {}, [] { return true; });
            model.structure().atom_site_moment[0]->crystalaxis_x.free = false;
        }
#else
        if (!model.structure().atom_site_moment.empty()) {
            model.structure().atom_site_moment[0].moment[0].set_free(true);
            (void)crysta::fit_project(model, {}, [] { return true; });
            model.structure().atom_site_moment[0].moment[0].set_free(false);
        }
#endif
        std::cout << "STAGE fit-preparation\n";
        product::save_project(model, argv[3]);
        auto second = product::load_project(argv[3]);
        product::save_project(second, std::string(argv[3]) + "-second");
        std::cout << "ACCEPT\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 2;
    }
}
