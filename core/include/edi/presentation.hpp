// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_PRESENTATION_HPP
#define EDI_PRESENTATION_HPP

#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <memory>
#include <optional>
#include <span>
#include <string>
#include <vector>

// ADR-0021: the pattern presentation — the one description every renderer
// draws (the app's chart now).
// crysta computes every number; this file selects, decimates for the screen and maps to a display
// scale, and computes nothing else. `present_pattern` is a pure function of its two arguments.
// Qt-free, and no crysta type.

namespace edi {

class Project;

enum class YScale : std::uint8_t { Linear, Sqrt, Log10 };
enum class Pane : std::uint8_t { Main, Bragg, Residual };
enum class SeriesKind : std::uint8_t { Measured, Calculated, Background, Residual, BraggTicks };

// One excluded region of the experiment, as [min, max] on the x axis. Never decimated.
struct ExcludedBand {
    double x_min = 0.0, x_max = 0.0;
};

// The immutable buffers of one experiment, captured on the model's owner thread. Plain data: a
// renderer, or a test, may build one by hand.
struct PatternSource {
    using Column = std::shared_ptr<const std::vector<double>>;
    struct Phase {
        std::string structure_id, label;
        std::size_t place = 0;  // the structure's place in the project's list: its row and colour
        Column position;        // `_refln` positions, on the experiment's x axis
        std::shared_ptr<const std::vector<std::array<std::int32_t, 3>>> hkl;
        // The `_refln` row of each position; empty when they are rows 0, 1, 2, …
        std::vector<std::size_t> rows;
    };
    std::string x_title;                   // `2θ (°)` or `TOF (µs)`
    Column x, meas, su, calc, bkg, resid;  // null: the column is absent
    std::vector<Phase> phases;
    std::vector<ExcludedBand> excluded;
    std::size_t experiment_place = 0;  // the experiment's place in the project's list: its colour
    bool current = false;              // the computed columns describe the model now
};

// Owner thread. The computed columns and the reflections are taken only when the experiment's
// computed categories are current; otherwise they are absent and `current` is false.
PatternSource capture_pattern(const Project& project, std::size_t experiment_index);

// What the renderer asks for.
struct PatternView {
    std::optional<double> x_min, x_max;  // absent: the data's full range
    int columns = 0;                     // plot width in device pixels (pixel_columns); 0: no decimation
    YScale y_scale = YScale::Linear;
};

// y is in the pane's display scale. (NaN, NaN) is a gap.
struct PresentedPoint {
    double x = 0.0, y = 0.0;
};

inline constexpr std::size_t kNoRow = std::numeric_limits<std::size_t>::max();

struct PatternSeries {
    SeriesKind kind{};
    Pane pane{};
    std::string id;     // "meas", "calc", "bkg", "resid", "bragg/<structure id>"
    std::string label;  // the legend text
    std::string style;  // a key of pattern_style_table()
    std::vector<PresentedPoint> points;
    // Per point: its `_data` row, or its `_refln` row; kNoRow for a gap or a tick's end.
    std::vector<std::size_t> rows;
    // Measured only, per point: the error bar's ends in the display scale. A NaN lower end is
    // drawn to the bottom of the pane.
    std::vector<double> bar_low, bar_high;
};

struct AxisDescription {
    std::string title;
    double min = 0.0, max = 0.0;  // of what is presented, in the display scale
    YScale scale = YScale::Linear;
};

// A pane's share of the height: `fixed_px` when set, else `stretch` of what the fixed panes leave.
struct PaneLayout {
    Pane pane{};
    double stretch = 0.0;
    double fixed_px = 0.0;
};

struct PatternPresentation {
    bool current = false;  // the calculated series describe the model now
    AxisDescription x, y_main, y_residual;
    std::vector<PatternSeries> series;
    std::vector<ExcludedBand> excluded;
    std::vector<PaneLayout> layout;  // top to bottom
};

PatternPresentation present_pattern(const PatternSource& source, const PatternView& view);

// One row of the style table: every colour, width and mark a pattern renderer uses, light and dark.
struct SeriesStyle {
    std::string key, light, dark, mark;
    double width_px = 0.0;
    double opacity = 1.0;
    double marker_px = 0.0;
};
const std::vector<SeriesStyle>& pattern_style_table();

// The display scales. Linear: the value. Sqrt: sign(y) × sqrt(|y|). Log10: log10(y) for y > 0,
// NaN otherwise.
double to_display(double value, YScale scale);
double from_display(double display, YScale scale);
// The original value of a display value, as an axis shows it: `%.6g`, C locale.
std::string axis_label(double display, YScale scale);
// The plot's width in device pixels: max(1, floor(plot_width × device_pixel_ratio)).
int pixel_columns(double plot_width, double device_pixel_ratio);
// What a renderer shows for one presented point: x and the original value, or a tick's `h k l`.
// Empty for a gap or a tick's end.
std::string hover_text(const PatternSource& source, const PatternSeries& series, std::size_t point);

// One line of a hover read-out: its text and the style key whose colour draws it (empty: the theme's
// text colour).
struct HoverLine {
    std::string text, style;
};
// Diffraction-lib's read-out of one presented point. A data or residual point: `x`, then `Imeas`, `Ibkg`,
// `Icalc` and `Imeas - Icalc` at its `_data` row, each present column in its series' colour. A Bragg tick:
// the structure's name, `x` and `Miller indices: (h k l)` of its `_refln` row, the Miller indices alone in the
// tick's colour. Numbers with two decimals and a thousands separator. Empty for a gap or a tick's end.
std::vector<HoverLine> hover_readout(const PatternSource& source, const PatternSeries& series, std::size_t point);

// The decimator. A row is visible when its x lies in [x_min, x_max]; one row beyond each edge is
// kept too. The pixel column of a row is min(columns − 1, floor((x − x_min) / (x_max − x_min) ×
// columns)). A run is a stretch of consecutive visible rows whose `low` and `high` are numbers.
// Per run and per column: at most 4 rows are all kept; otherwise the first, the last, the row of
// the least `low` and the row of the greatest `high`. With `columns` <= 0, or an axis that is not
// monotonic, every visible row of a run is kept. Returns the kept rows, ascending.
std::vector<std::size_t> decimate_min_max(std::span<const double> x, std::span<const double> low,
                                          std::span<const double> high, double x_min, double x_max,
                                          int columns);

}  // namespace edi

#endif  // EDI_PRESENTATION_HPP
