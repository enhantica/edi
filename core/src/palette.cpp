// SPDX-License-Identifier: BSD-3-Clause
#include "edi/palette.hpp"

#include <algorithm>
#include <array>
#include <cctype>
#include <cmath>
#include <cstdio>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace edi::detail {
extern const char* const kDefaultPaletteTsv;  // data/palettes, embedded by core/CMakeLists.txt
extern const char* const kColourBlindSafePaletteTsv;
}  // namespace edi::detail

namespace edi {

namespace {

struct Palette {
    std::vector<std::array<std::string, 2>> pattern, structure;  // light, dark
};

// A table's rows, by role, in the order listed; a malformed row refuses the whole table.
Palette parse(const char* text) {
    Palette palette;
    std::istringstream in(text);
    std::string line;
    std::getline(in, line);  // the header
    while (std::getline(in, line)) {
        if (line.empty()) {
            continue;
        }
        std::istringstream row(line);
        std::string role, index, light, dark;
        std::getline(row, role, '\t');
        std::getline(row, index, '\t');
        std::getline(row, light, '\t');
        std::getline(row, dark, '\t');
        const auto hex = [](const std::string& colour) {
            return colour.size() == 7 && colour[0] == '#' &&
                   std::all_of(colour.begin() + 1, colour.end(), [](char c) { return std::isxdigit(c) != 0; });
        };
        if (!hex(light) || !hex(dark) || (role != "pattern" && role != "structure")) {
            throw std::logic_error("a palette row is malformed: " + line);
        }
        (role == "pattern" ? palette.pattern : palette.structure).push_back({light, dark});
    }
    if (palette.pattern.size() < 2 || palette.structure.empty()) {
        throw std::logic_error("a palette lists too few colours");
    }
    return palette;
}

const Palette& palette_of(ColourScheme scheme) {
    static const Palette kDefault = parse(detail::kDefaultPaletteTsv);
    static const Palette kColourBlindSafe = parse(detail::kColourBlindSafePaletteTsv);
    return scheme == ColourScheme::ColourBlindSafe ? kColourBlindSafe : kDefault;
}

// Oklab (Björn Ottosson, 2020) from and to sRGB, for a gradient whose steps look even.
struct Lab {
    double l, a, b;
};

double to_linear(double c) { return c <= 0.04045 ? c / 12.92 : std::pow((c + 0.055) / 1.055, 2.4); }
double to_srgb(double c) { return c <= 0.0031308 ? 12.92 * c : 1.055 * std::pow(c, 1.0 / 2.4) - 0.055; }

Lab oklab(const std::string& hex) {
    const auto channel = [&hex](std::size_t at) { return to_linear(std::stoi(hex.substr(at, 2), nullptr, 16) / 255.0); };
    const double r = channel(1), g = channel(3), b = channel(5);
    const double l = std::cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
    const double m = std::cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
    const double s = std::cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
    return {0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s, 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s};
}

std::string hex_of(const Lab& lab) {
    const double l = std::pow(lab.l + 0.3963377774 * lab.a + 0.2158037573 * lab.b, 3.0);
    const double m = std::pow(lab.l - 0.1055613458 * lab.a - 0.0638541728 * lab.b, 3.0);
    const double s = std::pow(lab.l - 0.0894841775 * lab.a - 1.2914855480 * lab.b, 3.0);
    const std::array<double, 3> rgb{4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
                                    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
                                    -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s};
    char out[8];
    std::snprintf(out, sizeof(out), "#%02X%02X%02X",
                  static_cast<int>(std::lround(std::clamp(to_srgb(rgb[0]), 0.0, 1.0) * 255.0)),
                  static_cast<int>(std::lround(std::clamp(to_srgb(rgb[1]), 0.0, 1.0) * 255.0)),
                  static_cast<int>(std::lround(std::clamp(to_srgb(rgb[2]), 0.0, 1.0) * 255.0)));
    return out;
}

}  // namespace

std::optional<ColourScheme> colour_scheme_from_name(std::string_view name) {
    if (name == "default") {
        return ColourScheme::Default;
    }
    if (name == "colourBlindSafe") {
        return ColourScheme::ColourBlindSafe;
    }
    return std::nullopt;
}

std::size_t pattern_colour_count(ColourScheme scheme) { return palette_of(scheme).pattern.size(); }

std::string pattern_colour(ColourScheme scheme, std::size_t place, std::size_t count, bool dark) {
    const auto& rows = palette_of(scheme).pattern;
    const std::size_t side = dark ? 1 : 0;
    if (count <= rows.size()) {
        return rows[std::min(place, rows.size() - 1)][side];
    }
    const Lab from = oklab(rows[rows.size() - 2][side]);
    const Lab to = oklab(rows.back()[side]);
    const double t = static_cast<double>(std::min(place, count - 1)) / static_cast<double>(count - 1);
    return hex_of({from.l + (to.l - from.l) * t, from.a + (to.a - from.a) * t, from.b + (to.b - from.b) * t});
}

std::string structure_colour(ColourScheme scheme, std::size_t place, bool dark) {
    const auto& rows = palette_of(scheme).structure;
    return rows[place % rows.size()][dark ? 1 : 0];
}

}  // namespace edi
