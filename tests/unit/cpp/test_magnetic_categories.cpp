#include <doctest/doctest.h>

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iterator>

#include "edi/categories.hpp"
#include "edi/io.hpp"

TEST_CASE("Magnetic Main groups expose the four independent cobalt components") {
    const auto fixture = std::filesystem::path(__FILE__).parent_path() /
                         "../../fixtures/magnetic_pnma/magnetic.edi";
    std::ifstream input(fixture);
    REQUIRE_MESSAGE(input.good(), "The native magnetic fixture must be readable");
    const std::string text{std::istreambuf_iterator<char>(input), {}};
    auto structure = edi::structure_from_edi_text(text);
    const auto categories = edi::structure_categories(structure);
    const auto category = [&](const std::string& id) {
        return std::find_if(categories.begin(), categories.end(),
                            [&](const auto& row) { return row.id == id; });
    };
    const auto group = category("space_group_magn");
    const auto propagation = category("parent_propagation_vector");
    const auto moments = category("atom_site_moment");
    REQUIRE_MESSAGE(group != categories.end(), "The Main model exposes the magnetic space group");
    REQUIRE_MESSAGE(propagation != categories.end(),
                    "The Main model exposes the propagation vector");
    REQUIRE_MESSAGE(moments != categories.end(),
                    "The Main model exposes the moment companion rows");
    CHECK_MESSAGE(group < propagation, "The propagation vector follows the magnetic space group");
    CHECK_MESSAGE(propagation < moments, "The magnetic moments follow the propagation vector");
    CHECK_MESSAGE(moments->rows == 6, "The cobalt model presents all six asymmetric atom sites");
    CHECK_MESSAGE(moments->fields.size() >= 6,
                  "The all-site table retains the six magnetic component fields");
    const auto independent = std::count_if(moments->fields.begin(), moments->fields.end(),
                                           [](const auto& field) { return field.refinable; });
    CHECK_MESSAGE(independent == 4, "The core Main groups allow only four independent components");
}
