#include <doctest/doctest.h>

#include <array>
#include <cmath>
#include <memory>
#include <numbers>
#include <string>

#include "edi/io.hpp"
#include "edi/symmetry.hpp"

namespace {
edi::Project primitive(double z) {
    auto structure = edi::structure_from_edi_text(R"(data_phase
_edi.schema_version 3
_cell.length_a 5
_cell.length_b 4
_cell.length_c 3
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "P 1"
loop_
_space_group_symop_magn_operation.id
_space_group_symop_magn_operation.xyz
1 x,y,z,+1
loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.wyckoff_letter
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
_atom_site.adp_type
M Co a .13 .21 .32 1 0 Biso
loop_
_atom_site_moment.label
_atom_site_moment.crystalaxis_x
_atom_site_moment.crystalaxis_y
_atom_site_moment.crystalaxis_z
M 1 1 0
)");
    structure.atom_site_moment[0]->crystalaxis_z.value = z;
    edi::Project project;
    project.structures.clear();
    project.experiments.clear();
    project.structures.push_back(std::make_shared<edi::Structure>(std::move(structure)));
    project.experiments.push_back(
        std::make_shared<edi::BraggPdExperiment>(edi::simulation_experiment("bank", {}, "phase")));
    return project;
}

void alias(edi::Project& project, const std::string& id, const std::string& name) {
    auto row = std::make_shared<edi::ParameterAlias>();
    row->id = id;
    row->parameter_unique_name = name;
    project.aliases.push_back(row);
}

std::string snapshot(const edi::Project& project) {
    return edi::block_edi_text(project, edi::BlockKind::PROJECT) +
           edi::block_edi_text(project, edi::BlockKind::STRUCTURE, "phase") +
           edi::block_edi_text(project, edi::BlockKind::ANALYSIS);
}

void check_trial(const std::string& metric, const std::string& form, bool witness,
                 bool chain = false) {
    auto project = primitive(witness ? 0 : 1);
    alias(project, "m", "phase.atom_site_moment.M.crystalaxis_x");
    alias(project, "q", "phase.cell." + metric);
    const bool angle = metric.starts_with("angle_");
    const double initial = angle ? 90 : (metric == "length_a" ? 5 : metric == "length_b" ? 4 : 3);
    auto relation = std::make_shared<edi::ParameterConstraint>();
    relation->id = "q";
    relation->expression = "q = " + std::to_string(initial) + " + 10*(m-1)";
    if (chain) {
        alias(project, "r", "phase.atom_site.M.fract_x");
        auto intermediate = std::make_shared<edi::ParameterConstraint>();
        intermediate->id = "r";
        intermediate->expression = "r = .13 + .01*(m-1)";
        project.constraints.push_back(intermediate);
        relation->expression = "q = " + std::to_string(initial) + " + 1000*(r-.13)";
    }
    project.constraints.push_back(relation);
    edi::complete_relations(project);
    const auto before = snapshot(project);
    const auto& structure = *project.structures[0];
    const auto& moment = *structure.atom_site_moment[0];
    // In the orthogonal input cell Cartesian=(Mx,My,Mz). A Cartesian x=2
    // requests (2,1,z); spherical radius=sqrt(6) requests sqrt(2)*(1,1,1).
    const double requested = form == "cartesian" ? 2 : std::sqrt(6.0);
    if (angle) {
        // Independent unit-axis basis: a=(1,0,0), b=(cos gamma,sin gamma,0),
        // c=(cos beta,(cos alpha-cos beta*cos gamma)/sin gamma,positive cz).
        const double mx = form == "cartesian" ? 2 : std::sqrt(2.0);
        const double my = form == "cartesian" ? 1 : std::sqrt(2.0);
        const double mz = witness ? 0 : my;
        const double moved = (90 + 10 * (mx - 1)) * std::numbers::pi / 180;
        const double alpha = metric == "angle_alpha" ? moved : std::numbers::pi / 2;
        const double beta = metric == "angle_beta" ? moved : std::numbers::pi / 2;
        const double gamma = metric == "angle_gamma" ? moved : std::numbers::pi / 2;
        const double cy = (std::cos(alpha) - std::cos(beta) * std::cos(gamma)) / std::sin(gamma);
        const double cz = std::sqrt(1 - std::pow(std::cos(beta), 2) - cy * cy);
        const std::array<double, 3> landed{mx + my * std::cos(gamma) + mz * std::cos(beta),
                                           my * std::sin(gamma) + mz * cy, mz * cz};
        CHECK_MESSAGE(
            std::hypot(landed[0] - mx, landed[1] - my, landed[2] - mz) > .01,
            "R3-F2 the independent final-cell basis proves the requested moment cannot land");
    }
    const auto edit = edi::moment_edit(project, structure, moment, form, 0, requested);
    CHECK_MESSAGE(snapshot(project) == before,
                  "R3-F2 a converted trial must leave every real project document unchanged");
    if (angle) {
        CHECK_MESSAGE(
            !edit.refusal.empty(),
            "R3-F2 a cell-angle relation that changes the requested direction refuses visibly");
        CHECK_MESSAGE(edit.writes.empty(),
                      "R3-F2 a refused converted edit publishes no partial write set");
    } else {
        CHECK_MESSAGE(
            edit.refusal.empty(),
            "R3-F2 changing a length preserves unit-axis moments and remains representable");
        REQUIRE_MESSAGE(
            edit.writes.size() == 3,
            "R3-F2 the unconstrained P1 length control returns all independent components");
        for (const auto& [axis, value] : edit.writes) {
            const double expected = form == "cartesian" ? (axis == 0 ? 2 : 1) : std::sqrt(2.0);
            CHECK_MESSAGE(value == doctest::Approx(expected),
                          "R3-F2 length-only relations retain the closed-form requested moment");
        }
    }
}
}  // namespace

TEST_CASE("Converted magnetic edits validate the final related cell") {
    for (const std::string metric :
         {"angle_alpha", "angle_beta", "angle_gamma", "length_a", "length_b", "length_c"}) {
        for (const std::string form : {"cartesian", "spherical"}) {
            CAPTURE(metric);
            CAPTURE(form);
            for (bool chain : {false, true}) {
                CAPTURE(chain);
                check_trial(metric, form, false, chain);
            }
        }
    }
}

TEST_CASE("A gamma relation cannot silently change the requested Cartesian moment") {
    // Reviewer witness: gamma=90+10*(Mx-1), M=(1,1,0), request Cartesian x=2.
    // Final Cartesian=(2+cos(100deg),sin(100deg),0), unequal to (2,1,0).
    check_trial("angle_gamma", "cartesian", true);
}
