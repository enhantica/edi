#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

#include "edi/io.hpp"

// Observe the completed fit's numerical values BEFORE saving, never its saved coefficient text.
int main(int argc, char** argv) {
    if (argc != 4) return 2;
    auto project = edi::load_project(argv[1]);
    if (std::string(argv[2]) == "scan") {
        const auto outcome = project.fit_sequential();
        if (outcome.status != edi::FitStatus::DONE) return 3;
        const auto file = project.sequential_fit.template_file;
        const auto table = project.fit_result.scan_results.at(file)->correlations;
        if (!table || !table->names || !table->values) return 4;
        const auto& names = *table->names;
        const auto& values = *table->values;
        std::size_t position = 0;
        for (std::size_t i = 0; i < names.size(); ++i) {
            for (std::size_t j = i + 1; j < names.size(); ++j) {
                std::cout << std::quoted(names[i]) << ' ' << std::quoted(names[j]) << ' '
                          << std::hexfloat << values.at(position++) << '\n';
            }
        }
        if (position != values.size()) return 5;
    } else {
        const auto outcome = project.fit();
        if (outcome.status != edi::FitStatus::DONE) return 3;
        for (const auto& pair : outcome.correlations) {
            std::cout << std::quoted(pair.parameter_unique_name_i.value()) << ' '
                      << std::quoted(pair.parameter_unique_name_j.value()) << ' '
                      << std::hexfloat << pair.correlation.get() << '\n';
        }
    }
    edi::save_project_as(project, argv[3]);
}
