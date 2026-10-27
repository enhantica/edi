// SPDX-License-Identifier: BSD-3-Clause
#include "scan_layer.hpp"

#include <QColor>
#include <QImage>
#include <QPainter>
#include <QPainterPath>
#include <QPen>
#include <QQuickWindow>
#include <QSGRectangleNode>
#include <QThreadPool>
#include <QtConcurrent/QtConcurrentMap>
#include <algorithm>
#include <cmath>
#include <limits>
#include <numeric>

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
// A point's value as the views draw it: less the pattern's background there when subtracting and it has one.
double drawn_value(const ScanViewModel::Pattern& pattern, std::size_t i, bool subtract) {
    if (subtract && i < pattern.background.size() && std::isfinite(pattern.background[i])) {
        return pattern.intensity[i] - pattern.background[i];
    }
    return pattern.intensity[i];
}

DrawnPattern drawn_pattern(const ScanViewModel::Pattern& pattern, bool included_only, bool subtract) {
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
        out.intensity.push_back(gaps && ScanViewModel::excludedAt(pattern, x) ? kNaN
                                                                              : drawn_value(pattern, i, subtract));
    }
    return out;
}

// With only the included range, whether a pixel column (or a reduced trace's point) centred at x, `width` wide, reaches
// into an excluded region: it is left empty, so a column joining two sides of a gap never shows across it.
bool column_excluded(const ScanViewModel::Pattern& pattern, bool included_only, double x, double width) {
    return included_only && excluded_between(pattern, x - width / 2.0, x + width / 2.0);
}

}  // namespace

ScanLayer::ScanLayer(QQuickItem* parent)
    : QQuickPaintedItem(parent), lines_(new ScanLines(this)), top_(new ScanLines(lines_)) {
    legend_ = new ChartLegendModel(this);
    setAntialiasing(true);
    lines_->setVisible(false);
    top_->setVisible(false);
    // Rendered on the render thread, while the GUI thread waits: the count is atomic and its signal goes to the GUI
    // thread.
    connect(
        lines_, &ScanLines::rendered, this,
        [this] {
            ++redraws_;
            QMetaObject::invokeMethod(this, &ScanLayer::redrawCountChanged, Qt::QueuedConnection);
        },
        Qt::DirectConnection);
    // The labels shown follow the rows, the axis range, the plot's height and the current dataset.
    for (const auto changed : {&ScanLayer::placementChanged, &ScanLayer::yMinChanged, &ScanLayer::yMaxChanged,
                               &ScanLayer::currentChanged, &ScanLayer::modeChanged, &ScanLayer::modelChanged}) {
        connect(this, changed, this, &ScanLayer::labelsMoved);
    }
    connect(this, &QQuickItem::heightChanged, this, &ScanLayer::labelsMoved);
}

void ScanLayer::labelsMoved() {
    // Made again now, and announced only when the choice changed: a selection that leaves every label where it was
    // re-binds no label.
    shown_labels_stale_ = true;
    const QList<bool> before = shown_labels_;
    if (shownLabels() != before) {
        emit shownLabelsChanged();
    }
}

void ScanLayer::setLabelled(bool labelled) {
    if (labelled != labelled_) {
        labelled_ = labelled;
        emit labelledChanged();
        labelsMoved();
    }
}

void ScanLayer::setDisabledColour(const QColor& colour) {
    assign(disabled_colour_, colour, &ScanLayer::disabledColourChanged);
    syncLegend();
}

// Highlighting, the other Stacked lines recede (the owner, 2026-10-27): the disabled colour halfway to the plot's
// background, opaque so a line crossing itself stays even, and half as wide as the shown line, at least 0.75 px.
QColor ScanLayer::recededColour() const { return blendedColour(disabled_colour_, 0.5); }

double ScanLayer::recededWidth(double width) { return std::max(0.75, width / 2.0); }

bool ScanLayer::hiddenAt(std::size_t dataset) const {
    return std::find(hidden_.begin(), hidden_.end(), static_cast<int>(dataset)) != hidden_.end();
}

void ScanLayer::toggleHidden(int dataset) {
    if (dataset < 0) {
        return;
    }
    const auto found = std::find(hidden_.begin(), hidden_.end(), dataset);
    if (found != hidden_.end()) {
        hidden_.erase(found);
    } else {
        hidden_.push_back(dataset);
    }
    syncLegend();
    redraw();
}

