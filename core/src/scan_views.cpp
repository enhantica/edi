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

namespace edi::detail {
extern const char* const kViridisTsv;
}

namespace edi {

namespace {

constexpr std::size_t kMapColours = 256;

// The embedded viridis table, read once: 256 colours, a header, `index<TAB>#RRGGBB` rows in order.
const std::array<ScanMapColour, kMapColours>& viridis() {
    static const std::array<ScanMapColour, kMapColours> table = [] {
        std::array<ScanMapColour, kMapColours> out{};
        std::istringstream in(detail::kViridisTsv);
        std::string line;
        std::getline(in, line);  // the header
        std::size_t count = 0;
        while (std::getline(in, line)) {
            if (line.empty()) {
                continue;
            }
            const std::size_t tab = line.find('\t');
            if (count >= kMapColours || tab == std::string::npos || line.size() != tab + 8 || line[tab + 1] != '#') {
                throw std::logic_error("data/colormaps/viridis.tsv: row " + std::to_string(count + 1) + " is not '<index>\t#RRGGBB'");
            }
            const unsigned long rgb = std::strtoul(line.c_str() + tab + 2, nullptr, 16);
            out[count++] = {static_cast<std::uint8_t>(rgb >> 16), static_cast<std::uint8_t>(rgb >> 8),
                            static_cast<std::uint8_t>(rgb), 255};
        }
        if (count != kMapColours) {
            throw std::logic_error("data/colormaps/viridis.tsv holds " + std::to_string(count) + " colours, not 256");
        }
        return out;
    }();
    return table;
}

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

ScanMapColour scan_map_colour(double t) {
    if (!std::isfinite(t)) {
        return {};
    }
    const double clamped = std::clamp(t, 0.0, 1.0);
    return viridis()[static_cast<std::size_t>(std::lround(clamped * static_cast<double>(kMapColours - 1)))];
}

}  // namespace edi
