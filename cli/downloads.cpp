// SPDX-License-Identifier: BSD-3-Clause
// diffraction-lib's download commands over EasyDiffraction's collection and tutorials (edi ADR-0075). The core
// resolves, falls back, checks and places files; this file parses arguments, reads URLs and prints.
#include "downloads.hpp"

#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#include "edi/online_fetch.hpp"
#include "edi/online_index.hpp"
#include "transport.hpp"

namespace edi_cli {
namespace {

constexpr std::string_view kCommands[] = {"list-data", "download-data", "list-tutorials", "download-tutorial",
                                          "download-all-tutorials"};

struct Options {
    std::string name, kind, destination, source;
    bool overwrite = false, ipynb = false, py = false;
};

Options parse(std::string_view command, int argc, char** argv) {
    Options options;
    const bool data = command.ends_with("-data");
    options.destination = data ? "data" : "tutorials";
    for (int i = 2; i < argc; ++i) {
        const std::string_view argument = argv[i];
        const auto value = [&]() -> std::string {
            if (++i == argc) throw std::invalid_argument("missing value for " + std::string(argument));
            return argv[i];
        };
        if ((argument == "-d" || argument == "--destination") && command != "list-data" && command != "list-tutorials") {
            options.destination = value();
        } else if ((argument == "-o" || argument == "--overwrite") && command.starts_with("download")) {
            options.overwrite = true;
        } else if (argument == "--source") {
            options.source = value();
        } else if (argument == "--kind" && command == "list-data") {
            options.kind = value();
        } else if (argument == "--ipynb" && command == "download-tutorial") {
            options.ipynb = true;
        } else if (argument == "--py" && command == "download-tutorial") {
            options.py = true;
        } else if (options.name.empty() && !argument.starts_with('-') &&
                   (command == "download-data" || command == "download-tutorial")) {
            options.name = argument;
        } else {
            throw std::invalid_argument("unexpected argument " + std::string(argument));
        }
    }
    if ((command == "download-data" || command == "download-tutorial") && options.name.empty())
        throw std::invalid_argument("give an id or a listing number");
    return options;
}

// The same table the Python package prints: a header row, then one row per entry, columns padded to their widest.
void table(const std::vector<std::vector<std::string>>& rows) {
    std::vector<std::size_t> widths(rows.front().size(), 0);
    for (const auto& row : rows)
        for (std::size_t i = 0; i < row.size(); ++i) widths[i] = std::max(widths[i], row[i].size());
    for (const auto& row : rows) {
        std::string line;
        for (std::size_t i = 0; i < row.size(); ++i) {
            line += row[i];
            if (i + 1 < row.size()) line += std::string(widths[i] - row[i].size() + 2, ' ');
        }
        while (!line.empty() && line.back() == ' ') line.pop_back();
        std::cout << line << '\n';
    }
}

int run(std::string_view command, const Options& options) {
    const bool data = command.ends_with("-data");
    std::vector<std::string> sources =
        data ? edi::online::sources_for(options.source, "EDI_COLLECTION", edi::online::default_collection_sources())
             : edi::online::sources_for(options.source, "EDI_TUTORIALS", {edi::online::default_tutorials_source()});
    std::string why;
    if (std::any_of(sources.begin(), sources.end(), [](const std::string& s) { return s.rfind("http", 0) == 0; }) &&
        !web_available(why)) {
        std::cerr << "edi " << command << ": " << why << '\n';
        return 1;
    }
    const std::string text = edi::online::read_index(sources, fetch);
    const edi::online::Index index = edi::online::parse_index(text);
    const std::string kind = data ? options.kind : "tutorial";
    if (command == "list-data" || command == "list-tutorials") {
        std::vector<std::vector<std::string>> rows{data ? std::vector<std::string>{"#", "id", "kind", "format", "name"}
                                                        : std::vector<std::string>{"#", "id", "title"}};
        std::size_t number = 0;
        for (const edi::online::Entry* entry : edi::online::listing(index, kind)) {
            const std::string name = entry->name.empty() ? entry->description : entry->name;
            if (data) rows.push_back({std::to_string(++number), entry->id, entry->kind, entry->files.front().format, name});
            else rows.push_back({std::to_string(++number), entry->id, entry->name});
        }
        table(rows);
        return 0;
    }
    if (command == "download-all-tutorials") {
        for (const edi::online::Entry* entry : edi::online::listing(index, kind))
            std::cout << edi::online::download(sources, text, entry->id, kind, "ipynb", options.destination,
                                               options.overwrite, fetch)
                      << '\n';
        return 0;
    }
    std::vector<std::string> formats{""};
    if (!data) {
        formats.clear();
        if (options.ipynb || !options.py) formats.push_back("ipynb");
        if (options.py) formats.push_back("py");
    }
    for (const std::string& format : formats) {
        const std::string path = edi::online::download(sources, text, options.name, data ? "" : kind, format,
                                                       options.destination, options.overwrite, fetch);
        std::cout << (data ? "Data '" : "Tutorial '") << options.name << "' is at " << path << '\n';
    }
    return 0;
}

}  // namespace

const char* download_usage() {
    return "       edi list-data [--kind structure|experiment|data|project] [--source URL_OR_FOLDER]\n"
           "       edi download-data NAME [-d DIR] [-o] [--source URL_OR_FOLDER]\n"
           "       edi list-tutorials [--source URL_OR_FOLDER]\n"
           "       edi download-tutorial NAME [-d DIR] [--ipynb] [--py] [-o] [--source URL_OR_FOLDER]\n"
           "       edi download-all-tutorials [-d DIR] [-o] [--source URL_OR_FOLDER]\n";
}

int run_downloads(int argc, char** argv) {
    if (argc < 2) return -1;
    const std::string_view command = argv[1];
    if (std::find(std::begin(kCommands), std::end(kCommands), command) == std::end(kCommands)) return -1;
    if (argc == 3 && std::string_view(argv[2]) == "--help") {
        std::cout << "Usage:\n" << download_usage();
        return 0;
    }
    Options options;
    try {
        options = parse(command, argc, argv);
    } catch (const std::exception& error) {
        std::cerr << "edi " << command << ": " << error.what() << "\nUsage:\n" << download_usage();
        return 2;
    }
    try {
        return run(command, options);
    } catch (const std::exception& error) {
        std::cerr << "edi " << command << ": " << error.what() << '\n';
        return 1;
    }
}

}  // namespace edi_cli
