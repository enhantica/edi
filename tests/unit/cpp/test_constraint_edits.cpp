#include <doctest/doctest.h>

#include <filesystem>
#include <string>
#include <type_traits>

#include "edi/categories.hpp"
#include "edi/edit.hpp"
#include "edi/io.hpp"

namespace {
edi::Project relation_edit_project() {
    const auto root = std::filesystem::path(__FILE__).parent_path().parent_path().parent_path();
    return edi::load_project((root / "fixtures/constraint_expressions/project").string());
}

template <class Project, class Edit = edi::Edit>
void alias_edits(Project& project) {
    if constexpr (requires { project.aliases; }) {
        using Alias = std::remove_cvref_t<decltype(*project.aliases[0])>;
        if constexpr (requires {
                          Edit::append(project.aliases, Alias{});
                          Edit::erase(project.aliases, 0);
                      }) {
            const auto before = project;
            const auto count = project.aliases.size();
            Alias copy = *project.aliases[0];
            copy.id = "copied_alias";
            Edit::append(project.aliases, copy)();
            REQUIRE_MESSAGE(project.aliases.size() == count + 1,
                            "Appending a copied alias must create a distinct keyed row");
            Edit::assign(project.aliases[count]->parameter_unique_name,
                         std::string("phase.cell.length_a"))();
            CHECK_MESSAGE(project.aliases[0]->parameter_unique_name.value() ==
                              before.aliases[0]->parameter_unique_name.value(),
                          "Editing a duplicate must not mutate its source row");
            Edit::erase(project.aliases, count)();
            CHECK_MESSAGE(project.aliases.size() == count,
                          "Removing an alias must use the closed core operation");
            Edit::append(project.aliases, copy)();
            project = before;
            CHECK_MESSAGE(project.aliases.size() == count,
                          "Restoring an edit snapshot must restore the alias collection");
            CHECK_MESSAGE(project.aliases[0]->id.value() == before.aliases[0]->id.value(),
                          "Snapshot restoration must retain keyed alias identities");
        } else {
            FAIL_CHECK(
                "Alias append and removal must be available through the closed core edit "
                "operations");
        }
    } else {
        FAIL_CHECK("The core project must own editable aliases");
    }
}

template <class Project, class Edit = edi::Edit>
void constraint_edits(Project& project) {
    if constexpr (requires { project.constraints[0]->enabled; }) {
        using Constraint = std::remove_cvref_t<decltype(*project.constraints[0])>;
        if constexpr (requires {
                          Edit::append(project.constraints, Constraint{});
                          Edit::erase(project.constraints, 0);
                      }) {
            const auto before = project;
            const auto count = project.constraints.size();
            Constraint copy = *project.constraints[0];
            copy.id = "copied_constraint";
            copy.enabled = false;
            Edit::append(project.constraints, copy)();
            REQUIRE_MESSAGE(project.constraints.size() == count + 1,
                            "Duplicating a constraint must retain a separate declaration");
            Edit::assign(project.constraints[count]->expression, std::string("b = 3*a + 2"))();
            CHECK_MESSAGE(project.constraints[0]->expression.value() ==
                              before.constraints[0]->expression.value(),
                          "Editing a constraint duplicate must not change its source expression");
            Edit::erase(project.constraints, count)();
            CHECK_MESSAGE(project.constraints.size() == count,
                          "Removing a constraint must use the closed core operation");
            Edit::append(project.constraints, copy)();
            project = before;
            CHECK_MESSAGE(project.constraints.size() == count,
                          "Restoring an edit snapshot must restore the constraint collection");
        } else {
            FAIL_CHECK("Constraint append and removal must be closed core edit operations");
        }
    } else {
        FAIL_CHECK("Editable constraints must carry an enabled state in the core");
    }
}

template <class Project, class Edit = edi::Edit>
void enabled_edits(Project& project) {
    if constexpr (requires { project.constraints[0]->enabled; }) {
        for (auto& row : project.constraints) Edit::assign(row->enabled, false)();
        const auto disabled = project;
        project.structure().atom_sites[1]->adp_iso.value = 9;
        project.calculate();
        CHECK_MESSAGE(project.structure().atom_sites[1]->adp_iso.value == 9,
                      "A disabled core constraint must not complete its target on calculation");
        for (auto& row : project.constraints) Edit::assign(row->enabled, true)();
        project.calculate();
        CHECK_MESSAGE(project.structure().atom_sites[1]->adp_iso.value == doctest::Approx(1.6),
                      "Reenabled core constraints must apply at the next calculation");
        project = disabled;
        project.structure().atom_sites[1]->adp_iso.value = 7;
        project.calculate();
        CHECK_MESSAGE(project.structure().atom_sites[1]->adp_iso.value == 7,
                      "Restoring an edit snapshot must restore the disabled state too");
    } else {
        FAIL_CHECK("The core must retain disabled constraints without applying them");
    }
}
}  // namespace

TEST_CASE("Alias core edits support append duplicate removal and snapshot restoration") {
    auto project = relation_edit_project();
    alias_edits(project);
}
TEST_CASE("Constraint core edits support append duplicate removal and snapshot restoration") {
    auto project = relation_edit_project();
    constraint_edits(project);
}
TEST_CASE("Constraint core enable edits are reversible without deleting the declaration") {
    auto project = relation_edit_project();
    enabled_edits(project);
}

namespace {
template <class Project>
void suitable_parameters(Project& project, bool cubic) {
    if constexpr (requires { named_parameters(project); }) {
        if (cubic) {
            project.structure().space_group.name_h_m = "P m -3 m";
            project.structure().space_group.it_number = 221;
            for (auto& site : project.structure().atom_sites) {
                site->fract_x.value = 0;
                site->fract_y.value = 0;
                site->fract_z.value = 0;
            }
        }
        project.calculate();
        const auto candidates = named_parameters(project);
        bool independent = false;
        for (const auto& named : candidates) {
            independent = independent || named.unique_name == "phase.atom_site.A.adp_iso";
            CHECK_MESSAGE(named.unique_name != "phase.atom_site.B.adp_iso",
                          "Suitable aliases must exclude an active user-dependent target");
            if (cubic) {
                CHECK_MESSAGE(named.unique_name != "phase.cell.length_b",
                              "Suitable aliases must exclude a symmetry-dependent cell field");
                CHECK_MESSAGE(named.unique_name != "phase.cell.angle_beta",
                              "Suitable aliases must exclude a symmetry-fixed cell field");
                CHECK_MESSAGE(named.unique_name != "phase.atom_site.A.fract_x",
                              "Suitable aliases must exclude a Wyckoff-fixed coordinate");
            }
        }
        CHECK_MESSAGE(independent,
                      "A fixed but independently selectable parameter must remain suitable");
    } else {
        FAIL_CHECK("Suitable alias parameters must be enumerated by the core");
    }
}
}  // namespace
TEST_CASE("Alias candidates exclude dependents while retaining ordinary fixed parameters") {
    auto project = relation_edit_project();
    suitable_parameters(project, false);
}
TEST_CASE("Alias candidates exclude symmetry fixed coordinates and cell fields") {
    auto project = relation_edit_project();
    suitable_parameters(project, true);
}
