// SPDX-License-Identifier: BSD-3-Clause
#include "edi/presentation.hpp"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <locale>
#include <sstream>
#include <utility>

#include "edi/model.hpp"

namespace edi {
namespace {

const double kNaN = std::numeric_limits<double>::quiet_NaN();
constexpr double kBraggRowPx = 18.0;   // one Bragg row per structure (diffraction-lib's layout)
constexpr double kTickInset = 0.15;    // a tick spans the middle 70 % of its row
constexpr std::size_t kPaletteSize = 3;

// The x range a column index is taken over, and whether rows can be binned at all.
struct Columns {
    double x_min = 0.0, x_max = 0.0;
    int count = 0;  // 0: no decimation

    int of(double x) const {
        const double scaled = (x - x_min) / (x_max - x_min) * static_cast<double>(count);
        return std::min(count - 1, static_cast<int>(std::floor(scaled)));
    }
};

bool monotonic(std::span<const double> x) {
    bool ascending = true, descending = true;
    for (std::size_t i = 1; i < x.size(); ++i) {
        ascending = ascending && x[i] >= x[i - 1];
        descending = descending && x[i] <= x[i - 1];
    }
    return ascending || descending;
}

// The kept rows, ascending, and for each the number of its run (runs count from 0 in row order).
struct Kept {
    std::vector<std::size_t> rows;
    std::vector<std::size_t> runs;
};

Kept decimate(std::span<const double> x, std::span<const double> low, std::span<const double> high,
              double x_min, double x_max, int columns) {
    Kept kept;
    const std::size_t n = std::min({x.size(), low.size(), high.size()});
    if (n == 0) {
        return kept;
    }
    const auto valid = [&](std::size_t i) { return !std::isnan(low[i]) && !std::isnan(high[i]); };
    const auto inside = [&](std::size_t i) { return x[i] >= x_min && x[i] <= x_max; };
    const bool binned = columns > 0 && x_max > x_min && monotonic(x.first(n));
    const Columns bins{x_min, x_max, binned ? columns : 0};

    // The visible rows, and on a monotonic axis one row beyond each edge.
    std::vector<char> visible(n, 0);
    for (std::size_t i = 0; i < n; ++i) {
        visible[i] = inside(i) ? 1 : 0;
    }
    if (monotonic(x.first(n))) {
        for (std::size_t i = 0; i < n; ++i) {
            if (!inside(i) && ((i > 0 && inside(i - 1)) || (i + 1 < n && inside(i + 1)))) {
                visible[i] = 2;  // an edge neighbour: always kept, in a column of its own
            }
        }
        // A view that holds no row at all still has its two neighbours: the rows on either side of
        // it, so a line crosses the view.
        for (std::size_t i = 0; i + 1 < n; ++i) {
            const bool straddles = (x[i] < x_min && x[i + 1] > x_max) || (x[i] > x_max && x[i + 1] < x_min);
            if (straddles) {
                visible[i] = visible[i + 1] = 2;
            }
        }
    }

    // One group: the rows of one run in one pixel column.
    struct Group {
        std::size_t count = 0, first = 0, last = 0, least = 0, greatest = 0;
        std::size_t few[4] = {0, 0, 0, 0};
    } group;
    std::size_t run = 0;
    bool in_run = false;
    int column = 0;
    const auto flush = [&] {
        if (group.count == 0) {
            return;
        }
        if (group.count <= 4) {
            for (std::size_t k = 0; k < group.count; ++k) {
                kept.rows.push_back(group.few[k]);
                kept.runs.push_back(run);
            }
        } else {
            std::size_t picks[4] = {group.first, group.least, group.greatest, group.last};
            std::sort(std::begin(picks), std::end(picks));
            std::size_t previous = kNoRow;
            for (const std::size_t pick : picks) {
                if (pick != previous) {
                    kept.rows.push_back(pick);
                    kept.runs.push_back(run);
                    previous = pick;
                }
            }
        }
        group = Group{};
    };
    for (std::size_t i = 0; i < n; ++i) {
        if (visible[i] == 0 || !valid(i)) {
            if (in_run) {
                flush();
                ++run;
                in_run = false;
            }
            continue;
        }
        // Without bins every row is a group of its own; an edge neighbour is one too.
        const int here = !binned ? -1 : visible[i] == 2 ? -2 : bins.of(x[i]);
        if (in_run && (here < 0 || here != column)) {
            flush();
        }
        in_run = true;
        column = here;
        if (group.count == 0) {
            group.first = group.least = group.greatest = i;
        }
        if (group.count < 4) {
            group.few[group.count] = i;
        }
        if (low[i] < low[group.least]) {
            group.least = i;
        }
        if (high[i] > high[group.greatest]) {
            group.greatest = i;
        }
        group.last = i;
        ++group.count;
    }
    flush();
    return kept;
}

std::pair<double, double> full_range(const std::vector<double>& x) {
    double lo = kNaN, hi = kNaN;
    for (const double value : x) {
        if (std::isnan(value)) {
            continue;
        }
        lo = std::isnan(lo) ? value : std::min(lo, value);
        hi = std::isnan(hi) ? value : std::max(hi, value);
    }
    return {std::isnan(lo) ? 0.0 : lo, std::isnan(hi) ? 0.0 : hi};
}

// Widens an axis to what a series presents.
void cover(AxisDescription& axis, bool& any, double value) {
    if (std::isnan(value)) {
        return;
    }
    axis.min = any ? std::min(axis.min, value) : value;
    axis.max = any ? std::max(axis.max, value) : value;
    any = true;
}

std::vector<double> displayed(const std::vector<double>& values, YScale scale) {
    std::vector<double> out(values.size());
    for (std::size_t i = 0; i < values.size(); ++i) {
        out[i] = to_display(values[i], scale);
    }
    return out;
}

// A line series from the kept rows, with one gap point between two runs.
void fill_points(PatternSeries& series, const Kept& kept, const std::vector<double>& x,
                 const std::vector<double>& display) {
    series.points.reserve(kept.rows.size() + 8);
    series.rows.reserve(kept.rows.size() + 8);
    for (std::size_t k = 0; k < kept.rows.size(); ++k) {
        if (k > 0 && kept.runs[k] != kept.runs[k - 1]) {
            series.points.push_back({kNaN, kNaN});
            series.rows.push_back(kNoRow);
        }
        const std::size_t row = kept.rows[k];
        series.points.push_back({x[row], display[row]});
        series.rows.push_back(row);
    }
}

std::string style_key(const char* base, std::size_t place) {
    return std::string(base) + "." + std::to_string(place % kPaletteSize);
}

// Six significant digits, as `%.6g` spells them in the C locale, whatever the process's locale is (I21): a
// label has a decimal point, never a comma.
std::string number(double value) {
    std::ostringstream stream;
    stream.imbue(std::locale::classic());
    stream << std::setprecision(6) << value;
    return stream.str();
}

// A read-out number, as diffraction-lib's: two decimals and a comma between thousands (`1,192.23`).
std::string readout_number(double value) {
    if (!std::isfinite(value)) {
        return number(value);
    }
    std::ostringstream stream;
    stream.imbue(std::locale::classic());
    stream << std::fixed << std::setprecision(2) << std::fabs(value);
    std::string digits = stream.str();
    const std::size_t point = digits.find('.');
    for (std::size_t at = point; at > 3; at -= 3) {
        digits.insert(at - 3, ",");
    }
    return (value < 0.0 && digits.find_first_not_of("0.,") != std::string::npos ? "-" : "") + digits;
}

}  // namespace

double to_display(double value, YScale scale) {
    switch (scale) {
        case YScale::Linear:
            return value;
        case YScale::Sqrt:
            return std::isnan(value) ? value : std::copysign(std::sqrt(std::fabs(value)), value);
        case YScale::Log10:
            return value > 0.0 ? std::log10(value) : kNaN;
    }
    return value;
}

double from_display(double display, YScale scale) {
    switch (scale) {
        case YScale::Linear:
            return display;
        case YScale::Sqrt:
            return std::copysign(display * display, display);
        case YScale::Log10:
            return std::pow(10.0, display);
    }
    return display;
}

std::string axis_label(double display, YScale scale) {
    const double value = from_display(display, scale);
    return number(value == 0.0 ? 0.0 : value);  // never "-0"
}

int pixel_columns(double plot_width, double device_pixel_ratio) {
    const double columns = std::floor(plot_width * device_pixel_ratio);
    return columns >= 1.0 ? static_cast<int>(columns) : 1;
}

std::vector<std::size_t> decimate_min_max(std::span<const double> x, std::span<const double> low,
                                          std::span<const double> high, double x_min, double x_max,
                                          int columns) {
    return decimate(x, low, high, x_min, x_max, columns).rows;
}

const std::vector<SeriesStyle>& pattern_style_table() {
    // edi ADR-0017 §15: easydiffractionbeta's chart colours and widths (its QtCharts1dTab.qml; the residual's
    // 1 px line and the Bragg ticks' 1 px lines as it draws them, the owner, 2026-10-02). The measured and tick
    // palettes are §8's block colours, by the block's place.
    static const std::vector<SeriesStyle> table = {
        {"meas.0", "#03A9F4", "#81D4FA", "line+markers+bars", 2.0, 1.0, 5.0},
        {"meas.1", "#795548", "#BCAAA4", "line+markers+bars", 2.0, 1.0, 5.0},
        {"meas.2", "#4CAF50", "#A5D6A7", "line+markers+bars", 2.0, 1.0, 5.0},
        {"calc", "#F44336", "#EF9A9A", "line", 2.0, 1.0, 0.0},
        {"bkg", "#607D8B", "#B0BEC5", "line", 1.0, 1.0, 0.0},
        {"resid", "#8BC34A", "#C5E1A5", "line", 1.0, 1.0, 0.0},
        {"bragg.0", "#FF9800", "#FFCC80", "ticks", 1.0, 1.0, 0.0},
        {"bragg.1", "#009688", "#80CBC4", "ticks", 1.0, 1.0, 0.0},
        {"bragg.2", "#E91E63", "#F48FB1", "ticks", 1.0, 1.0, 0.0},
        {"excluded", "#8C8C8C", "#8C8C8C", "band", 0.0, 0.15, 0.0},
    };
    return table;
}

PatternSource capture_pattern(const Project& project, std::size_t experiment_index) {
    PatternSource source;
    const ExperimentBase& experiment = *project.experiments[experiment_index];
    source.experiment_place = experiment_index;
    for (const auto& [start, end] : excluded_region_ranges(experiment.excluded_regions)) {
        source.excluded.push_back({std::min(start, end), std::max(start, end)});
    }
    if (!experiment.data.has_value()) {
        return source;
    }
    const PdDataBase& data = *experiment.data;
    if (data.two_theta.has_value() == data.time_of_flight.has_value()) {
        return source;  // no single engaged axis: nothing to present
    }
    source.x_title = data.two_theta.has_value() ? "2θ (°)" : "TOF (µs)";
    const auto copy = [](const std::vector<double>& values) -> PatternSource::Column {
        return values.empty() ? nullptr : std::make_shared<const std::vector<double>>(values);
    };
    source.x = copy(data.axis());
    source.meas = copy(data.intensity_meas);
    source.su = copy(data.intensity_meas_su);
    source.current = experiment.computed_current();
    if (!source.current) {
        return source;
    }
    const auto shared = [](const ComputedColumn<double>& column) -> PatternSource::Column {
        return column.empty() ? nullptr : column.buffer();
    };
    source.calc = shared(data.intensity_calc);
    source.bkg = shared(data.intensity_bkg);
    source.resid = shared(data.residual);

    // One phase per structure id, in the order the ids first appear in `_refln`.
    const PowderReflnDataBase& refln = experiment.refln;
    struct Building {
        PatternSource::Phase phase;
        std::vector<double> position;
        std::vector<std::array<std::int32_t, 3>> hkl;
    };
    std::vector<Building> building;
    for (std::size_t row = 0; row < refln.size(); ++row) {
        const std::string& id = refln.structure_id[row];
        auto found = std::find_if(building.begin(), building.end(),
                                  [&](const Building& b) { return b.phase.structure_id == id; });
        if (found == building.end()) {
            Building next;
            next.phase.structure_id = id;
            next.phase.label = id;
            next.phase.place = building.size();
            for (std::size_t place = 0; place < project.structures.size(); ++place) {
                if (project.structures[place]->name == id) {
                    next.phase.place = place;
                }
            }
            building.push_back(std::move(next));
            found = building.end() - 1;
        }
        found->position.push_back(refln.position[row]);
        found->hkl.push_back({refln.index_h[row], refln.index_k[row], refln.index_l[row]});
        found->phase.rows.push_back(row);
    }
    for (Building& b : building) {
        b.phase.position = std::make_shared<const std::vector<double>>(std::move(b.position));
        b.phase.hkl =
            std::make_shared<const std::vector<std::array<std::int32_t, 3>>>(std::move(b.hkl));
        if (building.size() == 1) {
            b.phase.rows.clear();  // rows 0, 1, 2, …
        }
        source.phases.push_back(std::move(b.phase));
    }
    return source;
}

PatternPresentation present_pattern(const PatternSource& source, const PatternView& view) {
    PatternPresentation out;
    out.current = source.current;
    out.excluded = source.excluded;
    out.x.title = source.x_title;
    out.y_main.title = "Intensity";
    out.y_main.scale = view.y_scale;
    out.y_residual.title = "Residual";  // the owner, 2026-10-02
    static const std::vector<double> kNone;
    const std::vector<double>& x = source.x ? *source.x : kNone;
    const auto [data_min, data_max] = full_range(x);
    out.x.min = view.x_min.value_or(data_min);
    out.x.max = view.x_max.value_or(data_max);
    bool any_main = false, any_residual = false;

    const auto column_for = [&](const PatternSource::Column& column) -> const std::vector<double>* {
        return column && column->size() == x.size() && !x.empty() ? column.get() : nullptr;
    };

    // --- measured: the union of two passes, over the values and over the bar ends ---------------
    if (const std::vector<double>* meas = column_for(source.meas)) {
        PatternSeries series;
        series.kind = SeriesKind::Measured;
        series.pane = Pane::Main;
        series.id = "meas";
        series.label = "Measured (Imeas)";
        series.style = style_key("meas", source.experiment_place);
        const std::vector<double> display = displayed(*meas, view.y_scale);
        const std::vector<double>* su = column_for(source.su);
        std::vector<double> bar_low(x.size()), bar_high(x.size());
        for (std::size_t i = 0; i < x.size(); ++i) {
            const double half = su != nullptr ? (*su)[i] : 0.0;
            bar_low[i] = to_display((*meas)[i] - half, view.y_scale);
            bar_high[i] = to_display((*meas)[i] + half, view.y_scale);
        }
        Kept kept = decimate(x, display, display, out.x.min, out.x.max, view.columns);
        if (su != nullptr) {
            // A bar end that cannot be drawn stands in as the measured value, so both passes see
            // the same runs.
            std::vector<double> low(x.size()), high(x.size());
            for (std::size_t i = 0; i < x.size(); ++i) {
                low[i] = std::isnan(bar_low[i]) ? display[i] : bar_low[i];
                high[i] = std::isnan(bar_high[i]) ? display[i] : bar_high[i];
            }
            const Kept bars = decimate(x, low, high, out.x.min, out.x.max, view.columns);
            Kept merged;
            std::size_t a = 0, b = 0;
            while (a < kept.rows.size() || b < bars.rows.size()) {
                const bool take_a = b == bars.rows.size() ||
                                    (a < kept.rows.size() && kept.rows[a] <= bars.rows[b]);
                const std::size_t row = take_a ? kept.rows[a] : bars.rows[b];
                const std::size_t run = take_a ? kept.runs[a] : bars.runs[b];
                if (take_a && b < bars.rows.size() && bars.rows[b] == row) {
                    ++b;
                }
                take_a ? ++a : ++b;
                merged.rows.push_back(row);
                merged.runs.push_back(run);
            }
            kept = std::move(merged);
        }
        fill_points(series, kept, x, display);
        series.bar_low.reserve(series.rows.size());
        series.bar_high.reserve(series.rows.size());
        for (const std::size_t row : series.rows) {
            series.bar_low.push_back(row == kNoRow ? kNaN : bar_low[row]);
            series.bar_high.push_back(row == kNoRow ? kNaN : bar_high[row]);
        }
        for (std::size_t k = 0; k < series.points.size(); ++k) {
            cover(out.y_main, any_main, series.points[k].y);
            cover(out.y_main, any_main, series.bar_low[k]);
            cover(out.y_main, any_main, series.bar_high[k]);
        }
        out.series.push_back(std::move(series));
    }

    // --- the lines -------------------------------------------------------------------------------
    const auto line = [&](const PatternSource::Column& column, SeriesKind kind, Pane pane,
                          const char* id, const char* label, const char* style, YScale scale) {
        const std::vector<double>* values = column_for(column);
        if (values == nullptr) {
            return;
        }
        PatternSeries series;
        series.kind = kind;
        series.pane = pane;
        series.id = id;
        series.label = label;
        series.style = style;
        const std::vector<double> display = displayed(*values, scale);
        fill_points(series, decimate(x, display, display, out.x.min, out.x.max, view.columns), x,
                    display);
        for (const PresentedPoint& point : series.points) {
            pane == Pane::Residual ? cover(out.y_residual, any_residual, point.y)
                                   : cover(out.y_main, any_main, point.y);
        }
        out.series.push_back(std::move(series));
    };
    if (source.current) {
        line(source.calc, SeriesKind::Calculated, Pane::Main, "calc", "Total calculated (Icalc)", "calc",
             view.y_scale);
        line(source.bkg, SeriesKind::Background, Pane::Main, "bkg", "Background (Ibkg)", "bkg",
             view.y_scale);
        line(source.resid, SeriesKind::Residual, Pane::Residual, "resid", "Residual (Imeas − Icalc)", "resid",
             YScale::Linear);
    }
    const bool has_residual = std::any_of(out.series.begin(), out.series.end(), [](const auto& s) {
        return s.kind == SeriesKind::Residual;
    });

    // --- the Bragg ticks: one series per structure, at most one tick per pixel column -------------
    std::vector<const PatternSource::Phase*> phases;
    if (source.current) {
        for (const PatternSource::Phase& phase : source.phases) {
            if (phase.position) {
                phases.push_back(&phase);
            }
        }
    }
    std::stable_sort(phases.begin(), phases.end(),
                     [](const auto* a, const auto* b) { return a->place < b->place; });
    const bool binned = view.columns > 0 && out.x.max > out.x.min;
    const Columns bins{out.x.min, out.x.max, binned ? view.columns : 0};
    for (std::size_t k = 0; k < phases.size(); ++k) {
        const PatternSource::Phase& phase = *phases[k];
        PatternSeries series;
        series.kind = SeriesKind::BraggTicks;
        series.pane = Pane::Bragg;
        series.id = "bragg/" + phase.structure_id;
        series.label = phase.label;
        series.style = style_key("bragg", phase.place);
        const double row_bottom = static_cast<double>(phases.size() - k - 1);
        std::vector<char> taken(binned ? static_cast<std::size_t>(view.columns) : 0, 0);
        for (std::size_t r = 0; r < phase.position->size(); ++r) {
            const double position = (*phase.position)[r];
            // A tick is drawn inside the view's x range or not at all.
            if (std::isnan(position) || position < out.x.min || position > out.x.max) {
                continue;
            }
            if (binned) {
                char& slot = taken[static_cast<std::size_t>(std::max(0, bins.of(position)))];
                if (slot != 0) {
                    continue;
                }
                slot = 1;
            }
            series.points.push_back({position, row_bottom + kTickInset});
            series.points.push_back({position, row_bottom + 1.0 - kTickInset});
            series.points.push_back({kNaN, kNaN});
            series.rows.push_back(r < phase.rows.size() ? phase.rows[r] : r);
            series.rows.push_back(kNoRow);
            series.rows.push_back(kNoRow);
        }
        out.series.push_back(std::move(series));
    }

    // --- the layout, top to bottom ------------------------------------------------------------------
    out.layout.push_back({Pane::Main, has_residual ? 0.7 : 1.0, 0.0});
    if (!phases.empty()) {
        out.layout.push_back({Pane::Bragg, 0.0, kBraggRowPx * static_cast<double>(phases.size())});
    }
    if (has_residual) {
        out.layout.push_back({Pane::Residual, 0.3, 0.0});
    }
    return out;
}

std::string hover_text(const PatternSource& source, const PatternSeries& series, std::size_t point) {
    if (point >= series.rows.size() || series.rows[point] == kNoRow) {
        return {};
    }
    const std::size_t row = series.rows[point];
    if (series.kind == SeriesKind::BraggTicks) {
        for (const PatternSource::Phase& phase : source.phases) {
            if ("bragg/" + phase.structure_id != series.id || !phase.hkl) {
                continue;
            }
            // The tick's place among this phase's reflections.
            std::size_t index = row;
            if (!phase.rows.empty()) {
                const auto found = std::find(phase.rows.begin(), phase.rows.end(), row);
                if (found == phase.rows.end()) {
                    return {};
                }
                index = static_cast<std::size_t>(found - phase.rows.begin());
            }
            if (index >= phase.hkl->size()) {
                return {};
            }
            const auto& hkl = (*phase.hkl)[index];
            return std::to_string(hkl[0]) + " " + std::to_string(hkl[1]) + " " +
                   std::to_string(hkl[2]);
        }
        return {};
    }
    const PatternSource::Column& column = series.kind == SeriesKind::Measured     ? source.meas
                                          : series.kind == SeriesKind::Calculated ? source.calc
                                          : series.kind == SeriesKind::Background ? source.bkg
                                                                                  : source.resid;
    if (!source.x || !column || row >= source.x->size() || row >= column->size()) {
        return {};
    }
    return number((*source.x)[row]) + ", " + number((*column)[row]);
}

std::vector<HoverLine> hover_readout(const PatternSource& source, const PatternSeries& series, std::size_t point) {
    if (point >= series.rows.size() || series.rows[point] == kNoRow) {
        return {};
    }
    const std::size_t row = series.rows[point];
    if (series.kind == SeriesKind::BraggTicks) {
        for (const PatternSource::Phase& phase : source.phases) {
            if ("bragg/" + phase.structure_id != series.id || !phase.hkl || !phase.position) {
                continue;
            }
            std::size_t index = row;
            if (!phase.rows.empty()) {
                const auto found = std::find(phase.rows.begin(), phase.rows.end(), row);
                if (found == phase.rows.end()) {
                    return {};
                }
                index = static_cast<std::size_t>(found - phase.rows.begin());
            }
            if (index >= phase.hkl->size() || index >= phase.position->size()) {
                return {};
            }
            const auto& hkl = (*phase.hkl)[index];
            // Only the Miller indices take the tick's colour (the owner, 2026-10-03).
            return {{phase.structure_id, ""},
                    {"x: " + readout_number((*phase.position)[index]), ""},
                    {"Miller indices: (" + std::to_string(hkl[0]) + " " + std::to_string(hkl[1]) + " " +
                         std::to_string(hkl[2]) + ")",
                     series.style}};
        }
        return {};
    }
    if (!source.x || row >= source.x->size()) {
        return {};
    }
    std::vector<HoverLine> lines{{"x: " + readout_number((*source.x)[row]), ""}};
    const auto line = [&lines, row](const char* name, const PatternSource::Column& column, std::string style) {
        if (column && row < column->size()) {
            lines.push_back({std::string(name) + ": " + readout_number((*column)[row]), std::move(style)});
        }
    };
    line("Imeas", source.meas, style_key("meas", source.experiment_place));
    line("Ibkg", source.bkg, "bkg");
    line("Icalc", source.calc, "calc");
    line("Imeas - Icalc", source.resid, "resid");
    return lines;
}

}  // namespace edi
