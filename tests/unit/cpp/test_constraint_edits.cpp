#include <doctest/doctest.h>

#include <array>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <string>
#include <type_traits>

#include "edi/categories.hpp"
#include "edi/edit.hpp"
#include "edi/io.hpp"
#include "edi/validation.hpp"
#include "xray_doublet/physical_relation_inputs.hpp"

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
            CHECK_MESSAGE(project.aliases[0]->id.value() == before.aliases[0]->id.value(),
                          "Closed append and removal must retain the source alias identity");
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
            CHECK_MESSAGE(project.constraints[0]->id.value() == before.constraints[0]->id.value(),
                          "Closed append and removal must retain the source constraint identity");
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
        project.structure().atom_sites[1]->adp_iso.value = 9;
        project.calculate();
        CHECK_MESSAGE(project.structure().atom_sites[1]->adp_iso.value == 9,
                      "A disabled core constraint must not complete its target on calculation");
        for (auto& row : project.constraints) Edit::assign(row->enabled, true)();
        project.calculate();
        CHECK_MESSAGE(project.structure().atom_sites[1]->adp_iso.value == doctest::Approx(1.6),
                      "Reenabled core constraints must apply at the next calculation");
        for (auto& row : project.constraints) Edit::assign(row->enabled, false)();
        project.structure().atom_sites[1]->adp_iso.value = 7;
        project.calculate();
        CHECK_MESSAGE(project.structure().atom_sites[1]->adp_iso.value == 7,
                      "Disabling again must leave the directly assigned target independent");
    } else {
        FAIL_CHECK("The core must retain disabled constraints without applying them");
    }
}
}  // namespace

TEST_CASE("Alias core edits preserve source rows through append duplicate and removal") {
    auto project = relation_edit_project();
    alias_edits(project);
}
TEST_CASE("Constraint core edits preserve source rows through append duplicate and removal") {
    auto project = relation_edit_project();
    constraint_edits(project);
}
TEST_CASE("Constraint core enable edits retain the inactive declaration") {
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

namespace {
void physical_relation_diagnostics(std::size_t family) {
    const auto& input = physical_relation_inputs::inputs.at(family);
    for (const std::string entrance : {"refresh", "calculate"}) {
        CAPTURE(std::string(input.name));
        CAPTURE(entrance);
        struct Files {
            std::filesystem::path root =
                std::filesystem::temp_directory_path() /
                ("physical-relations-" +
                 std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
            ~Files() { std::filesystem::remove_all(root); }
        } files;
        for (const auto& dir : {"structures", "experiments", "analysis"})
            std::filesystem::create_directories(files.root / dir);
        std::ofstream(files.root / "structures/phase.edi") << input.structure;
        std::ofstream(files.root / "experiments/bank.edi") << input.experiment;
        std::ofstream(files.root / "analysis/analysis.edi") << input.analysis;
        auto project = edi::load_project(files.root.string());
        CHECK_NOTHROW_MESSAGE(
            edi::refresh_relations(project),
            "ADR-0078 valid physical relations must cross the consumer boundary");
        edi::Parameter *source = nullptr, *middle = nullptr, *target = nullptr;
        for (const auto& slot : edi::named_slots(project)) {
            if (slot.unique_name == "phase.atom_site.X.fract_x") source = slot.parameter;
            if (slot.unique_name == "bank.instrument.calib_twotheta_offset")
                middle = slot.parameter;
            if (slot.unique_name == std::string("bank.") + input.target) target = slot.parameter;
        }
        REQUIRE_MESSAGE((source && middle && target),
                        "ADR-0078 the consumer witness must resolve the complete authored chain");
        const std::array<double, 2> before{middle->value.get(), target->value.get()};
        const std::array<std::uint64_t, 2> clocks{middle->epoch.value(), target->epoch.value()};
        source->value = 0.4;
        bool structured = false;
        try {
            if (entrance == "refresh")
                edi::refresh_relations(project);
            else
                project.calculate();
        } catch (const edi::DomainValidationError& error) {
            structured = true;
            REQUIRE_MESSAGE(
                error.diagnostics().size() == 1,
                "ADR-0078 the native consumer must preserve one physical error diagnostic");
            const auto& diagnostic = error.diagnostics()[0];
            CHECK_MESSAGE(diagnostic.severity == edi::Severity::Error,
                          "ADR-0078 the consumer must retain error severity for physical refusal");
            CHECK_MESSAGE(diagnostic.code.starts_with("crysta.domain.constraint_"),
                          "ADR-0078 the native consumer must retain the engine domain code");
            CHECK_MESSAGE(
                (diagnostic.message.find("domain_relation") != std::string::npos &&
                 diagnostic.message.find(input.target) != std::string::npos),
                "ADR-0078 the native consumer must name the later relation and physical target");
        } catch (const std::exception&) {
            // The assertion below distinguishes a typed refusal from a generic escape.
        }
        CHECK_MESSAGE(structured,
                      "ADR-0078 the native consumer must refuse with DomainValidationError");
        CHECK_MESSAGE(
            (middle->value.get() == before[0] && target->value.get() == before[1] &&
             middle->epoch.value() == clocks[0] && target->epoch.value() == clocks[1]),
            "ADR-0078 a consumer refusal must preserve dependent values and write epochs");
        CHECK_MESSAGE(
            !edi::apply_relations(project),
            "ADR-0078 the consumer trial completion must refuse an invalid physical chain");
        CHECK_MESSAGE(
            (middle->value.get() == before[0] && target->value.get() == before[1]),
            "ADR-0078 a later consumer trial failure must not publish an earlier dependent");
        source->value = 0.1;
        CHECK_NOTHROW_MESSAGE(edi::refresh_relations(project),
                              "ADR-0078 a refused consumer must permit a valid relation retry");
        CHECK_MESSAGE(edi::apply_relations(project),
                      "ADR-0078 a valid consumer retry must complete the physical chain");
        CHECK_MESSAGE(middle->value.get() == doctest::Approx(0.06),
                      "ADR-0078 a valid consumer retry must complete the first affine relation");
    }
}
}  // namespace

TEST_CASE("Physical relation second wavelength ratio retains consumer diagnostics") {
    physical_relation_diagnostics(0);
}

TEST_CASE("Physical relation second wavelength retains consumer diagnostics") {
    physical_relation_diagnostics(1);
}

TEST_CASE("Physical relation polarization coefficient retains consumer diagnostics") {
    physical_relation_diagnostics(2);
}

TEST_CASE("Physical relation monochromator angle retains consumer diagnostics") {
    physical_relation_diagnostics(3);
}

TEST_CASE("Physical relation March Dollase fraction retains consumer diagnostics") {
    physical_relation_diagnostics(4);
}
