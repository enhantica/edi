#include <doctest/doctest.h>

#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <limits>
#include <string>
#include <type_traits>

#if __has_include("edi/report_model.hpp")
#include "edi/io.hpp"
#include "edi/presentation.hpp"
#include "edi/report_model.hpp"
#include "edi/structure_scene.hpp"
#define HAS_REPORT_MODEL 1
#endif

TEST_CASE("Report JSON carries shortest-roundtrip doubles without dropping fields") {
#ifdef HAS_REPORT_MODEL
    edi::ReportModel model;
    model.generated = "2026-10-13 16:00 UTC";
    model.name = "numeric_model";
    const std::array<double, 4> values{.1, -0.0, std::numeric_limits<double>::denorm_min(),
                                       std::numeric_limits<double>::max()};
    for (std::size_t index = 0; index < values.size(); ++index) {
        edi::ReportParameter parameter;
        parameter.name = "p" + std::to_string(index);
        parameter.label = "Parameter " + std::to_string(index);
        parameter.units = "K";
        parameter.value = {values[index], values[index], "independent numeric input"};
        parameter.start = values[index];
        parameter.free = true;
        model.parameters.push_back(parameter);
    }
    const auto text = edi::report_to_json(model);
    const auto restored = edi::report_from_json(text);
    REQUIRE_MESSAGE((restored.parameters.size() == values.size()),
                    "Every report parameter must survive the schema-one round trip");
    CHECK_MESSAGE((restored.schema_version == 1 && restored.generated == model.generated &&
                   restored.name == model.name),
                  "The schema and fixed UTC timestamp must survive JSON unchanged");
    for (std::size_t index = 0; index < values.size(); ++index) {
        const auto& row = restored.parameters[index];
        REQUIRE_MESSAGE((row.value.su.has_value() && row.start.has_value()),
                        "Numeric su and start fields must stay engaged");
        for (double actual : {row.value.value, *row.value.su, *row.start}) {
            CHECK_MESSAGE(
                (std::bit_cast<std::uint64_t>(actual) ==
                 std::bit_cast<std::uint64_t>(values[index])),
                "JSON keeps decimal, signed-zero, subnormal and maximal finite double bits");
        }
        CHECK_MESSAGE((row.name == model.parameters[index].name &&
                       row.label == model.parameters[index].label && row.units == "K" &&
                       row.value.text == "independent numeric input" && row.free),
                      "JSON must retain each parameter's identities, units, text and free state");
    }
    CHECK_MESSAGE((edi::report_to_json(restored) == text),
                  "A report model must re-serialize with byte-identical canonical JSON");
#else
    FAIL_CHECK("The planned versioned core report model must exist");
#endif
}

TEST_CASE("Report JSON retains hostile UTF8 text and encodes nonfinite su as null") {
#ifdef HAS_REPORT_MODEL
    edi::ReportModel model;
    model.generated = "2026-10-13 16:00 UTC";
    model.title =
        "Co\"Si\" "
        "<b>&amp;</b></script><script>alert(1)</script>\t\xe2\x80\xa8\xe2\x80\xa9\xf0\x9d\x9b\x82";
    model.authors = "Ada Lovelace; Émile O'Brien";
    model.description = "A backslash \\ and an apostrophe '";
    edi::ReportParameter parameter;
    parameter.name = "p";
    parameter.value = {.1, std::numeric_limits<double>::quiet_NaN(), "0.1()"};
    model.parameters.push_back(parameter);
    const auto text = edi::report_to_json(model);
    CHECK_MESSAGE(
        (text.find("NaN") == std::string::npos && text.find("null") != std::string::npos),
        "A nonfinite uncertainty must be valid JSON null, not a nonstandard NaN token");
    const auto restored = edi::report_from_json(text);
    CHECK_MESSAGE(
        (restored.title == model.title && restored.authors == model.authors &&
         restored.description == model.description),
        "JSON must recover every hostile UTF8 text without HTML or entity interpretation");
    CHECK_MESSAGE((edi::report_to_json(restored) == text),
                  "Null and escaped text must keep canonical report JSON bytes");
#else
    FAIL_CHECK("The planned versioned core report model must exist");
#endif
}

TEST_CASE("Report options retain section order and an explicitly fixed UTC timestamp") {
#ifdef HAS_REPORT_MODEL
    const auto project = edi::empty_project("empty_report", "independent option input");
    edi::ReportOptions options;
    options.generated = "2026-10-13 16:00 UTC";
    options.sections = {edi::ReportSection::Experiments, edi::ReportSection::Summary,
                        edi::ReportSection::Structures};
    const auto model = edi::build_report(project, options);
    CHECK_MESSAGE((model.generated == "2026-10-13 16:00 UTC"),
                  "An explicit report timestamp must remain the supplied UTC text");
    CHECK_MESSAGE(
        ((model.sections == std::vector<edi::ReportSection>{edi::ReportSection::Summary,
                                                            edi::ReportSection::Structures,
                                                            edi::ReportSection::Experiments})),
        "Contents removes sections and never reorders the report's declared sections");
    options.sections = {edi::ReportSection::Structures, edi::ReportSection::Experiments,
                        edi::ReportSection::Summary};
    CHECK_MESSAGE(
        (edi::report_to_json(edi::build_report(project, options)) == edi::report_to_json(model)),
        "Equal project, options and fixed generated time must give identical report bytes");
#else
    FAIL_CHECK("The planned versioned core report builder must exist");
#endif
}

