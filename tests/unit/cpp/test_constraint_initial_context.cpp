#include <doctest/doctest.h>

#include <cmath>
#include <filesystem>
#include <memory>
#include <string>

#include "edi/calculation.hpp"
#include "edi/io.hpp"

namespace {
edi::Project no_loop() {
    return edi::load_project(
        (std::filesystem::path(__FILE__).parent_path().parent_path().parent_path() /
         "fixtures/constraint_initial_context/project")
            .string());
}
void alias(edi::Project& p, const std::string& id, const std::string& name) {
    auto row = std::make_shared<edi::ParameterAlias>();
    row->id = id;
    row->parameter_unique_name = name;
    p.aliases.push_back(row);
}
void relation(edi::Project& p, bool cell) {
    alias(p, "u", "phase.atom_site.A.adp_iso");
    alias(p, "v", cell ? "phase.cell.length_a" : "phase.atom_site.A.fract_x");
    auto row = std::make_shared<edi::ParameterConstraint>();
    row->id = "v";
    row->expression = cell ? "v = 4+2*u" : "v = .1+.8*u";
    p.constraints.push_back(row);
}
void geometry_first(bool cell) {
    for (bool window : {false, true}) {
        auto p = no_loop();
        auto child = p.structures.front();
        (void)child->current_geometry();
        const auto held = edi::window_geometry(*child, {});
        REQUIRE_MESSAGE((child->geometry_current() && edi::window_geometry_current(*child, held)),
                        "A never-populated declaration project must start with current geometry");
        auto& target = cell ? child->cell.length_a : child->atom_sites[0]->fract_x;
        const auto before = target.value.get();
        relation(p, cell);
        CHECK_MESSAGE((target.value.get() == before),
                      "Native first declaration insertion must edit no target value");
        CHECK_MESSAGE((!child->geometry_current()),
                      "The first native declarations must revoke stored geometry");
        CHECK_MESSAGE((!edi::window_geometry_current(*child, held)),
                      "The first native declarations must revoke held-window geometry");
        const auto result =
            window ? edi::window_geometry(*child, {}).geometry : child->current_geometry();
        const double expected = cell ? 4.6 : .34;
        CHECK_MESSAGE((target.value.get() == doctest::Approx(expected)),
                      "Native lazy geometry must complete the first affine relation");
        bool found = false;
        for (std::size_t i = 0; i < result.expanded_atom_sites.atom_site_id.size(); ++i) {
            if (result.expanded_atom_sites.atom_site_id[i] == "A") {
                found = true;
                CHECK_MESSAGE((result.expanded_atom_sites.cartn_x[i] ==
                               doctest::Approx(cell ? 4.6 * .17 : 4.1 * .34)),
                              "First-declaration Cartesian geometry must match its closed form");
            }
        }
        CHECK_MESSAGE((found), "The first-declaration geometry must retain atom A");
    }
}
void category_first(bool reflections, bool cell) {
    auto p = no_loop();
    p.calculate();
    auto bank = p.experiments.front();
    edi::PdDataBase held_data = *bank->data;
    held_data.source.link(*bank, bank->data->epoch.value());
    edi::PowderReflnDataBase held_refln = bank->refln;
    held_refln.source.link(*bank, 0);
    const auto before = reflections ? held_refln.computed_for_read().f_squared_calc.values()
                                    : held_data.computed_for_read().intensity_calc.values();
    REQUIRE_MESSAGE((!before.empty() && bank->computed_current()),
                    "The native held-category witness must start with current nonempty rows");
    relation(p, cell);
    CHECK_MESSAGE(
        (!bank->computed_current()),
        "Native first declarations must revoke calculated currentness without editor hooks");
    const auto after = reflections ? held_refln.computed_for_read().f_squared_calc.values()
                                   : held_data.computed_for_read().intensity_calc.values();
    const auto child = p.structures.front();
    CHECK_MESSAGE(
        ((cell ? child->cell.length_a.value.get() : child->atom_sites[0]->fract_x.value.get()) ==
         doctest::Approx(cell ? 4.6 : .34)),
        "A native held data or reflection read must complete the first relation");
    CHECK_MESSAGE(
        (after != before),
        "Held category renewal must replace the pre-relation arrays after geometry motion");
    CHECK_MESSAGE((bank->computed_current()),
                  "A successful held-category renewal must leave current calculated rows");
}
void alias_only(bool constraints_only) {
    auto p = no_loop();
    if (constraints_only) {
        // Disabled declarations without aliases exercise the other one-sided record state.
        auto row = std::make_shared<edi::ParameterConstraint>();
        row->id = "unused";
        row->expression = "unused = 1";
        row->enabled = false;
        p.constraints.push_back(row);
    } else {
        alias(p, "u", "phase.atom_site.A.adp_iso");
    }
    p.calculate();
    auto child = p.structures.front();
    const auto held = edi::window_geometry(*child, {});
    CHECK_MESSAGE((child->geometry_current() && edi::window_geometry_current(*child, held)),
                  "A one-sided declaration record must be current immediately after calculation");
    CHECK_MESSAGE((p.experiments.front()->computed_current()),
                  "Alias-only and disabled-only calculated categories must report current");
}
}  // namespace

TEST_CASE("First native coordinate declarations revoke and renew warmed geometry") {
    geometry_first(false);
}
TEST_CASE("First native cell declarations revoke and renew warmed geometry") {
    geometry_first(true);
}
TEST_CASE("First coordinate declarations renew a native held data category") {
    category_first(false, false);
}
TEST_CASE("First cell declarations renew a native held data category") {
    category_first(false, true);
}
TEST_CASE("First coordinate declarations renew a native held reflection category") {
    category_first(true, false);
}
TEST_CASE("First cell declarations renew a native held reflection category") {
    category_first(true, true);
}
TEST_CASE("Alias-only native calculation keeps stored window and pattern categories current") {
    alias_only(false);
}
TEST_CASE("Disabled-only native calculation keeps one-sided declaration categories current") {
    alias_only(true);
}

