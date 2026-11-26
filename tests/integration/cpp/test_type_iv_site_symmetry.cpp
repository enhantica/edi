#include <doctest/doctest.h>

#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>

#include "edi/io.hpp"
#include "edi/symmetry.hpp"

namespace {
std::string input(const std::string& name) {
    const auto path = std::filesystem::path(__FILE__).parent_path() /
                      "../../fixtures/magnetic_type_iv" / (name + ".edi");
    std::ifstream stream(path);
    REQUIRE_MESSAGE(stream.good(), "The synthetic type IV input is committed in this repo");
    return {std::istreambuf_iterator<char>(stream), {}};
}
}  // namespace

TEST_CASE("The native structure page accepts verified type IV Wyckoff letters") {
    for (const std::string letter : {"a", "b", "c", "d", "e"}) {
        CAPTURE(letter);
        const auto model = edi::structure_from_edi_text(input("pnma-" + letter));
        CHECK_MESSAGE(edi::takes_wyckoff_letter(model),
                      "A verified type IV structure exposes its magnetic Wyckoff letters");
        CHECK_MESSAGE(model.atom_sites[0]->wyckoff_letter == letter,
                      "The displayed letter agrees with the independent magnetic table");
    }
}

TEST_CASE("The native type IV mirror exposes its two free coordinates") {
    const auto model = edi::structure_from_edi_text(input("pnma-d"));
    const auto ties = edi::structure_ties(model);
    REQUIRE_MESSAGE(ties.size() >= 9, "The page reports cell and site ties");
    CHECK_MESSAGE(ties[6].kind == edi::TieKind::Independent,
                  "The raw source leaves x free on the magnetic mirror");
    CHECK_MESSAGE(ties[7].kind == edi::TieKind::Fixed,
                  "The raw source fixes y on the magnetic mirror");
    REQUIRE_MESSAGE(ties[7].fixed_value.has_value(), "A fixed coordinate supplies its value");
    CHECK_MESSAGE(*ties[7].fixed_value == .25, "The source mirror lies at y equal to one quarter");
    CHECK_MESSAGE(ties[8].kind == edi::TieKind::Independent,
                  "The raw source leaves z free on the magnetic mirror");
}

TEST_CASE("The native type IV mirror projects a near-special imported coordinate") {
    auto text = input("pnma-d");
    const auto offset = text.find("0.13 0.25 0.31");
    REQUIRE_MESSAGE(offset != std::string::npos, "The independent mirror witness is present");
    text.replace(offset, std::string("0.13 0.25 0.31").size(), "0.13 0.250009 0.31");
    const auto model = edi::structure_from_edi_text(text);
    CHECK_MESSAGE(model.atom_sites[0]->fract_y.value == .25,
                  "The native importer publishes the completed mirror coordinate");
}

TEST_CASE("The native type IV anisotropic input reaches the structure page") {
    const auto model = edi::structure_from_edi_text(input("pnma-aniso"));
    REQUIRE_MESSAGE(model.atom_site_aniso.size() == 1,
                    "The native reader admits the type IV anisotropic site");
    const auto ties = edi::structure_ties(model);
    REQUIRE_MESSAGE(ties.size() >= 15, "The page includes six tensor component ties");
    CHECK_MESSAGE(ties[12].kind == edi::TieKind::Fixed,
                  "The source mirror fixes the displayed U12 component");
    CHECK_MESSAGE(ties[14].kind == edi::TieKind::Fixed,
                  "The source mirror fixes the displayed U23 component");
}

TEST_CASE("Equivalent type IV signed rows retain verified metadata in the native editor") {
    auto model = edi::structure_from_edi_text(input("pnma-d"));
    auto operations = model.magnetic.get().operations;
    REQUIRE_MESSAGE(!operations.empty(),
                    "The type IV editor witness holds its full signed operations");
    std::reverse(operations.begin(), operations.end());
    for (auto& [id, xyz] : operations) {
        if (xyz == "x,y,z,1" || xyz == "x,y,z,+1") xyz = "x+1,y,z,+1";
    }
    edi::set_magnetic_symmetry(model, operations, model.magnetic.get().centerings);
    CHECK_MESSAGE(
        model.magnetic.get().group.number_bns == "62.452",
        "Equivalent type IV signed sets keep their verified BNS identity after an editor change");
    CHECK_MESSAGE(model.atom_sites[0]->wyckoff_letter == "d",
                  "The native symmetry edit republishes the independently known mirror letter");
    CHECK_MESSAGE(model.atom_sites[0]->fract_y.value == .25,
                  "The native symmetry edit retains the completed mirror coordinate");
}
TEST_CASE("The native type IV setting edit derives its letter in the requested axes") {
    auto model = edi::structure_from_edi_text(input("pnma-d"));
    auto description = model.magnetic.get();
    description.propagation_vectors.clear();
    description.parent = {};
    model.magnetic = description;
    const auto settings = edi::magnetic_setting_transforms(model);
    const std::string target = "b,c,a;0,0,0";
    REQUIRE_MESSAGE(std::find(settings.begin(), settings.end(), target) != settings.end(),
                    "The orthorhombic BNS setting list contains the cyclic axis permutation");
    edi::set_magnetic_setting(model, target);
    CHECK_MESSAGE(edi::held_magnetic_setting(model) == target,
                  "The setting editor retains the nonidentity requested BNS transform");
    // Under x_current=(z_standard,x_standard,y_standard), the magnetic mirror is z=1/4.
    // The unchanged .13,.25,.31 site is general in this new setting.
    CHECK_MESSAGE(model.atom_sites[0]->wyckoff_letter == "e",
                  "A setting change retracts the old mirror letter and derives the raw "
                  "general-position letter");
    const auto ties = edi::structure_ties(model);
    REQUIRE_MESSAGE(ties.size() >= 9,
                    "The completed cyclic setting publishes every coordinate tie");
    for (std::size_t axis = 6; axis < 9; ++axis)
        CHECK_MESSAGE(ties[axis].kind == edi::TieKind::Independent,
                      "All three coordinates are independent at the raw general position in the "
                      "new setting");
}
TEST_CASE("Native type IV ADP conversion and new atoms use magnetic site geometry") {
    auto model = edi::structure_from_edi_text(input("pnma-d"));
    edi::change_adp_type(model, *model.atom_sites[0], "Uani");
    REQUIRE_MESSAGE(model.atom_site_aniso.size() == 1,
                    "A live type IV isotropic-to-anisotropic edit creates the tensor row");
    const auto ties = edi::structure_ties(model);
    REQUIRE_MESSAGE(ties.size() >= 15,
                    "The edited tensor publishes its six magnetic site relations");
    CHECK_MESSAGE(ties[12].kind == edi::TieKind::Fixed,
                  "The magnetic mirror fixes U12 after a live ADP conversion");
    CHECK_MESSAGE(ties[14].kind == edi::TieKind::Fixed,
                  "The magnetic mirror fixes U23 after a live ADP conversion");
    const auto added = edi::new_atom_site(model, [] { return .137; });
    CHECK_MESSAGE(added.wyckoff_letter != ".",
                  "A new atom in a verified type IV setting receives its derived magnetic letter");
}
