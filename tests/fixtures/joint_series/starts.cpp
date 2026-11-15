#include <crysta/analysis.hpp>
#include <crysta/model.hpp>
#include <crysta/threading.hpp>
#include <iomanip>
#include <iostream>
#include <mutex>
#ifdef EDI_PROBE
#include <edi/io.hpp>
#endif
static void starts(const std::string& file,
                   const std::vector<std::pair<std::string, double>>& values) {
    static std::mutex mutex;
    const std::lock_guard<std::mutex> lock(mutex);
    for (const auto& value : values)
        std::cout << file << '\t' << value.first << '\t' << std::setprecision(17) << value.second
                  << '\n';
}
int main(int argc, char** argv) {
    if (argc != 3) return 2;
    crysta::threading::set_scan_workers(std::stoi(argv[2]));
    crysta::set_scan_file_start_observer(starts);
    try {
#ifdef EDI_PROBE
        auto project = edi::load_project(argv[1]);
        if (project.fitting_mode == "independent")
            project.fit_independent();
        else
            project.fit_sequential();
#else
        auto project = crysta::load_project(argv[1]);
        crysta::fit_project(project);
#endif
    } catch (const std::exception& error) {
        std::cerr << error.what();
        return 1;
    }
}
