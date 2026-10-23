#include "edi/palette.hpp"
#include <iostream>
#include <string>

template<class Scheme>
std::string structure(Scheme scheme, std::size_t place, std::size_t count, bool dark) {
    if constexpr (requires { structure_colour(scheme, place, count, dark); })
        return structure_colour(scheme, place, count, dark);
    else
        return "missing-count-aware-structure-colour";
}
int main(int argc, char** argv) {
    const auto names = edi::colour_scheme_names();
    if (argc == 1) {
        for (auto name : names) std::cout << name << '\n';
        std::cout << "default=" << names[static_cast<std::size_t>(edi::kDefaultColourScheme)] << '\n';
        return 0;
    }
    const auto scheme = edi::colour_scheme_from_name(argv[1]);
    if (!scheme) return 2;
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
    for (std::size_t count : {0, 1, 2, 5, 6, 17}) {
        for (std::size_t place = 0; place <= count; ++place) {
            std::cout << count << '\t' << place << '\t'
                      << (role == "measured" ? edi::pattern_colour(*scheme, place, count, dark)
                                             : structure(*scheme, place, count, dark)) << '\n';
        }
    }
}
