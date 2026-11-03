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
    REQUIRE_MESSAGE((input.is_open()),
                    "Stored row changes retain the declared ownership contract");
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
        "_metadata.polarisation   none",
    };
    {
        std::ofstream record(directory.path / "source/project.edi", std::ios::app);
        REQUIRE_MESSAGE(
            (record.is_open()),
            "Example descriptive metadata survives native save reopen and shown PROJECT text");
        record << '\n';
        for (const auto& line : extra) record << line << '\n';
    }
    auto project = edi::load_project((directory.path / "source").string());
    project.metadata.title = "Edited example title";
    edi::save_project(project, (directory.path / "saved").string());
    const auto first = read_example_record(directory.path / "saved/project.edi");
    CHECK_MESSAGE(
        (first.find("Edited example title") != std::string::npos),
        "Example descriptive metadata survives native save reopen and shown PROJECT text");
    const std::string retired[] = {"_metadata.facility", "_metadata.instrument",
                                   "_metadata.dimensionality", "_metadata.purpose",
                                   "_metadata.polarisation"};
    const auto shown = edi::block_edi_text(project, edi::BlockKind::PROJECT);
    for (const auto& tag : retired) {
        CHECK_MESSAGE(first.find(tag) == std::string::npos,
                      "ADR-0054 removes converted descriptive tags from native project saves");
        CHECK_MESSAGE(shown.find(tag) == std::string::npos,
                      "ADR-0054 removes converted descriptive tags from shown PROJECT text");
    }
    const auto check_description = [](const edi::Project& loaded) {
        REQUIRE_MESSAGE(loaded.experiments.size() == 1,
                        "ADR-0054 migration retains the experiment");
        const auto& experiment = *loaded.experiments.front();
        CHECK_MESSAGE(experiment.experiment_type.dimensionality == "1d",
                      "ADR-0054 converts legacy 1D to experiment dimensionality 1d");
        CHECK_MESSAGE(experiment.experiment_type.polarisation == "unpolarised",
                      "ADR-0054 converts legacy none to neutron polarisation unpolarised");
        CHECK_MESSAGE(experiment.instrument.name == "D20",
                      "ADR-0054 transfers the legacy instrument to the experiment");
        CHECK_MESSAGE(experiment.instrument.facility == "Institut Laue–Langevin (ILL)",
                      "ADR-0054 transfers the legacy facility to the experiment");
    };
    check_description(project);
    auto reopened = edi::load_project((directory.path / "saved").string());
    CHECK_MESSAGE(
        (reopened.metadata.title == "Edited example title"),
        "Example descriptive metadata survives native save reopen and shown PROJECT text");
    edi::save_project(reopened, (directory.path / "resaved").string());
    const auto second = read_example_record(directory.path / "resaved/project.edi");
    for (const auto& tag : retired) {
        CHECK_MESSAGE(second.find(tag) == std::string::npos,
                      "ADR-0054 never reintroduces retired tags on a second save");
    }
    CHECK_MESSAGE(second.find("Edited example title") != std::string::npos,
                  "Editing the project title survives a second native save");
    check_description(reopened);
    check_description(edi::load_project((directory.path / "resaved").string()));
}
