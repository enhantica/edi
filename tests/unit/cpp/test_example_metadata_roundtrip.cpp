// SPDX-License-Identifier: BSD-3-Clause
#include <doctest/doctest.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <map>
#include <sstream>
#include <string>
#include <vector>

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
    REQUIRE_MESSAGE(input.is_open(), "The actual saved record is readable: " << path);
    return {std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
}

std::filesystem::path copy_example_fixture(const std::filesystem::path& directory) {
    std::filesystem::create_directories(directory);
    const auto fixture =
        std::filesystem::path(__FILE__).parent_path().parent_path().parent_path() /
        "fixtures/constraint_expressions/project";
    const auto source = directory / "source";
    std::filesystem::copy(fixture, source, std::filesystem::copy_options::recursive);
    return source;
}

const std::array<std::string, 5> retired = {"_metadata.facility", "_metadata.instrument",
                                            "_metadata.dimensionality", "_metadata.purpose",
                                            "_metadata.polarisation"};

void no_retired_tags(const std::string& text) {
    for (const auto& tag : retired)
        CHECK_MESSAGE(text.find(tag) == std::string::npos,
                      "Converted project text never writes the retired tag: " << tag);
}

void retired_notices(const std::vector<std::string>& notices, int count) {
    for (const auto& tag : retired)
        CHECK_MESSAGE(
            std::count_if(notices.begin(), notices.end(),
                          [&](const auto& notice) {
                              return notice.find(tag) != std::string::npos;
                          }) == count,
            "Each retired tag warns once on conversion, never on migrated reopen: " << tag);
}

// Same four non-scientific lines excluded by integration/test_experiment_descriptions.py.
// Every other canonical experiment byte, all structures and the analysis stay exact.
std::string without_description(const std::string& text) {
    const std::array<std::string, 4> fields = {"_experiment_type.dimensionality",
                                               "_experiment_type.polarisation", "_instrument.name",
                                               "_instrument.facility"};
    std::istringstream input(text);
    std::string line, result;
    while (std::getline(input, line)) {
        std::istringstream row(line);
        std::string tag;
        row >> tag;
        if (std::find(fields.begin(), fields.end(), tag) == fields.end()) result += line + '\n';
    }
    return result;
}

std::map<std::string, std::string> scientific_blocks(const edi::Project& project) {
    std::map<std::string, std::string> result;
    for (const auto& structure : project.structures)
        result["structure/" + structure->name.value()] =
            edi::block_edi_text(project, edi::BlockKind::STRUCTURE, structure->name);
    for (const auto& experiment : project.experiments)
        result["experiment/" + experiment->name.value()] = without_description(
            edi::block_edi_text(project, edi::BlockKind::EXPERIMENT, experiment->name));
    result["analysis"] = edi::block_edi_text(project, edi::BlockKind::ANALYSIS);
    return result;
}

void converted_description(const edi::Project& project, bool declared) {
    REQUIRE_FALSE(project.experiments.empty());
    for (const auto& experiment : project.experiments) {
        const bool protected_bank = declared && experiment->name.value() == "bank";
        CHECK(experiment->experiment_type.dimensionality == "1d");
        CHECK(experiment->experiment_type.effective_dimensionality() == "1d");
        CHECK(experiment->experiment_type.polarisation == "unpolarised");
        CHECK(experiment->experiment_type.effective_polarisation() == "unpolarised");
        CHECK(experiment->instrument.name == (protected_bank ? "?" : "D20"));
        CHECK(experiment->instrument.facility ==
              (protected_bank ? "Existing named facility" : "Institut Laue–Langevin (ILL)"));
    }
}
}  // namespace

