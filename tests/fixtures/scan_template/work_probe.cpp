#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <string>

#include "core/file_fit.hpp"
#include "crysta/analysis.hpp"
#include "crysta/model.hpp"
#include "edi/io.hpp"

bool observing = false;
bool escape_enabled = false;
std::string work_log;

namespace crysta {
FitResultBase observed_fit_scan_file(Project& project, const IterationCallback& iterations = {},
                                     const CancelCallback& cancel = {}) {
    if (observing) {
        const auto& data = *project.experiment().data.get();
        std::ofstream stream(work_log, std::ios::app);
        stream << std::setprecision(17) << '[';
        bool first_column = true;
        for (const auto* column : {&data.grid, &data.intensity, &data.sigma}) {
            if (!first_column) stream << ',';
            first_column = false;
            stream << '[';
            bool first = true;
            for (double value : *column) {
                if (!first) stream << ',';
                first = false;
                stream << value;
            }
            stream << ']';
        }
        stream << "]\n";
    }
    return fit_scan_file(project, iterations, cancel);
}
}  // namespace crysta

// The test compiles the pinned native scan source below this declaration. Only calls to
// the fit entry are observed; fitting and the resume loop retain their production bodies.
#define fit_scan_file observed_fit_scan_file
#include "observed_sequential.cpp"
#undef fit_scan_file

int main(int argc, char** argv) {
    if (argc != 4) return 2;
    work_log = argv[2];
    escape_enabled = std::string(argv[3]) == "duplicate";
    auto project = edi::load_project(argv[1]);
    std::size_t completed = 0;
    auto first = project.fit_scan(
        {}, {}, {}, [&](const auto&) { ++completed; }, [&] { return completed >= 1; });
    auto resumed = edi::load_project(argv[1]);
    observing = true;
    std::size_t events = 0;
    auto second = resumed.fit_scan({}, {}, {}, [&](const auto&) { ++events; });
    observing = false;
    std::cout << static_cast<int>(first.status) << ' ' << static_cast<int>(second.status) << ' '
              << events << '\n';
}