void ScanLayer::syncLegend() {
    const int count = model_ ? model_->count() : 0;
    std::vector<int> listed;
    if (count <= kFullLegend) {
        listed.resize(static_cast<std::size_t>(count));
        std::iota(listed.begin(), listed.end(), 0);
    } else {
        listed = {0};
        if (current_ > 0 && current_ < count - 1) {
            listed.push_back(current_);
        }
        listed.push_back(count - 1);
    }
    QList<ChartLegendModel::Entry> entries;
    for (const int dataset : listed) {
        // Highlighting, the shown pattern keeps its colour and every other is disabled-coloured; not highlighting, all
        // keep their colours and the shown one is named in bold (the owner, 2026-10-27).
        ChartLegendModel::Entry entry;
        entry.label = model_->rowText(dataset);
        entry.color = highlight_ && dataset != current_ ? disabled_colour_ : colourOf(dataset);
        entry.mark = QStringLiteral("line");
        entry.markWidth = 2.0;
        entry.selected = !highlight_ && dataset == current_;
        entry.key = QString::number(dataset);
        entry.hidden = hiddenAt(static_cast<std::size_t>(dataset));
        entries.append(entry);
    }
    if (static_cast<int>(listed.size()) < count) {
        ChartLegendModel::Entry more;
        more.label = tr("+ %1 more").arg(count - static_cast<int>(listed.size()));
        more.color = dark_ ? QColor(0x99, 0x99, 0x99) : QColor(0x8A, 0x93, 0xA0);
        entries.append(more);
    }
    legend_->setEntries(entries);
}

void ScanLayer::setLabelGap(double gap) {
    if (gap != label_gap_) {
        label_gap_ = gap;
        emit labelGapChanged();
        labelsMoved();
    }
}

QList<bool> ScanLayer::shownLabels() const {
    if (!shown_labels_stale_) {
        return shown_labels_;
    }
    shown_labels_stale_ = false;
    shown_labels_.clear();
    const int count = model_ ? model_->count() : 0;
    if (!labelled_ || count == 0 || !(pattern_height_ > 0.0) || !(y_max_ > y_min_) || height() <= 0.0) {
        return shown_labels_;
    }
    // Each row inside the axis range at its pixel row from the top, top first.
    struct Placed {
        int index;
        double px;
    };
    std::vector<Placed> placed;
    std::vector<bool> shown(static_cast<std::size_t>(count), false);
    for (int i = 0; i < count; ++i) {
        const double at = rowOf(i);
        if (std::isfinite(at) && at >= y_min_ && at <= y_max_) {
            placed.push_back({i, (y_max_ - at) / (y_max_ - y_min_) * height()});
        }
    }
    std::stable_sort(placed.begin(), placed.end(), [](const Placed& a, const Placed& b) { return a.px < b.px; });
    // The smallest stride through the rows, in order, that keeps neighbouring labels a label's height apart.
    const auto apart = [&placed, this](std::size_t k) {
        for (std::size_t n = k; n < placed.size(); n += k) {
            if (placed[n].px - placed[n - k].px < label_gap_) {
                return false;
            }
        }
        return true;
    };
    std::size_t stride = 1;
    while (stride < placed.size() && !apart(stride)) {
        ++stride;
    }
    const auto current = std::find_if(placed.begin(), placed.end(), [this](const Placed& row) { return row.index == current_; });
    for (std::size_t n = 0; n < placed.size(); n += stride) {
        if (current == placed.end() || std::abs(placed[n].px - current->px) >= label_gap_ || placed[n].index == current_) {
            shown[static_cast<std::size_t>(placed[n].index)] = true;
        }
    }
    if (current != placed.end()) {
        shown[static_cast<std::size_t>(current_)] = true;
    }
    shown_labels_.reserve(count);
    for (const bool row : shown) {
        shown_labels_.append(row);
    }
    return shown_labels_;
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
        connect(model_, &ScanViewModel::rowTextsChanged, this, &ScanLayer::syncLegend);
        connect(model_, &ScanViewModel::revisionChanged, this, [this] {
            measure();
            place();
            recolour();
            redraw();
        });
    }
    measure();
    place();
    recolour();
    emit modelChanged();
    redraw();
}

void ScanLayer::setMode(const QString& mode) {
    assign(mode_, mode, &ScanLayer::modeChanged);
    showLines();
    if (!deferred()) {
        update();  // the painted image clears when the lines move to the GPU
    }
}
bool ScanLayer::fitsShownRange() const { return mode_ == QLatin1String("stacked") && spacing_ >= 1.0; }

void ScanLayer::setXMin(double value) {
    if (value != x_min_) {
        x_min_ = value;
        if (fitsShownRange()) {
            measure();
        }
        emit xMinChanged();
        redraw();
    }
}

void ScanLayer::setXMax(double value) {
    if (value != x_max_) {
        x_max_ = value;
        if (fitsShownRange()) {
            measure();
        }
        emit xMaxChanged();
        redraw();
    }
}
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
void ScanLayer::setIncludedOnly(bool on) {
    if (on != included_only_) {
        included_only_ = on;
        measure();  // the intensity range leaves the excluded points out, or takes them back
        emit includedOnlyChanged();
        redraw();
    }
}

void ScanLayer::setPositions(const QList<int>& positions) {
    assign(positions_, positions, &ScanLayer::positionsChanged);
    recolour();
}

void ScanLayer::setTakenPositions(const QList<int>& positions) {
    assign(taken_positions_, positions, &ScanLayer::takenPositionsChanged);
    recolour();
}

void ScanLayer::setSubtractBackground(bool on) {
    if (on != subtract_background_) {
        subtract_background_ = on;
        measure();  // every pattern's own range and the intensity's ends move with it
        emit subtractBackgroundChanged();
        redraw();
    }
}

