// SPDX-License-Identifier: BSD-3-Clause
#include <doctest/doctest.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>

#include "edi/io.hpp"

namespace {
struct ExampleMetadataDirectory {
    std::filesystem::path path =
        std::filesystem::temp_directory_path() /
        ("edi-example-metadata-" +
         std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    ~ExampleMetadataDirectory() { std::filesystem::remove_all(path); }
};

std::string read_example_record(const std::filesystem::path& path) {
    std::ifstream input(path);
    REQUIRE_MESSAGE((input.is_open()), "Stored row changes retain the declared ownership contract");
    return {std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
}
}  // namespace

TEST_CASE("Example descriptive metadata survives native save reopen and shown PROJECT text") {
    ExampleMetadataDirectory directory;
    std::filesystem::create_directories(directory.path);
    const auto fixture =
        std::filesystem::path(__FILE__).parent_path().parent_path().parent_path() /
        "fixtures/constraint_expressions/project";
    std::filesystem::copy(fixture, directory.path / "source",
                          std::filesystem::copy_options::recursive);
    const std::string extra[] = {
        "_metadata.facility       \"Institut Laue–Langevin (ILL)\"",
        "_metadata.instrument     D20",
        "_metadata.dimensionality 1D",
        "_metadata.purpose        refinement",
        "_metadata.polarisation   ?",
    };
    {
        std::ofstream record(directory.path / "source/project.edi", std::ios::app);
        REQUIRE_MESSAGE((
            record.is_open()),
            "Example descriptive metadata survives native save reopen and shown PROJECT text");
        record << '\n';
        for (const auto& line : extra) record << line << '\n';
    }
    auto project = edi::load_project((directory.path / "source").string());
    project.metadata.title = "Edited example title";
    edi::save_project(project, (directory.path / "saved").string());
    const auto first = read_example_record(directory.path / "saved/project.edi");
    CHECK_MESSAGE((
        first.find("Edited example title") != std::string::npos),
        "Example descriptive metadata survives native save reopen and shown PROJECT text");
    for (const auto& line : extra) {
        CHECK_MESSAGE((first.find(line + '\n') != std::string::npos),
                      "Native metadata merge must retain each descriptive source tag: " << line);
    }
    const auto shown = edi::block_edi_text(project, edi::BlockKind::PROJECT);
    for (const auto& line : extra) {
        CHECK_MESSAGE((shown.find(line + '\n') != std::string::npos),
                      "The app's PROJECT text must carry the same descriptive tag: " << line);
    }
    auto reopened = edi::load_project((directory.path / "saved").string());
    CHECK_MESSAGE((
        reopened.metadata.title == "Edited example title"),
        "Example descriptive metadata survives native save reopen and shown PROJECT text");
    edi::save_project(reopened, (directory.path / "resaved").string());
    const auto second = read_example_record(directory.path / "resaved/project.edi");
    for (const auto& line : extra) {
        CHECK_MESSAGE((second.find(line + '\n') != std::string::npos),
                      "A second native save must retain the source metadata bytes: " << line);
    }
}
