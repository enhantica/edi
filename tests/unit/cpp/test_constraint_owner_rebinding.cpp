#include <doctest/doctest.h>

#include <filesystem>
#include <string>
#include <utility>

#include "edi/calculation.hpp"
#include "edi/io.hpp"

namespace {
edi::Project vehicle() {
    return edi::load_project(
        (std::filesystem::path(__FILE__).parent_path().parent_path().parent_path() /
         "fixtures/constraint_expressions/project")
            .string());
}
void prepare(edi::Project& p) {
    p.constraints.erase_at(0);
    p.aliases[0]->parameter_unique_name = "phase.atom_site.A.fract_x";
    p.aliases[1]->parameter_unique_name = "phase.atom_site.B.fract_y";
    p.constraints[0]->expression = "b = 3*a+.1";
}
void inspect(edi::Project& p, bool window) {
    // Direct collection access intentionally precedes structure(), calculate() and adoption.
    auto child = p.structures.front();
    const auto result =
        window ? edi::window_geometry(*child, {}).geometry : child->current_geometry();
    CHECK_MESSAGE(child->atom_sites[1]->fract_y.value.get() == doctest::Approx(.61),
                  "Project copy and move must bind children before a convenience accessor runs");
    bool found = false;
    for (std::size_t i = 0; i < result.expanded_atom_sites.atom_site_id.size(); ++i) {
        if (result.expanded_atom_sites.atom_site_id[i] == "B") {
            found = true;
            CHECK_MESSAGE(result.expanded_atom_sites.cartn_y[i] == doctest::Approx(4.1 * .61),
                          "Copied and moved children must calculate the destination relation");
        }
    }
    CHECK_MESSAGE(found, "Owner rebinding must preserve the dependent atom in geometry");
}
void ownership(const std::string& operation) {
    for (bool window : {false, true}) {
        CAPTURE(operation);
        CAPTURE(window);
        auto source = vehicle();
        prepare(source);
        if (operation == "copy") {
            auto copied = source;
            source.constraints[0]->expression = "b = .9";
            inspect(copied, window);
        } else if (operation == "move") {
            auto moved = std::move(source);
            inspect(moved, window);
        } else if (operation == "copy-assignment") {
            edi::Project copied;
            copied = source;
            source.constraints[0]->expression = "b = .9";
            inspect(copied, window);
        } else {
            edi::Project moved;
            moved = std::move(source);
            inspect(moved, window);
        }
    }
}
}  // namespace

TEST_CASE("Project copy binds direct children to its own relation declarations") {
    ownership("copy");
}
TEST_CASE("Project move binds direct children before any accessor") { ownership("move"); }
TEST_CASE("Project copy assignment binds direct children independently") {
    ownership("copy-assignment");
}
TEST_CASE("Project move assignment rebinds direct children immediately") {
    ownership("move-assignment");
}

TEST_CASE("Native collection transfer binds retained children before geometry reads") {
    for (const std::string route : {"insert", "replace", "assign"}) {
        for (bool window : {false, true}) {
            CAPTURE(route);
            CAPTURE(window);
            auto donor = vehicle();
            auto destination = vehicle();
            prepare(destination);
            auto held = donor.structures.front();
            donor.structures.clear();
            if (route == "insert") destination.structures.clear();
            if (route == "assign")
                destination.structures.assign({held});
            else if (route == "replace")
                destination.structures.replace_at(0, held);
            else
                destination.structures.push_back(held);
            const auto result =
                window ? edi::window_geometry(*held, {}).geometry : held->current_geometry();
            CHECK_MESSAGE(
                held->atom_sites[1]->fract_y.value.get() == doctest::Approx(.61),
                "Native collection mutation must establish the destination owner immediately");
            CHECK_MESSAGE(!result.expanded_atom_sites.atom_site_id.empty(),
                          "The directly retained child must publish destination geometry");
        }
    }
}
