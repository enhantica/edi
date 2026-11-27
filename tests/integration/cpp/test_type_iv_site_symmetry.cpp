#include <doctest/doctest.h>

#include <algorithm>
#include <array>
#include <chrono>
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

TEST_CASE("Edi save and reopen preserve a type IV site's written general position") {
    auto project = edi::empty_project("saved_general", "");
    auto structure =
        std::make_shared<edi::Structure>(edi::structure_from_edi_text(input("pnma-e")));
    auto& site = *structure->atom_sites[0];
    const auto original = edi::structure_ties(*structure);
    REQUIRE_MESSAGE((original.size() >= 9 && original[7].kind == edi::TieKind::Independent),
                    "The written general site begins with a free y coordinate");
    // The value takes the place of a published fit result at the save boundary.
    site.fract_y.value = .2500001;
    site.fract_y.free = true;
    project.structures.push_back(structure);
    const auto folder =
        std::filesystem::temp_directory_path() /
        ("edi-saved-magnetic-position-" +
         std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    struct Cleanup {
        std::filesystem::path path;
        ~Cleanup() { std::filesystem::remove_all(path); }
    } cleanup{folder};
    edi::save_project(project, folder.string());
    const auto reopened = edi::load_project(folder.string());
    const auto& restored = reopened.structure();
    const auto& atom = *restored.atom_sites[0];
    CHECK_MESSAGE(atom.wyckoff_letter == "e",
                  "The fitted site reopens at its written general letter");
    CHECK_MESSAGE(atom.fract_y.value.get() == .2500001,
                  "The fitted coordinate reopens at the saved value close to the mirror");
    CHECK_MESSAGE(atom.fract_y.free.get(), "Reopen retains the saved free flag beside the mirror");
    const auto ties = edi::structure_ties(restored);
    REQUIRE_MESSAGE(ties.size() >= 9, "Reopen exposes all three positional ties");
    for (std::size_t axis = 6; axis < 9; ++axis)
        CHECK_MESSAGE(ties[axis].kind == edi::TieKind::Independent,
                      "Reopening a saved general site keeps all three coordinates independent");
}

TEST_CASE("Edi type IV CIF loading detects a mirror only when its letter is absent") {
    auto cif = input("pnma-e");
    const auto replace = [&cif](const std::string& from, const std::string& to) {
        const auto offset = cif.find(from);
        REQUIRE_MESSAGE(offset != std::string::npos,
                        "The independent reference contains the CIF conversion field");
        cif.replace(offset, from.size(), to);
    };
    replace("_edi.schema_version 3\n", "");
    replace("_space_group.name_h_m", "_space_group_name_H-M_alt");
    replace("_parent_space_group.reference_setting standard\n", "");
    replace("_parent_space_group.derived true\n", "");
    replace(
        "loop_\n_space_group_magn_transforms.id\n_space_group_magn_transforms.Pp_abc\n"
        "_space_group_magn_transforms.source\n1 'a,b,c;0,0,0' BNS\n",
        "_space_group_magn.transform_BNS_Pp_abc 'a,b,c;0,0,0'\n");
    replace("_atom_site.id", "_atom_site_label");
    replace("_atom_site.wyckoff_letter", "_atom_site_Wyckoff_symbol");
    replace("_atom_site.adp_iso", "_atom_site_B_iso_or_equiv");
    const auto extras = cif.find("loop_\n_magnetic_form_factor.");
    REQUIRE_MESSAGE(extras != std::string::npos,
                    "The independent reference includes optional moment metadata");
    cif.erase(extras);
    replace("Co1 Co e 0.13 0.23 0.31", "Co1 Co e 0.13 0.2500001 0.31");
    const auto declared = edi::structure_from_edi_text(cif, "declared.mcif");
    CHECK_MESSAGE(declared.atom_sites[0]->wyckoff_letter == "e",
                  "A CIF's supplied general letter is preserved by the edi reader");
    CHECK_MESSAGE(declared.atom_sites[0]->fract_y.value.get() == .2500001,
                  "A supplied general letter prevents projecting the near-mirror value");
    const auto declared_ties = edi::structure_ties(declared);
    REQUIRE_MESSAGE(declared_ties.size() >= 9, "The declared site has three positional ties");
    CHECK_MESSAGE(declared_ties[7].kind == edi::TieKind::Independent,
                  "The declared general group's near-mirror y stays independent");
    replace("_atom_site_Wyckoff_symbol\n", "");
    replace("Co1 Co e 0.13 0.2500001 0.31", "Co1 Co 0.13 0.2500001 0.31");
    const auto detected = edi::structure_from_edi_text(cif, "missing.mcif");
    CHECK_MESSAGE(
        detected.atom_sites[0]->wyckoff_letter == "d",
        "Without a CIF declaration the edi reader detects the independent mirror letter");
    const auto ties = edi::structure_ties(detected);
    REQUIRE_MESSAGE(ties.size() >= 9, "The detected site has three positional ties");
    CHECK_MESSAGE((ties[7].kind == edi::TieKind::Fixed && ties[7].fixed_value == .25),
                  "Detection of the undeclared site ties y to the exact mirror value");
}
