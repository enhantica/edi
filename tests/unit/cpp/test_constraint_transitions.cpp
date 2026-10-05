#include <doctest/doctest.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "edi/calculation.hpp"
#include "edi/io.hpp"

namespace {
edi::Project transition_project() {
    return edi::load_project(
        (std::filesystem::path(__FILE__).parent_path().parent_path().parent_path() /
         "fixtures/constraint_expressions/project")
            .string());
}
void declaration_edit(edi::Project& p, const std::string& kind) {
    if (kind == "expression") p.constraints[1]->expression = "b = 3*a + 1";
    if (kind == "equal-expression") p.constraints[1]->expression = "b = 2*a + 1";
    if (kind == "disable") p.constraints[1]->enabled = false;
    if (kind == "constraint-rename") p.constraints[1]->id = "renamed";
    if (kind == "constraint-remove") p.constraints.erase_at(1);
    if (kind == "constraint-add") {
        edi::ParameterConstraint row;
        row.id = "new";
        row.expression = "a = .3";
        p.constraints.push_back(std::make_shared<edi::ParameterConstraint>(row));
    }
    if (kind == "alias-retarget") p.aliases[0]->parameter_unique_name = "phase.cell.length_a";
    if (kind == "alias-rename") p.aliases[0]->id = "renamed";
    if (kind == "alias-remove") p.aliases.erase_at(0);
    if (kind == "alias-add") {
        edi::ParameterAlias row;
        row.id = "extra";
        row.parameter_unique_name = "phase.cell.length_a";
        p.aliases.push_back(std::make_shared<edi::ParameterAlias>(row));
    }
}
const std::vector<std::string> edits{
    "expression",     "equal-expression", "disable",      "constraint-rename", "constraint-remove",
    "constraint-add", "alias-retarget",   "alias-rename", "alias-remove",      "alias-add"};
}  // namespace

TEST_CASE("Relation declaration writes revoke computed currentness without parameter writes") {
    for (const auto& kind : edits) {
        CAPTURE(kind);
        auto p = transition_project();
        p.calculate();
        auto& target = p.structure().atom_sites[1]->adp_iso;
        const auto before = target.value.get();
        REQUIRE_MESSAGE((p.experiment().computed_current()),
                        "The control must start with current calculated categories");
        declaration_edit(p, kind);
        CHECK_MESSAGE((target.value.get() == before),
                      "Declaration mutation must not incidentally change the target value");
        CHECK_MESSAGE((!p.experiment().computed_current()),
                      "A declaration write must revoke calculation currentness before any read or "
                      "calculation");
    }
}

TEST_CASE("Relation declaration writes supersede calculated publications atomically") {
    for (const auto& kind : edits) {
        for (bool parameters : {false}) {
            CAPTURE(kind);
            CAPTURE(parameters);
            auto p = transition_project();
            p.calculate();
            auto work = edi::snapshot_for_work(p);
            work.project.structure().atom_sites[0]->adp_iso.value = .4;
            work.project.calculate();
            auto staged = edi::stage_computed(work.project, work.stamps);
            (void)parameters;
            auto& target = p.structure().atom_sites[1]->adp_iso;
            const auto before = target.value.get();
            const auto error = target.uncertainty.get();
            const auto buffer = p.experiment().data->intensity_calc.values().data();
            declaration_edit(p, kind);
            CHECK_MESSAGE(
                (edi::publish(p, std::move(staged)) == edi::PublishOutcome::Superseded),
                "A declaration-only edit must refuse publication of the old relation result");
            CHECK_MESSAGE((target.value.get() == before && target.uncertainty.get() == error),
                          "A superseded publication must write neither values nor uncertainty");
            CHECK_MESSAGE(
                (p.experiment().data->intensity_calc.values().data() == buffer),
                "Superseded relation work must preserve the previously published buffer");
        }
    }
}

