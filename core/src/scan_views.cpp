// SPDX-License-Identifier: BSD-3-Clause
#include "edi/scan_views.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <limits>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>

#include "edi/palette.hpp"

namespace edi::detail {
extern const std::size_t kColourMapCount;
extern const char* const kColourMapNames[];
extern const char* const kColourMapTsvs[];
}

namespace edi {

namespace {

constexpr std::size_t kMapColours = 256;
using ColourTable = std::array<ScanMapColour, kMapColours>;

// One embedded colour map table: 256 colours, a header, `index<TAB>#RRGGBB` rows in order.
ColourTable read_colour_map(const char* tsv, const std::string& name) {
    ColourTable out{};
    std::istringstream in(tsv);
    std::string line;
    std::getline(in, line);  // the header
    std::size_t count = 0;
    while (std::getline(in, line)) {
        if (line.empty()) {
            continue;
        }
        const std::size_t tab = line.find('\t');
        if (count >= kMapColours || tab == std::string::npos || line.size() != tab + 8 || line[tab + 1] != '#') {
            throw std::logic_error("data/colormaps/" + name + ".tsv: row " + std::to_string(count + 1) +
                                   " is not '<index>\t#RRGGBB'");
        }
        const unsigned long rgb = std::strtoul(line.c_str() + tab + 2, nullptr, 16);
        out[count++] = {static_cast<std::uint8_t>(rgb >> 16), static_cast<std::uint8_t>(rgb >> 8),
                        static_cast<std::uint8_t>(rgb), 255};
    }
    if (count != kMapColours) {
        throw std::logic_error("data/colormaps/" + name + ".tsv holds " + std::to_string(count) + " colours, not 256");
    }
    return out;
}

// The embedded tables, read once, in scan_colour_map_names' order.
const std::vector<ColourTable>& colour_maps() {
    static const std::vector<ColourTable> tables = [] {
        std::vector<ColourTable> out;
        for (std::size_t i = 0; i < detail::kColourMapCount; ++i) {
            out.push_back(read_colour_map(detail::kColourMapTsvs[i], detail::kColourMapNames[i]));
        }
        return out;
    }();
    return tables;
}

// A map by name; viridis for any other name.
const ColourTable& colour_map_named(std::string_view name) {
    const std::vector<std::string>& names = scan_colour_map_names();
    const auto found = std::find(names.begin(), names.end(), name);
    return colour_maps()[found == names.end() ? 0 : static_cast<std::size_t>(found - names.begin())];
}

const ColourTable& colour_map(ScanColourMap map) { return colour_maps()[static_cast<std::size_t>(map)]; }

}  // namespace

ScanColumns scan_columns(std::span<const double> x, std::span<const double> intensity, double x_min, double x_max,
                         std::size_t columns) {
    constexpr float kNaN = std::numeric_limits<float>::quiet_NaN();
    ScanColumns out{std::vector<float>(columns, kNaN), std::vector<float>(columns, kNaN)};
    if (columns == 0 || !(x_max > x_min)) {
        return out;
    }
    const std::size_t points = std::min(x.size(), intensity.size());
    const double width = (x_max - x_min) / static_cast<double>(columns);
    for (std::size_t i = 0; i < points; ++i) {
        if (!std::isfinite(x[i]) || !std::isfinite(intensity[i]) || x[i] < x_min || x[i] > x_max) {
            continue;
        }
        const auto column = std::min(columns - 1, static_cast<std::size_t>((x[i] - x_min) / width));
        const auto value = static_cast<float>(intensity[i]);
        float& low = out.low[column];
        float& high = out.high[column];
        low = std::isnan(low) ? value : std::min(low, value);
        high = std::isnan(high) ? value : std::max(high, value);
    }
    return out;
}

namespace {

// The points of a pattern inside [x_min, x_max], counted, and the first and last place of a point inside.
struct Inside {
    std::size_t count = 0, first = 0, last = 0;
};
Inside points_inside(std::span<const double> x, std::span<const double> intensity, double x_min, double x_max) {
    Inside inside;
    const std::size_t points = std::min(x.size(), intensity.size());
    for (std::size_t i = 0; i < points; ++i) {
        if (std::isfinite(x[i]) && std::isfinite(intensity[i]) && x[i] >= x_min && x[i] <= x_max) {
            if (inside.count == 0) {
                inside.first = i;
            }
            inside.last = i;
            ++inside.count;
        }
    }
    return inside;
}

}  // namespace

ScanTrace scan_trace(std::span<const double> x, std::span<const double> intensity, double x_min, double x_max,
                     std::size_t columns) {
    constexpr float kNaN = std::numeric_limits<float>::quiet_NaN();
    ScanTrace trace;
    if (columns == 0 || !(x_max > x_min)) {
        return trace;
    }
    const Inside inside = points_inside(x, intensity, x_min, x_max);
    if (inside.count > columns) {
        const ScanColumns reduced = scan_columns(x, intensity, x_min, x_max, columns);
        const double width = (x_max - x_min) / static_cast<double>(columns);
        trace.x.reserve(columns);
        for (std::size_t c = 0; c < columns; ++c) {
            trace.x.push_back(x_min + (static_cast<double>(c) + 0.5) * width);
        }
        trace.low = reduced.low;
        trace.high = reduced.high;
        return trace;
    }
    const std::size_t points = std::min(x.size(), intensity.size());
    // No point inside: a zoom between two neighbouring points still shows the line joining them, as the map does,
    // on a rising or a falling grid; a point that cannot be drawn between them breaks it.
    if (inside.count == 0) {
        for (std::size_t i = 0; i + 1 < points; ++i) {
            const double xa = x[i], xb = x[i + 1], ya = intensity[i], yb = intensity[i + 1];
            if (!std::isfinite(xa) || !std::isfinite(xb) || !std::isfinite(ya) || !std::isfinite(yb) ||
                !(std::min(xa, xb) < x_min && std::max(xa, xb) > x_max)) {
                continue;
            }
            if (!trace.x.empty()) {
                trace.x.push_back(std::numeric_limits<double>::quiet_NaN());
                trace.low.push_back(kNaN);
                trace.high.push_back(kNaN);
            }
            for (const std::size_t k : {i, i + 1}) {
                trace.x.push_back(x[k]);
                trace.low.push_back(static_cast<float>(intensity[k]));
                trace.high.push_back(static_cast<float>(intensity[k]));
            }
        }
        return trace;
    }
    // The points inside, and the one beyond each end of the run inside, so the line leaves the plot at its edges.
    const std::size_t from = inside.first > 0 ? inside.first - 1 : 0;
    const std::size_t to = std::min(points, inside.last + 2);
    for (std::size_t i = from; i < to; ++i) {
        const bool finite = std::isfinite(x[i]) && std::isfinite(intensity[i]);
        trace.x.push_back(finite ? x[i] : std::numeric_limits<double>::quiet_NaN());
        const float value = finite ? static_cast<float>(intensity[i]) : kNaN;
        trace.low.push_back(value);
        trace.high.push_back(value);
    }
    return trace;
}

std::vector<float> scan_pixel_values(std::span<const double> x, std::span<const double> intensity, double x_min,
                                     double x_max, std::size_t columns) {
    constexpr float kNaN = std::numeric_limits<float>::quiet_NaN();
    std::vector<float> out(columns, kNaN);
    if (columns == 0 || !(x_max > x_min)) {
        return out;
    }
    if (points_inside(x, intensity, x_min, x_max).count > columns) {
        return scan_columns(x, intensity, x_min, x_max, columns).high;
    }
    // Each pair of neighbouring finite points, in the order given, covers the column centres between them.
    const std::size_t points = std::min(x.size(), intensity.size());
    const double width = (x_max - x_min) / static_cast<double>(columns);
    for (std::size_t i = 0; i + 1 < points; ++i) {
        const double xa = x[i], xb = x[i + 1], ya = intensity[i], yb = intensity[i + 1];
        if (!std::isfinite(xa) || !std::isfinite(xb) || !std::isfinite(ya) || !std::isfinite(yb) || xa == xb) {
            continue;
        }
        const double low = std::min(xa, xb), high = std::max(xa, xb);
        const double first = std::ceil((low - x_min) / width - 0.5), last = std::floor((high - x_min) / width - 0.5);
        for (double c = std::max(0.0, first); c <= std::min(static_cast<double>(columns) - 1.0, last); c += 1.0) {
            const double centre = x_min + (c + 0.5) * width;
            out[static_cast<std::size_t>(c)] = static_cast<float>(ya + (yb - ya) * (centre - xa) / (xb - xa));
        }
    }
    // A lone point inside, with no neighbour to join, colours its own column.
    for (std::size_t i = 0; i < points; ++i) {
        if (std::isfinite(x[i]) && std::isfinite(intensity[i]) && x[i] >= x_min && x[i] <= x_max) {
            const auto c = std::min(columns - 1, static_cast<std::size_t>((x[i] - x_min) / width));
            if (std::isnan(out[c])) {
                out[c] = static_cast<float>(intensity[i]);
            }
        }
    }
    return out;
}

std::vector<double> scan_row_positions(std::span<const double> values) {
    std::vector<double> out(values.begin(), values.end());
    if (std::any_of(out.begin(), out.end(), [](double value) { return !std::isfinite(value); })) {
        std::iota(out.begin(), out.end(), 0.0);
    }
    return out;
}

std::vector<ScanRowSpan> scan_row_spans(std::span<const double> positions) {
    std::vector<double> sorted(positions.begin(), positions.end());
    std::sort(sorted.begin(), sorted.end());
    sorted.erase(std::unique(sorted.begin(), sorted.end()), sorted.end());
    // The smallest distance between two rows: a lone row spans half of it either side.
    double step = std::numeric_limits<double>::infinity();
    for (std::size_t i = 1; i < sorted.size(); ++i) {
        step = std::min(step, sorted[i] - sorted[i - 1]);
    }
    if (!std::isfinite(step)) {
        step = 1.0;
    }
    std::vector<ScanRowSpan> out;
    out.reserve(positions.size());
    for (const double position : positions) {
        const auto at = std::lower_bound(sorted.begin(), sorted.end(), position);
        const double below = at == sorted.begin() ? position - step : *(at - 1);
        const double above = at + 1 >= sorted.end() ? position + step : *(at + 1);
        out.push_back({(below + position) / 2.0, (position + above) / 2.0});
    }
    return out;
}

const std::vector<std::string>& scan_colour_map_names() {
    static const std::vector<std::string> names(detail::kColourMapNames, detail::kColourMapNames + detail::kColourMapCount);
    return names;
}

std::string scan_colour_map_title(std::string_view name) {
    static const std::vector<std::pair<std::string_view, std::string_view>> titles{
        {"viridis", "Viridis"},                 {"magma", "Magma"},                 {"inferno", "Inferno"},
        {"plasma", "Plasma"},                   {"batlow", "batlow (Crameri)"},     {"oslo", "oslo (Crameri)"},
        {"lajolla", "lajolla (Crameri)"},       {"acton", "acton (Crameri)"},       {"devon", "devon (Crameri)"},
        {"lapaz", "lapaz (Crameri)"},           {"thermal", "thermal (cmocean)"},   {"haline", "haline (cmocean)"},
        {"deep", "deep (cmocean)"},             {"dense", "dense (cmocean)"},       {"ice", "ice (cmocean)"},
        {"tempo", "tempo (cmocean)"},           {"turbo", "turbo (Google)"},        {"ylgnbu", "YlGnBu (ColorBrewer)"},
        {"pubu", "PuBu (ColorBrewer)"},         {"gnbu", "GnBu (ColorBrewer)"},     {"blues", "Blues (ColorBrewer)"},
        {"purples", "Purples (ColorBrewer)"},   {"ylorrd", "YlOrRd (ColorBrewer)"}, {"cet-l08", "CET-L08"},
        {"cet-gouldian", "gouldian (CET-L20)"}, {"cet-l06", "CET-L06"},             {"cet-l17", "CET-L17"},
        {"cet-l18", "CET-L18"}};
    for (const auto& [key, title] : titles) {
        if (key == name) {
            return std::string(title);
        }
    }
    return std::string(name);
}

ScanColourMap scan_colour_map_or_default(std::string_view name) {
    const std::vector<std::string>& names = scan_colour_map_names();
    const auto found = std::find(names.begin(), names.begin() + 4, name);
    return found == names.begin() + 4 ? ScanColourMap::Viridis : static_cast<ScanColourMap>(found - names.begin());
}

ScanMapColour scan_map_colour(ScanColourMap map, double t) {
    if (!std::isfinite(t)) {
        return {};
    }
    const double clamped = std::clamp(t, 0.0, 1.0);
    return colour_map(map)[static_cast<std::size_t>(std::lround(clamped * static_cast<double>(kMapColours - 1)))];
}

ScanMapColour scan_map_colour(double t) { return scan_map_colour(ScanColourMap::Viridis, t); }

ScanRowPair scan_row_pair(std::span<const double> rising, double y, bool smooth) {
    ScanRowPair pair;
    if (rising.empty()) {
        return pair;
    }
    // The last row at or below y, and the one after it.
    const auto above = static_cast<std::size_t>(std::upper_bound(rising.begin(), rising.end(), y) - rising.begin());
    pair.first = pair.second = above == 0 ? 0 : above - 1;
    if (above > 0 && above < rising.size() && y > rising[pair.first]) {
        pair.second = above;
        pair.share = (y - rising[pair.first]) / (rising[pair.second] - rising[pair.first]);
        if (!smooth) {
            pair.share = pair.share < 0.5 ? 0.0 : 1.0;
        }
    }
    return pair;
}

const std::vector<std::string>& scan_colour_choices() {
    static const std::vector<std::string> choices = [] {
        std::vector<std::string> out = scan_colour_map_names();
        for (const std::string_view scheme : colour_scheme_names()) {
            out.push_back("ramp:" + std::string(scheme));
        }
        return out;
    }();
    return choices;
}

std::vector<ScanMapColour> scan_colour_table(std::string_view choice, const std::string& background, bool dark) {
    if (choice.starts_with("ramp:")) {
        const std::optional<ColourScheme> scheme = colour_scheme_from_name(choice.substr(5));
        if (scheme) {
            const std::string to = pattern_colour(*scheme, 0, 1, dark);
            std::vector<ScanMapColour> out(kMapColours);
            for (std::size_t i = 0; i < kMapColours; ++i) {
                const std::string hex =
                    mix_colours(background, to, static_cast<double>(i) / static_cast<double>(kMapColours - 1));
                const unsigned long rgb = std::strtoul(hex.c_str() + 1, nullptr, 16);
                out[i] = {static_cast<std::uint8_t>(rgb >> 16), static_cast<std::uint8_t>(rgb >> 8),
                          static_cast<std::uint8_t>(rgb), 255};
            }
            return out;
        }
    }
    const ColourTable& table = colour_map_named(choice);
    return {table.begin(), table.end()};
}

ScanMapColour scan_table_colour(std::span<const ScanMapColour> table, double t) {
    if (!std::isfinite(t) || table.empty()) {
        return {};
    }
    const double clamped = std::clamp(t, 0.0, 1.0);
    return table[static_cast<std::size_t>(std::lround(clamped * static_cast<double>(table.size() - 1)))];
}

}  // namespace edi
