// SPDX-License-Identifier: BSD-3-Clause
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>

#include "edi/io.hpp"
#include "edi/project_archive.hpp"
#include "edi/report.hpp"
#include "edi/version.hpp"

namespace {

constexpr std::string_view usage =
    "Usage: edi fit PROJECT [--dry | --output DIRECTORY] "
    "[--verbosity off|compact|full] [--report human|machine]\n";

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
    if (edi::is_scan_fitting_mode(project.fitting_mode) && dry) {
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

    const auto result = [&] {
        if (project.fitting_mode == "sequential") return project.fit_sequential();
        if (project.fitting_mode == "independent") return project.fit_independent();
        if (project.fitting_mode == "joint") return project.fit_joint();
        return project.fit();
    }();
    if (!dry) edi::save_project_as(project, project.path);

    if (machine) {
        std::cout << edi::machine_report(project, result, verbosity);
    } else if (verbosity != edi::VerbosityEnum::OFF) {
        std::cout << edi::summary_line(result, edi::metric_variant(project)) << '\n';
        if (verbosity == edi::VerbosityEnum::FULL) {
            std::cout << edi::parameter_table(result, &project);
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
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
        std::cout << usage;
        return 0;
    }

    bool dry = false;
    bool machine = false;
    std::string source;
    std::string output;
    auto verbosity = edi::VerbosityEnum::COMPACT;
    try {
        if (argc < 3 || std::string_view(argv[1]) != "fit") {
            throw std::invalid_argument("expected a fit command and project");
        }
        for (int i = 2; i < argc; ++i) {
            const std::string_view argument = argv[i];
            if (argument == "--dry") {
                dry = true;
            } else if (argument == "--output" || argument == "--verbosity" || argument == "--report") {
                if (++i == argc || std::string_view(argv[i]).starts_with("--")) {
                    throw std::invalid_argument("missing value for " + std::string(argument));
                }
                const std::string_view value = argv[i];
                if (argument == "--output") {
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
        std::cerr << "edi: " << error.what() << '\n' << usage;
        return 2;
    }
    try {
        fit(source, output, dry, verbosity, machine);
    } catch (const std::exception& error) {
        std::cerr << "edi fit: " << error.what() << '\n';
        if (machine) std::cout << edi::error_report(verbosity);
        return 1;
    }
}
