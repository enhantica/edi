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

#include "edi/palette.hpp"

// ADR-0021: the pattern presentation — the one description every renderer
// draws (the app's chart now).
// crysta computes every number; this file selects, decimates for the screen and maps to a display
// scale, and computes nothing else. `present_pattern` is a pure function of its two arguments.
// Qt-free, and no crysta type.

namespace edi {

class ExperimentBase;
class Project;

enum class YScale : std::uint8_t { Linear, Sqrt, Log10 };
enum class Pane : std::uint8_t { Main, Bragg, Residual };
enum class SeriesKind : std::uint8_t { Measured, Calculated, Background, Residual, BraggTicks, StructureCurve };

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
        Column readout;         // what a tick's readout shows when not its position: the reflection's d on the d axis
        std::shared_ptr<const std::vector<std::array<std::int32_t, 3>>> hkl;
        // The `_refln` row of each position; empty when they are rows 0, 1, 2, …
        std::vector<std::size_t> rows;
    };
    std::string x_title;                   // `2θ (deg)` or `TOF (µs)`
    std::string x_item;                    // the dictionary item of x, whose format its readouts take
    Column x, meas, su, calc, bkg, resid;  // null: the column is absent
    std::vector<Phase> phases;
    // Each linked structure's calculated curve above the background (crysta's component_intensities_net), in the
    // order the experiment links them; captured with the calculated columns.
    struct Component {
        std::string structure_id, label;
        std::size_t place = 0;  // the structure's place in the project's list: its colour
        Column net;
    };
    std::vector<Component> components;
    std::vector<ExcludedBand> excluded;
    // A single crystal's calculated F², one per measured reflection in its order (it has no pattern).
    Column refln_calc;
    std::size_t experiment_place = 0;  // the experiment's place in the project's list: its colour
    bool current = false;              // the computed columns describe the model now
    bool d_available = false;          // a current d column, so the pattern can be shown on the d axis
};

// The x axis a pattern is captured on: the experiment's own (2θ or TOF), or d-spacing.
enum class PatternAxis : std::uint8_t { Native, DSpacing };

// Owner thread. The computed columns and the reflections are taken only when the experiment's
// computed categories are current; otherwise they are absent and `current` is false.
// On the d axis x is `_pd_data.d_spacing`, titled `d (Å)`; every column is reversed when d descends (constant
// wavelength), so x ascends (a presented point's row then counts from the last `_data` row), and each excluded band's
// ends and each tick's `_refln.position` are mapped to d along the data, so a tick meets its peak; a tick's readout is
// its `_refln.d_spacing`. Without a current d column the pattern stays on its own axis.
PatternSource capture_pattern(const Project& project, std::size_t experiment_index,
                              PatternAxis axis = PatternAxis::Native);

// One experiment's `_refln` rows grouped into phases, one per structure id in the order the ids first
// appear. A phase's place is its structure's place in `structure_names` (its first place when there
// is no such name). capture_pattern groups this way, and so does a scan's fitted file.
std::vector<PatternSource::Phase> group_reflections(std::span<const std::string> structure_id,
                                                    std::span<const double> position,
                                                    std::span<const std::int32_t> index_h,
                                                    std::span<const std::int32_t> index_k,
                                                    std::span<const std::int32_t> index_l,
                                                    std::span<const std::string> structure_names);

// Each structure's curve above the background out of crysta's row-major table (`net`, one value per point and
// structure in `order`), one component per structure, placed as group_reflections places phases. None when the
// table does not hold one value per point and structure.
std::vector<PatternSource::Component> structure_components(std::span<const std::string> order,
                                                           std::span<const double> net, std::size_t points,
                                                           std::span<const std::string> structure_names);

// What the renderer asks for.
struct PatternView {
    std::optional<double> x_min, x_max;  // absent: the data's full range (the included range when included_only)
    int columns = 0;                     // plot width in device pixels (pixel_columns); 0: no decimation
    YScale y_scale = YScale::Linear;
    bool structure_curves = false;  // each structure's curve over the background (edi ADR-0017 §15)
    // The residual drawn as a band, (meas − calc) ± s.u. (edi ADR-0017 §15): its band's ends count in its pane's range.
    bool residual_band = false;
    // Only the included range (ADR-0044): the default x range runs from the first to the last included point, and
    // no measured point is drawn inside an excluded region. Reflection ticks are hidden there in both states.
    bool included_only = false;
    // Series (by id) still presented whose points do not count in the main pane's range: curves hidden from the
    // chart when the range is to fit the visible ones (edi ADR-0017 §15).
    std::vector<std::string> uncounted;
    // Every curve with the background subtracted (edi ADR-0017 §15): the measured and calculated values less the
    // calculated background at each point, the background drawn at zero and each structure's curve rising from zero;
    // the residual is unchanged. A pattern with no current background column is drawn as it is.
    bool subtract_background = false;
};