TEST_CASE(
    "Initial collection controls preserve clear-all equal-write and source-edit provenance") {
    for (const std::string edit : {"clear-all", "equal-write", "source-edit"}) {
        auto p = no_loop();
        relation(p, false);
        p.calculate();
        auto child = p.structures.front();
        const auto held = edi::window_geometry(*child, {});
        REQUIRE_MESSAGE((child->geometry_current()),
                        "Populated declaration controls must start with current geometry");
        if (edit == "clear-all") {
            p.constraints.clear();
            p.aliases.clear();
        } else if (edit == "equal-write") {
            p.constraints[0]->expression = std::string(p.constraints[0]->expression.value());
        } else {
            child->atom_sites[0]->adp_iso.value = .4;
        }
        CHECK_MESSAGE(
            (!child->geometry_current() && !edi::window_geometry_current(*child, held)),
            "Cleared declarations equal writes and source edits must revoke warm geometry");
        (void)child->current_geometry();
        CHECK_MESSAGE(
            (child->atom_sites[0]->fract_x.value.get() ==
             doctest::Approx(edit == "source-edit" ? .42 : .34)),
            "Controls must preserve removed values or apply the edited source closed form");
        CHECK_MESSAGE((child->geometry_current()),
                      "Geometry must be current after each populated-collection control renewal");
    }
}

namespace {
void warm_owner(const std::string& route, bool cell) {
    for (const std::string origin : {"constrained", "no-loop", "standalone"}) {
        for (bool window : {false, true}) {
            CAPTURE(route);
            CAPTURE(cell);
            CAPTURE(origin);
            CAPTURE(window);
            auto donor = std::make_unique<edi::Project>(no_loop());
            auto child = donor->structures.front();
            if (origin == "constrained") {
                relation(*donor, cell);
                donor->constraints[0]->expression = cell ? "v = 4.3" : "v = .23";
            }
            if (origin == "standalone") donor->structures.clear();
            (void)child->current_geometry();
            const auto held = edi::window_geometry(*child, {});
            REQUIRE_MESSAGE(
                (child->geometry_current() && edi::window_geometry_current(*child, held)),
                "Every native owner-transition donor must have warm current geometry");
            auto& target = cell ? child->cell.length_a : child->atom_sites[0]->fract_x;
            const double before = target.value.get();
            const bool entering = route == "insert" || route == "replace" || route == "assign";
            auto destination = no_loop();
            relation(destination, cell);
            destination.constraints[0]->expression = cell ? "v = 4.7" : "v = .37";
            if (entering) {
                if (origin != "standalone") donor->structures.clear();
                if (route == "insert") {
                    destination.structures.clear();
                    destination.structures.push_back(child);
                } else if (route == "replace") {
                    destination.structures.replace_at(0, child);
                } else {
                    destination.structures.assign({child});
                }
            } else if (route == "remove") {
                donor->structures.clear();
            } else {
                donor.reset();
            }
            const bool changed_owner = entering || origin != "standalone";
            CHECK_MESSAGE((target.value.get() == before),
                          "Native owner mutation must not incidentally write a geometry input");
            CHECK_MESSAGE((child->geometry_current() == !changed_owner),
                          "Stored geometry must certify precisely the current relation owner");
            CHECK_MESSAGE((edi::window_geometry_current(*child, held) == !changed_owner),
                          "Native held-window provenance must reject a revoked owner context");
            const auto result =
                window ? edi::window_geometry(*child, {}).geometry : child->current_geometry();
            const double expected = entering ? (cell ? 4.7 : .37) : before;
            CHECK_MESSAGE(
                (target.value.get() == doctest::Approx(expected)),
                "The first native geometry read must complete only the live owner relation");
            bool found = false;
            for (std::size_t i = 0; i < result.expanded_atom_sites.atom_site_id.size(); ++i) {
                if (result.expanded_atom_sites.atom_site_id[i] == "A") {
                    found = true;
                    CHECK_MESSAGE(
                        (result.expanded_atom_sites.cartn_x[i] ==
                         doctest::Approx(cell ? expected * .17 : 4.1 * expected)),
                        "Warmed owner transitions must publish closed-form Cartesian geometry");
                }
            }
            CHECK_MESSAGE((found), "The owner-transition geometry must retain atom A");
        }
    }
}
}  // namespace

TEST_CASE("Warm native coordinate geometry follows insertion into a new owner") {
    warm_owner("insert", false);
}
TEST_CASE("Warm native cell geometry follows insertion into a new owner") {
    warm_owner("insert", true);
}
TEST_CASE("Warm native coordinate geometry follows replacement into a new owner") {
    warm_owner("replace", false);
}
TEST_CASE("Warm native cell geometry follows replacement into a new owner") {
    warm_owner("replace", true);
}
TEST_CASE("Warm native coordinate geometry follows assignment into a new owner") {
    warm_owner("assign", false);
}
TEST_CASE("Warm native cell geometry follows assignment into a new owner") {
    warm_owner("assign", true);
}
TEST_CASE("Warm native coordinate geometry revokes a removed owner") {
    warm_owner("remove", false);
}
TEST_CASE("Warm native cell geometry revokes a removed owner") { warm_owner("remove", true); }
TEST_CASE("Warm native coordinate geometry revokes a destroyed owner") {
    warm_owner("destroy", false);
}
TEST_CASE("Warm native cell geometry revokes a destroyed owner") { warm_owner("destroy", true); }
