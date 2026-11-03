#include <doctest/doctest.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <vector>

#include "edi/io.hpp"
#include "edi/structure_scene.hpp"

namespace {
// ISODISTORT's eight signed Pnma operations, applied by hand to the two frozen moments.
// Fractional positions and axial vectors are independent of edi's scene and crysta's expansion.
struct Image {
    std::array<double, 3> position, moment;
};
constexpr std::array<Image, 8> images{{
    {{0, 0, 0}, {.7, 2.6, .3}},
    {{.5, .5, .5}, {.7, -2.6, -.3}},
    {{0, .5, 0}, {-.7, 2.6, -.3}},
    {{.5, 0, .5}, {-.7, -2.6, .3}},
    {{.2809, .25, .9836}, {0, 2.97, 0}},
    {{.7809, .25, .5164}, {0, -2.97, 0}},
    {{.7191, .75, .0164}, {0, 2.97, 0}},
    {{.2191, .75, .4836}, {0, -2.97, 0}},
}};

double norm(const std::array<double, 3>& v) {
    return std::sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
}

template <class Options, class Drawing>
void check_arrows(edi::Structure& structure) {
    // As in the existing ADP scene gate, absent additive scene fields give an executable red.
    // The adapter spells the scene extension as moments / moment_scale; physics is below it.
    if constexpr (requires(Options options, Drawing drawing) {
                      options.moments;
                      options.moment_scale;
                      drawing.moments;
                  }) {
        structure.current_geometry();
        const auto source = edi::capture_scene(structure);
        REQUIRE_MESSAGE(source.current, "The moment viewer captures current computed geometry");
        Options options;
        CHECK_MESSAGE(options.moment_scale == .75,
                      "Moment arrows default to three quarters of an Angstrom per Bohr magneton");
        options.moments = true;
        options.axes = options.bonds = options.cell = false;
        for (const double scale : {.5, .8}) {
            options.moment_scale = scale;
            const auto scene = edi::present_structure(source, options);
            const Drawing drawing = edi::scene_drawing(scene, {640, 480, 0});
            std::vector<std::array<double, 3>> centres, moments;
            for (std::size_t row = 0; row < source.atom_site_id->size(); ++row) {
                const auto& id = source.atom_site_id->at(row);
                if (id != "Co1_1" && id != "Co2_1") continue;
                const std::array<double, 3> fractional{
                    source.fract_x->at(row), source.fract_y->at(row), source.fract_z->at(row)};
                const auto match =
                    std::find_if(images.begin(), images.end(), [&](const auto& image) {
                        for (std::size_t axis = 0; axis < 3; ++axis) {
                            const double delta = fractional[axis] - image.position[axis];
                            if (std::abs(delta - std::round(delta)) > 1e-9) return false;
                        }
                        return true;
                    });
                REQUIRE_MESSAGE(match != images.end(),
                                "Every drawn cobalt position has an independent Pnma image");
                centres.push_back({10.308064 * fractional[0], 6.002187 * fractional[1],
                                   4.787394 * fractional[2]});
                moments.push_back(match->moment);
            }
            REQUIRE_MESSAGE(centres.size() >= images.size(),
                            "The cell view includes all eight independent magnetic images");
            REQUIRE_MESSAGE(drawing.moments.size() == centres.size(),
                            "The viewer draws one arrow per expanded magnetic atom only");
            std::vector<bool> matched(centres.size(), false);
            for (const auto& arrow : drawing.moments) {
                CHECK_MESSAGE(arrow.shaft_radius == doctest::Approx(.12),
                              "The arrow shaft is twice the preview radius");
                CHECK_MESSAGE(arrow.head_radius == doctest::Approx(.30),
                              "The arrow head is twice the preview radius");
                CHECK_MESSAGE(arrow.color.r == arrow.color.g && arrow.color.g == arrow.color.b,
                              "Moment arrows use neutral grey instead of the preview magenta");
                const double length = arrow.shaft_length + arrow.head_length;
                const std::array<double, 3> direction{arrow.direction.x, arrow.direction.y,
                                                      arrow.direction.z};
                const std::array<double, 3> centre{arrow.origin.x + .5 * length * direction[0],
                                                   arrow.origin.y + .5 * length * direction[1],
                                                   arrow.origin.z + .5 * length * direction[2]};
                const auto found =
                    std::find_if(centres.begin(), centres.end(), [&](const auto& point) {
                        return norm({centre[0] - point[0], centre[1] - point[1],
                                     centre[2] - point[2]}) < 1e-9;
                    });
                REQUIRE_MESSAGE(found != centres.end(),
                                "Each moment arrow is centred on its magnetic atom");
                const auto index = static_cast<std::size_t>(found - centres.begin());
                CHECK_MESSAGE(!matched[index], "No magnetic atom receives duplicate arrows");
                matched[index] = true;
                const double magnitude = norm(moments[index]);
                CHECK_MESSAGE(length == doctest::Approx(scale * magnitude).epsilon(1e-11),
                              "Moment arrow length uses the selected Angstrom per magneton scale");
                for (std::size_t axis = 0; axis < 3; ++axis)
                    CHECK_MESSAGE(
                        direction[axis] ==
                            doctest::Approx(moments[index][axis] / magnitude).epsilon(1e-11),
                        "Moment arrow direction preserves every axial-vector sign");
            }
        }
        options.atoms = edi::AtomSubset::None;
        const Drawing independent =
            edi::scene_drawing(edi::present_structure(source, options), {640, 480, 0});
        CHECK_MESSAGE(independent.moments.size() >= images.size(),
                      "Hiding atoms leaves all magnetic moment arrows visible");
        options.moments = false;
        const Drawing hidden =
            edi::scene_drawing(edi::present_structure(source, options), {640, 480, 0});
        CHECK_MESSAGE(hidden.moments.empty(),
                      "Hiding magnetic moments removes every moment arrow");
    } else {
        REQUIRE_MESSAGE(
            false, "The core scene exposes magnetic arrows, visibility and their length scale");
    }
}
}  // namespace

TEST_CASE("Cobalt moment arrows preserve the independent cell expansion and display scale") {
    const auto fixture = std::filesystem::path(__FILE__).parent_path() /
                         "../../fixtures/magnetic_pnma/magnetic.edi";
    std::ifstream input(fixture);
    REQUIRE_MESSAGE(input.good(), "The magnetic scene fixture must be readable");
    const std::string text{std::istreambuf_iterator<char>(input), {}};
    auto structure = edi::structure_from_edi_text(text);
    check_arrows<edi::SceneOptions, edi::SceneDrawing>(structure);
}
