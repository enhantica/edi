#include <doctest/doctest.h>

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
}

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
    CHECK_MESSAGE(*ties[7].fixed_value == .25,
                  "The source mirror lies at y equal to one quarter");
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
