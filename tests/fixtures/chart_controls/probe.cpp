#include "edi/palette.hpp"
#include "edi/scan_views.hpp"
#include <iostream>
#include <string>
#include <vector>

int main(int argc, char** argv) {
    const std::string mode = argc > 1 ? argv[1] : "catalogue";
    if (mode == "catalogue") {
        for (auto name : edi::colour_scheme_names()) {
            auto scheme = edi::colour_scheme_from_name(name);
            std::cout << name << '\t' << edi::colour_scheme_title(*scheme) << '\n';
        }
        std::cout << "default\t" << edi::colour_scheme_title(edi::kDefaultColourScheme) << '\n';
    } else if (mode == "colours") {
        auto scheme = edi::colour_scheme_from_name(argv[2]);
        if (!scheme) return 2;
        bool dark = std::string(argv[3]) == "dark";
        std::cout << "calc\t" << edi::role_colour(*scheme, edi::ChartRole::TotalCalculation, dark) << '\n';
        const std::size_t count = argc > 4 ? std::stoul(argv[4]) : 11;
        for (std::size_t i = 0; i < count; ++i)
            std::cout << i << '\t' 
#ifdef HAS_FIGURE_COLOURS
                      << edi::figure_colour(*scheme, i, count, dark) << '\t'
                      << edi::figure_colour(*scheme, i, count, dark)
#else
                      << edi::pattern_colour(*scheme, i, count, dark) << '\t'
                      << edi::structure_colour(*scheme, i, count, dark)
#endif
 << '\n';
    } else if (mode == "readable") {
        std::vector<std::string> backgrounds;
        for (int i = 3; i < argc; ++i) backgrounds.emplace_back(argv[i]);
        std::cout << edi::readable_colour(argv[2], backgrounds, 2.0) << '\n';
    } else if (mode == "positions") {
#ifdef HAS_FIGURE_COLOURS
        auto scheme = edi::colour_scheme_from_name(argv[2]);
        if (!scheme) return 2;
        std::vector<edi::FigureItem> items;
        for (int i = 3; i < argc; ++i) {
            std::string value = argv[i];
            edi::FigureItem item;
            item.kind = value[0] == 'e' ? edi::FigureKind::Experiment : edi::FigureKind::Structure;
            if (value.size() > 2) item.position = std::stoul(value.substr(2));
            items.push_back(item);
        }
        for (auto position : edi::colour_positions(*scheme, items)) std::cout << position << '\n';
#else
        std::cout << "missing-shared-assignment" << '\n';
#endif
    } else if (mode == "maps") {
        for (auto& name : edi::scan_colour_map_names())
            std::cout << name << '\t' << edi::scan_colour_map_title(name) << '\n';
    } else if (mode == "map") {
        bool dark = std::string(argv[3]) == "dark";
        auto table = edi::scan_colour_table(argv[2], dark ? "#444444" : "#FFFFFF", dark);
        for (std::size_t i = 0; i < table.size(); ++i) {
            auto c = table[i];
            std::cout << i << '\t' << int(c.r) << '\t' << int(c.g) << '\t' << int(c.b) << '\t' << int(c.a) << '\n';
        }
    } else if (mode == "legacy") {
        for (int i = 2; i < argc; ++i)
            std::cout << edi::colour_scheme_title(edi::colour_scheme_or_default(argv[i])) << '\n';
    }
}
