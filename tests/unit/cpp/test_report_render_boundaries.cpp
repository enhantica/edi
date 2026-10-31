// SPDX-License-Identifier: BSD-3-Clause
#include <doctest/doctest.h>

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <variant>
#include <vector>

#include "../../../core/src/json.hpp"
#include "edi/report_html.hpp"
#include "edi/report_model.hpp"

namespace {
void render_boundary_replace(edi::json::Value& value, const std::string& path,
                             edi::json::Value replacement) {
    std::istringstream tokens(path);
    std::string key;
    auto* target = &value;
    while (std::getline(tokens, key, '.')) {
        if (std::holds_alternative<edi::json::Array>(target->data)) {
            target = &std::get<edi::json::Array>(target->data).at(std::stoul(key));
        } else {
            auto& members = std::get<edi::json::Object>(target->data);
            const auto found =
                std::find_if(members.begin(), members.end(),
                             [&](const auto& member) { return member.first == key; });
            REQUIRE_MESSAGE(found != members.end(), "The authored schema route must exist");
            target = &found->second;
        }
    }
    *target = std::move(replacement);
}

edi::ReportModel render_boundary_model() {
    const auto fixture =
        std::filesystem::path(__FILE__).parent_path().parent_path().parent_path() /
        "fixtures/report_integer_domain/schema-seed.json";
    std::ifstream input(fixture);
    REQUIRE_MESSAGE(input.good(), "The existing report schema fixture is available");
    auto document = edi::json::parse(std::string(std::istreambuf_iterator<char>(input), {}));
    auto atom = document.at("structures")
                    .array("structures")
                    .front()
                    .at("scene")
                    .at("atoms")
                    .array("atoms")
                    .front();
    const auto part = atom.at("parts").array("parts").front();
    render_boundary_replace(atom, "parts", edi::json::Array{part});
    render_boundary_replace(atom, "major", 0.0);
    render_boundary_replace(atom, "drawn", true);
    render_boundary_replace(document, "structures.0.scene.atoms", edi::json::Array{atom, atom});
    for (const auto& path : {"scene.bonds.0.atom_1", "scene.bonds.0.atom_2", "scene.labels.0.atom",
                             "drawing.spheres.0.atom", "drawing.shared.0", "labels.0.atom"}) {
        render_boundary_replace(document, std::string("structures.0.") + path,
                                std::string(path) == "scene.bonds.0.atom_1" ? 0.0 : 1.0);
    }
    return edi::report_from_json(edi::json::write(document));
}

void invalid_render_reference(edi::ReportModel& model, const std::string& route, bool empty) {
    auto& structure = model.structures.front();
    auto& scene = structure.scene;
    const auto sphere = structure.drawing.spheres.front();
    const auto bond = scene.bonds.front();
    const auto label = scene.labels.front();
    if (route == "major") {
        auto& atom = scene.atoms.front();
        if (empty) atom.parts.clear();
        atom.major = atom.parts.size();
        return;
    }
    if (empty) {
        scene.atoms.clear();
        scene.bonds.clear();
        scene.labels.clear();
        structure.drawing.spheres.clear();
        structure.drawing.shared.clear();
        structure.labels.clear();
    }
    const auto invalid = scene.atoms.size();
    if (route == "sphere") {
        structure.drawing.spheres = {sphere};
        structure.drawing.spheres.front().atom = invalid;
    } else if (route == "shared") {
        structure.drawing.shared = {invalid};
    } else if (route == "bond-start" || route == "bond-end") {
        scene.bonds = {bond};
        // One-past cases isolate each endpoint; neither can address an empty collection.
        scene.bonds.front().atom_1 = invalid;
        scene.bonds.front().atom_2 = invalid;
        if (!empty) {
            if (route == "bond-start")
                scene.bonds.front().atom_2 = 1;
            else
                scene.bonds.front().atom_1 = 0;
        }
    } else if (route == "scene-label") {
        scene.labels = {label};
        scene.labels.front().atom = invalid;
    } else if (route == "report-label") {
        structure.labels = {label};
        structure.labels.front().atom = invalid;
    } else {
        FAIL("An unknown reference route cannot silently omit a boundary");
    }
}
}  // namespace

TEST_CASE(
    "Native report writer refuses every addressed scene reference before render derivation") {
    const auto original = render_boundary_model();
    for (const auto& route :
         {"major", "sphere", "shared", "bond-start", "bond-end", "scene-label", "report-label"}) {
        for (const bool empty : {false, true}) {
            auto invalid = original;
            invalid_render_reference(invalid, route, empty);
            INFO("route=", route, " empty=", empty);
            const auto encoded = edi::report_to_json(invalid);
            CHECK_THROWS_AS_MESSAGE(
                edi::report_from_json(encoded), std::invalid_argument,
                "The existing public reader independently refuses this address");
            CHECK_THROWS_AS_MESSAGE(edi::report_html(invalid), std::invalid_argument,
                                    "The writer refuses before eager subset/mesh dereferences");
        }
    }
}

TEST_CASE("Native report writer retains valid final references and nonaddressing provenance") {
    auto model = render_boundary_model();
    auto& structure = model.structures.front();
    // These are provenance rows, explicitly distinguished from addressing indices by the
    // existing test_report_collection_domain.py contract.
    structure.scene.atoms.front().row = 900;
    structure.scene.atoms.front().parts.front().row = 901;
    structure.scene.bonds.front().row = 902;
    for (auto& instance : structure.drawing.cylinders) instance.atom = 903;
    const auto encoded = edi::report_to_json(model);
    const auto restored = edi::report_from_json(encoded);
    CHECK_MESSAGE(edi::report_to_json(restored) == encoded,
                  "Final valid scene references and arbitrary provenance survive the reader");
    const auto html = edi::report_html(restored);
    CHECK_MESSAGE(html.find("edi-report-model") != std::string::npos,
                  "A genuinely valid model reaches the native HTML writer");
}

TEST_CASE("Native report HTML preserves arbitrary style keys alongside every original style row") {
    auto model = render_boundary_model();
    const auto original = model.structure_styles;
    for (const auto& key :
         {"edi_renderer_number", "edi_renderer_number.extra", "__proto__", "constructor"})
        model.structure_styles.push_back({key, "#123456", "#abcdef", .375});
    const auto encoded = edi::report_to_json(model);
    const auto restored = edi::report_from_json(encoded);
    CHECK_MESSAGE(edi::report_to_json(restored) == encoded,
                  "The public model codec admits these arbitrary metadata keys unchanged");
    REQUIRE_MESSAGE(restored.structure_styles.size() == original.size() + 4,
                    "No old or authored style record is discarded");
    const auto html = edi::report_html(restored);
    const std::regex model_script(
        R"(<script[^>]*id=["']edi-report-model["'][^>]*>([\s\S]*?)</script>)");
    std::smatch embedded;
    REQUIRE_MESSAGE(std::regex_search(html, embedded, model_script),
                    "The native-generated HTML supplies its actual embedded model");
    const auto payload = edi::json::parse(embedded[1].str());
    const auto raw = edi::json::parse(encoded);
    CHECK_MESSAGE(edi::json::write(payload.at("structure_styles")) ==
                      edi::json::write(raw.at("structure_styles")),
                  "Native HTML carries every original and collision-shaped style row whole");
}
