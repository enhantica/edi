#include <doctest/doctest.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>

#include "edi/io.hpp"

namespace {
std::string read_relation_text(const std::filesystem::path& path) {
    std::ifstream input(path);
    std::ostringstream text;
    text << input.rdbuf();
    return text.str();
}
struct RelationTextDirectory {
    std::filesystem::path path =
        std::filesystem::temp_directory_path() /
        ("relation-text-" +
         std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    ~RelationTextDirectory() { std::filesystem::remove_all(path); }
};
}  // namespace

TEST_CASE("Saved analysis and shown block text retain enabled and disabled relation loops") {
    RelationTextDirectory directory;
    std::filesystem::create_directories(directory.path);
    const auto fixture =
        std::filesystem::path(__FILE__).parent_path().parent_path().parent_path() /
        "fixtures/constraint_expressions/project";
    std::filesystem::copy(fixture, directory.path / "input",
                          std::filesystem::copy_options::recursive);
    const auto analysis = directory.path / "input/analysis/analysis.edi";
    auto text = read_relation_text(analysis);
    const auto column = text.find("_constraint.expression\n");
    REQUIRE_MESSAGE(column != std::string::npos,
                    "The saved-text witness must declare its expression column");
    text.insert(column + std::string("_constraint.expression\n").size(), "_constraint.enabled\n");
    const auto first = text.find("\"c = b/10\"");
    text.insert(first + std::string("\"c = b/10\"").size(), " false");
    const auto second = text.find("\"b = 2*a + 1\"");
    text.insert(second + std::string("\"b = 2*a + 1\"").size(), " true");
    std::ofstream(analysis) << text;
    auto project = edi::load_project((directory.path / "input").string());
    edi::save_project(project, (directory.path / "first").string());
    const auto saved = read_relation_text(directory.path / "first/analysis/analysis.edi");
    CHECK_MESSAGE(saved.find("_alias.parameter_unique_name") != std::string::npos,
                  "Saving must not silently discard aliases read from the project");
    CHECK_MESSAGE(saved.find("_constraint.expression") != std::string::npos,
                  "Saving must not silently discard active or disabled constraints");
    CHECK_MESSAGE(saved.find("_constraint.enabled") != std::string::npos,
                  "The canonical save must retain its mixed enabled states");
    CHECK_MESSAGE(saved.find("false") != std::string::npos,
                  "The disabled state must survive in the canonical relation loop");
    CHECK_MESSAGE(edi::block_edi_text(project, edi::BlockKind::ANALYSIS) == saved,
                  "Shown Analysis block text must equal the canonical saved file bytes");
    bool shown = false;
    for (const auto& [name, body] : edi::project_edi_files(project)) {
        if (name == "analysis/analysis.edi") {
            shown = true;
            CHECK_MESSAGE(body == saved,
                          "The app saved-files source must retain the same analysis loops");
        }
    }
    CHECK_MESSAGE(shown, "The app text source must contain its analysis block");
    auto reopened = edi::load_project((directory.path / "first").string());
    edi::save_project(reopened, (directory.path / "second").string());
    CHECK_MESSAGE(
        read_relation_text(directory.path / "second/analysis/analysis.edi") == saved,
        "Open save reopen save must preserve both canonical relation loops byte for byte");
}
