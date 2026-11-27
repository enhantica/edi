#include <doctest/doctest.h>

#include <filesystem>
#include <fstream>
#include <iterator>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

#include "edi/edit.hpp"
#include "edi/io.hpp"
#include "edi/magnetic_cell.hpp"

namespace {
edi::Project candidate_project() {
    const auto path = std::filesystem::path(__FILE__).parent_path() /
                      "../../fixtures/magnetic_type_iv/gui/popup";
    auto project = edi::load_project(path.string());
    for (const auto& structure : project.structures)
        for (const auto& site : structure->atom_sites)
            site->wyckoff_letter = structure->name.value() == "parent" ? "c" : "a";
    return project;
}
std::shared_ptr<edi::PreparedMagneticCandidates> staged_three() {
    const auto path = std::filesystem::path(__FILE__).parent_path() /
                      "../../fixtures/magnetic_type_iv/pnma-d.edi";
    std::ifstream input(path);
    REQUIRE_MESSAGE(input.good(), "The independently authored magnetic child is committed");
    const auto child_model =
        edi::structure_from_edi_text({std::istreambuf_iterator<char>(input), {}});
    auto prepared = std::make_shared<edi::PreparedMagneticCandidates>();
    prepared->parent = "parent";
    for (int i = 0; i < 3; ++i) {
        const std::string name = "candidate_" + std::to_string(i);
        auto child = std::make_shared<edi::Structure>(child_model);
        child->name = name;
        prepared->structures.push_back(child);
        prepared->links.push_back({0, name, .9, i == 0});
        prepared->textures.push_back({0, name, .7, .13, true, true, {2, 1, 0}});
    }
    return prepared;
}
std::vector<std::string> candidate_snapshot(const edi::Project& project) {
    std::vector<std::string> out;
    for (const auto& structure : project.structures)
        out.push_back(
            edi::block_edi_text(project, edi::BlockKind::STRUCTURE, structure->name.value()));
    for (const auto& experiment : project.experiments)
        out.push_back(
            edi::block_edi_text(project, edi::BlockKind::EXPERIMENT, experiment->name.value()));
    return out;
}
}  // namespace

TEST_CASE("The candidate transaction accepts three independently valid staged rows") {
    auto project = candidate_project();
    const auto count = project.structures.size();
    auto prepared = staged_three();
    REQUIRE_MESSAGE(!prepared->links[1].enabled,
                    "The second staged candidate is disabled before the transaction");
    CHECK_NOTHROW_MESSAGE(edi::Edit::add_magnetic_candidates(project, prepared)(),
                          "A complete valid three-candidate transaction commits");
    CHECK_MESSAGE(project.structures.size() == count + 3,
                  "The positive control publishes all three candidate structures");
    const auto& links = project.experiments[0]->linked_structures;
    for (const auto& link : links) {
        if (link->structure_id.value() == "parent")
            CHECK_MESSAGE(!link->enabled.get(), "Adding candidates keeps the parent disabled");
        if (link->structure_id.value().starts_with("candidate_"))
            CHECK_MESSAGE(link->enabled.get() == (link->structure_id.value() == "candidate_0"),
                          "Only the first new candidate is enabled after the transaction");
    }
}

TEST_CASE("An invalid disabled second candidate row refuses the whole transaction") {
    auto project = candidate_project();
    const auto before = candidate_snapshot(project);
    auto prepared = staged_three();
    prepared->textures[1].axis = {1002, 1, 0};
    REQUIRE_MESSAGE(
        (prepared->textures[0].axis == std::array<int, 3>{2, 1, 0} &&
         prepared->textures[2].axis == std::array<int, 3>{2, 1, 0} && !prepared->links[1].enabled),
        "Only the disabled second row exceeds the declared texture-axis bound");
    CHECK_THROWS_AS_MESSAGE(edi::Edit::add_magnetic_candidates(project, prepared)(),
                            std::exception,
                            "The transaction validates the disabled second row before publishing");
    CHECK_MESSAGE(candidate_snapshot(project) == before,
                  "The disabled-row refusal preserves every structure, link and texture byte");
}
