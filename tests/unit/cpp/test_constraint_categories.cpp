#include <doctest/doctest.h>

#include <filesystem>
#include <string>

#include "edi/io.hpp"
#include "edi/parameter_walk.hpp"

TEST_CASE("Core dependent marks cover both Structure and Experiment fields") {
    const auto path = std::filesystem::path(__FILE__).parent_path().parent_path().parent_path() /
                      "fixtures/constraint_expressions/project";
    auto project = edi::load_project(path.string());
    project.calculate();
    bool structural = false;
    bool instrument = false;
    for (const auto& entry : edi::parameter_entries(project)) {
        if (entry.category == "atom_site" && entry.row_label == "B" && entry.name == "adp_iso") {
            structural = true;
            CHECK_MESSAGE(
                !entry.refinable,
                "A user-dependent structure field must be absent from the Analysis rows");
            CHECK_MESSAGE(entry.parameter->value == doctest::Approx(1.6),
                          "The Structure page must receive the implied core value");
        }
        if (entry.category == "instrument" && entry.name == "calib_twotheta_offset") {
            instrument = true;
            CHECK_MESSAGE(
                !entry.refinable,
                "A user-dependent Experiment field must have its free checkbox disabled");
            CHECK_MESSAGE(entry.parameter->value == doctest::Approx(.16),
                          "The Experiment page must receive the chained core value");
        }
    }
    CHECK_MESSAGE(structural,
                  "The core category walk must expose the declared structural dependent");
    CHECK_MESSAGE(instrument,
                  "The core category walk must expose the declared instrument dependent");
}

namespace {
template <class Project>
void check_empty_declarations(const Project& project) {
    if constexpr (requires {
                      project.aliases.empty();
                      project.constraints.empty();
                  }) {
        CHECK_MESSAGE(project.aliases.empty(), "A new project must contain no sample aliases");
        CHECK_MESSAGE(project.constraints.empty(),
                      "A new project must contain no sample constraints");
    } else {
        FAIL_CHECK(
            "The core project must own aliases and constraints before the GUI consumes them");
    }
}
}  // namespace

TEST_CASE("New core projects contain no GUI preview declarations") {
    const edi::Project project;
    check_empty_declarations(project);
}