TEST_CASE("Example legacy descriptions convert once through save PROJECT reopen and second save") {
    ExampleMetadataDirectory directory;
    const auto source = copy_example_fixture(directory.path);
    bool declared = false;
    SUBCASE("omitted per-experiment fields receive the declared legacy conversion") {}
    SUBCASE("current experiment declarations including unknown instrument keep precedence") {
        declared = true;
        std::ofstream experiment(source / "experiments/bank.edi", std::ios::app);
        REQUIRE(experiment.is_open());
        experiment << "\n_experiment_type.dimensionality 1d\n"
                      "_experiment_type.polarisation unpolarised\n"
                      "_instrument.name ?\n"
                      "_instrument.facility \"Existing named facility\"\n";
    }
    const auto source_experiment = read_example_record(source / "experiments/bank.edi");
    const auto source_structure = read_example_record(source / "structures/phase.edi");
    const auto source_analysis = read_example_record(source / "analysis/analysis.edi");
    const auto baseline = edi::load_project(source.string());
    const auto science = scientific_blocks(baseline);
    const std::string extra[] = {
        "_metadata.facility       \"Institut Laue–Langevin (ILL)\"",
        "_metadata.instrument     D20",
        "_metadata.dimensionality 1D",
        "_metadata.purpose        refinement",
        "_metadata.polarisation   none",
    };
    {
        std::ofstream record(source / "project.edi", std::ios::app);
        REQUIRE(record.is_open());
        record << '\n';
        for (const auto& line : extra) record << line << '\n';
    }
    const auto legacy_record = read_example_record(source / "project.edi");
    std::vector<std::string> notices;
    auto project = edi::load_project(
        source.string(), [&](const std::string& notice) { notices.push_back(notice); });
    retired_notices(notices, 1);
    converted_description(project, declared);
    CHECK(scientific_blocks(project) == science);
    CHECK(read_example_record(source / "experiments/bank.edi") == source_experiment);
    CHECK(read_example_record(source / "structures/phase.edi") == source_structure);
    CHECK(read_example_record(source / "analysis/analysis.edi") == source_analysis);
    CHECK(read_example_record(source / "project.edi") == legacy_record);
    project.metadata.title = "Edited example title";
    edi::save_project(project, (directory.path / "saved").string());
    const auto first = read_example_record(directory.path / "saved/project.edi");
    CHECK_MESSAGE(first.find("Edited example title") != std::string::npos,
                  "The genuine title edit survives native save");
    no_retired_tags(first);
    const auto shown = edi::block_edi_text(project, edi::BlockKind::PROJECT);
    CHECK(shown.find("Edited example title") != std::string::npos);
    no_retired_tags(shown);
    notices.clear();
    auto reopened =
        edi::load_project((directory.path / "saved").string(),
                          [&](const std::string& notice) { notices.push_back(notice); });
    CHECK(reopened.metadata.title == "Edited example title");
    retired_notices(notices, 0);
    converted_description(reopened, declared);
    CHECK(scientific_blocks(reopened) == science);
    edi::save_project(reopened, (directory.path / "resaved").string());
    const auto second = read_example_record(directory.path / "resaved/project.edi");
    no_retired_tags(second);
    CHECK(second.find("Edited example title") != std::string::npos);
    notices.clear();
    const auto resaved =
        edi::load_project((directory.path / "resaved").string(),
                          [&](const std::string& notice) { notices.push_back(notice); });
    CHECK(resaved.metadata.title == "Edited example title");
    retired_notices(notices, 0);
    converted_description(resaved, declared);
    CHECK(scientific_blocks(resaved) == science);
}

TEST_CASE("Retired project polarisation unknown is refused rather than converted as none") {
    ExampleMetadataDirectory directory;
    const auto source = copy_example_fixture(directory.path);
    {
        std::ofstream record(source / "project.edi", std::ios::app);
        REQUIRE(record.is_open());
        record << "\n_metadata.polarisation ?\n";
    }
    CHECK_THROWS_WITH_AS(edi::load_project(source.string()),
                         doctest::Contains("_metadata.polarisation"), edi::IoError);
}
