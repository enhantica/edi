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
    if (kind == "clear-all") {
        p.constraints.clear();
        p.aliases.clear();
    }
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
const std::vector<std::string> edits{"expression",        "equal-expression",  "disable",
                                     "constraint-rename", "constraint-remove", "constraint-add",
                                     "alias-retarget",    "alias-rename",      "alias-remove",
                                     "alias-add",         "clear-all"};
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

namespace {
void check_queued_declaration_edit(const std::string& kind) {
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
        CHECK_MESSAGE((a.value.get() == av && b.value.get() == bv && a.uncertainty.get() == au &&
                       b.uncertainty.get() == bu),
                      "Supersession must publish neither independent nor dependent values and "
                      "uncertainties");
        CHECK_MESSAGE((!a.start_value.get()), "Supersession must publish no fit-start record");
    }
}
}  // namespace

TEST_CASE("Queued FitJob declaration adoption: control") {
    check_queued_declaration_edit("control");
}

TEST_CASE("Queued FitJob declaration adoption: clear-all") {
    check_queued_declaration_edit("clear-all");
}

TEST_CASE("Queued FitJob declaration adoption: expression") {
    check_queued_declaration_edit("expression");
}

TEST_CASE("Queued FitJob declaration adoption: equal-expression") {
    check_queued_declaration_edit("equal-expression");
}

TEST_CASE("Queued FitJob declaration adoption: disable") {
    check_queued_declaration_edit("disable");
}

TEST_CASE("Queued FitJob declaration adoption: constraint-remove") {
    check_queued_declaration_edit("constraint-remove");
}

TEST_CASE("Queued FitJob declaration adoption: constraint-add") {
    check_queued_declaration_edit("constraint-add");
}

TEST_CASE("Queued FitJob declaration adoption: constraint-rename") {
    check_queued_declaration_edit("constraint-rename");
}

TEST_CASE("Queued FitJob declaration adoption: alias-add") {
    check_queued_declaration_edit("alias-add");
}

TEST_CASE("Queued FitJob declaration adoption: alias-remove") {
    check_queued_declaration_edit("alias-remove");
}

TEST_CASE("Queued FitJob declaration adoption: alias-rename") {
    check_queued_declaration_edit("alias-rename");
}

