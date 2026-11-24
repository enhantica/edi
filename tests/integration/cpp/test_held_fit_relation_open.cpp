#include <doctest/doctest.h>

#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

#include "edi/io.hpp"
#include "edi/model.hpp"
#include "edi/project_archive.hpp"

namespace {
struct Scratch {
    std::filesystem::path path =
        std::filesystem::temp_directory_path() /
        ("edi-held-relations-" +
         std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    Scratch() { std::filesystem::create_directory(path); }
    ~Scratch() { std::filesystem::remove_all(path); }
};

bool names_broken_relation(const std::string& text) {
    return text.find("alias") != std::string::npos || text.find("constraint") != std::string::npos;
}
}  // namespace

TEST_CASE("A held fit opens for repair when aliases break in a folder or archive") {
    const auto source = std::filesystem::path(__FILE__).parent_path() /
                        "../../fixtures/constraint_expressions/project";
    const Scratch scratch;
    auto valid = edi::load_project(source.string());
    auto& seed = valid.structure().atom_sites[0]->adp_iso;
    seed.free = true;
    const auto fit = valid.fit();
    REQUIRE_MESSAGE(!fit.values.empty(), "The valid control produces a real fit with free seeds");
    const auto saved = scratch.path / "held";
    edi::save_project(valid, saved.string());
    const auto fitted = edi::load_project(saved.string());
    REQUIRE_MESSAGE(!fitted.fit_result.result_kind.empty(),
                    "The saved control retains an actual completed fit record");
    REQUIRE_MESSAGE(fitted.structure().atom_sites[0]->adp_iso.free.get(),
                    "The held fit retains the seed that requests dependent uncertainties");

    const auto analysis = saved / "analysis/analysis.edi";
    std::ifstream file(analysis);
    std::string declarations(std::istreambuf_iterator<char>{file}, {});
    file.close();
    const std::string alias = "a phase.atom_site.A.adp_iso";
    const auto row = declarations.find(alias);
    REQUIRE_MESSAGE(row != std::string::npos, "The valid fit saved its independent alias row");
    declarations.replace(row, alias.size(), "missing_seed phase.atom_site.A.adp_iso");
    std::ofstream(analysis) << declarations;

    const auto archive = scratch.path / "held.zip";
    edi::write_project_archive(saved.string(), archive.string());
    for (const auto& input : {saved, archive}) {
        CAPTURE(input.string());
        std::vector<std::string> warnings;
        auto opened = edi::load_project(input.string(), edi::ProjectLoadMode::Construction,
                                      [&](const std::string& text) { warnings.push_back(text); });
        CHECK_MESSAGE(std::any_of(warnings.begin(), warnings.end(), names_broken_relation),
                      "Opening the held project for repair reports the broken relation");
        CHECK_MESSAGE(opened.structure().atom_sites.size() == fitted.structure().atom_sites.size(),
                      "Repair-mode opening retains the scientific model");
        CHECK_MESSAGE(opened.fit_result.result_kind == fitted.fit_result.result_kind,
                      "Repair-mode opening retains the held fit record");
        CHECK_THROWS_MESSAGE(edi::load_project(input.string()),
                             "The complete loader refuses broken relations");
        CHECK_THROWS_MESSAGE(opened.calculate(),
                             "Calculation refuses the still-broken graph after opening for repair");
    }
}