TEST_CASE("Unchanged relation declarations admit calculated publication") {
    auto p = transition_project();
    p.calculate();
    auto work = edi::snapshot_for_work(p);
    work.project.calculate();
    const bool parameters = false;
    auto staged = edi::stage_computed(work.project, work.stamps);
    (void)parameters;
    CHECK_MESSAGE((edi::publish(p, std::move(staged)) == edi::PublishOutcome::Published),
                  "The publication gate must admit an unchanged relation graph control");
}

TEST_CASE("Native unrefreshed constraints save active dependents bare") {
    auto p = transition_project();
    p.constraints.clear();
    edi::refresh_relations(p);
    auto& target = p.structure().atom_sites[1]->adp_iso;
    target.free = true;
    edi::ParameterConstraint row;
    row.id = "b";
    row.expression = "b = 2*a + 1";
    p.constraints.push_back(std::make_shared<edi::ParameterConstraint>(row));
    REQUIRE_MESSAGE((target.free.get()),
                    "The native save witness must retain the unrefreshed target free flag");
    const auto directory =
        std::filesystem::temp_directory_path() /
        ("constraint-save-" +
         std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    struct Cleanup {
        std::filesystem::path path;
        ~Cleanup() { std::filesystem::remove_all(path); }
    } cleanup{directory};
    edi::save_project(p, directory.string());
    std::ifstream in(directory / "structures/phase.edi");
    std::string line, token;
    std::vector<std::string> columns;
    bool found = false;
    while (std::getline(in, line)) {
        std::istringstream words(line);
        if (!(words >> token)) continue;
        if (token == "loop_") {
            columns.clear();
            continue;
        }
        if (token.starts_with("_atom_site.")) {
            columns.push_back(token);
            continue;
        }
        if (token != "B") continue;
        const auto column = std::find(columns.begin(), columns.end(), "_atom_site.adp_iso");
        REQUIRE_MESSAGE(column != columns.end(),
                        "The saved atom loop must declare its ADP column");
        std::vector<std::string> row{token};
        while (words >> token) row.push_back(token);
        const auto index = static_cast<std::size_t>(column - columns.begin());
        REQUIRE_MESSAGE(index < row.size(), "The saved dependent row must contain its ADP token");
        found = true;
        CHECK_MESSAGE(
            (row[index].find('(') == std::string::npos),
            "A native active dependent must serialize bare without requiring refresh before save");
    }
    CHECK_MESSAGE((found), "The saved native witness must contain the dependent atom row");
    CHECK_MESSAGE(
        (target.free.get()),
        "Save normalization must operate on its copy and preserve the caller's free state");
}

#include <algorithm>
#include <condition_variable>
#include <mutex>
#include <optional>

#include "e04_t9_support.hpp"
#include "edi/fit_job.hpp"

TEST_CASE("A declaration-only edit supersedes completed queued FitJob adoption") {
    for (const std::string kind :
         {"control", "expression", "equal-expression", "disable", "constraint-remove",
          "constraint-add", "constraint-rename", "alias-add", "alias-remove", "alias-rename",
          "alias-retarget"}) {
        CAPTURE(kind);
        auto live = transition_project();
        live.structure().atom_sites[0]->adp_iso.free = true;
        live.minimizer_max_iterations = 2;
        live.calculate();
        e04_t9::OwnerQueue queue;
        std::mutex mutex;
        std::condition_variable ready;
        bool finished = false;
        edi::work::Worker worker([&](auto delivery) { queue.post(std::move(delivery)); },
                                 {{}, [&](const auto& event) {
                                      if (event.kind == edi::work::EventKind::Finished) {
                                          std::lock_guard lock(mutex);
                                          finished = true;
                                          ready.notify_one();
                                      }
                                  }});
        std::optional<edi::FitReport> report;
        edi::FitJob fit(live, worker, {{}, {}, {}, [&](const auto& result) { report = result; }});
        REQUIRE_MESSAGE((fit.start()), "The declaration-race control must start an actual FitJob");
        {
            std::unique_lock lock(mutex);
            REQUIRE_MESSAGE(
                (ready.wait_for(lock, std::chrono::seconds(10), [&] { return finished; })),
                "The worker must finish before the declaration edit while owner deliveries remain "
                "queued");
        }
        auto& a = live.structure().atom_sites[0]->adp_iso;
        auto& b = live.structure().atom_sites[1]->adp_iso;
        const auto av = a.value.get(), bv = b.value.get();
        const auto au = a.uncertainty.get(), bu = b.uncertainty.get();
        if (kind != "control") declaration_edit(live, kind);
        while (!report) queue.one();
        queue.drain();
        if (kind == "control") {
            CHECK_MESSAGE((report->adopted()),
                          "An unchanged relation fit must finish with adopted output");
        } else {
            CHECK_MESSAGE((report->status == edi::FitStatus::SUPERSEDED),
                          "A declaration-only edit must supersede a finished fit waiting for "
                          "owner adoption");
            CHECK_MESSAGE((a.value.get() == av && b.value.get() == bv &&
                           a.uncertainty.get() == au && b.uncertainty.get() == bu),
                          "Supersession must publish neither independent nor dependent values and "
                          "uncertainties");
            CHECK_MESSAGE((!a.start_value.get()), "Supersession must publish no fit-start record");
        }
    }
}

TEST_CASE("Coordinate and cell declaration edits revoke stored geometry") {
    for (const std::string family : {"coordinate", "cell"}) {
        CAPTURE(family);
        auto p = transition_project();
        p.constraints.erase_at(0);
        p.aliases[0]->parameter_unique_name =
            family == "cell" ? "phase.cell.length_a" : "phase.atom_site.A.fract_x";
        p.aliases[1]->parameter_unique_name =
            family == "cell" ? "phase.cell.length_b" : "phase.atom_site.B.fract_y";
        p.calculate();
        (void)p.structure().current_geometry();
        REQUIRE_MESSAGE((p.structure().geometry_current()),
                        "The geometry control must be current before the declaration-only edit");
        p.constraints[0]->expression = "b = 3*a + 1";
        CHECK_MESSAGE((!p.structure().geometry_current()),
                      "Geometry must become stale when a coordinate or cell relation changes "
                      "without a parameter write");
    }
}

TEST_CASE("Native alias admission refuses invalid saves and canonical text before publication") {
    for (const std::string history : {"alias-only", "last-removed", "disabled"}) {
        for (const std::string fault : {"reserved", "dangling"}) {
            CAPTURE(history);
            CAPTURE(fault);
            auto p = transition_project();
            if (history == "disabled") {
                for (auto& row : p.constraints) row->enabled = false;
            } else
                p.constraints.clear();
            if (fault == "reserved")
                p.aliases[0]->id = "sin";
            else
                p.aliases[0]->parameter_unique_name = "phase.atom_site.missing.adp_iso";
            const auto directory =
                std::filesystem::temp_directory_path() /
                ("alias-admission-" +
                 std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
            struct Cleanup {
                std::filesystem::path path;
                ~Cleanup() { std::filesystem::remove_all(path); }
            } cleanup{directory};
            std::filesystem::create_directories(directory);
            std::ofstream(directory / "caller.txt") << "untouched";
            bool refused = false;
            try {
                edi::save_project(p, directory.string());
            } catch (const std::exception&) {
                refused = true;
            }
            CHECK_MESSAGE(refused, "Invalid native aliases must refuse save admission");
            std::size_t files = 0;
            for (const auto& entry : std::filesystem::recursive_directory_iterator(directory)) {
                if (entry.is_regular_file()) ++files;
            }
            CHECK_MESSAGE((files == 1),
                          "Alias admission must refuse before publishing any project file");
            std::ifstream saved(directory / "caller.txt");
            std::string text;
            saved >> text;
            CHECK_MESSAGE((text == "untouched"),
                          "A refused save must preserve caller-owned file bytes");
            refused = false;
            try {
                (void)edi::block_edi_text(p, edi::BlockKind::ANALYSIS);
            } catch (const std::exception&) {
                refused = true;
            }
            CHECK_MESSAGE(refused,
                          "Canonical Analysis text must apply the same alias admission as save");
        }
    }
}
