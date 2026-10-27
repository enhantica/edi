#include <doctest/doctest.h>

#include <filesystem>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "edi/assistant_limits.hpp"
#include "edi/background_estimate.hpp"
#include "edi/edit.hpp"
#include "edi/io.hpp"

namespace {
edi::Project point_project(const std::string& mode) {
    const auto root = std::filesystem::path(__FILE__).parent_path().parent_path().parent_path();
    auto project = edi::load_project(
        (root / "fixtures/background_estimate/projects/fitted-auto-line-segment").string());
    edi::set_background_estimate_mode(project.experiment(), mode);
    return project;
}

struct PointState {
    const edi::LineSegment* identity;
    std::string id;
    double position, intensity;
    bool free;
    std::optional<double> uncertainty, start_value, start_uncertainty;
    bool operator==(const PointState&) const = default;
};
struct BackgroundState {
    std::vector<PointState> rows;
    std::string mode;
    std::uint64_t inputs, points;
    const edi::PdDataBase* data;
    bool operator==(const BackgroundState&) const = default;
};
BackgroundState state(const edi::ExperimentBase& experiment) {
    BackgroundState result{{}, edi::background_estimate_mode(experiment),
                           experiment.background_estimate_inputs, experiment.background_estimate_points,
                           experiment.data ? &*experiment.data : nullptr};
    for (const auto& row : experiment.background)
        result.rows.push_back({row.get(), row->id.value(), row->position.get(),
            row->intensity.value.get(), row->intensity.free.get(), row->intensity.uncertainty.get(),
            row->intensity.start_value.get(), row->intensity.start_uncertainty.get()});
    return result;
}

edi::BackgroundPointInput request(edi::ExperimentBase& experiment,
                                 edi::BackgroundPointInput::Action action) {
    REQUIRE(experiment.background.size() >= 3);
    edi::BackgroundPointInput result;
    result.action = action;
    const auto& middle = *experiment.background[experiment.background.size() / 2];
    result.id = middle.id.value();
    result.position = middle.position.get();
    result.intensity = middle.intensity.value.get() + 0.375;
    result.free = !middle.intensity.free.get();
    if (action == edi::BackgroundPointInput::Action::Add) {
        result.id = "independent_added_point";
        result.position = (experiment.background[0]->position.get() +
                           experiment.background[1]->position.get()) / 2;
    }
    return result;
}

std::shared_ptr<edi::BackgroundPointChange> prepare(edi::Project& project,
                                                  const edi::BackgroundPointInput& input) {
    auto& experiment = project.experiment();
    REQUIRE(experiment.data.has_value());
    return edi::prepare_background_point(project, experiment, input,
        experiment.background.size() + 1, edi::assistant::Limits::id_bytes,
        experiment.data->axis().size(), project.aliases.size(), true);
}
}

TEST_CASE("E11 native background structural preparation respects automatic ownership") {
    for (const auto action : {edi::BackgroundPointInput::Action::Add,
                              edi::BackgroundPointInput::Action::Update,
                              edi::BackgroundPointInput::Action::Remove}) {
        CAPTURE(static_cast<int>(action));
        auto project = point_project("auto");
        const auto input = request(project.experiment(), action);
        const auto before = state(project.experiment());
        CHECK_THROWS(prepare(project, input));
        CHECK(state(project.experiment()) == before);
    }
}

TEST_CASE("E11 native background structural execution rechecks a changed automatic owner") {
    for (const auto action : {edi::BackgroundPointInput::Action::Add,
                              edi::BackgroundPointInput::Action::Update,
                              edi::BackgroundPointInput::Action::Remove}) {
        CAPTURE(static_cast<int>(action));
        auto project = point_project("manual");
        const auto input = request(project.experiment(), action);
        auto prepared = prepare(project, input);
        const auto edit = edi::Edit::background_point(project, prepared);
        edi::set_background_estimate_mode(project.experiment(), "auto");
        const auto before = state(project.experiment());
        CHECK_THROWS(edit());
        CHECK_FALSE(prepared->committed);
        CHECK(state(project.experiment()) == before);
    }
}

TEST_CASE("E11 native manual background structural operations retain exact ordinary Undo") {
    for (const auto action : {edi::BackgroundPointInput::Action::Add,
                              edi::BackgroundPointInput::Action::Update,
                              edi::BackgroundPointInput::Action::Remove}) {
        CAPTURE(static_cast<int>(action));
        auto project = point_project("manual");
        const auto input = request(project.experiment(), action);
        const auto before = state(project.experiment());
        auto prepared = prepare(project, input);
        REQUIRE_NOTHROW(edi::Edit::background_point(project, prepared)());
        CHECK(prepared->committed);
        CHECK_FALSE(state(project.experiment()) == before);
        CHECK(edi::background_estimate_mode(project.experiment()) == "manual");
        REQUIRE_NOTHROW(edi::Edit::background_point(project, prepared, true)());
        CHECK(state(project.experiment()) == before);
    }
}