// y is in the pane's display scale. (NaN, NaN) is a gap.
struct PresentedPoint {
    double x = 0.0, y = 0.0;
};

inline constexpr std::size_t kNoRow = std::numeric_limits<std::size_t>::max();

struct PatternSeries {
    SeriesKind kind{};
    Pane pane{};
    std::string id;     // "meas", "calc", "bkg", "resid", "bragg/<structure id>", "structure/<structure id>"
    std::string label;  // the legend text
    std::string style;  // a key of pattern_style_table(): `meas.<experiment place>`, `bragg.<structure place>`
    std::vector<PresentedPoint> points;
    // Per point: its `_data` row, or its `_refln` row; kNoRow for a gap or a tick's end.
    std::vector<std::size_t> rows;
    // Measured, per point: the error bar's ends in the display scale. A NaN lower end is
    // drawn to the bottom of the pane. A structure curve: bar_low is the background its fill starts from. The
    // residual, when the view asks for its band: (meas − calc) ∓ the measured s.u.
    std::vector<double> bar_low, bar_high;
};

// A piece of an axis title in a series' colour: `style` names its style row; empty, it is plain (a separator).
struct TitleSegment {
    std::string text, style;
};

struct AxisDescription {
    std::string title;
    // The title as coloured pieces, each series' word in its colour: the main pane's "meas, calc, bkg" and the
    // residual's "meas − calc", of the series presented. Empty for the x axis.
    std::vector<TitleSegment> segments;
    double min = 0.0, max = 0.0;  // of what is presented, in the display scale
    YScale scale = YScale::Linear;
};

// A pane's share of the height: `fixed_px` when set, else `stretch` of what the fixed panes leave.
struct PaneLayout {
    Pane pane{};
    double stretch = 0.0;
    double fixed_px = 0.0;
};

// A Bragg tick row's label, drawn at the row's left in its colour: the structure's name, its style row and the
// row's centre in the Bragg pane's units (row k from the bottom spans k to k + 1).
struct BraggRowLabel {
    std::string text, style;
    double centre = 0.0;
};

struct PatternPresentation {
    bool current = false;  // the calculated series describe the model now
    AxisDescription x, y_main, y_residual;
    std::vector<PatternSeries> series;
    std::vector<BraggRowLabel> bragg_labels;
    std::vector<ExcludedBand> excluded;
    std::vector<PaneLayout> layout;  // top to bottom
};

PatternPresentation present_pattern(const PatternSource& source, const PatternView& view);

// Whether the experiment declares a background: line-segment points, or polynomial or Chebyshev terms, fitted or not.
// One that declares none has nothing to subtract (PatternView::subtract_background).
bool has_background(const ExperimentBase& experiment);

// One row of the style table: every colour, width and mark a pattern renderer uses, light and dark.
struct SeriesStyle {
    std::string key, light, dark, mark;
    double width_px = 0.0;
    double opacity = 1.0;
    double marker_px = 0.0;
};
// The style table of a project of `experiments` experiments and `structures` structures in `scheme`: a
// `meas.<place>` row per experiment (at least three), and a `bragg.<place>` and a `structure.<place>` row per
// structure (at least five), each in the palette's colour at the item's position (edi::figure_colour); and the role
// rows: the calculated, background and residual styles in the palette's role colours (edi::role_colour) and the
// excluded-region style. `positions` holds the experiments' positions, then the structures'; empty, or of another
// length, they are colour_positions' for a project with none held. Rows beyond the items take the next free positions.
std::vector<SeriesStyle> pattern_style_table(ColourScheme scheme = kDefaultColourScheme, std::size_t experiments = 3,
                                             std::size_t structures = 0, std::span<const std::size_t> positions = {});

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

// A series' legend label as coloured pieces: its label in its own style, except the residual's, "Residual (meas −
// calc)", whose `meas − calc` is coloured as the residual pane's title colours it.
std::vector<TitleSegment> legend_label(const PatternPresentation& presentation, const PatternSeries& series);

// One line of a hover read-out: its text and the style key whose colour draws it (empty: the theme's
// text colour), or, when `segments` is not empty, the same text as pieces each in its own style's colour.
struct HoverLine {
    std::string text, style;
    std::vector<TitleSegment> segments;
};
// Diffraction-lib's read-out of one presented point, named as the y titles name the series. A data or residual
// point: `x`, then `meas`, `bkg`, `calc` and `meas − calc` at its `_data` row, each present column in its series'
// colour, `meas − calc` coloured as the residual pane's title with its value in the residual's colour. A Bragg tick:
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
