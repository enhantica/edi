#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <map>
#include <optional>
#include <set>
#include <string>
#include <tuple>
#include <vector>

#include "assistant_parameter_edits.hpp"
#include "edi/assistant.hpp"
#include "edi/background_estimate.hpp"
#include "edi/edit.hpp"
#include "edi/io.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/selectors.hpp"
#include "json.hpp"

namespace {
using J = edi::json::Value;
using A = edi::json::Array;
using O = edi::json::Object;
namespace fs = std::filesystem;

fs::path repo() {
    return fs::path(__FILE__).parent_path().parent_path().parent_path().parent_path();
}

edi::Project background_project(const std::string& kind, const std::string& mode) {
    auto project = edi::load_project(
        (repo() / "tests/fixtures/background_estimate/projects" / ("fitted-auto-" + kind)).string());
    edi::set_background_estimate_mode(project.experiment(), mode);
    return project;
}

using NumericState = std::vector<std::tuple<std::string, double, bool, std::optional<double>,
                                          std::optional<double>, std::optional<double>>>;
NumericState numeric_state(edi::Project& project) {
    NumericState result;
    for (const auto& slot : edi::named_slots(project)) {
        const auto& p = *slot.parameter;
        result.emplace_back(slot.unique_name, p.value.get(), p.free.get(), p.uncertainty.get(),
                            p.start_value.get(), p.start_uncertainty.get());
    }
    return result;
}

struct Target {
    edi::Parameter* parameter;
    std::string path, unique;
};
Target target(edi::Project& project, edi::Parameter& parameter) {
    Target result{&parameter, {}, {}};
    for (const auto& entry : edi::parameter_entries(project))
        if (entry.parameter == &parameter) result.path = entry.path;
    for (const auto& slot : edi::named_slots(project))
        if (slot.parameter == &parameter) result.unique = slot.unique_name;
    REQUIRE_FALSE(result.path.empty());
    REQUIRE_FALSE(result.unique.empty());
    return result;
}
Target background_target(edi::Project& project) {
    auto& experiment = project.experiment();
    if (experiment.background_type == "line-segment") {
        REQUIRE_FALSE(experiment.background.empty());
        return target(project, experiment.background[0]->intensity);
    }
    REQUIRE_FALSE(experiment.background_terms.empty());
    return target(project, experiment.background_terms[0]->coef);
}

struct ControllerHost {
    std::vector<J> requests;
    unsigned applies = 0;
    edi::work::Worker worker{[](edi::work::Delivery delivery) { delivery(); }};
    edi::assistant::Controller controller;

    explicit ControllerHost(edi::Project& project)
        : controller(worker, edi::assistant::Hooks{
              [](const std::string&) {},
              [&](const std::string& request) { requests.push_back(edi::json::parse(request)); },
              [&](const edi::Edit& edit, bool) {
                  try {
                      edit();
                      ++applies;
                      return std::string{};
                  } catch (const std::exception& error) {
                      return std::string(error.what());
                  }
              },
              [] { return std::uint64_t{100}; }, {}}) {
        REQUIRE(controller.attach(&project, "independent-dev-owner").ok);
    }

    edi::assistant::Reply tool(const std::string& name, J arguments,
                               const std::string& plan = {}) {
        REQUIRE_FALSE(requests.empty());
        const auto& request = requests.back();
        const auto version = controller.revision();
        O event{{"schema", "edi.assistant/1"}, {"type", "tool_call"},
                {"connection_id", "independent-connection"},
                {"turn_id", request.at("turn_id")}, {"request_id", request.at("request_id")},
                {"call_id", "independent-call-" + std::to_string(++calls)}, {"name", name},
                {"project_id", version.project_id}, {"revision", std::to_string(version.revision)},
                {"arguments", std::move(arguments)}};
        if (!plan.empty()) event.emplace_back("plan_id", plan);
        return controller.provider_event(edi::json::write(event));
    }

