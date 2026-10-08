#include <doctest/doctest.h>

#include <stdexcept>
#include <vector>

#include "edi/edit.hpp"
#include "edi/io.hpp"

namespace {
edi::Project simulation_project() {
    edi::Project project;
    project.experiments.clear();
    project.structures.clear();
    edi::Structure structure;
    structure.name = "cosio";
    project.structures.push_back(std::make_shared<edi::Structure>(structure));
    return project;
}
}  // namespace

TEST_CASE("creating and undoing a simulation preserves prior experiments") {
    auto project = simulation_project();
    edi::Edit::create_experiment(project, edi::simulation_experiment("first", {}, "cosio"))();
    const auto* first = project.experiments[0].get();
    edi::Edit::create_experiment(project, edi::simulation_experiment("second", {}, "cosio"))();
    REQUIRE_MESSAGE(project.experiments.size() == 2, "Create experiment adds one simulation");
    CHECK_MESSAGE(project.experiments[0].get() == first,
                  "Create experiment preserves prior row identity");
    CHECK_MESSAGE(project.experiments[1]->calculation_only,
                  "A created experiment has no measured data");
    const auto* second = project.experiments[1].get();
    edi::Edit::erase_experiments(project, {second})();
    CHECK_MESSAGE(project.experiments.size() == 1, "Undo of creation removes exactly the new row");
    CHECK_MESSAGE(project.experiments[0].get() == first,
                  "Undo of creation keeps the prior row intact");
    CHECK_THROWS_AS_MESSAGE(
        edi::Edit::create_experiment(project, edi::simulation_experiment("first", {}, "cosio"))(),
        edi::IoError, "Duplicate creation refuses atomically");
    CHECK_MESSAGE(project.experiments.size() == 1, "Refused creation cannot add a row");
}

TEST_CASE("simulation type and range edits target only the selected experiment") {
    auto project = simulation_project();
    edi::Edit::create_experiment(project, edi::simulation_experiment("first", {}, "cosio"))();
    edi::Edit::create_experiment(project, edi::simulation_experiment("second", {}, "cosio"))();
    const auto* first = project.experiments[0].get();
    const auto before = *project.experiments[1];
    edi::ExperimentTypeTokens type;
    type.beam_mode = "time-of-flight";
    const auto replacement = edi::simulation_experiment("second", type, "cosio");
    edi::Edit::replace_experiment(project, *project.experiments[1], replacement)();
    CHECK_MESSAGE(project.experiments[0].get() == first,
                  "Type edits leave the unselected row intact");
    REQUIRE_MESSAGE(project.experiments[1]->data.has_value(),
                    "A TOF simulation has its default grid");
    CHECK_MESSAGE(project.experiments[1]->data->time_of_flight.get()->front() == 2000.0,
                  "The declared TOF default begins at 2000 microseconds");
    CHECK_MESSAGE(project.experiments[1]->data->time_of_flight.get()->back() == 20000.0,
                  "The declared TOF default ends at 20000 microseconds");
    edi::Edit::data_range(*project.experiments[1], 2400.0, 2412.0, 3.0)();
    const auto grid = project.experiments[1]->data->time_of_flight.get();
    REQUIRE_MESSAGE(grid.has_value(), "The edited TOF grid remains an axis");
    CHECK_MESSAGE((*grid == std::vector<double>{2400., 2403., 2406., 2409., 2412.}),
                  "Nontrivial range edits reach the selected simulation's data");
    edi::Edit::replace_experiment(project, *project.experiments[1], before)();
    CHECK_MESSAGE(
        project.experiments[1]->effective_beam_mode() == edi::BeamModeEnum::CONSTANT_WAVELENGTH,
        "Undo of the type edit restores the earlier beam mode");
    CHECK_MESSAGE(project.experiments[0].get() == first,
                  "Undo of a type edit preserves other rows");
}

TEST_CASE("measured experiments lock type and range while allowing simulation creation") {
    auto project = simulation_project();
    edi::Edit::create_experiment(project, edi::simulation_experiment("measured", {}, "cosio"))();
    auto& selected = *project.experiments[0];
    selected.calculation_only = false;
    const auto data = selected.data;
    const auto* identity = &selected;
    CHECK_THROWS_AS_MESSAGE(edi::Edit::data_range(selected, 17.0, 20.0, 0.5)(),
                            std::invalid_argument, "Measured data fixes its range");
    CHECK_THROWS_AS_MESSAGE(
        edi::Edit::replace_experiment(project, selected,
                                      edi::simulation_experiment("measured", {}, "cosio"))(),
        std::invalid_argument, "Measured data fixes its type");
    CHECK_NOTHROW_MESSAGE(
        edi::Edit::create_experiment(project, edi::simulation_experiment("extra", {}, "cosio"))(),
        "Mixed projects allow adding a simulation alongside measured data");
    CHECK_MESSAGE((project.experiments.size() == 2 && project.experiments[0].get() == identity),
                  "Type and range refusals plus creation preserve the measured row identity");
    CHECK_MESSAGE(selected.data->two_theta.get() == data->two_theta.get(),
                  "Every refusal preserves the measured axis");
}
