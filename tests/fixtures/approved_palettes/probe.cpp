#include "edi/palette.hpp"
#include <algorithm>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    const auto names = edi::colour_scheme_names();
    if (argc == 1) {
        for (auto name : names) std::cout << name << '\n';
        std::cout << "default=" << names[static_cast<std::size_t>(edi::kDefaultColourScheme)] << '\n';
        return 0;
    }
    const auto scheme = edi::colour_scheme_from_name(argv[1]);
    if (!scheme) return 2;
    if (argc >= 4 && std::string(argv[2]) == "table") {
        const bool dark = std::string(argv[3]) == "dark";
        for (std::size_t i = 0; i < 11; ++i)
            std::cout << i << '\t' << edi::figure_colour(*scheme, i, 11, dark) << '\n';
        return 0;
    }
    if (argc >= 4 && std::string(argv[2]) == "patterns") {
        const bool dark = std::string(argv[3]) == "dark";
        for (std::size_t structures : {3, 4, 8}) {
            std::vector<std::size_t> taken;
            for (std::size_t i = 0; i < structures; ++i) taken.push_back(i + 2);
            for (std::size_t count : {1, 2, 7, 8, 9, 13, 257})
                for (std::size_t i = 0; i < count; ++i)
                    std::cout << structures << '\t' << count << '\t' << i << '\t'
                              << edi::pattern_set_colour(*scheme, i, count, taken, dark) << '\n';
        }
        return 0;
    }
    if (argc == 3) {
#ifdef HAS_CHART_ROLES
        for (bool dark : {false, true})
            for (auto role : {edi::ChartRole::TotalCalculation, edi::ChartRole::Background, edi::ChartRole::Difference})
                std::cout << edi::role_colour(*scheme, role, dark) << '\n';
#else
        std::cout << "missing-chart-role-colours\n";
#endif
        return 0;
    }
    const std::string role = argv[2];
    const bool dark = std::string(argv[3]) == "dark";
    for (std::size_t count : {0, 1, 2, 5, 6, 11, 12, 17}) {
        for (std::size_t place = 0; place <= count; ++place) {
            const auto positions = edi::colour_positions(*scheme, role == "measured" ? count : 0,
                                                          role == "measured" ? 0 : count);
            const std::size_t position = positions.empty() ? 0 : positions[std::min(place, count - 1)];
            const std::size_t size = positions.empty() ? 0 : *std::max_element(positions.begin(), positions.end()) + 1;
            std::cout << count << '\t' << place << '\t'
                      << edi::figure_colour(*scheme, position, size, dark) << '\n';
        }
    }
}