// The shown dataset is drawn again only while it is highlighted.
void ScanLayer::setCurrent(int dataset) {
    if (dataset != current_) {
        current_ = dataset;
        emit currentChanged();
        syncLegend();
        if (highlight_) {
            redraw();
        }
    }
}

void ScanLayer::setHighlight(bool on) {
    assign(highlight_, on, &ScanLayer::highlightChanged);
    syncLegend();
}
void ScanLayer::setFaded(double opacity) { assign(faded_, std::clamp(opacity, 0.0, 1.0), &ScanLayer::fadedChanged); }

void ScanLayer::setBusy(bool busy) {
    if (busy != busy_) {
        busy_ = busy;
        emit busyChanged();
    }
}

void ScanLayer::setActive(bool active) {
    if (active != active_) {
        active_ = active;
        emit activeChanged();
        lines_->setActive(active_);
        top_->setActive(active_);
        if (active_ && stale_) {
            update();  // the painted image too: a renderer chosen while hidden may need it cleared
            redraw();
        }
    }
}

int ScanLayer::highlighted() const {
    return highlight_ && current_ >= 0 && static_cast<std::size_t>(current_) < reductions_.size() &&
                   !hiddenAt(static_cast<std::size_t>(current_))
               ? current_
               : -1;
}

void ScanLayer::setGpu(bool on) {
    assign(gpu_, on, &ScanLayer::gpuChanged);
    showLines();
    if (!deferred()) {
        update();  // the painted image clears when the lines move to the GPU
    }
}

void ScanLayer::setSpacing(double spacing) {
    assign(spacing_, std::clamp(spacing, 0.0, 1.0), &ScanLayer::spacingChanged);
    measure();  // Separate spans each pattern over the range shown
    place();
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
    top_->setSize(next.size());  // a child of the lines, over them at the same place
    redraw();
}

bool ScanLayer::deferred() {
    if (!active_) {
        stale_ = true;
    }
    return !active_;
}

void ScanLayer::showLines() {
    lines_->setVisible(lines_on_gpu());
    top_->setVisible(lines_on_gpu() && highlighted() >= 0);
}

void ScanLayer::redraw() {
    if (deferred()) {
        return;
    }
    stale_ = false;
    polish();
    if (!lines_on_gpu()) {
        update();
    }
}