    std::string approve(const std::vector<std::string>& paths) {
        const J connection = O{{"schema", "edi.assistant/1"}, {"type", "connection"},
            {"connection_id", "independent-connection"}, {"status", "ready"},
            {"capabilities", A{O{{"id", "gpt-6.1-sol"}, {"display_name", "Independent fixture"},
                {"efforts", A{"high"}}, {"attachment_types", A{}}}}}};
        REQUIRE(controller.provider_event(edi::json::write(connection)).ok);
        REQUIRE(controller.user_command(edi::json::write(O{{"schema", "edi.assistant/1"},
            {"type", "message"}, {"text", "Change only the explicitly named native values"},
            {"connection_id", "independent-connection"}, {"model", "gpt-6.1-sol"},
            {"effort", "high"}})).ok);
        A scope;
        for (const auto& path : paths) scope.emplace_back(path);
        auto proposed = tool("propose_plan", O{{"summary", "Independent finite edit scope"},
            {"groups", A{O{{"id", "values"}, {"paths", scope}}}},
            {"budget", O{{"max_trials", 1}, {"max_iterations", 1}, {"max_elapsed_ms", 1000}}},
            {"objective", O{{"absolute_tolerance", 0.0}, {"relative_tolerance", 0.0}}}});
        REQUIRE(proposed.ok);
        const auto id = edi::json::parse(proposed.value).at("plan_id").string("plan_id");
        const auto version = controller.revision();
        REQUIRE(controller.user_command(edi::json::write(O{{"schema", "edi.assistant/1"},
            {"type", "approve_plan"}, {"plan_id", id}, {"project_id", version.project_id},
            {"revision", std::to_string(version.revision)}})).ok);
        return id;
    }

   private:
    unsigned calls = 0;
};
}

TEST_CASE("E11 dev auto background rejects complete shared mixed value batches before writes") {
    for (const std::string kind : {"line-segment", "polynomial", "chebyshev"}) {
        CAPTURE(kind);
        auto project = background_project(kind, "auto");
        auto unrelated = target(project, project.structure().cell.length_a);
        auto owned = background_target(project);
        const auto before = numeric_state(project);
        bool refused = false;
        try {
            auto edit = edi::assistant::detail::prepare_parameter_edit<double>(project,
                {{unrelated.path, unrelated.parameter->value.get() + 0.03125},
                 {owned.path, owned.parameter->value.get() + 1.0}});
            edit();
        } catch (const std::exception&) {
            refused = true;
        }
        CHECK(refused);
        CHECK(numeric_state(project) == before);
        CHECK(edi::background_estimate_mode(project.experiment()) == "auto");
    }
}

TEST_CASE("E11 dev background batch validates ownership again at actual Edit execution") {
    for (const std::string kind : {"line-segment", "polynomial", "chebyshev"}) {
        CAPTURE(kind);
        auto project = background_project(kind, "manual");
        auto unrelated = target(project, project.structure().cell.length_a);
        auto owned = background_target(project);
        auto prepared = edi::assistant::detail::prepare_parameter_edit<double>(project,
            {{unrelated.path, unrelated.parameter->value.get() + 0.03125},
             {owned.path, owned.parameter->value.get() + 1.0}});
        edi::set_background_estimate_mode(project.experiment(), "auto");
        const auto before = numeric_state(project);
        CHECK_THROWS(prepared());
        CHECK(numeric_state(project) == before);
        CHECK_THROWS(edi::Edit::parameter_values(project,
            {{unrelated.unique, unrelated.parameter->value.get() + 0.03125},
             {owned.unique, owned.parameter->value.get() + 1.0}})());
        CHECK(numeric_state(project) == before);
    }
}

