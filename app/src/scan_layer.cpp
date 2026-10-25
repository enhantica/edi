// SPDX-License-Identifier: BSD-3-Clause
#include "scan_layer.hpp"

#include <QColor>
#include <QImage>
#include <QPainter>
#include <QPainterPath>
#include <QPen>
#include <QQuickWindow>
#include <algorithm>
#include <cmath>
#include <limits>

#include "edi/palette.hpp"
#include "edi/presentation.hpp"
#include "edi/scan_views.hpp"

namespace edi_app {

namespace {

edi::YScale scale_of(const QString& scale) {
    return scale == QLatin1String("log")    ? edi::YScale::Log10
           : scale == QLatin1String("sqrt") ? edi::YScale::Sqrt
                                            : edi::YScale::Linear;
}

// Whether an excluded region reaches into the span between two x values.
bool excluded_between(const ScanViewModel::Pattern& pattern, double a, double b) {
    const double low = std::min(a, b), high = std::max(a, b);
    return std::any_of(pattern.excluded_shown.begin(), pattern.excluded_shown.end(),
                       [low, high](const std::pair<double, double>& range) {
                           return range.first <= high && range.second >= low;
                       });
}

// A pattern's points as the views draw them. With only the included range (the owner, 2026-10-22), a point inside an
// excluded region is taken out and a break goes between two neighbouring points with one between them, so no line or
// pixel joins across it; otherwise, every point.
struct DrawnPattern {
    std::vector<double> x, intensity;
};
DrawnPattern drawn_pattern(const ScanViewModel::Pattern& pattern, bool included_only) {
    constexpr double kNaN = std::numeric_limits<double>::quiet_NaN();
    const std::size_t points = std::min(pattern.shown.size(), pattern.intensity.size());
    DrawnPattern out;
    out.x.reserve(points);
    out.intensity.reserve(points);
    const bool gaps = included_only && !pattern.excluded_shown.empty();
    for (std::size_t i = 0; i < points; ++i) {
        const double x = pattern.shown[i];
        if (gaps && i > 0 && excluded_between(pattern, pattern.shown[i - 1], x)) {
            out.x.push_back(kNaN);
            out.intensity.push_back(kNaN);
        }
        out.x.push_back(x);
        out.intensity.push_back(gaps && ScanViewModel::excludedAt(pattern, x) ? kNaN : pattern.intensity[i]);
    }
    return out;
}

// With only the included range, whether a pixel column (or a reduced trace's point) centred at x, `width` wide, reaches
// into an excluded region: it is left empty, so a column joining two sides of a gap never shows across it.
bool column_excluded(const ScanViewModel::Pattern& pattern, bool included_only, double x, double width) {
    return included_only && excluded_between(pattern, x - width / 2.0, x + width / 2.0);
}

}  // namespace

ScanLayer::ScanLayer(QQuickItem* parent) : QQuickPaintedItem(parent), lines_(new ScanLines(this)) {
    setAntialiasing(true);
    lines_->setVisible(false);
    // Rendered on the render thread, while the GUI thread waits: the count is atomic and its signal goes to the GUI
    // thread.
    connect(
        lines_, &ScanLines::rendered, this,
        [this] {
            ++redraws_;
            QMetaObject::invokeMethod(this, &ScanLayer::redrawCountChanged, Qt::QueuedConnection);
        },
        Qt::DirectConnection);
}

void ScanLayer::setModel(ScanViewModel* model) {
    if (model == model_) {
        return;
    }
    if (model_) {
        disconnect(model_, nullptr, this, nullptr);
    }
    model_ = model;
    if (model_) {
        connect(model_, &ScanViewModel::revisionChanged, this, [this] {
            measure();
            recolour();
            redraw();
        });
    }
    measure();
    recolour();
    emit modelChanged();
    redraw();
}

void ScanLayer::setMode(const QString& mode) {
    assign(mode_, mode, &ScanLayer::modeChanged);
    lines_->setVisible(lines_on_gpu());
    update();  // the painted image clears when the lines move to the GPU
}
void ScanLayer::setXMin(double value) { assign(x_min_, value, &ScanLayer::xMinChanged); }
void ScanLayer::setXMax(double value) { assign(x_max_, value, &ScanLayer::xMaxChanged); }
void ScanLayer::setYMin(double value) { assign(y_min_, value, &ScanLayer::yMinChanged); }
void ScanLayer::setYMax(double value) { assign(y_max_, value, &ScanLayer::yMaxChanged); }
void ScanLayer::setColourScheme(const QString& scheme) {
    assign(colour_scheme_, scheme, &ScanLayer::colourSchemeChanged);
    recolour();
}
void ScanLayer::setColourMap(const QString& map) { assign(colour_map_, map, &ScanLayer::colourMapChanged); }
void ScanLayer::setBackground(const QColor& colour) {
    assign(background_, colour, &ScanLayer::backgroundChanged);
    recolour();
}
void ScanLayer::setSmoothRows(bool smooth) { assign(smooth_rows_, smooth, &ScanLayer::smoothRowsChanged); }
void ScanLayer::setReversed(bool reversed) { assign(reversed_, reversed, &ScanLayer::reversedChanged); }
void ScanLayer::setStackedReversed(bool reversed) {
    assign(stacked_reversed_, reversed, &ScanLayer::stackedReversedChanged);
    recolour();
}
void ScanLayer::setDark(bool dark) {
    assign(dark_, dark, &ScanLayer::darkChanged);
    recolour();
}
void ScanLayer::setIncludedOnly(bool on) { assign(included_only_, on, &ScanLayer::includedOnlyChanged); }

// The shown dataset is marked by the chart, not drawn here: nothing is drawn again.
void ScanLayer::setCurrent(int dataset) {
    if (dataset != current_) {
        current_ = dataset;
        emit currentChanged();
    }
}

void ScanLayer::setGpu(bool on) {
    assign(gpu_, on, &ScanLayer::gpuChanged);
    lines_->setVisible(lines_on_gpu());
    update();  // the painted image clears when the lines move to the GPU
}

void ScanLayer::setScale(const QString& scale) {
    if (scale != scale_) {
        scale_ = scale;
        measure();
        emit scaleChanged();
        redraw();
    }
}

void ScanLayer::geometryChange(const QRectF& next, const QRectF& previous) {
    QQuickPaintedItem::geometryChange(next, previous);
    lines_->setSize(next.size());
    redraw();
}

void ScanLayer::redraw() {
    polish();
    if (!lines_on_gpu()) {
        update();
    }
}

// Every read dataset's lowest and highest value on the y scale: the ends of the intensity the views spread.
void ScanLayer::measure() {
    double low = std::numeric_limits<double>::infinity(), high = -low;
    if (model_) {
        const edi::YScale scale = scale_of(scale_);
        for (const ScanViewModel::Pattern& pattern : model_->patterns()) {
            for (const double value : pattern.intensity) {
                const double shown = edi::to_display(value, scale);
                if (std::isfinite(shown)) {
                    low = std::min(low, shown);
                    high = std::max(high, shown);
                }
            }
        }
    }
    if (!(high > low)) {
        low = 0.0;
        high = 1.0;
    }
    if (low != display_min_) {
        display_min_ = low;
        emit displayMinChanged();
    }
    if (high != display_max_) {
        display_max_ = high;
        emit displayMaxChanged();
    }
}

ScanLayer::ReductionKey ScanLayer::reductionKey() const {
    return {x_min_, x_max_, std::max(1, static_cast<int>(std::ceil(width()))), included_only_,
            static_cast<int>(scale_of(scale_))};
}

// Each dataset's reduction for the range shown at the plot's pixel columns, made again only for a dataset whose points
// changed, or for every dataset when what they all depend on changed.
void ScanLayer::reduce() {
    if (!model_) {
        reductions_.clear();
        return;
    }
    const std::vector<ScanViewModel::Pattern>& patterns = model_->patterns();
    const ReductionKey key = reductionKey();
    if (!(key == reduced_for_) || reduced_mode_ != mode_) {
        reductions_.clear();
        reduced_for_ = key;
        reduced_mode_ = mode_;
    }
    reductions_.resize(patterns.size());
    const edi::YScale scale = scale_of(scale_);
    const auto columns = static_cast<std::size_t>(key.columns);
    const double column_width = (x_max_ - x_min_) / static_cast<double>(columns);
    constexpr float kNaN = std::numeric_limits<float>::quiet_NaN();
    int built = 0;
    for (std::size_t d = 0; d < patterns.size(); ++d) {
        const ScanViewModel::Pattern& pattern = patterns[d];
        Reduction& reduction = reductions_[d];
        if (reduction.generation == pattern.generation && reduction.generation != 0) {
            continue;
        }
        const bool had = !reduction.x.empty() || !reduction.v.empty();
        reduction = Reduction{pattern.generation, {}, {}};
        if (pattern.x.empty() || !(x_max_ > x_min_)) {
            reduction_changes_ += had ? 1 : 0;
            continue;
        }
        ++built;
        const DrawnPattern drawn = drawn_pattern(pattern, included_only_);
        if (mode_ == QLatin1String("map")) {
            const std::vector<float> values = edi::scan_pixel_values(drawn.x, drawn.intensity, x_min_, x_max_, columns);
            reduction.v.resize(values.size());
            for (std::size_t c = 0; c < values.size(); ++c) {
                const double centre = x_min_ + (static_cast<double>(c) + 0.5) * column_width;
                reduction.v[c] = column_excluded(pattern, included_only_, centre, column_width)
                                     ? kNaN
                                     : static_cast<float>(edi::to_display(values[c], scale));
            }
            continue;
        }
        // Each column a vertical stroke from its lowest to its highest value, joined column to column, so a narrow
        // peak stays at its height whatever the width; a column reaching into an excluded region is a break, as the
        // map's pixels are.
        const edi::ScanTrace trace = edi::scan_trace(drawn.x, drawn.intensity, x_min_, x_max_, columns);
        reduction.x.reserve(2 * trace.x.size());
        reduction.v.reserve(2 * trace.x.size());
        const auto add = [&reduction](double x, double v) {
            reduction.x.push_back(static_cast<float>(x));
            reduction.v.push_back(static_cast<float>(v));
        };
        for (std::size_t k = 0; k < trace.x.size(); ++k) {
            const double low = edi::to_display(trace.low[k], scale), high = edi::to_display(trace.high[k], scale);
            const double x = (trace.x[k] - x_min_) / (x_max_ - x_min_) * width();
            if (!std::isfinite(trace.x[k]) || column_excluded(pattern, included_only_, trace.x[k], column_width) ||
                !std::isfinite(low) || !std::isfinite(high)) {
                add(kNaN, kNaN);
                continue;
            }
            add(x, low);
            if (high != low) {
                add(x, high);
            }
        }
    }
    if (built > 0) {
        trace_builds_ += built;
        reduction_changes_ += built;
        emit traceBuildCountChanged();
    }
}

void ScanLayer::recolour() {
    const int count = model_ ? model_->count() : 0;
    const QString key = QStringLiteral("%1|%2|%3|%4|%5")
                            .arg(colour_scheme_, background_.name())
                            .arg(dark_)
                            .arg(stacked_reversed_)
                            .arg(count);
    if (key == coloured_for_) {
        return;
    }
    coloured_for_ = key;
    colours_.assign(static_cast<std::size_t>(count), QColor());
    // A scheme's colours (ADR-0038), or a colour map's, a dataset at its place along the scan between a tenth and nine
    // tenths of the map, whose ends can be as dark or as light as a background.
    const std::string choice = colour_scheme_.toStdString();
    const std::vector<std::string>& maps = edi::scan_colour_map_names();
    const bool map = std::find(maps.begin(), maps.end(), choice) != maps.end();
    const std::vector<edi::ScanMapColour> table =
        map ? edi::scan_colour_table(choice, background_.name().toStdString(), dark_) : std::vector<edi::ScanMapColour>{};
    const auto size = static_cast<std::size_t>(count);
    for (std::size_t dataset = 0; dataset < size; ++dataset) {
        // Reversed, the last dataset takes the first colour.
        const std::size_t place = stacked_reversed_ ? size - 1 - dataset : dataset;
        if (!map) {
            colours_[dataset] = QColor(QString::fromStdString(
                edi::pattern_colour(edi::colour_scheme_or_default(choice), place, size, dark_)));
            continue;
        }
        const double at = size > 1 ? static_cast<double>(place) / static_cast<double>(size - 1) : 1.0;
        const edi::ScanMapColour c = edi::scan_table_colour(table, 0.1 + 0.8 * at);
        colours_[dataset] = QColor(c.r, c.g, c.b);
    }
    ++colours_revision_;
    emit coloursRevisionChanged();
    redraw();
}

QColor ScanLayer::colourOf(int dataset) const {
    if (dataset < 0 || static_cast<std::size_t>(dataset) >= colours_.size()) {
        return {};
    }
    return colours_[static_cast<std::size_t>(dataset)];
}

QColor ScanLayer::mapColour(double t) const {
    const edi::ScanMapColour colour = edi::scan_table_colour(
        edi::scan_colour_table(colour_map_.toStdString(), background_.name().toStdString(), dark_), t);
    return QColor(colour.r, colour.g, colour.b, colour.a);
}

double ScanLayer::peakOf(int dataset) const {
    constexpr double kNaN = std::numeric_limits<double>::quiet_NaN();
    if (!model_ || dataset < 0 || static_cast<std::size_t>(dataset) >= model_->patterns().size() ||
        static_cast<std::size_t>(dataset) >= model_->rows().size()) {
        return kNaN;
    }
    const ScanViewModel::Pattern& pattern = model_->patterns()[static_cast<std::size_t>(dataset)];
    const edi::YScale scale = scale_of(scale_);
    // The line's highest point in the range shown: a point inside, or where the line joining two neighbouring points
    // crosses an edge of the range (the only part shown when no point is inside), as the line is drawn.
    // With only the included range, as drawn: nothing inside or across an excluded region.
    const DrawnPattern drawn = drawn_pattern(pattern, included_only_);
    const std::size_t points = drawn.x.size();
    const auto value_at = [&](std::size_t i) {
        return std::isfinite(drawn.x[i]) ? edi::to_display(drawn.intensity[i], scale) : kNaN;
    };
    const double lo = std::min(x_min_, x_max_), hi = std::max(x_min_, x_max_);
    double high = -std::numeric_limits<double>::infinity();
    for (std::size_t i = 0; i < points; ++i) {
        const double x = drawn.x[i], value = value_at(i);
        if (x >= lo && x <= hi && std::isfinite(value)) {
            high = std::max(high, value);
        }
        if (i + 1 == points) {
            continue;
        }
        const double xb = drawn.x[i + 1], next = value_at(i + 1);
        if (!std::isfinite(value) || !std::isfinite(next) || x == xb) {
            continue;
        }
        for (const double edge : {lo, hi}) {
            if (edge > std::min(x, xb) && edge < std::max(x, xb)) {
                high = std::max(high, value + (next - value) * (edge - x) / (xb - x));
            }
        }
    }
    const double span = display_max_ - display_min_;
    if (!std::isfinite(high) || !(span > 0.0)) {
        return kNaN;
    }
    return model_->rows()[static_cast<std::size_t>(dataset)] + (high - display_min_) / span * model_->stackHeight();
}

namespace {

// The order the stacked lines are drawn in: from the top row down, so a lower pattern is drawn over the ones it rises
// into. Rows not placed yet are left out.
std::vector<std::size_t> top_down(const std::vector<double>& rows, std::size_t count) {
    std::vector<std::size_t> order;
    for (std::size_t d = 0; d < count && d < rows.size(); ++d) {
        if (std::isfinite(rows[d])) {
            order.push_back(d);
        }
    }
    std::sort(order.begin(), order.end(), [&rows](std::size_t a, std::size_t b) { return rows[a] > rows[b]; });
    return order;
}

// As wide as the pattern chart's measured line, 2 px (the owner, 2026-10-22), narrowing toward 1 px where
// neighbouring rows are closer than six pixels, so the lines of a dense scan never merge.
double line_width(const std::vector<double>& rows, const std::vector<std::size_t>& order, double y_span, double height) {
    double step_px = std::numeric_limits<double>::infinity();
    for (std::size_t k = 1; k < order.size(); ++k) {
        const double gap = std::abs(rows[order[k - 1]] - rows[order[k]]) / y_span * height;
        if (gap > 0.0) {
            step_px = std::min(step_px, gap);
        }
    }
    return std::clamp(step_px / 3.0, 1.0, 2.0);
}

// The pattern chart's tint of an excluded region (edi::pattern_style_table's `excluded`).
QColor excluded_tint(bool dark) {
    QColor tint;
    for (const edi::SeriesStyle& style : edi::pattern_style_table()) {
        if (style.key == "excluded") {
            tint = QColor(QString::fromStdString(dark ? style.dark : style.light));
            tint.setAlphaF(static_cast<float>(style.opacity));
        }
    }
    return tint;
}

// The excluded ranges (edi ADR-0021 §4), each over its dataset's row, on whole pixels so that two rows' bands meet
// without a line between them; a scan's datasets share the template's ranges, so its bands run the plot's height.
std::vector<QRect> excluded_bands(const ScanViewModel& model, double x_min, double x_max, double y_min, double y_max,
                                  int columns, int pixel_rows) {
    const std::vector<ScanViewModel::Pattern>& patterns = model.patterns();
    const std::vector<edi::ScanRowSpan>& spans = model.spans();
    const std::size_t count = std::min({patterns.size(), model.rows().size(), spans.size()});
    const auto px = [&](double x) { return (x - x_min) / (x_max - x_min) * columns; };
    const auto py = [&](double y) { return (y_max - y) / (y_max - y_min) * pixel_rows; };
    std::vector<QRect> bands;
    const auto band = [&](double a, double b, int top, int bottom) {
        const int left = std::clamp(static_cast<int>(std::lround(px(std::min(a, b)))), 0, columns);
        const int right = std::clamp(static_cast<int>(std::lround(px(std::max(a, b)))), 0, columns);
        if (right > left && bottom > top) {
            bands.emplace_back(left, top, right - left, bottom - top);
        }
    };
    if (!model.joint()) {
        for (std::size_t d = 0; d < count; ++d) {
            if (!patterns[d].x.empty()) {
                for (const auto& [a, b] : patterns[d].excluded_shown) {
                    band(a, b, 0, pixel_rows);
                }
                break;
            }
        }
        return bands;
    }
    for (std::size_t d = 0; d < count; ++d) {
        const int top = std::clamp(static_cast<int>(std::lround(py(spans[d].high))), 0, pixel_rows);
        const int bottom = std::clamp(static_cast<int>(std::lround(py(spans[d].low))), 0, pixel_rows);
        for (const auto& [a, b] : patterns[d].excluded_shown) {
            band(a, b, top, bottom);
        }
    }
    return bands;
}

}  // namespace

void ScanLayer::updatePolish() {
    reduce();
    lines_->setObjectName(objectName() + QStringLiteral(".gpuLines"));
    lines_->setVisible(lines_on_gpu());
    if (lines_on_gpu() && model_) {
        feedLines();
    }
}

// The stacked lines to the GPU: the reductions again only when one changed or the drawing order did; every frame the
// rows, the height and the colours, which the shader takes as they are, and the excluded bands.
void ScanLayer::feedLines() {
    const std::vector<double>& rows = model_->rows();
    const std::vector<std::size_t> order = top_down(rows, std::min(reductions_.size(), model_->patterns().size()));
    if (reduction_changes_ != lines_fed_builds_ || order != lines_order_) {
        std::vector<ScanLines::Trace> traces;
        traces.reserve(order.size());
        for (const std::size_t d : order) {
            traces.push_back({reductions_[d].x, reductions_[d].v});
        }
        lines_->setTraces(std::move(traces));
        lines_fed_builds_ = reduction_changes_;
        lines_order_ = order;
    }
    // A value v reaches lift (v - displayMin) / span above its row: the shader's row and lift, folded.
    const double span = display_max_ - display_min_, lift = model_->stackHeight();
    std::vector<ScanLines::Style> styles;
    styles.reserve(order.size());
    for (const std::size_t d : order) {
        const double scaled = span > 0.0 ? lift / span : 0.0;
        styles.push_back({rows[d] - display_min_ * scaled, scaled, colourOf(static_cast<int>(d))});
    }
    lines_->setStyles(std::move(styles));
    lines_->setYMin(y_min_);
    lines_->setYMax(y_max_);
    lines_->setLineWidth(y_max_ > y_min_ ? line_width(rows, order, y_max_ - y_min_, height()) : 1.0);
    std::vector<QRectF> bands;
    if (x_max_ > x_min_ && y_max_ > y_min_) {
        const int columns = std::max(1, static_cast<int>(std::ceil(width())));
        const int pixel_rows = std::max(1, static_cast<int>(std::ceil(height())));
        for (const QRect& band : excluded_bands(*model_, x_min_, x_max_, y_min_, y_max_, columns, pixel_rows)) {
            bands.emplace_back(band);
        }
    }
    lines_->setBands(std::move(bands), excluded_tint(dark_));
}

QSGNode* ScanLayer::updatePaintNode(QSGNode* old, UpdatePaintNodeData* data) {
    QSGNode* node = QQuickPaintedItem::updatePaintNode(old, data);
    if (!lines_on_gpu()) {
        ++redraws_;
        QMetaObject::invokeMethod(this, &ScanLayer::redrawCountChanged, Qt::QueuedConnection);
    }
    return node;
}

void ScanLayer::paint(QPainter* painter) {
    if (!model_ || lines_on_gpu() || !(x_max_ > x_min_) || !(y_max_ > y_min_) || width() <= 0.0 || height() <= 0.0) {
        return;
    }
    const std::vector<double>& rows = model_->rows();
    const std::vector<edi::ScanRowSpan>& spans = model_->spans();
    const double span = display_max_ - display_min_;
    const auto py = [this](double y) { return (y_max_ - y) / (y_max_ - y_min_) * height(); };
    const std::size_t count = std::min({reductions_.size(), rows.size(), spans.size()});
    const int pixel_columns = std::max(1, static_cast<int>(std::ceil(width())));
    const int pixel_rows = std::max(1, static_cast<int>(std::ceil(height())));
    const auto excluded = [&](const QColor& colour) {
        for (const QRect& band : excluded_bands(*model_, x_min_, x_max_, y_min_, y_max_, pixel_columns, pixel_rows)) {
            painter->fillRect(band, colour);
        }
    };
    const QColor tint = excluded_tint(dark_);

    if (mode_ == QLatin1String("map")) {
        // Every placed row, a dataset not read (or not readable) included: its band stays empty, and no neighbour
        // blends into it.
        std::vector<std::size_t> order;
        for (std::size_t d = 0; d < count; ++d) {
            if (std::isfinite(rows[d])) {
                order.push_back(d);
            }
        }
        std::sort(order.begin(), order.end(), [&rows](std::size_t a, std::size_t b) { return rows[a] < rows[b]; });
        if (order.empty()) {
            return;
        }
        // The datasets in row order, each as its pixel columns' values on the y scale, empty when not read.
        const std::vector<float> none(static_cast<std::size_t>(pixel_columns), std::numeric_limits<float>::quiet_NaN());
        std::vector<const std::vector<float>*> values(order.size());
        for (std::size_t i = 0; i < order.size(); ++i) {
            const std::vector<float>& own = reductions_[order[i]].v;
            values[i] = own.size() == none.size() ? &own : &none;
        }
        std::vector<edi::ScanMapColour> table =
            edi::scan_colour_table(colour_map_.toStdString(), background_.name().toStdString(), dark_);
        if (reversed_) {
            std::reverse(table.begin(), table.end());
        }
        // One image pixel per plot pixel, so no row of the plot is drawn twice and nothing shows between datasets. Up,
        // each dataset is one band out to halfway to its neighbours, blended into the next only near their edge when
        // smooth (below); beyond the first or the last row, out to its extent, it is that dataset's. A column left
        // empty stays clear.
        QImage image(pixel_columns, pixel_rows, QImage::Format_ARGB32);
        image.fill(Qt::transparent);
        const double low_edge = spans[order.front()].low, high_edge = spans[order.back()].high;
        // The bands' lower edges in rising order: each pixel row finds the band it lies in, whatever the order the
        // pixel rows are visited in.
        std::vector<double> lows(order.size());
        for (std::size_t i = 0; i < order.size(); ++i) {
            lows[i] = spans[order[i]].low;
        }
        const auto band_height = [&](std::size_t i) { return spans[order[i]].high - spans[order[i]].low; };
        for (int j = 0; j < pixel_rows; ++j) {
            const double y = y_max_ - (static_cast<double>(j) + 0.5) / static_cast<double>(pixel_rows) * (y_max_ - y_min_);
            if (y < low_edge || y > high_edge) {
                continue;
            }
            const auto past = static_cast<std::size_t>(std::upper_bound(lows.begin(), lows.end(), y) - lows.begin());
            const std::size_t band = past == 0 ? 0 : past - 1;
            // The edge zone y lies in, if any: a quarter of each band's own height on its side of the edge (the owner,
            // 2026-10-22). A band's bottom quarter belongs to the edge below it and its top quarter to the edge above,
            // so the zone is chosen by the band y lies in, not by the rows around y: a wide band's zone reaches past a
            // narrow neighbour's row.
            std::size_t neighbour = band;
            if (band > 0 && y < spans[order[band]].low + band_height(band) / 4.0) {
                neighbour = band - 1;
            } else if (band + 1 < order.size() && y > spans[order[band]].high - band_height(band) / 4.0) {
                neighbour = band + 1;
            }
            const std::size_t lower = std::min(band, neighbour), upper = std::max(band, neighbour);
            const double below = band_height(lower) / 4.0, above = band_height(upper) / 4.0;
            const double edge_y = spans[order[lower]].high;
            const double edge = lower == upper || !(below + above > 0.0)
                                    ? 0.0
                                    : std::clamp((y - (edge_y - below)) / (below + above), 0.0, 1.0);
            const std::vector<float>& own = *values[band];
            const std::vector<float>& a = *values[lower];
            const std::vector<float>& b = *values[upper];
            QRgb* line = reinterpret_cast<QRgb*>(image.scanLine(j));
            for (int i = 0; i < pixel_columns; ++i) {
                const auto at = static_cast<std::size_t>(i);
                const double va = a[at], vb = b[at];
                // A band is its own dataset's, out to halfway to each neighbouring row, empty where that dataset has no
                // point. Stepped, its edges are hard; smooth, it blends into its neighbour's only in the edge zone, and
                // never into or out of an empty column, so no band shows a neighbour's data. One rule for scan values,
                // files and datablocks (the owner, 2026-10-22): blending from row to row had invented patterns between
                // a sparse scan's rows.
                const double value = !smooth_rows_ || lower == upper || !std::isfinite(va) || !std::isfinite(vb)
                                         ? own[at]
                                         : va + (vb - va) * edge;
                const edi::ScanMapColour colour = edi::scan_table_colour(table, (value - display_min_) / span);
                line[i] = qRgba(colour.r, colour.g, colour.b, colour.a);
            }
        }
        painter->drawImage(QRectF(0, 0, static_cast<double>(pixel_columns), static_cast<double>(pixel_rows)), image);
        // Over the colours, the excluded ranges wash them towards the plot's background, as a band greys a pattern;
        // with only the included range they hold no colours, and take the pattern chart's tint as empty gaps.
        QColor wash = background_;
        wash.setAlphaF(0.6F);
        excluded(included_only_ ? tint : wash);
        return;
    }

    // Stacked, painted: the excluded bands under the patterns, as on the pattern chart; then each dataset's reduced
    // trace, from the top row down.
    excluded(tint);
    const double lift = model_->stackHeight();
    const std::vector<std::size_t> order = top_down(rows, count);
    const qreal width_px = line_width(rows, order, y_max_ - y_min_, height());
    for (const std::size_t d : order) {
        const Reduction& reduction = reductions_[d];
        QPainterPath path;
        bool drawing = false;
        for (std::size_t k = 0; k < reduction.x.size(); ++k) {
            const double x = reduction.x[k];
            const double y = py(rows[d] + (reduction.v[k] - display_min_) / span * lift);
            if (!std::isfinite(x) || !std::isfinite(y)) {
                drawing = false;
            } else if (drawing) {
                path.lineTo(x, y);
            } else {
                path.moveTo(x, y);
                drawing = true;
            }
        }
        QPen pen(colourOf(static_cast<int>(d)));
        pen.setWidthF(width_px);
        pen.setCosmetic(true);
        // Ends stop at their points: a square cap reaches half the width past a break and fills a one-pixel gap.
        pen.setCapStyle(Qt::FlatCap);
        painter->setPen(pen);
        painter->setBrush(Qt::NoBrush);
        painter->drawPath(path);
    }
}

ScanColourBar::ScanColourBar(QQuickItem* parent) : QQuickPaintedItem(parent) {}

void ScanColourBar::setColourMap(const QString& map) {
    if (map != colour_map_) {
        colour_map_ = map;
        emit colourMapChanged();
        update();
    }
}

void ScanColourBar::setBackground(const QColor& colour) {
    if (colour != background_) {
        background_ = colour;
        emit backgroundChanged();
        update();
    }
}

void ScanColourBar::setDark(bool dark) {
    if (dark != dark_) {
        dark_ = dark;
        emit darkChanged();
        update();
    }
}

void ScanColourBar::setReversed(bool reversed) {
    if (reversed != reversed_) {
        reversed_ = reversed;
        emit reversedChanged();
        update();
    }
}

void ScanColourBar::paint(QPainter* painter) {
    const int rows = static_cast<int>(std::ceil(height()));
    if (rows <= 0 || width() <= 0.0) {
        return;
    }
    std::vector<edi::ScanMapColour> table =
        edi::scan_colour_table(colour_map_.toStdString(), background_.name().toStdString(), dark_);
    if (reversed_) {
        std::reverse(table.begin(), table.end());
    }
    QImage image(1, rows, QImage::Format_ARGB32);
    for (int j = 0; j < rows; ++j) {
        const double t = rows == 1 ? 1.0 : 1.0 - static_cast<double>(j) / static_cast<double>(rows - 1);
        const edi::ScanMapColour colour = edi::scan_table_colour(table, t);
        image.setPixel(0, j, qRgba(colour.r, colour.g, colour.b, colour.a));
    }
    painter->setRenderHint(QPainter::SmoothPixmapTransform, false);
    painter->drawImage(QRectF(0, 0, width(), static_cast<double>(rows)), image);
}

}  // namespace edi_app
