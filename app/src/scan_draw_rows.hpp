// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <algorithm>
#include <cmath>
#include <limits>
#include <span>
#include <vector>
#include <utility>
#include "edi/scan_views.hpp"

namespace edi_app {

/// The Stacked rows that fit a screen: top down, evenly spread through visible rows, plus the selected row.
/// The selected curve may also enter from below; other off-screen baselines consume no display slots.
inline std::vector<std::size_t> stacked_draw_rows(std::span<const double> baselines, double pattern_height,
                                                 double low, double high, double pixels, int selected,
                                                 std::span<const int> hidden) {
    std::vector<std::size_t> order;
    if (!(high > low) || !(pixels > 0) || !std::isfinite(pixels) || !std::isfinite(low) ||
        !std::isfinite(high) || !std::isfinite(pattern_height)) return order;
    for (std::size_t d = 0; d < baselines.size(); ++d) {
        const double row = baselines[d];
        if (std::isfinite(row) && row >= low && row <= high &&
            std::find(hidden.begin(), hidden.end(), static_cast<int>(d)) == hidden.end()) order.push_back(d);
    }
    const auto above = [&baselines](std::size_t a, std::size_t b) {
        return baselines[a] != baselines[b] ? baselines[a] > baselines[b] : a < b;
    };
    std::sort(order.begin(), order.end(), above);
    const auto limit = static_cast<std::size_t>(std::clamp(std::floor(pixels / 12.0), 2.0, 256.0));
    std::vector<std::size_t> drawn;
    if (order.size() <= limit) drawn = std::move(order);
    else {
        drawn.reserve(limit + 1);
        for (std::size_t i = 0; i < limit; ++i) drawn.push_back(order[i * (order.size() - 1) / (limit - 1)]);
    }
    if (selected >= 0 && static_cast<std::size_t>(selected) < baselines.size() &&
        std::isfinite(baselines[static_cast<std::size_t>(selected)]) &&
        baselines[static_cast<std::size_t>(selected)] <= high &&
        baselines[static_cast<std::size_t>(selected)] + pattern_height >= low &&
        std::find(hidden.begin(), hidden.end(), selected) == hidden.end() &&
        std::find(drawn.begin(), drawn.end(), static_cast<std::size_t>(selected)) == drawn.end()) {
        drawn.push_back(static_cast<std::size_t>(selected));
        std::sort(drawn.begin(), drawn.end(), above);
    }
    return drawn;
}

/// The actual datasets contributing to one Map pixel row, with the existing band-edge interpolation.
struct MapPixelRow {
    static constexpr std::size_t none = std::numeric_limits<std::size_t>::max();
    std::size_t band = none, lower = none, upper = none;
    double share = 0;
};

/// Maps screen pixel centres to original dataset bands; at most three datasets contribute to each pixel row.
inline std::vector<MapPixelRow> map_pixel_rows(std::span<const double> rows, std::span<const edi::ScanRowSpan> spans,
                                              double low, double high, int pixels, bool smooth) {
    if (!(high > low) || pixels <= 0 || !std::isfinite(low) || !std::isfinite(high)) return {};
    std::vector<MapPixelRow> plan(static_cast<std::size_t>(pixels));
    std::vector<std::size_t> order;
    for (std::size_t d = 0; d < std::min(rows.size(), spans.size()); ++d)
        if (std::isfinite(rows[d])) order.push_back(d);
    std::sort(order.begin(), order.end(), [&rows](std::size_t a, std::size_t b) { return rows[a] < rows[b]; });
    if (order.empty()) return plan;
    std::vector<double> lows;
    lows.reserve(order.size());
    for (const auto d : order) lows.push_back(spans[d].low);
    const auto band_height = [&](std::size_t i) { return spans[order[i]].high - spans[order[i]].low; };
    for (int j = 0; j < pixels; ++j) {
        const double y = high - (static_cast<double>(j) + 0.5) / pixels * (high - low);
        if (y < spans[order.front()].low || y > spans[order.back()].high) continue;
        const auto past = static_cast<std::size_t>(std::upper_bound(lows.begin(), lows.end(), y) - lows.begin());
        const std::size_t band = past == 0 ? 0 : past - 1;
        std::size_t neighbour = band;
        if (smooth && band > 0 && y < spans[order[band]].low + band_height(band) / 4.0) neighbour = band - 1;
        else if (smooth && band + 1 < order.size() && y > spans[order[band]].high - band_height(band) / 4.0)
            neighbour = band + 1;
        const auto lower = std::min(band, neighbour), upper = std::max(band, neighbour);
        const double below = band_height(lower) / 4.0, above = band_height(upper) / 4.0;
        const double share = lower == upper || !(below + above > 0.0) ? 0.0
            : std::clamp((y - (spans[order[lower]].high - below)) / (below + above), 0.0, 1.0);
        plan[static_cast<std::size_t>(j)] = {order[band], order[lower], order[upper], share};
    }
    return plan;
}

}  // namespace edi_app
