#include "edi/threading.hpp"
#include "crysta/analysis.hpp"

#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <string>
#include <utility>
#include <vector>

namespace {
std::mutex mutex;
void finished() {
    const char* path = std::getenv("EDI_CLI_PERFORMANCE_TRACE");
    if (!path) return;
    std::lock_guard lock(mutex);
    std::ofstream out(path, std::ios::app);
    out << "{\"kind\":\"end\",\"threads\":" << edi::engine_threads_setting()
        << ",\"parallel\":" << edi::scan_workers_setting() << "}\n";
}
void starting(const std::string& file,
              const std::vector<std::pair<std::string, double>>& starts) {
    std::lock_guard lock(mutex);
    if (std::getenv("EDI_CLI_PROGRESS_CONTROL")) {
        std::cerr << "EDI_PROGRESS_BOUNDARY\n" << std::flush;
        std::string reply;
        if (!std::getline(std::cin, reply) || reply != "continue") std::abort();
    }
    const char* trace = std::getenv("EDI_CLI_PERFORMANCE_TRACE");
    if (!trace) return;
    std::ofstream out(trace, std::ios::app);
    out << "{\"kind\":\"start\",\"file\":" << std::quoted(file)
        << ",\"threads\":" << edi::engine_threads_setting()
        << ",\"parallel\":" << edi::scan_workers_setting() << ",\"values\":{";
    bool first = true;
    for (const auto& [name, value] : starts) {
        if (!first) out << ',';
        first = false;
        out << std::quoted(name) << ':' << std::setprecision(17) << value;
    }
    out << "}}\n";
}
struct Observe {
    Observe() {
        if (!std::getenv("EDI_CLI_PERFORMANCE_TRACE") && !std::getenv("EDI_CLI_PROGRESS_CONTROL")) return;
        edi::set_engine_threads(5);
        edi::set_scan_workers(7);
        crysta::set_scan_file_start_observer(starting);
        std::atexit(finished);
    }
} observe;
}