#ifdef HAS_REPORT_MODEL
namespace {
template <class Model>
void carry_presentations(Model model) {
    if constexpr (requires {
                      model.experiments.front().pattern;
                      model.structures.front().scene;
                      model.structures.front().view;
                      model.structures.front().drawing;
                  }) {
        using Pattern = std::remove_cvref_t<decltype(model.experiments.front().pattern)>;
        using Drawing = std::remove_cvref_t<decltype(model.structures.front().drawing)>;
        CHECK_MESSAGE(((std::is_same_v<Pattern, edi::PatternPresentation>)),
                      "The report keeps the existing full PatternPresentation type");
        CHECK_MESSAGE(((std::is_same_v<Drawing, edi::SceneDrawing>)),
                      "The report keeps the existing SceneDrawing instance contract");
        model.experiments.emplace_back();
        model.structures.emplace_back();
        auto& pattern = model.experiments.back().pattern;
        edi::PatternSeries measured;
        measured.kind = edi::SeriesKind::Measured;
        measured.id = "meas";
        measured.style = "meas";
        const auto nan = std::numeric_limits<double>::quiet_NaN();
        measured.points = {{1, 100}, {nan, nan}, {3, 110}};
        measured.rows = {0, edi::kNoRow, 2};
        measured.bar_low = {90, nan, 100};
        measured.bar_high = {112, nan, 122};
        pattern.series.push_back(measured);
        pattern.layout = {
            {edi::Pane::Main, .7, 0}, {edi::Pane::Bragg, 0, 36}, {edi::Pane::Residual, .3, 0}};
        auto& structure = model.structures.back();
        edi::SceneAtom left, right;
        left.centre = {0, 0, 0};
        right.centre = {1, 0, 0};
        left.radius = right.radius = .2;
        left.ellipsoid = true;
        left.semi_axes = {.2, .35, .5};
        left.orientation = {std::cos(.3), 0, std::sin(.3), 0};
        edi::ScenePart part;
        part.fraction = 1;
        part.color = {12, 34, 56};
        left.parts.push_back(part);
        right.parts.push_back(part);
        structure.scene.atoms = {left, right};
        edi::SceneBond bond;
        bond.start = left.centre;
        bond.end = right.centre;
        bond.distance = 1;
        bond.color_1 = bond.color_2 = part.color;
        structure.scene.bonds.push_back(bond);
        structure.scene.frame.half_width = structure.scene.frame.half_height = 2;
        structure.scene.frame.target = {.5, 0, 0};
        structure.scene.frame.view_direction = {0, 0, 1};
        structure.scene.frame.view_up = {0, 1, 0};
        structure.view = edi::default_view(structure.scene);
        structure.drawing = edi::scene_drawing(structure.scene, {800, 600, 0});
        REQUIRE_MESSAGE(
            (!structure.drawing.spheres.empty() && !structure.drawing.cylinders.empty()),
            "The independent drawing witness contains atoms and a bond along +x");
        const auto text = edi::report_to_json(model);
        const auto restored = edi::report_from_json(text);
        CHECK_MESSAGE((edi::report_to_json(restored) == text),
                      "Pattern gaps, asymmetric bar ends, pane layout and scene instances survive "
                      "JSON whole");
        const auto& out = restored.experiments.back().pattern;
        REQUIRE_MESSAGE((out.series.size() == 1 && out.series[0].points.size() == 3),
                        "The report must retain every presented series point including its gap");
        CHECK_MESSAGE(
            (std::isnan(out.series[0].points[1].x) && std::isnan(out.series[0].points[1].y)),
            "A presented NaN gap remains a gap after report serialization");
        CHECK_MESSAGE(
            (out.series[0].bar_low[0] == 90 && out.series[0].bar_high[0] == 112),
            "The report retains unequal bar ends instead of recomputing a symmetric error");
        const auto& drawing = restored.structures.back().drawing;
        REQUIRE_MESSAGE((drawing.spheres.size() == structure.drawing.spheres.size() &&
                         drawing.cylinders.size() == structure.drawing.cylinders.size()),
                        "Every existing-core sphere and half-bond instance remains in the report");
        for (std::size_t i = 0; i < drawing.cylinders.size(); ++i) {
            CHECK_MESSAGE(
                (drawing.cylinders[i].rotation == structure.drawing.cylinders[i].rotation),
                "A bond's nonidentity quaternion must survive the report's serialization");
        }
        CHECK_MESSAGE(
            (drawing.spheres[0].rotation == structure.drawing.spheres[0].rotation &&
             drawing.spheres[0].scale.y == structure.drawing.spheres[0].scale.y),
            "An anisotropic nonidentity ellipsoid keeps the existing core orientation and scale");
    } else {
        FAIL_CHECK("The model must carry the existing pattern, scene, view and drawing outputs");
    }
}
}  // namespace
#endif

TEST_CASE("Report JSON retains existing presentation and drawing outputs at nontrivial seams") {
#ifdef HAS_REPORT_MODEL
    carry_presentations(edi::ReportModel{});
#else
    FAIL_CHECK("The planned report presentation and drawing model must exist");
#endif
}