TEST_CASE("E11 dev manual background values and permitted automatic free flags remain editable") {
    for (const std::string kind : {"line-segment", "polynomial", "chebyshev"}) {
        CAPTURE(kind);
        auto project = background_project(kind, "manual");
        auto unrelated = target(project, project.structure().cell.length_a);
        auto owned = background_target(project);
        const double next_unrelated = unrelated.parameter->value.get() + 0.03125;
        const double next_owned = owned.parameter->value.get() + 1.0;
        CHECK_NOTHROW(edi::assistant::detail::prepare_parameter_edit<double>(project,
            {{unrelated.path, next_unrelated}, {owned.path, next_owned}})());
        CHECK(unrelated.parameter->value.get() == next_unrelated);
        CHECK(owned.parameter->value.get() == next_owned);
        auto automatic = background_project(kind, "auto");
        auto flag = background_target(automatic);
        const double before_value = flag.parameter->value.get();
        const bool before_free = flag.parameter->free.get();
        CHECK_NOTHROW(edi::assistant::detail::prepare_parameter_edit<bool>(automatic,
            {{flag.path, !before_free}})());
        CHECK(flag.parameter->free.get() != before_free);
        CHECK(flag.parameter->value.get() == before_value);
        CHECK(edi::background_estimate_mode(automatic.experiment()) == "auto");
    }
}

TEST_CASE("E11 dev restricted Controller preserves mixed batches rejected by native background ownership") {
    for (const std::string kind : {"line-segment", "polynomial", "chebyshev"}) {
        CAPTURE(kind);
        auto project = background_project(kind, "auto");
        auto unrelated = target(project, project.structure().cell.length_a);
        auto owned = background_target(project);
        ControllerHost host(project);
        const auto plan = host.approve({unrelated.path, owned.path});
        const auto before = numeric_state(project);
        const auto result = host.tool("set_parameters", O{{"values", A{
            O{{"path", unrelated.path}, {"value", unrelated.parameter->value.get() + 0.03125}},
            O{{"path", owned.path}, {"value", owned.parameter->value.get() + 1.0}}}}}, plan);
        CHECK_FALSE(result.ok);
        CHECK(host.applies == 0);
        CHECK(numeric_state(project) == before);
        CHECK(host.controller.revision().revision == 0);
    }
}

TEST_CASE("E11 dev context preserves actual published CW and TOF single crystal observations") {
    for (const std::string name : {"sc-neut-cwl_tb2ti2o7-heidi_basic",
                                    "sc-neut-tof_taurine-unknown_basic"}) {
        SUBCASE(name.c_str()) {
        CAPTURE(name);
        auto project = edi::load_project((repo() / "docs/user/cli" / name / "project").string());
        REQUIRE_FALSE(project.experiments.empty());
        ControllerHost host(project);
        const auto context = edi::json::parse(host.controller.context());
        REQUIRE(context.get("error").is_null());
        const auto& rows = context.at("datasets").array("datasets");
        REQUIRE(rows.size() == project.experiments.size());
        for (std::size_t index = 0; index < rows.size(); ++index) {
            const auto& experiment = *project.experiments[index];
            REQUIRE(experiment.reflections.has_value());
            const auto& native = *experiment.reflections;
            REQUIRE(native.rectangular());
            REQUIRE(native.size() > 0);
            const auto& row = rows[index];
            CHECK(row.at("sample_form").string("sample_form") == "single crystal");
            CHECK(row.at("data_status").string("data_status") == "present");
            const auto& axis = row.at("axis");
            CHECK(axis.at("kind").string("kind") == "miller_indices");
            CHECK(axis.at("unit").string("unit") == "dimensionless");
            CHECK(axis.at("count").number("count") == native.index_h.size());
            CHECK(axis.at("min").is_null());
            CHECK(axis.at("max").is_null());
            const auto& observations = row.at("observations");
            CHECK(observations.at("intensity_count").number("count") == native.intensity_meas.size());
            CHECK(observations.at("sigma_count").number("count") == native.intensity_meas_su.size());
            CHECK(observations.at("weighting").string("weighting") == "measured_standard_uncertainty");
            for (const std::string field : {"peak_profile_options", "absorption_type_options"})
                CHECK((row.get(field).is_null() || row.at(field).array("options").empty()));
            CHECK((row.get("background").is_null() ||
                   row.at("background").get("type").is_null()));
        }
        }
    }
}

