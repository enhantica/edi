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
    model.correlations.emplace();
    auto& input = *model.correlations;
    const std::array<double, 4> values{.1, -0.0, std::numeric_limits<double>::denorm_min(),
                                       std::numeric_limits<double>::max()};
    input.labels = {"p0", "p1"};
    input.values.assign(values.begin(), values.end());
    input.available = 2;
    input.level = .125;
    input.empty_text = "independent chart text";
    const auto text = edi::report_to_json(model);
    const auto restored = edi::report_from_json(text);
    REQUIRE_MESSAGE(restored.correlations.has_value(),
                    "The versioned report JSON retains its actual numeric correlation payload");
    const auto& output = *restored.correlations;
    REQUIRE_MESSAGE(output.values.size() == values.size(),
                    "Every actual numeric payload field survives the schema-one round trip");
    CHECK_MESSAGE((restored.schema_version == 1 && restored.generated == model.generated &&
                   restored.name == model.name),
                  "The schema and fixed UTC timestamp survive JSON unchanged");
    for (std::size_t index = 0; index < values.size(); ++index) {
        CHECK_MESSAGE((std::bit_cast<std::uint64_t>(output.values[index]) ==
                       std::bit_cast<std::uint64_t>(values[index])),
                      "JSON keeps decimal, signed-zero, subnormal and maximal finite double bits");
    }
    CHECK_MESSAGE((output.labels == input.labels && output.available == input.available &&
                   output.level == input.level && output.empty_text == input.empty_text),
                  "JSON retains each chart's identities, count, threshold and display text");
    CHECK_MESSAGE((edi::report_to_json(restored) == text),
                  "The actual report model re-serializes with byte-identical canonical JSON");
#else
    FAIL_CHECK("The planned versioned core report model must exist");
#endif
}

TEST_CASE("Report JSON retains hostile UTF8 text and encodes nonfinite values as null") {
#ifdef HAS_REPORT_MODEL
    edi::ReportModel model;
    model.generated = "2026-10-13 16:00 UTC";
    model.title = "Co\"Si\" <b>&amp;</b></script><script>alert(1)</script>\t"
                  "\xe2\x80\xa8\xe2\x80\xa9\xf0\x9d\x9b\x82";
    model.authors = "Ada Lovelace; Émile O'Brien";
    model.description = "A backslash \\ and an apostrophe '";
    model.correlations.emplace();
    model.correlations->labels = {"p0", "p1"};
    model.correlations->values = {.1, std::numeric_limits<double>::quiet_NaN(),
                                 std::numeric_limits<double>::infinity(),
                                 -std::numeric_limits<double>::infinity()};
    const auto text = edi::report_to_json(model);
    CHECK_MESSAGE((text.find("NaN") == std::string::npos &&
                   text.find("Infinity") == std::string::npos && text.find("null") != std::string::npos),
                  "Nonfinite numeric payloads are valid JSON null instead of nonstandard tokens");
    const auto restored = edi::report_from_json(text);
    CHECK_MESSAGE((restored.title == model.title && restored.authors == model.authors &&
                   restored.description == model.description),
                  "JSON recovers every hostile UTF8 text without HTML or entity interpretation");
    CHECK_MESSAGE((edi::report_to_json(restored) == text),
                  "Null and escaped text retain canonical report JSON bytes");
#else
    FAIL_CHECK("The planned versioned core report model must exist");
#endif
}

#ifdef HAS_REPORT_MODEL
namespace {
template <class Options>
void check_optional_group_order(Options options) {
    const auto project = edi::empty_project("empty_report", "independent option input");
    options.generated = "2026-10-13 16:00 UTC";
    if constexpr (requires { options.hidden; }) {
        options.hidden = {"reflections", "charts"};
        const auto model = edi::build_report(project, options);
        CHECK_MESSAGE(model.generated == options.generated,
                      "An explicit report timestamp remains the supplied UTC text");
        options.hidden = {"charts", "reflections"};
        CHECK_MESSAGE((edi::report_to_json(edi::build_report(project, options)) ==
                       edi::report_to_json(model)),
                      "Reordering optional exclusion keys never reorders or changes report records");
    } else {
        FAIL_CHECK("The current report API excludes optional groups while always retaining its records");
    }
}
}

#endif

TEST_CASE("Report options retain section order and an explicitly fixed UTC timestamp") {
#ifdef HAS_REPORT_MODEL
    check_optional_group_order(edi::ReportOptions{});
#else
    FAIL_CHECK("The planned versioned core report builder must exist");
#endif
}

#ifdef HAS_REPORT_MODEL
namespace {
template <class Pattern>
decltype(auto) pattern_payload(Pattern& pattern) {
    if constexpr (requires { pattern.presentation; }) return (pattern.presentation);
    else return (pattern);
}
template <class Model>
void carry_presentations(Model model) {
    if constexpr (requires {
                      model.experiments.front().pattern;
                      model.structures.front().scene;
                      model.structures.front().view;
                      model.structures.front().drawing;
                  }) {
        using Pattern = std::remove_cvref_t<decltype(pattern_payload(model.experiments.front().pattern))>;
        using Drawing = std::remove_cvref_t<decltype(model.structures.front().drawing)>;
        CHECK_MESSAGE(((std::is_same_v<Pattern, edi::PatternPresentation>)),
                      "The report keeps the existing full PatternPresentation type");
        CHECK_MESSAGE(((std::is_same_v<Drawing, edi::SceneDrawing>)),
                      "The report keeps the existing SceneDrawing instance contract");
        model.experiments.emplace_back();
        model.structures.emplace_back();
        auto& pattern = pattern_payload(model.experiments.back().pattern);
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
        const auto& out = pattern_payload(restored.experiments.back().pattern);
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