// Every read dataset's lowest and highest value on the y scale: the ends of the intensity the views spread, over its
// included points only while only the included range is shown (the owner, 2026-10-27). At Separate each stacked
// pattern spans its lowest to highest value in the x range shown, so its band stays filled as the zoom leaves its
// large peaks out (the owner, 2026-10-26); one with no point in the range spans all its points.
void ScanLayer::measure() {
    constexpr double kInfinity = std::numeric_limits<double>::infinity();
    double low = kInfinity, high = -low;
    lows_.clear();
    highs_.clear();
    if (model_) {
        const edi::YScale scale = scale_of(scale_);
        const bool visible_only = fitsShownRange();
        const double from = std::min(x_min_, x_max_), to = std::max(x_min_, x_max_);
        for (const ScanViewModel::Pattern& pattern : model_->patterns()) {
            double own_low = kInfinity, own_high = -kInfinity, seen_low = kInfinity, seen_high = -kInfinity;
            for (std::size_t i = 0; i < pattern.intensity.size(); ++i) {
                const double shown = edi::to_display(drawn_value(pattern, i, subtract_background_), scale);
                const double x = i < pattern.shown.size() ? pattern.shown[i] : std::nan("");
                if (!std::isfinite(shown) || (included_only_ && ScanViewModel::excludedAt(pattern, x))) {
                    continue;
                }
                own_low = std::min(own_low, shown);
                own_high = std::max(own_high, shown);
                if (visible_only && x >= from && x <= to) {
                    seen_low = std::min(seen_low, shown);
                    seen_high = std::max(seen_high, shown);
                }
            }
            const bool seen = seen_high >= seen_low;
            lows_.push_back(seen ? seen_low : own_low);
            highs_.push_back(seen ? seen_high : own_high);
            low = std::min(low, own_low);
            high = std::max(high, own_high);
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

// The stacked baselines (edi ADR-0041 §4): the datasets in the order of their rows, each the spacing's height tall and
// the i-th at i steps (edi::stacked_placement on the plot's height, 1), so the stack fills the plot exactly.
void ScanLayer::place() {
    const std::vector<double> rows = model_ ? model_->rows() : std::vector<double>{};
    std::vector<std::size_t> order;
    for (std::size_t d = 0; d < rows.size(); ++d) {
        if (std::isfinite(rows[d])) {
            order.push_back(d);
        }
    }
    std::stable_sort(order.begin(), order.end(), [&rows](std::size_t a, std::size_t b) { return rows[a] < rows[b]; });
    const double count = static_cast<double>(order.size());
    const edi::StackedPlacement placement = edi::stacked_placement(order.size(), 1.0, spacing_);
    pattern_height_ = placement.height;
    baselines_.assign(rows.size(), std::numeric_limits<double>::quiet_NaN());
    for (std::size_t i = 0; i < order.size(); ++i) {
        baselines_[order[i]] = static_cast<double>(i) * placement.step;
    }
    const double top = std::max(0.0, count - 1.0) * placement.step + pattern_height_;
    if (top != stack_top_) {
        stack_top_ = top;
        emit stackTopChanged();
    }
    emit placementChanged();
    redraw();
}

std::vector<edi::ScanRowSpan> ScanLayer::stackedSpans() const {
    // Each stacked pattern from its baseline to its top (place), the extent its excluded ranges are tinted over.
    std::vector<edi::ScanRowSpan> spans(baselines_.size());
    for (std::size_t d = 0; d < baselines_.size(); ++d) {
        spans[d].low = baselines_[d];
        spans[d].high = baselines_[d] + pattern_height_;
    }
    return spans;
}

double ScanLayer::rowOf(int dataset) const {
    if (mode_ == QLatin1String("map")) {
        return model_ ? model_->rowOf(dataset) : std::numeric_limits<double>::quiet_NaN();
    }
    return dataset >= 0 && static_cast<std::size_t>(dataset) < baselines_.size()
               ? baselines_[static_cast<std::size_t>(dataset)]
               : std::numeric_limits<double>::quiet_NaN();
}

int ScanLayer::datasetNear(double x, double y) const {
    if (!model_) {
        return -1;
    }
    if (mode_ == QLatin1String("map")) {
        return model_->datasetAt(y);
    }
    // The stacked line passing nearest to (x, y): what each dataset's line covers within a pixel either side of x, its
    // points there and its segments crossing there, read where they cross.
    const double column = (x - x_min_) / (x_max_ - x_min_) * width();
    const double from = column - 1.0, to = column + 1.0;
    int nearest = -1;
    double best = std::numeric_limits<double>::infinity();
    for (std::size_t d = 0; d < reductions_.size() && d < baselines_.size(); ++d) {
        if (hiddenAt(d)) {
            continue;
        }
        const Reduction& reduction = reductions_[d];
        double low = std::numeric_limits<double>::infinity(), high = -low;
        const auto take = [&low, &high](double v) {
            low = std::min(low, v);
            high = std::max(high, v);
        };
        for (std::size_t k = 0; k < reduction.x.size(); ++k) {
            const double xa = reduction.x[k], va = reduction.v[k];
            if (!std::isfinite(xa) || !std::isfinite(va)) {
                continue;
            }
            if (xa >= from && xa <= to) {
                take(va);
            }
            if (k + 1 == reduction.x.size()) {
                continue;
            }
            const double xb = reduction.x[k + 1], vb = reduction.v[k + 1];
            if (!std::isfinite(xb) || !std::isfinite(vb) || xb == xa) {
                continue;
            }
            for (const double at : {from, to}) {
                if (at > std::min(xa, xb) && at < std::max(xa, xb)) {
                    take(va + (vb - va) * (at - xa) / (xb - xa));
                }
            }
        }
        if (!std::isfinite(low)) {
            continue;
        }
        const double y_low = stackedY(d, low), y_high = stackedY(d, high);
        const double distance = y < y_low ? y_low - y : y > y_high ? y - y_high : 0.0;
        if (std::isfinite(distance) && distance < best) {
            best = distance;
            nearest = static_cast<int>(d);
        }
    }
    return nearest;
}

double ScanLayer::stackedY(std::size_t dataset, double value) const {
    if (dataset >= baselines_.size() || dataset >= lows_.size()) {
        return std::numeric_limits<double>::quiet_NaN();
    }
    const double span = highs_[dataset] - lows_[dataset];
    return baselines_[dataset] + (span > 0.0 ? (value - lows_[dataset]) / span : 0.0) * pattern_height_;
}

ScanLayer::ReductionKey ScanLayer::reductionKey() const {
    // The Stacked lines at the screen's device pixels, so a high-DPI screen gets its full resolution; the Map's pixel
    // columns are the item's own.
    const double ratio = mode_ == QLatin1String("map") || window() == nullptr ? 1.0 : window()->effectiveDevicePixelRatio();
    return {x_min_, x_max_, std::max(1, static_cast<int>(std::ceil(width() * ratio))), included_only_,
            subtract_background_, static_cast<int>(scale_of(scale_))};
}

// Each dataset's reduction for the range shown at the plot's pixel columns (device pixels for the Stacked lines), made
// again only for a dataset whose points changed, or for every dataset when what they all depend on changed.
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
        const DrawnPattern drawn = drawn_pattern(pattern, included_only_, subtract_background_);
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
        // The line through the points as it looks at the device pixels, so a narrow peak stays at its height whatever
        // the width and the line is as smooth as the pattern chart's (edi::scan_polyline); a point in an excluded
        // region is a break, as the map's pixels are.
        const edi::ScanTrace trace = edi::scan_polyline(drawn.x, drawn.intensity, x_min_, x_max_, columns);
        reduction.x.reserve(trace.x.size());
        reduction.v.reserve(trace.x.size());
        const auto add = [&reduction](double x, double v) {
            reduction.x.push_back(static_cast<float>(x));
            reduction.v.push_back(static_cast<float>(v));
        };
        for (std::size_t k = 0; k < trace.x.size(); ++k) {
            const double v = edi::to_display(trace.low[k], scale);
            const double x = (trace.x[k] - x_min_) / (x_max_ - x_min_) * width();
            if (!std::isfinite(trace.x[k]) || column_excluded(pattern, included_only_, trace.x[k], column_width) ||
                !std::isfinite(v)) {
                add(kNaN, kNaN);
                continue;
            }
            add(x, v);
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
    const auto joined = [](const QList<int>& values) {
        QStringList texts;
        for (const int value : values) {
            texts.append(QString::number(value));
        }
        return texts.join(QLatin1Char(','));
    };
    const QString key = QStringLiteral("%1|%2|%3|%4|%5|%6|%7")
                            .arg(colour_scheme_, background_.name())
                            .arg(dark_)
                            .arg(stacked_reversed_)
                            .arg(count)
                            .arg(joined(positions_), joined(taken_positions_));
    if (key == coloured_for_) {
        return;
    }
    coloured_for_ = key;
    colours_.assign(static_cast<std::size_t>(count), QColor());
    // A palette's colours, each dataset at its position (ADR-0038), or a colour map's, a dataset at its place along
    // the scan between a tenth and nine tenths of the map, whose ends can be as dark or as light as a background.
    const std::string choice = colour_scheme_.toStdString();
    const std::vector<std::string>& maps = edi::scan_colour_map_names();
    const bool map = std::find(maps.begin(), maps.end(), choice) != maps.end();
    const std::vector<edi::ScanMapColour> table =
        map ? edi::scan_colour_table(choice, background_.name().toStdString(), dark_) : std::vector<edi::ScanMapColour>{};
    const auto size = static_cast<std::size_t>(count);
    const edi::ColourScheme scheme = edi::colour_scheme_or_default(choice);
    std::vector<std::size_t> taken;
    for (const int position : taken_positions_) {
        taken.push_back(static_cast<std::size_t>(std::max(position, 0)));
    }
    // A joint fit's experiments keep their own positions while the palette has a colour for each; a scan's datasets,
    // and any set larger than the palette, take the pattern set's colours (edi::pattern_set_colour).
    const bool own = positions_.size() == count && size <= edi::kPaletteColourCount;
    std::size_t used = 0;
    for (const int position : positions_) {
        used = std::max(used, static_cast<std::size_t>(std::max(position, 0)) + 1);
    }
    for (std::size_t dataset = 0; dataset < size; ++dataset) {
        // Reversed, the last dataset takes the first colour.
        const std::size_t place = stacked_reversed_ ? size - 1 - dataset : dataset;
        if (!map) {
            colours_[dataset] = QColor(QString::fromStdString(
                own ? edi::figure_colour(scheme, static_cast<std::size_t>(std::max(positions_[static_cast<qsizetype>(place)], 0)),
                                         used, dark_)
                    : edi::pattern_set_colour(scheme, place, size, taken, dark_)));
            continue;
        }
        const double at = size > 1 ? static_cast<double>(place) / static_cast<double>(size - 1) : 1.0;
        const edi::ScanMapColour c = edi::scan_table_colour(table, 0.1 + 0.8 * at);
        colours_[dataset] = QColor(c.r, c.g, c.b);
    }
    ++colours_revision_;
    emit coloursRevisionChanged();
    syncLegend();
    redraw();
}

QColor ScanLayer::lineColour(int dataset, int top) const {
    // Every line at 75 % (the owner, 2026-10-27); highlighting, the shown one in full and the others receded.
    constexpr double kLineOpacity = 0.75;
    if (top >= 0) {
        return dataset == top ? colourOf(dataset) : recededColour();
    }
    return blendedColour(colourOf(dataset), kLineOpacity);
}

QColor ScanLayer::blendedColour(const QColor& colour, double keep) const {
    // Blended toward the background rather than made translucent: a line crossing itself, up and down a narrow peak,
    // stays one even colour, as the pattern chart's opaque lines do.
    const auto mix = [keep](double ink, double paper) { return keep * ink + (1.0 - keep) * paper; };
    return QColor::fromRgbF(static_cast<float>(mix(colour.redF(), background_.redF())),
                            static_cast<float>(mix(colour.greenF(), background_.greenF())),
                            static_cast<float>(mix(colour.blueF(), background_.blueF())), 1.0F);
}

QColor ScanLayer::colourOf(int dataset) const {
    if (dataset < 0 || static_cast<std::size_t>(dataset) >= colours_.size()) {
        return {};
    }
    return colours_[static_cast<std::size_t>(dataset)];
}

double ScanLayer::valueAt(int dataset, double x) const {
    constexpr double kNaN = std::numeric_limits<double>::quiet_NaN();
    if (!model_ || dataset < 0 || static_cast<std::size_t>(dataset) >= model_->patterns().size() || !std::isfinite(x)) {
        return kNaN;
    }
    const ScanViewModel::Pattern& pattern = model_->patterns()[static_cast<std::size_t>(dataset)];
    const std::size_t points = std::min(pattern.shown.size(), pattern.intensity.size());
    for (std::size_t i = 0; i + 1 < points; ++i) {
        const double xa = pattern.shown[i], xb = pattern.shown[i + 1];
        if (!std::isfinite(xa) || !std::isfinite(xb) || x < std::min(xa, xb) || x > std::max(xa, xb)) {
            continue;
        }
        const double va = drawn_value(pattern, i, subtract_background_), vb = drawn_value(pattern, i + 1, subtract_background_);
        return xb == xa ? va : va + (vb - va) * (x - xa) / (xb - xa);
    }
    return kNaN;
}

double ScanLayer::curveAt(int dataset, double x) const {
    if (mode_ == QLatin1String("map") || dataset < 0) {
        return rowOf(dataset);
    }
    return stackedY(static_cast<std::size_t>(dataset), edi::to_display(valueAt(dataset, x), scale_of(scale_)));
}

QString ScanLayer::intensityText(double value) const {
    return std::isfinite(value) ? QString::fromStdString(edi::measured_readout(value)) : QString();
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
    const DrawnPattern drawn = drawn_pattern(pattern, included_only_, subtract_background_);
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
    if (!std::isfinite(high)) {
        return kNaN;
    }
    return stackedY(static_cast<std::size_t>(dataset), high);
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

// 1.5 px (the owner, 2026-10-27), narrowing toward 1 px where neighbouring rows are closer than 4.5 pixels, so the
// lines of a dense scan never merge.
double line_width(const std::vector<double>& rows, const std::vector<std::size_t>& order, double y_span, double height) {
    double step_px = std::numeric_limits<double>::infinity();
    for (std::size_t k = 1; k < order.size(); ++k) {
        const double gap = std::abs(rows[order[k - 1]] - rows[order[k]]) / y_span * height;
        if (gap > 0.0) {
            step_px = std::min(step_px, gap);
        }
    }
    return std::clamp(step_px / 3.0, 1.0, 1.5);
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

// The excluded ranges (edi ADR-0021 §4), each over its dataset's row, `spans` (the Map's rows, or each stacked pattern's
// baseline to its top), on whole pixels so that two rows' bands meet without a line between them; a scan's datasets
// share the template's ranges, so its bands run the plot's height.
std::vector<QRect> excluded_bands(const ScanViewModel& model, const std::vector<edi::ScanRowSpan>& spans, double x_min,
                                  double x_max, double y_min, double y_max, int columns, int pixel_rows) {
    const std::vector<ScanViewModel::Pattern>& patterns = model.patterns();
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
        if (!std::isfinite(spans[d].low) || !std::isfinite(spans[d].high)) {
            continue;  // a dataset with no place
        }
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
    lines_->setObjectName(objectName() + QStringLiteral(".gpuLines"));
    // A polish asked for while the view was shown can come after it is hidden.
    if (deferred()) {
        return;
    }
    reduce();
    showLines();
    if (lines_on_gpu() && model_) {
        feedLines();
    }
}

// The stacked lines to the GPU: the reductions again only when one changed or the drawing order did; every frame the
// rows, the height and the colours, which the shader takes as they are, and the excluded bands.
void ScanLayer::feedLines() {
    std::vector<std::size_t> order = top_down(baselines_, std::min(reductions_.size(), model_->patterns().size()));
    std::erase_if(order, [this](std::size_t d) { return hiddenAt(d); });
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
    // A value v reaches H (v - low) / (high - low) above its baseline: the shader's row and lift, folded.
    // Highlighted, the shown dataset is drawn by the line over the others, which are faded.
    const int top = highlighted();
    const auto style_of = [this, top](std::size_t d) {
        const double span = highs_[d] - lows_[d];
        const double scaled = span > 0.0 ? pattern_height_ / span : 0.0;
        QColor colour = lineColour(static_cast<int>(d), top);
        if (top >= 0 && static_cast<int>(d) == top) {
            colour.setAlphaF(0.0F);  // drawn by the line over the others
        }
        return ScanLines::Style{baselines_[d] - (span > 0.0 ? lows_[d] : 0.0) * scaled, scaled, colour};
    };
    std::vector<ScanLines::Style> styles;
    styles.reserve(order.size());
    for (const std::size_t d : order) {
        styles.push_back(style_of(d));
    }
    lines_->setStyles(std::move(styles));
    const double line_px = y_max_ > y_min_ ? line_width(baselines_, order, y_max_ - y_min_, height()) : 1.0;
    for (ScanLines* item : {lines_, top_}) {
        item->setYMin(y_min_);
        item->setYMax(y_max_);
        // Highlighting, the other lines are thinner than the shown one's (the owner, 2026-10-27).
        item->setLineWidth(item == lines_ && top >= 0 ? recededWidth(line_px) : line_px);
    }
    top_->setVisible(top >= 0);
    if (top >= 0) {
        if (top != top_dataset_ || top_fed_builds_ != reduction_changes_) {
            const Reduction& reduction = reductions_[static_cast<std::size_t>(top)];
            top_->setTraces({{reduction.x, reduction.v}});
            top_dataset_ = top;
            top_fed_builds_ = reduction_changes_;
        }
        ScanLines::Style style = style_of(static_cast<std::size_t>(top));
        style.colour.setAlphaF(1.0F);
        top_->setStyles({style});
    }
    std::vector<QRectF> bands;
    if (x_max_ > x_min_ && y_max_ > y_min_) {
        const int columns = std::max(1, static_cast<int>(std::ceil(width())));
        const int pixel_rows = std::max(1, static_cast<int>(std::ceil(height())));
        for (const QRect& band : excluded_bands(*model_, stackedSpans(), x_min_, x_max_, y_min_, y_max_, columns, pixel_rows)) {
            bands.emplace_back(band);
        }
    }
    lines_->setBands(std::move(bands), excluded_tint(dark_));
}

QSGNode* ScanLayer::updatePaintNode(QSGNode* old, UpdatePaintNodeData* data) {
    // Not painted while not shown, whatever asked for it (a resize, an update already queued); the GUI thread waits
    // while the scene is synchronised, so the flags are read and written safely here.
    if (deferred()) {
        return old;
    }
    QSGNode* node = QQuickPaintedItem::updatePaintNode(old, data);
    if (!lines_on_gpu()) {
        ++redraws_;
        QMetaObject::invokeMethod(this, &ScanLayer::redrawCountChanged, Qt::QueuedConnection);
    }
    return node;
}

void ScanLayer::paint(QPainter* painter) {
    if (deferred()) {
        return;
    }
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
        for (const QRect& band : excluded_bands(*model_, mode_ == QLatin1String("map") ? spans : stackedSpans(), x_min_, x_max_, y_min_, y_max_,
                                                 pixel_columns, pixel_rows)) {
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
            // Highlighted, every row's band but the shown dataset's is blended toward the background.
            const bool faded = highlighted() >= 0 && order[band] != static_cast<std::size_t>(highlighted());
            const double keep = faded ? faded_ : 1.0;
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
                const auto mix = [keep](int c, int b) { return static_cast<int>(std::lround(b + (c - b) * keep)); };
                line[i] = keep < 1.0 && colour.a > 0 ? qRgba(mix(colour.r, background_.red()), mix(colour.g, background_.green()),
                                                             mix(colour.b, background_.blue()), colour.a)
                                                       : qRgba(colour.r, colour.g, colour.b, colour.a);
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
    std::vector<std::size_t> order = top_down(baselines_, std::min(count, baselines_.size()));
    std::erase_if(order, [this](std::size_t d) { return hiddenAt(d); });
    const qreal width_px = line_width(baselines_, order, y_max_ - y_min_, height());
    // Highlighted, the shown dataset is drawn last, over the others, which are faded.
    const int top = highlighted();
    std::vector<std::size_t> drawn = order;
    if (top >= 0) {
        std::erase(drawn, static_cast<std::size_t>(top));
        if (std::isfinite(baselines_[static_cast<std::size_t>(top)])) {
            drawn.push_back(static_cast<std::size_t>(top));
        }
    }
    // Each dataset's line, its colour and its extent down the plot, in item pixels.
    struct Line {
        QPainterPath path;
        QColor colour;
        double width = 0.0;
        double top = 0.0, bottom = 0.0;
    };
    std::vector<Line> lines;
    lines.reserve(drawn.size());
    for (const std::size_t d : drawn) {
        const Reduction& reduction = reductions_[d];
        Line line;
        bool drawing = false;
        for (std::size_t k = 0; k < reduction.x.size(); ++k) {
            const double x = reduction.x[k];
            const double y = py(stackedY(d, reduction.v[k]));
            if (!std::isfinite(x) || !std::isfinite(y)) {
                drawing = false;
            } else if (drawing) {
                line.path.lineTo(x, y);
            } else {
                line.path.moveTo(x, y);
                drawing = true;
            }
        }
        if (line.path.isEmpty()) {
            continue;
        }
        const QRectF bounds = line.path.boundingRect();
        line.top = bounds.top() - width_px;
        line.bottom = bounds.bottom() + width_px;
        line.colour = lineColour(static_cast<int>(d), top);
        line.width = top >= 0 && static_cast<int>(d) != top ? recededWidth(width_px) : width_px;
        lines.push_back(std::move(line));
    }
    // Stroked in horizontal tiles, one per thread: every core, one while a fit runs; EDI_SCAN_PAINT_THREADS sets the
    // count to compare the drawings (never set in use). Each thread strokes, in order, the lines that cross its tile into
    // an image of the whole plot clipped to the tile; Qt's strokers place a line by the image, not by the clip, so each
    // pixel is drawn exactly as one image of the whole plot would draw it, whatever the number of tiles. The width in
    // item pixels, as the pattern chart's lines, whatever the device pixel ratio: a cosmetic pen (Qt's fast stroker) as
    // wide in device pixels as the line is in item pixels times the ratio. Joins round, so a peak keeps its tip; ends
    // stop at their points, as a square cap would reach half the width past a break and fill a one-pixel gap.
    const qreal ratio = painter->device()->devicePixelRatioF();
    const int device_width = std::max(1, static_cast<int>(std::ceil(width() * ratio)));
    const int device_height = std::max(1, static_cast<int>(std::ceil(height() * ratio)));
    const int forced = qEnvironmentVariableIntValue("EDI_SCAN_PAINT_THREADS");
    const int threads = forced > 0 ? forced : busy_ ? 1 : QThreadPool::globalInstance()->maxThreadCount();
    const int tiles = std::clamp(threads, 1, std::max(1, device_height / 16));
    const bool smooth = painter->testRenderHint(QPainter::Antialiasing);
    std::vector<QImage> images(static_cast<std::size_t>(tiles));
    std::vector<int> firsts(static_cast<std::size_t>(tiles) + 1);
    for (int t = 0; t <= tiles; ++t) {
        firsts[static_cast<std::size_t>(t)] = static_cast<int>(static_cast<long long>(device_height) * t / tiles);
    }
    std::vector<int> indices(static_cast<std::size_t>(tiles));
    std::iota(indices.begin(), indices.end(), 0);
    QThreadPool pool;
    pool.setMaxThreadCount(tiles);
    QtConcurrent::blockingMap(&pool, indices, [&](int t) {
        const int first = firsts[static_cast<std::size_t>(t)], last = firsts[static_cast<std::size_t>(t) + 1];
        QImage& image = images[static_cast<std::size_t>(t)];
        image = QImage(device_width, device_height, QImage::Format_ARGB32_Premultiplied);
        image.setDevicePixelRatio(ratio);
        QPainter tile(&image);
        tile.setCompositionMode(QPainter::CompositionMode_Source);
        tile.fillRect(QRectF(0.0, first / ratio, device_width / ratio, (last - first) / ratio), Qt::transparent);
        tile.setCompositionMode(QPainter::CompositionMode_SourceOver);
        tile.setRenderHint(QPainter::Antialiasing, smooth);
        tile.setClipRect(QRectF(0.0, first / ratio, device_width / ratio, (last - first) / ratio));
        const double from = first / ratio, to = last / ratio;
        for (const Line& line : lines) {
            if (line.bottom < from || line.top > to) {
                continue;
            }
            QPen pen(line.colour);
            pen.setWidthF(line.width * ratio);
            pen.setCosmetic(true);
            pen.setCapStyle(Qt::FlatCap);
            pen.setJoinStyle(Qt::RoundJoin);
            tile.setPen(pen);
            tile.setBrush(Qt::NoBrush);
            tile.drawPath(line.path);
        }
    });
    // Each tile copied pixel for pixel: no smoothing or antialiasing at a tile's edge, which may fall inside an item pixel.
    painter->save();
    painter->setRenderHint(QPainter::Antialiasing, false);
    painter->setRenderHint(QPainter::SmoothPixmapTransform, false);
    for (int t = 0; t < tiles; ++t) {
        const int first = firsts[static_cast<std::size_t>(t)], last = firsts[static_cast<std::size_t>(t) + 1];
        painter->drawImage(QRectF(0.0, first / ratio, device_width / ratio, (last - first) / ratio),
                           images[static_cast<std::size_t>(t)], QRectF(0, first, device_width, last - first));
    }
    painter->restore();
}

ScanRowTicks::ScanRowTicks(QQuickItem* parent) : QQuickItem(parent) { setFlag(ItemHasContents, true); }

void ScanRowTicks::setScanLayer(ScanLayer* layer) {
    if (layer == layer_) {
        return;
    }
    if (layer_) {
        disconnect(layer_, nullptr, this, nullptr);
    }
    layer_ = layer;
    if (layer_) {
        for (const auto changed : {&ScanLayer::placementChanged, &ScanLayer::yMinChanged, &ScanLayer::yMaxChanged,
                                   &ScanLayer::coloursRevisionChanged, &ScanLayer::modelChanged, &ScanLayer::modeChanged}) {
            connect(layer_, changed, this, [this] { update(); });
        }
    }
    emit scanLayerChanged();
    update();
}

void ScanRowTicks::setTickWidth(double width) {
    if (width != tick_width_) {
        tick_width_ = width;
        emit tickWidthChanged();
        update();
    }
}

void ScanRowTicks::setPlotHeight(double height) {
    if (height != plot_height_) {
        plot_height_ = height;
        emit plotHeightChanged();
        update();
    }
}

QSGNode* ScanRowTicks::updatePaintNode(QSGNode* old, UpdatePaintNodeData* /*data*/) {
    auto* root = old != nullptr ? old : new QSGNode;
    while (QSGNode* child = root->firstChild()) {
        root->removeChildNode(child);
        delete child;
    }
    const ScanViewModel* model = layer_ ? layer_->model() : nullptr;
    const double low = layer_ ? layer_->property("yMin").toDouble() : 0.0;
    const double high = layer_ ? layer_->property("yMax").toDouble() : 0.0;
    if (model == nullptr || window() == nullptr || !(high > low) || plot_height_ < 1.0) {
        return root;
    }
    for (int d = 0; d < model->count(); ++d) {
        const double at = layer_->rowOf(d);
        if (!std::isfinite(at) || at < low || at > high) {
            continue;
        }
        const double row = std::clamp(std::floor((high - at) / (high - low) * plot_height_), 0.0, plot_height_ - 1.0);
        QSGRectangleNode* tick = window()->createRectangleNode();
        tick->setRect(QRectF(0.0, row, tick_width_, 1.0));
        tick->setColor(layer_->colourOf(d));
        root->appendChildNode(tick);
    }
    return root;
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
