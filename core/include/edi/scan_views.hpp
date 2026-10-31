// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

// The two views of a sequential fit's patterns (edi ADR-0041): every dataset's measured pattern one above another,
// and the same patterns as a 2D map, x across and the scan value up, intensity as colour. These functions reduce the
// patterns and place the rows; the app draws them.

namespace edi {

/// One dataset's measured pattern over an x range, cut into `columns` equal columns: each column's lowest and highest
/// intensity, NaN where no measured point falls. The points may come in any order along x.
struct ScanColumns {
    std::vector<float> low, high;
};
ScanColumns scan_columns(std::span<const double> x, std::span<const double> intensity, double x_min, double x_max,
                         std::size_t columns);

/// What the Stacked view draws of one pattern over [x_min, x_max] at `columns` pixel columns, always from the measured
/// points (never from a reduction made for another range): while the range holds no more points than columns, the
/// points themselves, with the nearest one beyond each end so the line reaches the plot's edges; with more, each
/// column's lowest and highest intensity at the column's centre (scan_columns). A vertex is drawn from `low` to `high`
/// and joined to the next one; the two are equal for a point. Points are taken in the order given (x rising or
/// falling); a point with no finite x or intensity breaks the line.
struct ScanTrace {
    std::vector<double> x;
    std::vector<float> low, high;
};
ScanTrace scan_trace(std::span<const double> x, std::span<const double> intensity, double x_min, double x_max,
                     std::size_t columns);

/// The line the Stacked view draws of one pattern over [x_min, x_max] at `columns` device pixel columns, as a line
/// through the measured points looks at that resolution: while the range holds no more than four points a column,
/// the points themselves, as scan_trace gives them; with more, each column's first, lowest, highest and last point in
/// their order, which draws the same pixels as every point would. Each vertex is one point (`low` equals `high`); a
/// point with no finite x or intensity breaks the line.
ScanTrace scan_polyline(std::span<const double> x, std::span<const double> intensity, double x_min, double x_max,
                        std::size_t columns);

/// What the Map colours one pattern's pixel columns by over [x_min, x_max]: with more points than columns, each
/// column's highest intensity; with no more, the line joining the measured points read at each column's centre, so a
/// zoomed map follows the points and not a reduction. NaN where the pattern has no value.
std::vector<float> scan_pixel_values(std::span<const double> x, std::span<const double> intensity, double x_min,
                                     double x_max, std::size_t columns);

/// Where each dataset's row sits on the vertical axis: at its scan value when every dataset has a finite one, else at
/// its place in the scan, from 0.
std::vector<double> scan_row_positions(std::span<const double> values);

/// A row's extent on the vertical axis: halfway to its neighbours, rows sorted by position; a lone row, or one sharing
/// its position, spans half a step either side (a step being 1 when there is no other distance to take).
struct ScanRowSpan {
    double low = 0.0, high = 0.0;
};
std::vector<ScanRowSpan> scan_row_spans(std::span<const double> positions);

/// Rows sharing a position (a scan value held, or reached again) each keep a band of their own: their shared span is
/// split equally among them in the order given, the first lowest, and each row moves to its share's centre. A row at a
/// position of its own keeps it and its span. `positions` and `spans` are scan_row_positions' and scan_row_spans'.
void separate_shared_rows(std::vector<double>& positions, std::vector<ScanRowSpan>& spans);

/// The two datasets whose rows bracket `y` on the Map's vertical axis, from `rising` (their rows in rising order), and
/// how far y is from the first towards the second: `first == second` and `share == 0` at or beyond the end rows. In
/// stepped mode the share is 0 or 1, the nearer row's. Empty input gives {0, 0, 0}.
struct ScanRowPair {
    std::size_t first = 0, second = 0;
    double share = 0.0;
};
ScanRowPair scan_row_pair(std::span<const double> rising, double y, bool smooth);

/// The Stacked view's spacing steps (the owner, 2026-10-26), from overlaid to fully separated, s = 0, 0.25, 0.5, 0.75
/// and 1; Wide is the default.
enum class StackedSpacing { Overlay, Close, Medium, Wide, Separate };
/// The steps' names, in the enum's order: "overlay", "close", "medium", "wide", "separate".
const std::vector<std::string>& stacked_spacing_names();
/// A step's title as the app lists it: "Overlay", "Close", "Medium", "Wide", "Separate".
std::string stacked_spacing_title(StackedSpacing spacing);
/// The step a stored name stands for; Wide for any other name.
StackedSpacing stacked_spacing_or_default(std::string_view name);
/// A step's s, from 0 (Overlay) to 1 (Separate).
double stacked_spacing_share(StackedSpacing spacing);

/// `count` stacked patterns on a plot `plot_height` tall at spacing `s` in [0, 1] (the linear rule, the owner,
/// 2026-10-26): each pattern `height` = H (1 - s) + (H / N) s tall, and the i-th from the bottom with its baseline at
/// i × `step`, step = s H / N, so the top pattern ends at H. s = 0 puts every baseline on one line; s = 1 makes the
/// patterns H / N tall, each starting where the one below ends. No patterns: the plot's height and no step.
struct StackedPlacement {
    double height = 0.0;
    double step = 0.0;
};
StackedPlacement stacked_placement(std::size_t count, double plot_height, double s);

/// The scan views' colour maps (data/colormaps/PROVENANCE.md; ADR-0041), in the order the app lists them; Blue-Red is
/// the default.
enum class ScanColourMap { BlueRed, Viridis, Batlow, Inferno, Lapaz, Greys };
/// Every map's name, in the enum's order: "blue-red", "viridis", "batlow", "inferno", "lapaz", "greys".
const std::vector<std::string>& scan_colour_map_names();
/// A map's title as the app lists it: "Blue-Red", "Viridis", "Batlow", "Inferno", "Lapaz", "Greys"; any other name
/// as it is.
std::string scan_colour_map_title(std::string_view name);
/// The map a name stands for; nullopt for any other name.
std::optional<ScanColourMap> scan_colour_map_from_name(std::string_view name);
/// The map a stored name stands for; Blue-Red for any other name, the maps offered before included.
ScanColourMap scan_colour_map_or_default(std::string_view name);

/// A colour map's colour of `t` in [0, 1], clamped to the ends; none (alpha 0) for a value that is not finite.
struct ScanMapColour {
    std::uint8_t r = 0, g = 0, b = 0, a = 0;
};
/// A map's 256 colours from its low end to its high end, as its name means them. Blue-Red runs from the plot area's
/// colour through blue to red, mixed in Oklab, in the theme's colours: #FFFFFF, #3F7FBF, #C8323C in the light theme,
/// #181818, #6AA6EA, #FC4F81 in the dark, whose Map plot area is black (the owner, 2026-10-27); the other maps are
/// their tables in either theme.
std::vector<ScanMapColour> scan_colour_map_table(ScanColourMap map, bool dark);
/// The map's colour of `t` in the theme.
ScanMapColour scan_map_colour(ScanColourMap map, double t, bool dark = false);
/// viridis's colour of `t`.
ScanMapColour scan_map_colour(double t);

/// Which way a map runs along the values: Auto, the default, puts the map's end nearest the chart's background at the
/// low values, so it follows the theme; Normal runs it low to high as its name means; Inverted the other way.
enum class ScanMapDirection { Auto, Normal, Inverted };
/// The directions' names, in the enum's order: "auto", "normal", "inverted".
const std::vector<std::string>& scan_map_direction_names();
/// A direction's title as the app lists it: "Auto", "Normal", "Inverted".
std::string scan_map_direction_title(ScanMapDirection direction);
/// The direction a stored name stands for; Auto for any other name.
ScanMapDirection scan_map_direction_or_default(std::string_view name);
/// Whether `map` is drawn inverted, its high end at the low values, on `background` (`#RRGGBB`) in the theme. Auto
/// inverts a map whose high end is nearer the background than its low end, by distance in Oklab.
bool scan_map_inverted(ScanColourMap map, ScanMapDirection direction, const std::string& background, bool dark);

/// The scan views' colour choices: the figure palettes' tokens (the Stacked view's only, edi::colour_scheme_names) and
/// the colour maps' names.
const std::vector<std::string>& scan_colour_choices();
/// A map's 256 colours in the order the values take them, from the low values to the high: the map's table in the
/// theme, inverted when `direction` inverts it on `background` (`#RRGGBB`). An unknown name is Blue-Red.
std::vector<ScanMapColour> scan_colour_table(std::string_view map, const std::string& background, bool dark,
                                             ScanMapDirection direction = ScanMapDirection::Normal);
/// A table's colour of `t` in [0, 1], clamped to the ends; none (alpha 0) for a value that is not finite.
ScanMapColour scan_table_colour(std::span<const ScanMapColour> table, double t);

}  // namespace edi
