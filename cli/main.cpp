// SPDX-License-Identifier: BSD-3-Clause
#include <algorithm>
#include <chrono>
#include <charconv>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#ifdef _WIN32
#include <io.h>
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include "windows_sdk.hpp"
#else
#include <unistd.h>
#include <sys/ioctl.h>
#endif

#include "edi/io.hpp"
#include "edi/model.hpp"
#include "edi/project_archive.hpp"
#include "edi/report.hpp"
#include "edi/selectors.hpp"
#include "edi/threading.hpp"
#include "edi/version.hpp"
#include "downloads.hpp"
#include "scan_progress.hpp"

namespace {

constexpr std::string_view usage =
    "Usage: edi fit PROJECT [--dry | --output DIRECTORY] "
    "[--verbosity off|compact|full] [--report human|machine] [--log-level error|warning|info|debug] "
    "[--threads auto|N] [--parallel-fits N]\n"
    "  --threads: threads per calculation (default: auto).\n"
    "  --parallel-fits: scan files fitted together (default: 1); each uses one thread.\n"
    "    In a sequential scan, files in a group start from the preceding group's result.\n";

int positive_count(std::string_view value, std::string_view option) {
    int count = 0;
    const auto [end, error] = std::from_chars(value.data(), value.data() + value.size(), count);
    if (error != std::errc{} || end != value.data() + value.size() || count < 1) {
        throw std::invalid_argument(std::string(option) + " requires a positive integer");
    }
    return count;
}

bool stdout_is_terminal() {
#ifdef _WIN32
    return _isatty(_fileno(stdout)) != 0;
#else
    return isatty(STDOUT_FILENO) != 0;
#endif
}

std::size_t terminal_columns() {
#ifdef _WIN32
    CONSOLE_SCREEN_BUFFER_INFO info{};
    if (GetConsoleScreenBufferInfo(GetStdHandle(STD_OUTPUT_HANDLE), &info))
        return static_cast<std::size_t>(info.srWindow.Right - info.srWindow.Left + 1);
#else
    winsize size{};
    if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &size) == 0 && size.ws_col > 0) return size.ws_col;
#endif
    return 80;
}

// The scan's counts and reduced chi-square range, folded once per committed row: the resumed rows
// from the preamble, then each file this run fits. `prior` is where this run's rows begin, the
// basis of its timing.
struct ScanTally {
    int completed = 0;
    int ok = 0;
    int prior = 0;
    double chi2_min = std::numeric_limits<double>::quiet_NaN();
    double chi2_max = std::numeric_limits<double>::quiet_NaN();
    void add(const edi::ScanFileRecord& row) {
        if (!std::isnan(row.reduced_chi_square)) {
            chi2_min = std::isnan(chi2_min) ? row.reduced_chi_square
                                            : std::min(chi2_min, row.reduced_chi_square);
            chi2_max = std::isnan(chi2_max) ? row.reduced_chi_square
                                            : std::max(chi2_max, row.reduced_chi_square);
        }
        ++completed;
        ok += row.converged ? 1 : 0;
    }
};

