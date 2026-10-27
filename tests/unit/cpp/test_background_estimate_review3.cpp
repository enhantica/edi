#include <doctest/doctest.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <crysta/background_estimate.hpp>
#include <filesystem>
#include <iomanip>
#include <memory>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "edi/background_estimate.hpp"
#include "edi/io.hpp"
#include "edi/model.hpp"
#include "edi/selectors.hpp"
#include "project_save/rounding.hpp"

namespace {
namespace fs = std::filesystem;
struct Scratch {
    fs::path root = fs::temp_directory_path() /
                    ("edi-background-review3-" +
                     std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    Scratch() { fs::create_directories(root); }
    ~Scratch() {
        std::error_code ignored;
        fs::remove_all(root, ignored);
    }
};
edi::Project input(const std::string& kind, bool full_span = false) {
    auto p = edi::load_project((fs::path(__FILE__).parent_path().parent_path().parent_path() /
                                "fixtures/background_estimate/projects" / ("fitted-auto-" + kind))
                                   .string());
    // A short angular window and every sixteenth sample bound these lifecycle-only controls.
    const auto& old = *p.experiment().data;
    std::vector<double> x, y, sigma;
    for (std::size_t i = 0; i < old.axis().size() && (full_span || old.axis()[i] <= 70.0);
         i += 16) {
        x.push_back(old.axis()[i]);
        y.push_back(old.intensity_meas[i]);
        sigma.push_back(old.intensity_meas_su[i]);
    }
    edi::PdDataBase sampled;
    sampled.two_theta = x;
    sampled.intensity_meas = y;
    sampled.intensity_meas_su = sigma;
    p.experiment().data = sampled;
    return p;
}
std::vector<double> values(const edi::ExperimentBase& e) {
    std::vector<double> result;
    if (e.background_type == "line-segment")
        for (const auto& r : e.background) result.push_back(r->intensity.value.get());
    else
        for (const auto& r : e.background_terms) result.push_back(r->coef.value.get());
    return result;
}
struct State {
    std::string type;
    std::vector<double> values;
    std::optional<double> origin, low, high;
    std::optional<std::string> mode;
    std::uint64_t inputs, points;
    std::vector<std::string> ids;
    std::vector<double> positions_or_orders;
    std::vector<bool> free;
    bool operator==(const State&) const = default;
};
State state(const edi::ExperimentBase& e) {
    State result{e.background_type,
                 values(e),
                 e.background_origin,
                 e.background_x_min,
                 e.background_x_max,
                 e.background_estimate_mode,
                 e.background_estimate_inputs,
                 e.background_estimate_points,
                 {},
                 {},
                 {}};
    if (e.background_type == "line-segment") {
        for (const auto& r : e.background) {
            result.ids.push_back(r->id);
            result.positions_or_orders.push_back(r->position);
            result.free.push_back(r->intensity.free.get());
        }
    } else
        for (const auto& r : e.background_terms) {
            result.ids.push_back(r->id);
            result.positions_or_orders.push_back(r->order);
            result.free.push_back(r->coef.free.get());
        }
    return result;
}
std::string saved_difference(const State& expected, const State& actual) {
    if (expected == actual) return "";
    std::ostringstream out;
    out << std::setprecision(17) << " input digests " << expected.inputs << "/" << actual.inputs
        << " point digests " << expected.points << "/" << actual.points;
    for (std::size_t i = 0; i < std::min(expected.values.size(), actual.values.size()); ++i)
        if (expected.values[i] != actual.values[i])
            out << " value[" << i << "] " << expected.values[i] << "/" << actual.values[i];
    for (std::size_t i = 0;
         i < std::min(expected.positions_or_orders.size(), actual.positions_or_orders.size()); ++i)
        if (expected.positions_or_orders[i] != actual.positions_or_orders[i])
            out << " position[" << i << "] " << expected.positions_or_orders[i] << "/"
                << actual.positions_or_orders[i];
    return out.str();
}
State saved_state(State state) {
    for (double& value : state.values) value = saved_reference::six_digits(value);
    if (state.mode == "auto") {
        // The values above have an independent decimal oracle. The separate wire-checksum
        // invariant must now describe those written rows, rather than their old binary values.
        std::vector<crysta::BackgroundPointValues> points;
        for (std::size_t i = 0; i < state.values.size(); ++i)
            points.push_back(
                {state.ids[i], state.positions_or_orders[i], state.values[i], state.free[i]});
        state.points = crysta::background_points_digest(points);
    }
    return state;
}
void delegated(const std::string& kind, bool data) {
    auto p = input(kind);
    auto other = std::make_shared<edi::BraggPdExperiment>(p.experiment());
    other->name = "other";
    other->background_estimate_mode = "manual";
    p.experiments.push_back(other);
    p.calculate();
    auto& e = p.experiment();
    if (data) {
        auto y = e.data->intensity_meas.get();
        for (double& v : y) v += 125;
        e.data->intensity_meas = y;
    } else
        e.background_estimate_max_terms = 1;
    REQUIRE_MESSAGE(other->computed_current(),
                    "The delegated save witness must keep a genuinely current second bank");
    const auto before = state(e);
    Scratch scratch;
    REQUIRE_NOTHROW_MESSAGE(
        edi::save_project(p, (scratch.root / "saved").string()),
        "A due Auto series beside a current bank must save without incompatible row provenance");
    CHECK_MESSAGE(state(e) == before,
                  "Native delegated save must preserve the exact live host rows, constants, mode "
                  "and digests");
    auto loaded = edi::load_project((scratch.root / "saved").string());
    CHECK_MESSAGE(state(loaded.experiment()) == saved_state(before),
                  "Native delegated save must write the complete background state with six-digit "
                  "saved values"
                      << saved_difference(saved_state(before), state(loaded.experiment())));
    REQUIRE_NOTHROW_MESSAGE(
        loaded.calculate(),
        "A saved due series must reload and refresh without an unauthorized-edit refusal");
}
void typed_undo(const std::string& source, const std::string& target) {
    auto p = input(source);
    auto& e = p.experiment();
    edi::set_background_estimate_mode(e, "manual");
    const auto original = state(e);
    const auto captured = edi::capture_background(e);
    const auto options = edi::background_estimate_options(e);
    edi::apply_background_estimate(e, edi::estimate_background(e, options), options);
    edi::select_background_type(e, target);
    const auto before = state(e);
    bool refused = false;
    try {
        edi::restore_background(e, captured);
    } catch (const std::invalid_argument& error) {
        refused = true;
        const std::string reason = error.what();
        CHECK_MESSAGE(
            (reason.find("type") != std::string::npos ||
             reason.find("background") != std::string::npos),
            "An incompatible Estimate Undo refusal must clearly name its background type");
    }
    if (source == target)
        CHECK_MESSAGE(!refused,
                      "Same-type Estimate Undo must remain supported by the native helper");
    if (refused)
        CHECK_MESSAGE(state(e) == before, "An incompatible Estimate Undo refusal must be atomic");
    else
        CHECK_MESSAGE(
            state(e) == original,
            "Estimate Undo after a type change must restore the complete original typed state");
    REQUIRE_NOTHROW_MESSAGE(
        p.calculate(),
        "Admitted or atomically refused Estimate Undo must leave a calculable typed background");
    Scratch scratch;
    REQUIRE_NOTHROW_MESSAGE(
        edi::save_project(p, (scratch.root / "saved").string()),
        "A cross-type Estimate Undo must leave a saveable complete typed background");
    auto loaded = edi::load_project((scratch.root / "saved").string());
    CHECK_MESSAGE(state(loaded.experiment()) == saved_state(state(e)),
                  "Typed Estimate Undo retains every field with independently projected six-digit "
                  "saved values"
                      << saved_difference(saved_state(state(e)), state(loaded.experiment())));
}
void explicit_fit(const std::string& kind, bool joint, bool simulation, bool phases,
                  bool automatic = true, bool already_current = false) {
    auto p = input(kind);
    // The oracle is observed at provider construction; a single solver step is sufficient.
    p.minimizer_max_iterations = 1;
    p.experiment().background_estimate_use_model = "ignore";
    p.experiment().background_estimate_width = 1.0;
    edi::set_background_estimate_mode(p.experiment(),
                                      automatic && already_current ? "auto" : "manual");
    p.calculate();
    if (automatic && !already_current) edi::set_background_estimate_mode(p.experiment(), "auto");
    auto& e = p.experiment();
    for (auto* parameter : p.parameters()) parameter->free = false;
    p.structure().cell.length_a.free = true;
    auto supplied = *e.data;
    auto measured = supplied.intensity_meas.get();
    for (double& v : measured) v += 125;
    supplied.intensity_meas = measured;
    if (simulation) {
        e.data->intensity_meas = std::vector<double>{};
        e.data->intensity_meas_su = std::vector<double>{};
        e.calculation_only = true;
    } else if (!already_current) {
        if (kind == "line-segment")
            e.background_estimate_n_points = 11;
        else
            e.background_estimate_max_terms = 1;
    }
    if (phases) {
        auto structure = std::make_shared<edi::Structure>(p.structure());
        structure->name = "extra";
        p.structures.push_back(structure);
        auto link = std::make_shared<edi::LinkedStructure>(e.linked_structure());
        link->structure_id = "extra";
        e.linked_structures.push_back(link);
    }
    std::vector<edi::PdDataBase> patterns{supplied};
    if (joint) {
        auto other = std::make_shared<edi::BraggPdExperiment>(e);
        other->name = "other";
        p.experiments.push_back(other);
        auto other_pattern = supplied;
        auto y = other_pattern.intensity_meas.get();
        for (double& v : y) v += 57.5;
        other_pattern.intensity_meas = y;
        patterns.push_back(other_pattern);
        p.fitting_mode = "joint";
    }
    if (already_current)
        for (const auto& bank : p.experiments)
            REQUIRE_MESSAGE(!edi::background_estimate_due(*bank),
                            "The supplied-pattern case must start with current Auto host data and "
                            "unchanged settings");
    auto control = p;
    for (std::size_t bank = 0; bank < patterns.size(); ++bank) {
        control.experiments[bank]->data = patterns[bank];
        control.experiments[bank]->calculation_only = false;
    }
    edi::refresh_background_estimates(control);
    std::vector<std::vector<double>> expected;
    std::vector<State> backgrounds_before;
    std::vector<std::vector<std::vector<double>>> data_before;
    std::vector<bool> simulation_before;
    for (std::size_t bank = 0; bank < patterns.size(); ++bank) {
        expected.push_back(values(*control.experiments[bank]));
        const auto& b = *p.experiments[bank];
        if (automatic) {
            const auto old = values(b);
            bool differs = old.size() != expected.back().size();
            for (std::size_t i = 0; i < std::min(old.size(), expected.back().size()); ++i)
                differs = differs || std::abs(old[i] - expected.back()[i]) > 1e-5;
            REQUIRE_MESSAGE(
                differs,
                "Supplied measurements must require a genuinely different pre-fit Auto baseline");
            if (!simulation && !already_current)
                REQUIRE_MESSAGE(old.size() != expected.back().size(),
                                "The due-settings native fit must change the row layout before "
                                "provider construction");
        }
        backgrounds_before.push_back(state(b));
        data_before.push_back(
            {b.data->axis(), b.data->intensity_meas.get(), b.data->intensity_meas_su.get()});
        simulation_before.push_back(b.calculation_only);
    }
    std::vector<std::pair<double, bool>> parameters_before;
    for (const auto* parameter : p.parameters())
        parameters_before.emplace_back(parameter->value.get(), parameter->free.get());
    bool started = false, refused = false;
    edi::PreambleCallback on_start = [&](const auto&) {
        started = true;
        for (std::size_t bank = 0; bank < patterns.size(); ++bank) {
            CAPTURE(bank);
            const auto actual = values(*p.experiments[bank]);
            CHECK_MESSAGE(actual.size() == expected[bank].size(),
                          "Every explicit-data fit must refresh every Auto bank's row count "
                          "before building its provider");
            for (std::size_t i = 0; i < std::min(actual.size(), expected[bank].size()); ++i)
                CHECK_MESSAGE(std::abs(actual[i] - expected[bank][i]) <=
                                  1e-8 + 1e-11 * std::abs(expected[bank][i]),
                              "Every native provider must estimate each bank from its own "
                              "supplied measurements before solving");
        }
    };
    try {
        if (joint)
            p.fit_joint(patterns, {}, on_start);
        else
            p.fit(supplied.axis(), supplied.intensity_meas, supplied.intensity_meas_su, {},
                  on_start);
    } catch (const std::invalid_argument& error) {
        refused = true;
        const std::string reason = error.what();
        CHECK_MESSAGE(automatic,
                      "The native explicit-data Manual fit control must remain supported");
        CHECK_MESSAGE(!started,
                      "An admitted explicit-data fit must not refuse its own Auto baseline after "
                      "building a provider");
        CHECK_MESSAGE(
            (reason.find("auto") != std::string::npos || reason.find("Auto") != std::string::npos),
            "An explicit-data boundary declining Auto must name Auto as the unsupported reason");
        std::vector<std::pair<double, bool>> parameters_after;
        for (const auto* parameter : p.parameters())
            parameters_after.emplace_back(parameter->value.get(), parameter->free.get());
        CHECK_MESSAGE(parameters_after == parameters_before,
                      "An unsupported explicit-data refusal must preserve all parameter values "
                      "and free flags");
        for (std::size_t bank = 0; bank < patterns.size(); ++bank) {
            const auto& b = *p.experiments[bank];
            CHECK_MESSAGE(state(b) == backgrounds_before[bank],
                          "An unsupported explicit-data refusal must preserve every complete "
                          "typed background and digest");
            CHECK_MESSAGE(b.data->axis() == data_before[bank][0],
                          "An unsupported explicit-data refusal must preserve every host grid");
            CHECK_MESSAGE(
                b.data->intensity_meas.get() == data_before[bank][1],
                "An unsupported explicit-data refusal must preserve every host measured column");
            CHECK_MESSAGE(b.data->intensity_meas_su.get() == data_before[bank][2],
                          "An unsupported explicit-data refusal must preserve every host "
                          "uncertainty column");
            CHECK_MESSAGE(b.calculation_only == simulation_before[bank],
                          "An unsupported explicit-data refusal must preserve all "
                          "calculation-only declarations");
        }
    }
    CHECK_MESSAGE((started || refused),
                  "The direct native overload must reach its provider or clearly refuse "
                  "unsupported Auto atomically");
}
void type_transition(const std::string& source, const std::string& target) {
    auto p = input(source);
    p.calculate();
    edi::select_background_type(p.experiment(), target);
    REQUIRE_NOTHROW_MESSAGE(p.calculate(),
                            "A supported native type selection must establish a valid Auto "
                            "baseline without Manual recovery");
    CHECK_MESSAGE(p.experiment().background_type == target,
                  "Native type refresh must retain its selected type");
    CHECK_MESSAGE(edi::background_estimate_mode(p.experiment()) == "auto",
                  "A native type transition must retain Auto mode");
    CHECK_MESSAGE(
        !values(p.experiment()).empty(),
        "Native automatic type selection must estimate a nonempty destination background");
}
void changed_basis(const std::string& kind, int field) {
    auto p = input(kind, true);
    p.experiment().background_estimate_use_model = "ignore";
    p.calculate();
    auto control = p;
    const auto change = [&](auto& e) {
        if (field == 0)
            e.background_origin = 105.25;
        else if (field == 1)
            e.background_x_min = 3.375;
        else
            e.background_x_max = 160.625;
    };
    change(p.experiment());
    change(control.experiment());
    edi::set_background_estimate_mode(control.experiment(), "manual");
    const auto options = edi::background_estimate_options(control.experiment());
    edi::apply_background_estimate(
        control.experiment(), edi::estimate_background(control.experiment(), options), options);
    const auto expected = values(control.experiment());
    const auto original = values(p.experiment());
    bool differs = original.size() != expected.size();
    for (std::size_t i = 0; i < std::min(original.size(), expected.size()); ++i)
        differs = differs || std::abs(original[i] - expected[i]) > 1e-5;
    REQUIRE_MESSAGE(
        differs, "The native basis stimulus must be nonconstant and require changed coefficients");
    p.calculate();
    const auto actual = values(p.experiment());
    REQUIRE_MESSAGE(actual.size() == expected.size(),
                    "The native basis refresh must obey its saved term cap");
    for (std::size_t i = 0; i < actual.size(); ++i)
        CHECK_MESSAGE(std::abs(actual[i] - expected[i]) <= 1e-8 + 1e-11 * std::abs(expected[i]),
                      "Native automatic provenance must include the declared origin and domain");
}
}  // namespace

TEST_CASE("Auto native delegated series save polynomial settings") {
    delegated("polynomial", false);
}

TEST_CASE("Auto native delegated series save polynomial data") { delegated("polynomial", true); }

TEST_CASE("Auto native delegated series save chebyshev settings") {
    delegated("chebyshev", false);
}

TEST_CASE("Auto native delegated series save chebyshev data") { delegated("chebyshev", true); }

TEST_CASE("Auto native typed Estimate Undo line-segment to polynomial") {
    typed_undo("line-segment", "polynomial");
}

TEST_CASE("Auto native typed Estimate Undo line-segment to chebyshev") {
    typed_undo("line-segment", "chebyshev");
}

TEST_CASE("Auto native typed Estimate Undo polynomial to line-segment") {
    typed_undo("polynomial", "line-segment");
}

TEST_CASE("Auto native typed Estimate Undo polynomial to chebyshev") {
    typed_undo("polynomial", "chebyshev");
}

TEST_CASE("Auto native typed Estimate Undo chebyshev to line-segment") {
    typed_undo("chebyshev", "line-segment");
}

TEST_CASE("Auto native typed Estimate Undo chebyshev to polynomial") {
    typed_undo("chebyshev", "polynomial");
}

TEST_CASE("Auto native explicit data fit line-segment single measured") {
    explicit_fit("line-segment", false, false, false);
}

TEST_CASE("Auto native explicit data fit line-segment single simulation") {
    explicit_fit("line-segment", false, true, false);
}

TEST_CASE("Auto native explicit data fit line-segment single phase-sum") {
    explicit_fit("line-segment", false, false, true);
}

TEST_CASE("Auto native explicit data fit line-segment joint measured") {
    explicit_fit("line-segment", true, false, false);
}

TEST_CASE("Auto native explicit data fit line-segment joint simulation") {
    explicit_fit("line-segment", true, true, false);
}

TEST_CASE("Auto native explicit data fit line-segment joint phase-sum") {
    explicit_fit("line-segment", true, false, true);
}

TEST_CASE("Auto native explicit data fit polynomial single measured") {
    explicit_fit("polynomial", false, false, false);
}

TEST_CASE("Auto native explicit data fit polynomial single simulation") {
    explicit_fit("polynomial", false, true, false);
}

TEST_CASE("Auto native explicit data fit polynomial single phase-sum") {
    explicit_fit("polynomial", false, false, true);
}

TEST_CASE("Auto native explicit data fit polynomial joint measured") {
    explicit_fit("polynomial", true, false, false);
}

TEST_CASE("Auto native explicit data fit polynomial joint simulation") {
    explicit_fit("polynomial", true, true, false);
}

TEST_CASE("Auto native explicit data fit polynomial joint phase-sum") {
    explicit_fit("polynomial", true, false, true);
}

TEST_CASE("Auto native explicit data fit chebyshev single measured") {
    explicit_fit("chebyshev", false, false, false);
}

TEST_CASE("Auto native explicit data fit chebyshev single simulation") {
    explicit_fit("chebyshev", false, true, false);
}

TEST_CASE("Auto native explicit data fit chebyshev single phase-sum") {
    explicit_fit("chebyshev", false, false, true);
}

TEST_CASE("Auto native explicit data fit chebyshev joint measured") {
    explicit_fit("chebyshev", true, false, false);
}

TEST_CASE("Auto native explicit data fit chebyshev joint simulation") {
    explicit_fit("chebyshev", true, true, false);
}

TEST_CASE("Auto native explicit data fit chebyshev joint phase-sum") {
    explicit_fit("chebyshev", true, false, true);
}

TEST_CASE("Auto native type transition line-segment to polynomial") {
    type_transition("line-segment", "polynomial");
}

TEST_CASE("Auto native type transition line-segment to chebyshev") {
    type_transition("line-segment", "chebyshev");
}

TEST_CASE("Auto native type transition polynomial to line-segment") {
    type_transition("polynomial", "line-segment");
}

TEST_CASE("Auto native type transition polynomial to chebyshev") {
    type_transition("polynomial", "chebyshev");
}

TEST_CASE("Auto native type transition chebyshev to line-segment") {
    type_transition("chebyshev", "line-segment");
}

TEST_CASE("Auto native type transition chebyshev to polynomial") {
    type_transition("chebyshev", "polynomial");
}

TEST_CASE("Auto native basis dependency polynomial field0") { changed_basis("polynomial", 0); }

TEST_CASE("Auto native basis dependency chebyshev field1") { changed_basis("chebyshev", 1); }

TEST_CASE("Auto native basis dependency chebyshev field2") { changed_basis("chebyshev", 2); }

TEST_CASE("Manual native same type Estimate Undo line-segment") {
    typed_undo("line-segment", "line-segment");
}

TEST_CASE("Manual native explicit data fit line-segment single") {
    explicit_fit("line-segment", false, false, false, false);
}

TEST_CASE("Manual native explicit data fit line-segment joint") {
    explicit_fit("line-segment", true, false, false, false);
}

TEST_CASE("Manual native same type Estimate Undo polynomial") {
    typed_undo("polynomial", "polynomial");
}

TEST_CASE("Manual native explicit data fit polynomial single") {
    explicit_fit("polynomial", false, false, false, false);
}

TEST_CASE("Manual native explicit data fit polynomial joint") {
    explicit_fit("polynomial", true, false, false, false);
}

TEST_CASE("Manual native same type Estimate Undo chebyshev") {
    typed_undo("chebyshev", "chebyshev");
}

TEST_CASE("Manual native explicit data fit chebyshev single") {
    explicit_fit("chebyshev", false, false, false, false);
}

TEST_CASE("Manual native explicit data fit chebyshev joint") {
    explicit_fit("chebyshev", true, false, false, false);
}

TEST_CASE("Auto native delegated point save settings") { delegated("line-segment", false); }

TEST_CASE("Auto native delegated point save data") { delegated("line-segment", true); }

TEST_CASE("Auto native explicit data fit line-segment single current supplied pattern") {
    explicit_fit("line-segment", false, false, false, true, true);
}

TEST_CASE("Auto native explicit data fit line-segment joint current supplied pattern") {
    explicit_fit("line-segment", true, false, false, true, true);
}

TEST_CASE("Auto native explicit data fit polynomial single current supplied pattern") {
    explicit_fit("polynomial", false, false, false, true, true);
}

TEST_CASE("Auto native explicit data fit polynomial joint current supplied pattern") {
    explicit_fit("polynomial", true, false, false, true, true);
}

TEST_CASE("Auto native explicit data fit chebyshev single current supplied pattern") {
    explicit_fit("chebyshev", false, false, false, true, true);
}

TEST_CASE("Auto native explicit data fit chebyshev joint current supplied pattern") {
    explicit_fit("chebyshev", true, false, false, true, true);
}
