// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

// The two views of a sequential fit's patterns (edi ADR-0041): every dataset's measured pattern one above another,
// and the same patterns as a 2D map, x across and the scan value up, intensity as colour. These functions reduce the
// patterns and place the rows; the app draws them.

namespace edi {

/// One dataset's measured pattern over the views' x range, cut into `columns` equal columns: each column's lowest and
/// highest intensity, NaN where no measured point falls. A long scan keeps only these, never its patterns.
struct ScanColumns {
    std::vector<float> low, high;
};
ScanColumns scan_columns(std::span<const double> x, std::span<const double> intensity, double x_min, double x_max,
                         std::size_t columns);

/// Where each dataset's row sits on the vertical axis: at its scan value when every dataset has a finite one, else at
/// its place in the scan, from 0.
std::vector<double> scan_row_positions(std::span<const double> values);

/// A row's extent on the vertical axis: halfway to its neighbours, rows sorted by position; a lone row, or one sharing
/// its position, spans half a step either side (a step being 1 when there is no other distance to take).
struct ScanRowSpan {
    double low = 0.0, high = 0.0;
};
std::vector<ScanRowSpan> scan_row_spans(std::span<const double> positions);

/// The 2D map's colour of `t` in [0, 1] (viridis, data/colormaps/PROVENANCE.md), clamped to the ends; none (alpha 0)
/// for a value that is not finite.
struct ScanMapColour {
    std::uint8_t r = 0, g = 0, b = 0, a = 0;
};
ScanMapColour scan_map_colour(double t);

}  // namespace edi