void fit(const std::string& source, const std::string& output, bool dry,
         edi::VerbosityEnum verbosity, bool machine) {
    auto project = edi::load_project(source, [](const std::string& warning) {
        std::cerr << "edi fit: " << warning << '\n';
    });
    const bool from_archive = project.path.empty();
    if (from_archive && output.empty() && !dry) {
        std::cerr << "edi fit: use --output DIRECTORY to save results from an archive.\n";
        dry = true;
    }

    struct ScanScratch {
        std::string path;
        ~ScanScratch() {
            if (path.empty()) return;
            try {
                edi::remove_archive_directory(path);
            } catch (const std::exception& error) {
                std::cerr << "edi fit: temporary directory cleanup failed: " << error.what() << '\n';
            }
        }
    } scratch, unpacked{from_archive ? project.scan_data_root : std::string{}};
    // Independent without a declared scan fits each experiment alone, never a scan (ADR-0081).
    const bool scan = edi::fits_a_scan(project);
    if (scan && dry) {
        scratch.path = edi::fresh_archive_directory("cli-dry");
        if (!project.path.empty()) project.scan_data_root = project.path;
        project.path = scratch.path;
        project.metadata.path = project.path;
        project.archive.clear();
    }
    if (!output.empty()) {
        if (std::filesystem::exists(output)) {
            throw std::invalid_argument("--output must name a new project directory");
        }
        edi::save_project_as(project, output);
        project.archive.clear();
    }

    const bool human = !machine && verbosity != edi::VerbosityEnum::OFF;
    const std::string variant = edi::metric_variant(project);
    // The project's directory name, as Python's Path(...).name gives it (a trailing slash
    // dropped).
    auto source_path = std::filesystem::path(source);
    if (!source_path.has_filename()) source_path = source_path.parent_path();
    const std::string name = source_path.filename().string();
    double previous = 0.0;
    // The same lines as `python -m edi fit`, all rendered by the core (edi/report.hpp): a single
    // fit streams its header, the starting row and one row per iteration; a scan one progress line
    // per file (in place on a terminal) and its summary, with the iteration rows only at full
    // verbosity.
    edi::IterationCallback on_iteration;
    edi::PreambleCallback on_start;
    edi::ScanStartCallback on_scan_start;
    edi::FileCompleteCallback on_file_complete;
    ScanTally tally;
    std::optional<int> total;
    const auto started = std::chrono::steady_clock::now();
    double elapsed = 0.0;
    const bool scan_rows = verbosity == edi::VerbosityEnum::FULL;
    const bool in_place = scan && !scan_rows && stdout_is_terminal();
    std::size_t last_width = 0;
    bool live = false;
    if (human && !scan) {
        on_start = [&](const edi::FitPreamble& preamble) {
            std::cout << edi::stream_header(preamble, name, variant) << std::flush;
            previous = preamble.pre_fit.reduced_chi_square;
        };
    }
    if (human && (!scan || scan_rows)) {
        on_iteration = [&](const edi::IterationRecord& record) {
            std::cout << edi::iteration_line(record, previous, variant) << '\n' << std::flush;
            previous = record.reduced_chi_square;
        };
    }
    if (human && scan) {
        on_scan_start = [&](const edi::ScanPreamble& preamble) {
            total = preamble.total_files;
            for (const auto& row : preamble.completed_rows) tally.add(row);
            tally.prior = tally.completed;
            std::cout << edi::detail::scan_progress_heading(name, project.fitting_mode == "sequential",
                                                            total, tally.prior > 0, in_place ? terminal_columns() : 0)
                      << '\n' << std::flush;
        };
        on_file_complete = [&](const edi::ScanFileRecord& record) {
            tally.add(record);
            elapsed =
                std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
            const std::size_t columns = in_place ? terminal_columns() : 0;
            const std::string line = edi::detail::scan_progress_row(
                tally.completed, total, elapsed, tally.completed - tally.prior, tally.ok,
                tally.completed - tally.ok, record.reduced_chi_square, columns);
            if (in_place) {
                std::cout << edi::detail::scan_progress_rewrite(line, last_width, columns);
                last_width = line.size();
                live = true;
            } else {
                std::cout << line << '\n';
            }
            std::cout << std::flush;
        };
    }

    const auto result = [&] {
        if (project.fitting_mode == "sequential") {
            return project.fit_sequential(on_iteration, {}, on_scan_start, on_file_complete);
        }
        if (project.fitting_mode == "independent" && !project.sequential_fit.declared()) {
            return project.fit_independent(on_iteration, on_start);  // each experiment alone (ADR-0081)
        }
        if (project.fitting_mode == "independent") {
            return project.fit_independent(on_iteration, {}, on_scan_start, on_file_complete);
        }
        if (project.fitting_mode == "joint") return project.fit_joint(on_iteration, on_start);
        return project.fit(on_iteration, on_start);
    }();
    if (!dry) edi::save_project_as(project, project.path);

    if (machine) {
        std::cout << edi::machine_report(project, result, verbosity);
    } else if (human && scan) {
        if (live) std::cout << '\n';
        std::cout << edi::scan_summary(total.value_or(tally.completed), tally.ok,
                                       tally.completed - tally.ok, tally.chi2_min, tally.chi2_max,
                                       elapsed, tally.completed - tally.prior);
    } else if (human) {
        std::cout << edi::summary_line(result, variant);
        if (verbosity == edi::VerbosityEnum::FULL) {
            std::cout << edi::parameter_table(result, &project);
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
    // The one message level, on every command (owner record 2026-11-09): taken out of the arguments
    // here, warning when not given.
    std::vector<char*> kept{argv[0]};
    std::string level = "warning";
    for (int index = 1; index < argc; ++index) {
        const std::string_view argument(argv[index]);
        if (argument == "--log-level" && index + 1 < argc) {
            level = argv[++index];
        } else if (argument.starts_with("--log-level=")) {
            level = std::string(argument.substr(12));
        } else {
            kept.push_back(argv[index]);
        }
    }
    try {
        edi::set_log_level(level);
    } catch (const std::invalid_argument& error) {
        std::cerr << "edi: " << error.what() << '\n';
        return 2;
    }
    argc = static_cast<int>(kept.size());
    kept.push_back(nullptr);
    argv = kept.data();
    if (argc == 2 && std::string_view(argv[1]) == "--version") {
#ifdef EDI_CLI_VERSION
        std::cout << "edi " << EDI_CLI_VERSION << '\n';
#else
        std::cout << "easydiffraction (edi core " << edi::core_version() << ")\n";
#endif
        return 0;
    }
    if ((argc == 2 && std::string_view(argv[1]) == "--help") ||
        (argc == 3 && std::string_view(argv[1]) == "fit" && std::string_view(argv[2]) == "--help")) {
        std::cout << usage << edi_cli::download_usage();
        return 0;
    }
    if (const int code = edi_cli::run_downloads(argc, argv); code >= 0) return code;

    bool dry = false;
    bool machine = false;
    std::string source;
    std::string output;
    auto verbosity = edi::VerbosityEnum::COMPACT;
    int threads = 0;
    int parallel_fits = 1;
    try {
        if (argc < 3 || std::string_view(argv[1]) != "fit") {
            throw std::invalid_argument("expected a fit or download command");
        }
        for (int i = 2; i < argc; ++i) {
            std::string_view argument = argv[i];
            std::optional<std::string_view> inline_value;
            if (argument.starts_with("--threads=") || argument.starts_with("--parallel-fits=")) {
                const auto separator = argument.find('=');
                inline_value = argument.substr(separator + 1);
                argument = argument.substr(0, separator);
            }
            if (argument == "--dry") {
                dry = true;
            } else if (argument == "--output" || argument == "--verbosity" || argument == "--report" ||
                       argument == "--threads" || argument == "--parallel-fits") {
                if (!inline_value && (++i == argc || std::string_view(argv[i]).starts_with("--"))) {
                    throw std::invalid_argument("missing value for " + std::string(argument));
                }
                const std::string_view value = inline_value ? *inline_value : argv[i];
                if (argument == "--threads") {
                    threads = value == "auto" ? 0 : positive_count(value, argument);
                } else if (argument == "--parallel-fits") {
                    parallel_fits = positive_count(value, argument);
                } else if (argument == "--output") {
                    output = value;
                } else if (argument == "--verbosity" && value == "off") {
                    verbosity = edi::VerbosityEnum::OFF;
                } else if (argument == "--verbosity" && value == "compact") {
                    verbosity = edi::VerbosityEnum::COMPACT;
                } else if (argument == "--verbosity" && value == "full") {
                    verbosity = edi::VerbosityEnum::FULL;
                } else if (argument == "--report" && (value == "human" || value == "machine")) {
                    machine = value == "machine";
                } else {
                    throw std::invalid_argument("invalid value for " + std::string(argument));
                }
            } else if (source.empty() && !argument.starts_with('-')) {
                source = argument;
            } else {
                throw std::invalid_argument("unexpected argument " + std::string(argument));
            }
        }
        if (source.empty() || (dry && !output.empty())) {
            throw std::invalid_argument("give a project and choose either --dry or --output");
        }
    } catch (const std::exception& error) {
        std::cerr << "edi: " << error.what() << '\n' << usage << edi_cli::download_usage();
        return 2;
    }
    try {
        edi::set_engine_threads(threads);
        edi::set_scan_workers(parallel_fits);
        fit(source, output, dry, verbosity, machine);
    } catch (const std::exception& error) {
        std::cerr << "edi fit: " << error.what() << '\n';
        if (machine) std::cout << edi::error_report(verbosity);
        return 1;
    }
}
