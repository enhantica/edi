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
// data/palettes, one table per scheme in ColourScheme's order, embedded by cmake/edi_core_sources.cmake.
extern const char* const kPaletteTsv[];
extern const std::size_t kPaletteTsvCount;
}  // namespace edi::detail

namespace edi {

namespace {

// The role rows' names, in ChartRole's order.
constexpr std::array<std::string_view, 3> kRoleNames{"total_calculation", "background", "difference"};

struct Palette {
    std::vector<std::array<std::string, 2>> measured, structure;  // light, dark
    std::array<std::array<std::string, 2>, 3> role;                // by ChartRole
};

// A table's rows, by role, in the order listed; a malformed row or a missing colour refuses the whole table.
Palette parse(const char* text) {
    Palette palette;
    std::array<bool, 3> roles_read{};
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
        if (!hex(light) || !hex(dark)) {
            throw std::logic_error("a palette row is malformed: " + line);
        }
        if (role == "measured") {
            palette.measured.push_back({light, dark});
        } else if (role == "structure") {
            palette.structure.push_back({light, dark});
        } else {
            const auto found = std::find(kRoleNames.begin(), kRoleNames.end(), role);
            if (found == kRoleNames.end()) {
                throw std::logic_error("a palette row is malformed: " + line);
            }
            const auto at = static_cast<std::size_t>(found - kRoleNames.begin());
            palette.role[at] = {light, dark};
            roles_read[at] = true;
        }
    }
    if (palette.measured.size() != kGroupColourCount || palette.structure.size() != kGroupColourCount ||
        !std::all_of(roles_read.begin(), roles_read.end(), [](bool read) { return read; })) {
        throw std::logic_error("a palette does not list five measured, five structure and three role colours");
    }
    return palette;
}

constexpr std::array<std::string_view, 5> kNames{"ediNatural", "ediCoast", "ediGarden", "ediStudio", "ediContrast"};
constexpr std::array<std::string_view, 5> kTitles{"Edi Natural", "Edi Coast", "Edi Garden", "Edi Studio",
                                                  "Edi Contrast"};

const Palette& palette_of(ColourScheme scheme) {
    static const std::vector<Palette> kPalettes = [] {
        if (detail::kPaletteTsvCount != kNames.size()) {
            throw std::logic_error("the embedded palettes are not one per colour scheme");
        }
        std::vector<Palette> out;
        for (std::size_t i = 0; i < detail::kPaletteTsvCount; ++i) {
            out.push_back(parse(detail::kPaletteTsv[i]));
        }
        return out;
    }();
    return kPalettes[static_cast<std::size_t>(scheme)];
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

// ADR-0038: up to five items take the group's first colours in order; more take a gradient over the whole group, from
// its first colour to its second, item `place` at t = place / (count - 1). The ends are the colours themselves.
std::string group_colour(const std::vector<std::array<std::string, 2>>& group, std::size_t place, std::size_t count,
                         std::size_t side) {
    if (count <= group.size()) {
        return group[std::min(place, group.size() - 1)][side];
    }
    const std::size_t at = std::min(place, count - 1);
    if (at == 0 || at == count - 1) {
        return group[at == 0 ? 0 : 1][side];
    }
    const double t = static_cast<double>(at) / static_cast<double>(count - 1);
    const Lab from = oklab(group[0][side]);
    const Lab to = oklab(group[1][side]);
    return hex_of({from.l + (to.l - from.l) * t, from.a + (to.a - from.a) * t, from.b + (to.b - from.b) * t});
}

}  // namespace

std::string mix_colours(const std::string& from, const std::string& to, double t) {
    const double at = std::clamp(t, 0.0, 1.0);
    if (at <= 0.0 || at >= 1.0) {
        return at <= 0.0 ? from : to;
    }
    const Lab a = oklab(from);
    const Lab b = oklab(to);
    return hex_of({a.l + (b.l - a.l) * at, a.a + (b.a - a.a) * at, a.b + (b.b - a.b) * at});
}

double contrast_ratio(const std::string& a, const std::string& b) {
    const auto luminance = [](const std::string& hex) {
        const auto channel = [&hex](std::size_t at) { return to_linear(std::stoi(hex.substr(at, 2), nullptr, 16) / 255.0); };
        return 0.2126 * channel(1) + 0.7152 * channel(3) + 0.0722 * channel(5);
    };
    const double one = luminance(a), other = luminance(b);
    return (std::max(one, other) + 0.05) / (std::min(one, other) + 0.05);
}

std::string readable_colour(const std::string& colour, const std::string& background, double ratio) {
    if (contrast_ratio(colour, background) >= ratio) {
        return colour;
    }
    const Lab lab = oklab(colour);
    const double end = contrast_ratio("#000000", background) >= contrast_ratio("#FFFFFF", background) ? 0.0 : 1.0;
    const auto at = [&lab, end](double t) { return hex_of({lab.l + (end - lab.l) * t, lab.a, lab.b}); };
    if (contrast_ratio(at(1.0), background) < ratio) {
        return at(1.0);
    }
    // The least move that reaches the ratio, to well under one step of 8-bit colour.
    double low = 0.0, high = 1.0;
    for (int step = 0; step < 32; ++step) {
        const double middle = (low + high) / 2.0;
        (contrast_ratio(at(middle), background) >= ratio ? high : low) = middle;
    }
    return at(high);
}

std::span<const std::string_view> colour_scheme_names() { return kNames; }

std::optional<ColourScheme> colour_scheme_from_name(std::string_view name) {
    const auto found = std::find(kNames.begin(), kNames.end(), name);
    if (found == kNames.end()) {
        return std::nullopt;
    }
    return static_cast<ColourScheme>(found - kNames.begin());
}

ColourScheme colour_scheme_or_default(std::string_view name) {
    return colour_scheme_from_name(name).value_or(kDefaultColourScheme);
}

std::string_view colour_scheme_title(ColourScheme scheme) { return kTitles[static_cast<std::size_t>(scheme)]; }

std::string pattern_colour(ColourScheme scheme, std::size_t place, std::size_t count, bool dark) {
    return group_colour(palette_of(scheme).measured, place, count, dark ? 1 : 0);
}

std::string structure_colour(ColourScheme scheme, std::size_t place, std::size_t count, bool dark) {
    return group_colour(palette_of(scheme).structure, place, count, dark ? 1 : 0);
}

std::string role_colour(ColourScheme scheme, ChartRole role, bool dark) {
    return palette_of(scheme).role[static_cast<std::size_t>(role)][dark ? 1 : 0];
}

}  // namespace edi