TEST_CASE("E11 dev context retains manual and automatic point and series background metadata") {
    for (const std::string kind : {"line-segment", "polynomial", "chebyshev"}) {
        for (const std::string mode : {"manual", "auto"}) {
            const auto case_id = kind + "/" + mode;
            SUBCASE(case_id.c_str()) {
            CAPTURE(kind);
            CAPTURE(mode);
            auto project = background_project(kind, mode);
            const auto& experiment = project.experiment();
            const auto native = edi::background_estimate_options(experiment);
            ControllerHost host(project);
            const auto context = edi::json::parse(host.controller.context());
            REQUIRE(context.get("error").is_null());
            const auto& row = context.at("datasets").array("datasets")[0];
            CHECK(row.at("sample_form").string("sample_form") == "powder");
            const auto& background = row.at("background");
            CHECK(background.at("type").string("type") == kind);
            const auto& estimate = background.at("estimate");
            CHECK(estimate.at("mode").string("mode") == mode);
            CHECK(estimate.at("method").string("method") == native.method);
            CHECK(estimate.at("in_peaks").string("in_peaks") == native.in_peaks);
            CHECK(estimate.at("use_model").string("use_model") == native.use_model);
            const auto check_optional = [&](const char* field, const auto& value) {
                if (value) CHECK(estimate.at(field).number(field) == *value);
                else CHECK(estimate.at(field).is_null());
            };
            check_optional("width", native.width);
            check_optional("smoothness", native.smoothness);
            check_optional("n_points", native.n_points);
            check_optional("tolerance", native.tolerance);
            check_optional("max_terms", native.max_terms);
            const auto& points = background.at("anchors").array("anchors");
            REQUIRE(points.size() == experiment.background.size());
            for (std::size_t i = 0; i < points.size(); ++i) {
                CHECK(points[i].at("id").string("id") == experiment.background[i]->id.value());
                CHECK(points[i].at("position").number("position") == experiment.background[i]->position.get());
                CHECK(points[i].at("intensity").number("intensity") == experiment.background[i]->intensity.value.get());
                CHECK(points[i].at("free").boolean("free") == experiment.background[i]->intensity.free.get());
            }
            const auto& terms = background.at("terms").array("terms");
            REQUIRE(terms.size() == experiment.background_terms.size());
            for (std::size_t i = 0; i < terms.size(); ++i) {
                const auto& term = *experiment.background_terms[i];
                CHECK(terms[i].at("id").string("id") == term.id.value());
                CHECK(terms[i].at("order").number("order") == term.order.get());
                CHECK(terms[i].at("coefficient").number("coefficient") == term.coef.value.get());
                CHECK(terms[i].at("free").boolean("free") == term.coef.free.get());
                if (term.coef.uncertainty.get())
                    CHECK(terms[i].at("uncertainty").number("uncertainty") == *term.coef.uncertainty.get());
                else CHECK(terms[i].at("uncertainty").is_null());
            }
            }
        }
    }
}

TEST_CASE("E11 dev context size admission agrees at the actual encoded byte boundary") {
    auto project = edi::load_project((repo() / "docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_basic/project").string());
    ControllerHost host(project);
    const auto original = host.controller.context();
    REQUIRE(edi::json::parse(original).get("error").is_null());
    REQUIRE(original.size() < edi::assistant::Limits::context_bytes);
    project.metadata.name.append(edi::assistant::Limits::context_bytes - original.size(), 'x');
    const auto exact = host.controller.context();
    REQUIRE(edi::json::parse(exact).get("error").is_null());
    CHECK(exact.size() == edi::assistant::Limits::context_bytes);
    project.metadata.name.push_back('x');
    const auto refused = edi::json::parse(host.controller.context());
    REQUIRE_FALSE(refused.get("error").is_null());
    CHECK(refused.at("error").at("code").string("code") == "edi.assistant.resource_exhausted");
}
