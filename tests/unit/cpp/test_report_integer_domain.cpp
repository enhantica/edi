// SPDX-License-Identifier: BSD-3-Clause
#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <limits>
#include <sstream>
#include <string>
#include <variant>
#include <vector>

#include "edi/report_model.hpp"
#include "edi/report_html.hpp"
#include "../../../core/src/json.hpp"

namespace {
const std::vector<std::string> index_paths{
    "structures.0.scene.atoms.0.row", "structures.0.scene.atoms.0.parts.0.row",
    "structures.0.scene.atoms.0.major", "structures.0.scene.bonds.0.row",
    "structures.0.scene.bonds.0.atom_1", "structures.0.scene.bonds.0.atom_2",
    "structures.0.scene.labels.0.atom", "structures.0.drawing.spheres.0.atom",
    "structures.0.drawing.cylinders.0.atom", "structures.0.drawing.shared.0",
    "structures.0.labels.0.atom", "experiments.0.pattern.series.0.rows.0"};

edi::json::Value seed() {
    const auto path = std::filesystem::path(__FILE__).parent_path().parent_path().parent_path() /
                      "fixtures/report_integer_domain/schema-seed.json";
    std::ifstream input(path);
    REQUIRE_MESSAGE(input.good(), "The JSON integer gate loads its labelled schema regression seed");
    return edi::json::parse(std::string(std::istreambuf_iterator<char>(input), {}));
}
void replace(edi::json::Value& value, const std::string& path, edi::json::Value replacement) {
    std::istringstream words(path);
    std::string key;
    auto* target = &value;
    while (std::getline(words, key, '.')) {
        if (std::holds_alternative<edi::json::Array>(target->data)) {
            target = &std::get<edi::json::Array>(target->data).at(std::stoul(key));
        } else {
            auto& object = std::get<edi::json::Object>(target->data);
            auto found = std::find_if(object.begin(), object.end(), [&](auto& member) { return member.first == key; });
            REQUIRE_MESSAGE(found != object.end(), "Each integer route exists in the schema seed");
            target = &found->second;
        }
    }
    *target = std::move(replacement);
}
}

TEST_CASE("Report signed JSON integers reject null fractions and both range overflows") {
    const auto original = seed();
    for (const auto& path : {"structures.0.scene.atoms.0.cluster_id", "correlations.available"}) {
        for (const auto& invalid : {edi::json::Value(nullptr), edi::json::Value(1.25),
                                   edi::json::Value(1e300), edi::json::Value(2147483648.0),
                                   edi::json::Value(-2147483649.0)}) {
            auto document = original;
            replace(document, path, invalid);
            INFO(path, " ", edi::json::write(invalid));
            CHECK_THROWS_AS_MESSAGE(edi::report_from_json(edi::json::write(document)), std::invalid_argument,
                                    "Signed parsed numbers are refused before an undefined or truncating conversion");
        }
    }
}

TEST_CASE("Report index JSON integers reject every invalid scene and pattern route") {
    const auto original = seed();
    const double outside_size = std::ldexp(1.0, std::numeric_limits<std::size_t>::digits);
    for (const auto& path : index_paths) {
        for (const auto& invalid : {edi::json::Value(nullptr), edi::json::Value(1.25),
                                   edi::json::Value(1e300), edi::json::Value(-2.0),
                                   edi::json::Value(9007199254740994.0), edi::json::Value(outside_size)}) {
            auto document = original;
            replace(document, path, invalid);
            INFO(path, " ", edi::json::write(invalid));
            CHECK_THROWS_AS_MESSAGE(edi::report_from_json(edi::json::write(document)), std::invalid_argument,
                                    "Every index fits both the JSON exact-integer domain and the target size_t");
        }
    }
}

TEST_CASE("Report integer JSON controls retain signed endpoints nonzero indices and missing rows") {
    auto document = seed();
    auto atom = document.at("structures").array("structures").front().at("scene").at("atoms").array("atoms").front();
    const auto part = atom.at("parts").array("parts").front();
    replace(atom, "parts", edi::json::Array(8, part));
    replace(document, "structures.0.scene.atoms", edi::json::Array(8, atom));
    replace(document, "structures.0.scene.atoms.0.cluster_id", -2147483648.0);
    replace(document, "correlations.available", 2147483647.0);
    for (const auto& path : index_paths) replace(document, path, path.starts_with("experiments.") ? -1.0 : 7.0);
    const auto text = edi::json::write(document);
    CHECK_MESSAGE(edi::json::write(edi::json::parse(edi::report_to_json(edi::report_from_json(text)))) == text,
                  "Valid destination endpoints and the explicit pattern-gap sentinel survive unchanged");
    auto model = edi::report_from_json(text);
    model.analysis = {{"authored", "Authored ragged table", {},
        {{"first", "second"}, {{}, {"authored-cell"}, {"one", "two", "extra"}}}}};
    for (const auto count : {0, 1, 5}) {
        model.correlations->values.assign(count, 0.5);
        model.experiments.front().pattern.hover.assign(count, {"authored hover"});
        const auto imported = edi::report_from_json(edi::report_to_json(model));
        CHECK_MESSAGE(edi::report_html(imported).find("authored-cell") != std::string::npos,
            "HTML safely renders ragged tables and correlation dimensions with local bounds");
        CHECK_MESSAGE(edi::report_static_html(imported, 400).find("authored-cell") != std::string::npos,
            "Static PDF text safely renders ragged tables and correlation dimensions with local bounds");
    }

}
