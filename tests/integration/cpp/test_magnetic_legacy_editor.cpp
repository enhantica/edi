#include <doctest/doctest.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <iterator>

#include "../../fixtures/magnetic_type_iv/legacy/observe.hpp"
namespace {
void legacy_editor_pin(const std::string& kind) {
    const auto root =
        std::filesystem::path(__FILE__).parent_path() / "../../fixtures/magnetic_type_iv/legacy";
    const auto scratch =
        std::filesystem::temp_directory_path() /
        ("magnetic-legacy-" + kind +
         std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    const auto actual = legacy_magnetic_editor::observe(root / kind, scratch);
    std::filesystem::remove_all(scratch);
    std::ifstream file(root / (kind + ".pin"));
    REQUIRE_MESSAGE(file.good(), "The original edi baseline editor regression pin is committed");
    const std::string expected(std::istreambuf_iterator<char>(file), {});
    CHECK_MESSAGE(actual == expected,
                  "Regression pins preserve non-table legacy load, new atom, FullProf export and "
                  "reimport bytes");
}
}  // namespace
TEST_CASE("Regression pin preserves type I native and FullProf editor paths") {
    legacy_editor_pin("I");
}
TEST_CASE("Regression pin preserves type III native and FullProf editor paths") {
    legacy_editor_pin("III");
}