TEST_CASE("Queued FitJob declaration adoption: alias-retarget") {
    check_queued_declaration_edit("alias-retarget");
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

TEST_CASE("Declaration edits before a work snapshot publish completed values with arrays") {
    auto p = transition_project();
    p.calculate();
    auto& target = p.structure().atom_sites[1]->adp_iso;
    const double before = target.value.get();
    const auto buffer = p.experiment().data->intensity_calc.values().data();
    p.constraints[1]->expression = "b = 3*a + 1";
    auto work = edi::snapshot_for_work(p);
    work.project.calculate();
    REQUIRE_MESSAGE(
        work.project.structure().atom_sites[1]->adp_iso.value.get() == doctest::Approx(1.9),
        "The worker must apply the edited relation at the independent input 0.3");
    const auto& expected_column = work.project.experiment().data->intensity_calc.values();
    const std::vector<double> expected_array(expected_column.begin(), expected_column.end());
    auto staged = edi::stage_computed(work.project, work.stamps);
    const auto outcome = edi::publish(p, std::move(staged));
    if (outcome == edi::PublishOutcome::Superseded) {
        CHECK_MESSAGE((target.value.get() == before &&
                       p.experiment().data->intensity_calc.values().data() == buffer),
                      "A refused calculation publication preserves both values and arrays");
    } else {
        const auto& published_column = p.experiment().data->intensity_calc.values();
        CHECK_MESSAGE((std::vector<double>(published_column.begin(), published_column.end()) ==
                       expected_array),
                      "Published arrays must equal the completed worker arrays accompanying the "
                      "dependent values");
        CHECK_MESSAGE(
            target.value.get() == doctest::Approx(1.9),
            "Published arrays and their completed dependent values must describe one model");
        CHECK_MESSAGE(p.experiment().computed_current(),
                      "A successful calculation publication must carry current arrays");
    }
}

TEST_CASE("Native geometry renewal applies valid relations and refuses invalid declarations") {
    for (const std::string family : {"coordinate", "cell"}) {
        for (const bool invalid : {false, true}) {
            CAPTURE(family);
            CAPTURE(invalid);
            auto p = transition_project();
            p.constraints.erase_at(0);
            p.aliases[0]->parameter_unique_name =
                family == "cell" ? "phase.cell.length_a" : "phase.atom_site.A.fract_x";
            p.aliases[1]->parameter_unique_name =
                family == "cell" ? "phase.cell.length_b" : "phase.atom_site.B.fract_y";
            p.constraints[0]->expression = family == "cell" ? "b = 1.2*a" : "b = 2*a + .1";
            p.calculate();
            auto old = p.structure().current_geometry();
            p.constraints[0]->expression = invalid            ? "b = missing"
                                           : family == "cell" ? "b = 1.3*a"
                                                              : "b = 3*a + .1";
            bool refused = false;
            try {
                const auto renewed = p.structure().current_geometry();
                CHECK_MESSAGE(!invalid, "Invalid geometry relations must refuse value reads");
                if (!invalid) {
                    const double expected = family == "cell" ? 5.33 : .61;
                    CHECK_MESSAGE(
                        (family == "cell" ? p.structure().cell.length_b.value.get()
                                          : p.structure().atom_sites[1]->fract_y.value.get()) ==
                            doctest::Approx(expected),
                        "Geometry reads must complete the new relation before computing");
                    if (family == "cell") {
                        CHECK_MESSAGE(
                            renewed.atom_sites_cartn_transform.matrix[4] == doctest::Approx(5.33),
                            "The renewed Cartesian frame must use the dependent cell length");
                    } else {
                        const auto& atoms = renewed.expanded_atom_sites;
                        bool found = false;
                        for (std::size_t i = 0; i < atoms.atom_site_id.size(); ++i) {
                            if (atoms.atom_site_id[i] == "B") {
                                found = true;
                                CHECK_MESSAGE(
                                    atoms.fract_y[i] == doctest::Approx(.61),
                                    "The renewed expanded site must use the dependent coordinate");
                            }
                        }
                        CHECK_MESSAGE(found,
                                      "The geometry witness must include the dependent atom");
                    }
                }
            } catch (const std::exception&) {
                refused = true;
            }
            CHECK_MESSAGE(refused == invalid,
                          "Valid geometry renews and invalid relation admission refuses");
        }
    }
}

TEST_CASE("Held native window geometry retains relation provenance and renews dependent values") {
    auto p = transition_project();
    p.constraints.erase_at(0);
    p.aliases[0]->parameter_unique_name = "phase.atom_site.A.fract_x";
    p.aliases[1]->parameter_unique_name = "phase.atom_site.B.fract_y";
    p.constraints[0]->expression = "b = 2*a + .1";
    p.calculate();
    const auto held = edi::window_geometry(p.structure(), {});
    REQUIRE_MESSAGE(edi::window_geometry_current(p.structure(), held),
                    "The window control must be current before the declaration edit");
    p.constraints[0]->expression = "b = 3*a + .1";
    CHECK_MESSAGE(!edi::window_geometry_current(p.structure(), held),
                  "A held window must retain the relation generation that produced it");
    const auto renewed = edi::window_geometry(p.structure(), {});
    CHECK_MESSAGE(
        p.structure().atom_sites[1]->fract_y.value.get() == doctest::Approx(.61),
        "A window read must complete the dependent coordinate before producing geometry");
    const auto& sites = renewed.geometry.expanded_atom_sites;
    bool found = false;
    for (std::size_t i = 0; i < sites.atom_site_id.size(); ++i) {
        if (sites.atom_site_id[i] == "B") {
            found = true;
            CHECK_MESSAGE(sites.fract_y[i] == doctest::Approx(.61),
                          "Window arrays must describe the new relation's dependent value");
        }
    }
    CHECK_MESSAGE(found, "The renewed native window must contain its dependent atom");
    p.constraints[0]->expression = "b = missing";
    CHECK_THROWS_MESSAGE(edi::window_geometry(p.structure(), {}),
                         "Invalid relations must refuse native window geometry");
}

// E11-T5: additive public WorkStamps overload, exercised in the ORIGINAL edi_tests target.
// The unbounded API is a labelled compatibility reference, not a new hand-written codec.
#include <limits>
#include <optional>
#include <stdexcept>

TEST_CASE("E11-T5 bounded work stamps preserve original encoding and stale sources") {
    using Capture = edi::WorkStamps (*)(const edi::Project&, std::size_t);
    const Capture capture = static_cast<Capture>(&edi::work_stamps); // Required actual API; no absent-feature fallback.
    auto project = transition_project();
    REQUIRE_MESSAGE(project.experiment().data.has_value(), "STAMP482 SETUP original measured fixture has actual data");
    REQUIRE_MESSAGE(!project.experiment().data->intensity_meas.get().empty(),
                    "STAMP482 SETUP original fixture supplies nonempty actual measured columns");
    REQUIRE_MESSAGE((project.aliases.size() > 0 && project.constraints.size() > 1),
                    "STAMP482 SETUP original fixture exercises real alias lookup and relation encoding");
    const auto maximum = std::numeric_limits<std::size_t>::max();
    const auto equal = [](const edi::WorkStamps& a, const edi::WorkStamps& b) {
        CHECK_MESSAGE((a.experiment_inputs == b.experiment_inputs && a.structure_inputs == b.structure_inputs),
                      "STAMP482 compatibility reference: bounded capture retains EVERY original scientific input byte");
        CHECK_MESSAGE((a.experiments == b.experiments && a.structures == b.structures &&
                          a.experiments_generation == b.experiments_generation && a.structures_generation == b.structures_generation),
                      "STAMP482 bounded capture preserves original collection and write identities");
        CHECK_MESSAGE((a.edits == b.edits && a.edits_at == b.edits_at),
                      "STAMP482 bounded capture preserves original live edit identity");
        CHECK_MESSAGE((a.aliases == b.aliases && a.constraints == b.constraints && a.relations == b.relations),
                      "STAMP482 bounded capture preserves original alias/constraint identities and exact relation bytes");
    };
    const auto original = edi::work_stamps(project);
    const auto saved = edi::project_edi_files(project);
    const auto bounded = capture(project, maximum);
    equal(bounded, original);
    CHECK_MESSAGE(edi::unchanged_since(project, bounded), "STAMP482 synchronous capture does not write or renew live scientific state");
    CHECK_MESSAGE(edi::project_edi_files(project) == saved, "STAMP482 successful capture preserves original saved model bytes");

    // Independent NECESSARY retained payload lower bound: actual original returned byte strings.
    // This does not copy the encoder/count formula or claim a particular allocator/RSS threshold.
    std::size_t payload = original.relations.size();
    for (const auto& text : original.experiment_inputs) {
        REQUIRE_MESSAGE(text.size() <= maximum - payload, "STAMP482 fixture lower-bound addition is representable");
        payload += text.size();
    }
    for (const auto& text : original.structure_inputs) {
        REQUIRE_MESSAGE(text.size() <= maximum - payload, "STAMP482 fixture lower-bound addition is representable");
        payload += text.size();
    }
    REQUIRE_MESSAGE(payload > 0, "STAMP482 nonempty original scientific payload gives a meaningful finite insufficiency boundary");
    for (const auto limit : {std::size_t{0}, sizeof(edi::WorkStamps) - 1, payload - 1}) {
        CAPTURE(limit);
        std::optional<edi::WorkStamps> partial;
        CHECK_THROWS_AS_MESSAGE(partial = capture(project, limit), std::length_error,
                                "STAMP482 insufficient actual container/payload admission fails with length_error");
        CHECK_MESSAGE(!partial.has_value(), "STAMP482 refusal returns NO partial WorkStamps");
        equal(edi::work_stamps(project), original);
        CHECK_MESSAGE((edi::unchanged_since(project, bounded) && edi::project_edi_files(project) == saved),
                      "STAMP482 insufficient capture neither writes model nor changes original source identities");
    }

    auto measured = project.experiment().data->intensity_meas.get();
    measured[0] += 1.25; // Independent literal changed observation, not a computed scientific golden.
    project.experiment().data->write_column(&edi::PdDataBase::intensity_meas, std::move(measured));
    CHECK_MESSAGE(!edi::unchanged_since(project, bounded), "STAMP482 actual measured-column change stales original bounded source");
    const auto after_measured = capture(project, maximum);
    equal(after_measured, edi::work_stamps(project));
    CHECK_MESSAGE(after_measured.experiment_inputs != bounded.experiment_inputs,
                  "STAMP482 measured-column mutation changes exact scientific input encoding");

    project.structure().cell.length_a.value = project.structure().cell.length_a.value.get() + .125;
    CHECK_MESSAGE(!edi::unchanged_since(project, after_measured), "STAMP482 actual original shape change stales old bounded source");
    const auto after_shape = capture(project, maximum);
    equal(after_shape, edi::work_stamps(project));
    CHECK_MESSAGE(after_shape.structure_inputs != after_measured.structure_inputs,
                  "STAMP482 shape change changes exact original structure encoding");

    declaration_edit(project, "expression"); // Existing original relation mutation vehicle.
    CHECK_MESSAGE(!edi::unchanged_since(project, after_shape), "STAMP482 actual relation change stales old bounded authority");
    const auto after_relation = capture(project, maximum);
    equal(after_relation, edi::work_stamps(project));
    CHECK_MESSAGE(after_relation.relations != after_shape.relations,
                  "STAMP482 changed actual expression changes original relation encoding");

    // Preserve the original equal-write semantics too, without inventing a second currency rule.
    const auto equal_write_reference = edi::work_stamps(project);
    project.structure().cell.length_a.value = project.structure().cell.length_a.value.get();
    CHECK_MESSAGE(edi::unchanged_since(project, after_relation) == edi::unchanged_since(project, equal_write_reference),
                  "STAMP482 bounded/unbounded old receipts agree after actual equal scalar write");
    equal(capture(project, maximum), edi::work_stamps(project));
}
