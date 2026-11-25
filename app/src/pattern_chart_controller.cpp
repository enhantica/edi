// SPDX-License-Identifier: BSD-3-Clause
#include "pattern_chart_controller.hpp"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <limits>
#include <numbers>
#include <QCryptographicHash>
#include <QFontMetricsF>
#include <QScopeGuard>
#include <QStringList>
#include <set>
#include <utility>

#include "ui_probe.hpp"

namespace edi_app {

namespace {
QString superscript_power(int power) {
    static const QString digits = QStringLiteral("⁰¹²³⁴⁵⁶⁷⁸⁹");
    QString exponent = power < 0 ? QStringLiteral("⁻") : QString();
    for (const QChar digit : QString::number(std::abs(power))) exponent += digits.at(digit.digitValue());
    return QStringLiteral("×10") + exponent;
}

bool in_decimal_range(double size) { return size >= 0.001 && size < 1000.0; }

// A tick without the rounding its computation left: to the quantum, and 0 below it.
double snapped(double value, double quantum) {
    if (!(quantum > 0.0)) return value;
    const double near = std::round(value / quantum) * quantum;
    return std::fabs(near) < quantum ? 0.0 : near;
}

// Whether `digits` places after the point write `value` exactly, to the quantum.
bool exact(double value, double scale, int places, double tolerance) {
    const double factor = std::pow(10.0, places);
    return std::fabs(value * factor - std::round(value * factor)) * scale / factor <= tolerance;
}
}  // namespace

QString axis_label(double value, const AxisLabels& format) {
    value = snapped(value, format.quantum);
    if (!std::isfinite(value)) return QString::number(value);
    if (value == 0.0) return QStringLiteral("0");
    const double size = std::fabs(value);
    if (in_decimal_range(size)) {
        QString text = QString::number(value, 'f', format.decimals);
        return text;
    }
    int power = static_cast<int>(std::floor(std::log10(size)));
    QString mantissa = QString::number(value / std::pow(10.0, power), 'f', std::max(0, format.digits - 1));
    if (std::fabs(mantissa.toDouble()) >= 10.0) {
        ++power;
        mantissa = QString::number(value / std::pow(10.0, power), 'f', std::max(0, format.digits - 1));
    }
    if (mantissa.contains(u'.')) {
        while (mantissa.endsWith(u'0')) mantissa.chop(1);
        if (mantissa.endsWith(u'.')) mantissa.chop(1);
    }
    return mantissa + superscript_power(power);
}

AxisLabels axis_labels(const std::vector<double>& ticks) {
    AxisLabels format;
    double largest = 0.0;
    for (const double tick : ticks) {
        if (std::isfinite(tick)) largest = std::max(largest, std::fabs(tick));
    }
    if (largest > 0.0) format.quantum = std::pow(10.0, std::floor(std::log10(largest)) - 9);
    const auto distinct = [&] {
        std::set<QString> texts;
        for (const double tick : ticks) texts.insert(axis_label(tick, format));
        return texts.size() == ticks.size();
    };
    const auto all = [&](const auto& test) {
        return std::all_of(ticks.begin(), ticks.end(), [&](double tick) {
            const double value = snapped(tick, format.quantum);
            return !std::isfinite(value) || value == 0.0 || test(value);
        });
    };
    // Decimals for the ticks inside the decimal range, significant digits for the others.
    while (format.decimals < 6 && !all([&](double v) {
               return !in_decimal_range(std::fabs(v)) || exact(v, 1.0, format.decimals, format.quantum);
           }))
        ++format.decimals;
    while (format.digits < 6 && !all([&](double v) {
               if (in_decimal_range(std::fabs(v))) return true;
               const double power = std::pow(10.0, std::floor(std::log10(std::fabs(v))));
               return exact(v / power, power, format.digits - 1, format.quantum);
           }))
        ++format.digits;
    while (!distinct() && (format.decimals < 12 || format.digits < 15)) {
        format.decimals = std::min(12, format.decimals + 1);
        format.digits = std::min(15, format.digits + 1);
    }
    return format;
}

QString axis_labels_text(const AxisLabels& format) {
    return QStringLiteral("%1|%2|%3").arg(format.decimals).arg(format.digits).arg(format.quantum, 0, 'g', 17);
}

AxisLabels axis_labels_from_text(const QString& text) {
    AxisLabels format;
    const QStringList parts = text.split(u'|');
    if (parts.size() == 3) {
        format.decimals = parts[0].toInt();
        format.digits = parts[1].toInt();
        format.quantum = parts[2].toDouble();
    }
    return format;
}

std::vector<double> axis_ticks(double low, double high, double step) {
    std::vector<double> ticks;
    if (!(step > 0.0) || !(high >= low) || !std::isfinite(low) || !std::isfinite(high)) return ticks;
    const double first = std::ceil(low / step - 1e-9);
    for (int k = 0; k < 200; ++k) {
        const double tick = (first + k) * step;
        if (tick > high + step * 1e-9) break;
        ticks.push_back(tick);
    }
    return ticks;
}

double labelled_step(double low, double high, double pixels, const QFont& font, bool horizontal, int target) {
    const double span = high - low;
    if (!(span > 0.0) || !std::isfinite(span)) return 1.0;
    const QFontMetricsF metrics(font);
    // A gap of about an em between labels along the axis; a vertical axis keeps half a line between them.
    const double gap = horizontal ? metrics.height() : 0.5 * metrics.height();
    const double base = std::pow(10.0, std::floor(std::log10(span / std::max(1, target))) - 1);
    double best = 0.0, fallback = 0.0;
    int best_distance = std::numeric_limits<int>::max();
    for (int decade = 0; decade < 8; ++decade) {
        for (const double factor : {1.0, 2.0, 2.5, 5.0}) {
            const double step = factor * base * std::pow(10.0, decade);
            const std::vector<double> ticks = axis_ticks(low, high, step);
            if (ticks.size() > 64) continue;
            if (ticks.size() >= 2 || fallback == 0.0) fallback = step;
            if (ticks.empty()) continue;
            if (pixels > 0.0) {
                double room = 0.0;
                if (horizontal) {
                    // Only the labels with the most characters can be the widest: shaping every label of every step
                    // tried was most of a chart's redraw after a Next (the owner, 2026-11-23).
                    const AxisLabels format = axis_labels(ticks);
                    std::vector<QString> labels;
                    labels.reserve(ticks.size());
                    qsizetype longest = 0;
                    for (const double tick : ticks) {
                        labels.push_back(axis_label(tick, format));
                        longest = std::max(longest, labels.back().size());
                    }
                    for (const QString& label : labels)
                        if (label.size() >= longest - 1) room = std::max(room, metrics.horizontalAdvance(label));
                } else {
                    room = metrics.height();
                }
                if (pixels * step / span < room + gap) continue;
            }
            const int distance = std::abs(static_cast<int>(ticks.size()) - target);
            // On a tie the larger step: fewer, rounder ticks.
            if (distance <= best_distance) {
                best_distance = distance;
                best = step;
            }
        }
    }
    return best > 0.0 ? best : fallback > 0.0 ? fallback : span;
}

namespace {

constexpr double kWheelNotch = 120.0;
constexpr double kWheelFactor = 0.8;  // one notch away from the user multiplies the x span by this

edi::YScale core_scale(PatternChartController::YScale scale) {
    return scale == PatternChartController::Sqrt    ? edi::YScale::Sqrt
           : scale == PatternChartController::Log10 ? edi::YScale::Log10
                                                    : edi::YScale::Linear;
}

// One presented series as the typed list Qt Graphs takes: a gap stays a NaN point.
QList<QPointF> points_of(const edi::PatternSeries& series) {
    QList<QPointF> list;
    list.reserve(static_cast<qsizetype>(series.points.size()));
    for (const edi::PresentedPoint& point : series.points) {
        list.append(QPointF(point.x, point.y));
    }
    return list;
}

// Whether two columns hold the same values, a missing value (NaN) matching another.
bool same_values(const edi::PatternSource::Column& a, const edi::PatternSource::Column& b) {
    if (a == b) {
        return true;
    }
    return a && b &&
           std::equal(a->begin(), a->end(), b->begin(), b->end(),
                      [](double u, double v) { return u == v || (std::isnan(u) && std::isnan(v)); });
}

constexpr int kTicks = 5;  // about this many labelled ticks along an axis (edi ADR-0017 §15)

// The round step — 1, 2, 2.5 or 5 times a power of ten — whose ticks inside [low, high] are closest to `kTicks`
// in number.
double round_step(double low, double high) {
    const double span = high - low;
    if (!(span > 0.0)) {
        return 1.0;
    }
    const double power = std::pow(10.0, std::floor(std::log10(span / kTicks)));
    double best = power;
    int best_distance = std::numeric_limits<int>::max();
    for (const double step : {power, 2.0 * power, 2.5 * power, 5.0 * power, 10.0 * power, 20.0 * power, 25.0 * power}) {
        const double first = std::ceil(low / step) * step, last = std::floor(high / step) * step;
        const int distance = std::abs(static_cast<int>(std::lround((last - first) / step)) + 1 - kTicks);
        // On a tie the larger step: fewer, rounder ticks.
        if (distance <= best_distance) {
            best_distance = distance;
            best = step;
        }
    }
    return best;
}

// The greatest round value — 1, 2, 2.5 or 5 times a power of ten — that is at most `reach`.
double round_within(double reach) {
    if (!(reach > 0.0)) {
        return 1.0;
    }
    const double power = std::pow(10.0, std::floor(std::log10(reach)));
    double within = power;
    for (const double step : {2.0 * power, 2.5 * power, 5.0 * power}) {
        if (step <= reach) {
            within = step;
        }
    }
    return within;
}

constexpr double kFitPadding = 0.1;  // a fitted main y range has this share of its span beyond each end
constexpr double kLogDecades = 6.0;  // a fitted log range with no measured value spans this many decades

// A series emptied keeps its last drawing in Qt Graphs, colour changes included (a scan's first structure outline
// stayed on screen): an empty list is given as one point the chart cannot draw, which redraws it as nothing.
void replace(const QPointer<QXYSeries>& target, const QList<QPointF>& list) {
    if (target) {
        const double nan = std::numeric_limits<double>::quiet_NaN();
        target->replace(list.isEmpty() ? QList<QPointF>{QPointF(nan, nan)} : list);
    }
}

// A style's colour from a style table already built: building the table takes longer than drawing the chart.
QColor style_colour(const std::vector<edi::SeriesStyle>& table, const std::string& key, bool dark) {
    for (const edi::SeriesStyle& style : table) {
        if (style.key == key) {
            QColor out(QString::fromStdString(dark ? style.dark : style.light));
            out.setAlphaF(static_cast<float>(style.opacity));
            return out;
        }
    }
    return {};
}

// The tick series a `bragg.<place>` style draws in: its structure's own.
std::size_t bragg_place(const std::string& style) {
    std::size_t place = 0;
    if (style.starts_with("bragg.")) {
        std::from_chars(style.data() + 6, style.data() + style.size(), place);
    }
    return place;
}

// An area's two edges for Qt Graphs from a curve and, per point, its base (NaN: `floor`). The area holds the drawn
// points only: a gap (an excluded region, or a value the log scale cannot show) is not a point an area can take, so
// the area closes onto its base at each gap instead of bridging it. The upper edge keeps `lift` above the lower one:
// where the two met (a curve on its base, or a closed gap) Qt Graphs filled the area as a fan from its first point
// or not at all.
struct AreaEdges {
    QList<QPointF> upper, lower;
};
AreaEdges area_edges(const QList<QPointF>& curve, const std::vector<double>& base, double floor, double lift) {
    AreaEdges area;
    area.upper.reserve(curve.size() + 2);
    area.lower.reserve(curve.size() + 2);
    bool drawing = false;
    for (qsizetype k = 0; k < curve.size(); ++k) {
        if (!std::isfinite(curve[k].x()) || !std::isfinite(curve[k].y())) {
            if (drawing) {
                area.upper.append(QPointF(area.lower.back().x(), area.lower.back().y() + lift));
                area.lower.append(area.lower.back());
                drawing = false;
            }
            continue;
        }
        const auto at = static_cast<std::size_t>(k);
        const double low = at < base.size() ? base[at] : std::numeric_limits<double>::quiet_NaN();
        const QPointF bottom(curve[k].x(), std::isfinite(low) ? low : floor);
        if (!drawing && !area.upper.isEmpty()) {
            area.upper.append(QPointF(bottom.x(), bottom.y() + lift));
            area.lower.append(bottom);
        }
        area.upper.append(QPointF(curve[k].x(), std::max(curve[k].y(), bottom.y() + lift)));
        area.lower.append(bottom);
        drawing = true;
    }
    return area;
}

// A band: its area and its two edges, each point's ends (the presentation gives a point without a finite s.u. its ends
// at the point, so only a finite interval reaching below the log scale's domain takes the pane's bottom).
struct Band {
    QList<QPointF> top, bottom;
    AreaEdges area;
};
Band band_of(const edi::PatternSeries& series, double floor, double lift, bool with_area = true) {
    Band out;
    std::vector<double> base;
    base.reserve(series.points.size());
    const double nan = std::numeric_limits<double>::quiet_NaN();
    for (std::size_t k = 0; k < series.points.size(); ++k) {
        const double x = series.points[k].x, y = series.points[k].y;
        if (!std::isfinite(y)) {
            out.top.append(QPointF(nan, nan));
            out.bottom.append(QPointF(nan, nan));
            base.push_back(nan);
            continue;
        }
        const double high = k < series.bar_high.size() && std::isfinite(series.bar_high[k]) ? series.bar_high[k] : y;
        const double low = k < series.bar_low.size() ? series.bar_low[k] : y;
        out.top.append(QPointF(x, high));
        out.bottom.append(QPointF(x, std::isfinite(low) ? low : floor));
        base.push_back(out.bottom.back().y());
    }
    if (with_area) out.area = area_edges(out.top, base, floor, lift);
    return out;
}

// Whether a series holds these points as they would be drawn: a gap matches a gap, and no points the one point that an
// emptied series holds (replace()).
bool holds(const QPointer<QXYSeries>& target, const QList<QPointF>& list) {
    if (!target) return false;
    const auto same = [](double a, double b) { return a == b || (std::isnan(a) && std::isnan(b)); };
    const QList<QPointF> now = target->points();
    if (list.isEmpty()) return now.size() == 1 && std::isnan(now.first().x());
    return std::equal(now.begin(), now.end(), list.begin(), list.end(),
                      [&same](const QPointF& a, const QPointF& b) { return same(a.x(), b.x()) && same(a.y(), b.y()); });
}

}  // namespace

PatternChartController::PatternChartController(QObject* parent)
    : QObject(parent), legend_(new ChartLegendModel(this)), excluded_bands_(new ChartBandModel(this)) {
    // A series the QML just handed over is filled at once.
    for (const auto changed :
         {&PatternChartController::measuredSeriesChanged, &PatternChartController::measuredLayerChanged,
          &PatternChartController::calculatedSeriesChanged, &PatternChartController::backgroundSeriesChanged,
          &PatternChartController::residualSeriesChanged}) {
        connect(this, changed, this, &PatternChartController::invalidate);
    }
    connect(&animation_, &RangeAnimation::frame, this, &PatternChartController::animationFrame);
    connect(&animation_, &RangeAnimation::finished, this, &PatternChartController::finishAnimation);
}

PatternChartController::~PatternChartController() {
    if (experiment_) {
        experiment_->setChartShown(this, false);
        experiment_->setChartAxis(this, edi::PatternAxis::Native);
    }
}

void PatternChartController::setAnimationDuration(int milliseconds) {
    milliseconds = std::max(0, milliseconds);
    if (milliseconds != animation_duration_) {
        animation_duration_ = milliseconds;
        emit animationDurationChanged();
    }
}

void PatternChartController::animateTo(std::optional<double> x_min, std::optional<double> x_max,
                                       std::optional<double> y_min, std::optional<double> y_max) {
    // A running animation stops where it is shown, and the new one starts there: drawing its end first would be
    // thrown away by the frame below.
    stopAnimation();
    const double from[4] = {shown_x_min_, shown_x_max_, shown_y_min_, shown_y_max_};
    x_min_ = x_min;
    x_max_ = x_max;
    y_min_ = y_min;
    y_max_ = y_max;
    emit viewRangesChanged();
    if (!active_ || animation_duration_ <= 0 || plot_width_ <= 0.0) {
        invalidate();
        return;
    }
    // The end, as it will be shown, then back to the start before anything is drawn: both in this one turn.
    refresh();
    const double to[4] = {shown_x_min_, shown_x_max_, shown_y_min_, shown_y_max_};
    if (std::equal(std::begin(from), std::end(from), std::begin(to))) {
        return;
    }
    target_[0] = x_min;
    target_[1] = x_max;
    target_[2] = y_min;
    target_[3] = y_max;
    animating_ = true;
    animation_.setDuration(animation_duration_);
    animation_.start({from[0], from[1], from[2], from[3]}, {to[0], to[1], to[2], to[3]});
}

QList<double> PatternChartController::viewRanges() const {
    QList<double> out;
    for (int i = 0; i < 4; ++i) {
        const std::optional<double>& value = animating_ ? target_[i] : i == 0 ? x_min_ : i == 1 ? x_max_ : i == 2 ? y_min_ : y_max_;
        out.append(value ? *value : std::numeric_limits<double>::quiet_NaN());
    }
    return out;
}

// The x axis the ranges are on, so a chart that last showed another axis keeps them rather than resetting.
QString PatternChartController::viewRangesAxis() const {
    return QString::fromStdString(ranges_axis_.empty() ? presented_x_ : ranges_axis_);
}

void PatternChartController::setViewRanges(const QList<double>& ranges) {
    std::optional<double> values[4];
    for (int i = 0; i < 4 && i < ranges.size(); ++i) {
        if (std::isfinite(ranges[i])) {
            values[i] = ranges[i];
        }
    }
    // The same ranges change nothing: a reset gives none, which suit every axis.
    const QList<double> now = viewRanges();
    bool same = true;
    for (int i = 0; i < 4; ++i) {
        const std::optional<double>& value = values[i];
        same = same && (value.has_value() ? std::isfinite(now[i]) && now[i] == *value : !std::isfinite(now[i]));
    }
    if (same) {
        return;
    }
    stopAnimation();
    x_min_ = values[0];
    x_max_ = values[1];
    y_min_ = values[2];
    y_max_ = values[3];
    emit viewRangesChanged();
    invalidate();
}

// The axis is read when the chart next presents, after the ranges given with it.
void PatternChartController::setViewRangesAxis(const QString& axis) {
    const std::string value = axis.toStdString();
    if (value != ranges_axis_) {
        ranges_axis_ = value;
        emit viewRangesAxisChanged();
    }
}

void PatternChartController::animationFrame() {
    if (!animating_) {
        return;
    }
    if (!active_) {
        finishAnimation();  // never a frame of a hidden chart
        return;
    }
    const RangeAnimation::Ranges& at = animation_.shown();
    x_min_ = at[0];
    x_max_ = at[1];
    y_min_ = at[2];
    y_max_ = at[3];
    refresh();
}

void PatternChartController::finishAnimation() {
    if (animating_) {
        stopAnimation();
        invalidate();
    }
}

void PatternChartController::stopAnimation() {
    if (!animating_) {
        return;
    }
    animating_ = false;
    animation_.stop();
    x_min_ = target_[0];
    x_max_ = target_[1];
    y_min_ = target_[2];
    y_max_ = target_[3];
}

void PatternChartController::setStructureCurves(bool on) {
    if (on != structure_curves_) {
        structure_curves_ = on;
        emit structureCurvesChanged();
        invalidate();
    }
}

void PatternChartController::setMeasuredStyle(const QString& style) {
    const QString known = style == QLatin1String("line") || style == QLatin1String("points") ||
                                  style == QLatin1String("linePoints") || style == QLatin1String("bars")
                              ? style
                              : QStringLiteral("band");
    if (known != measured_drawing_) {
        measured_drawing_ = known;
        emit measuredStyleChanged();
        invalidate();
    }
}

void PatternChartController::setBandSeries(int pane, QXYSeries* upper, QXYSeries* lower, QXYSeries* top,
                                           QXYSeries* bottom) {
    if (pane < 0 || pane >= static_cast<int>(band_series_.size())) {
        return;
    }
    band_series_[static_cast<std::size_t>(pane)] = {upper, lower, top, bottom};
    invalidateLater();
}

void PatternChartController::setStructureSeries(int index, QXYSeries* upper, QXYSeries* lower, QXYSeries* outline) {
    if (index < 0) {
        return;
    }
    if (structure_series_.size() <= index) {
        structure_series_.resize(index + 1);
    }
    structure_series_[index] = {upper, lower, outline};
    invalidateLater();
}

void PatternChartController::setBraggSeries(int place, QXYSeries* series) {
    if (place < 0) {
        return;
    }
    if (bragg_series_.size() <= place) {
        bragg_series_.resize(place + 1);
    }
    if (bragg_series_[place] != series) {
        bragg_series_[place] = series;
        invalidateLater();
    }
}

void PatternChartController::setExperiment(ExperimentViewModel* experiment) {
    keeps_panes_ = false;
    if (experiment == experiment_) {
        return;
    }
    if (experiment_) {
        disconnect(experiment_, nullptr, this, nullptr);
        experiment_->setChartShown(this, false);
        experiment_->setChartAxis(this, edi::PatternAxis::Native);
    }
    experiment_ = experiment;
    scan_styles_.reset();
    // Hidden curves belong to the project they were hidden in: another project's experiment shows every curve.
    if (experiment_ && experiment_->parent() != hidden_project_) {
        hidden_project_ = experiment_->parent();
        if (!hidden_.isEmpty()) {
            hidden_.clear();
            emit hiddenSeriesChanged();
        }
    }
    if (experiment_) {
        experiment_->setChartShown(this, active_);
        experiment_->setChartAxis(this, axis());
        connect(experiment_, &ExperimentViewModel::patternSourceChanged, this, &PatternChartController::invalidate);
        connect(experiment_, &ExperimentViewModel::colourPositionsChanged, this, [this] {
            scan_styles_.reset();
            invalidate();
        });
        // The slider let go: the y range is fitted once again, shrinking as well as growing.
        connect(experiment_, &ExperimentViewModel::adjustingChanged, this, [this] {
            if (!experiment_->adjusting()) {
                invalidate();
            }
        });
        // An admitted edit: the frame stays, and it no longer describes the model.
        connect(experiment_, &ExperimentViewModel::patternWentStale, this, [this] {
            shown_.current = false;
            publish(current_, false, &PatternChartController::currentChanged);
        });
    }
    // Another experiment is another pattern: the view starts over.
    finishAnimation();
    x_min_.reset();
    x_max_.reset();
    y_min_.reset();
    y_max_.reset();
    emit experimentChanged();
    emit viewRangesChanged();
    invalidate();
}

void PatternChartController::setReport(ReportViewModel* report) {
    if (report == report_) {
        return;
    }
    if (report_) {
        disconnect(report_, nullptr, this, nullptr);
    }
    report_ = report;
    if (report_) {
        // A new model can bring other styles (another colour scheme) under the same keys.
        connect(report_, &ReportViewModel::modelChanged, this, &PatternChartController::invalidate);
    }
    emit reportChanged();
    invalidate();
}

void PatternChartController::setReportExperiment(const QString& experiment) {
    if (experiment != report_experiment_) {
        report_experiment_ = experiment;
        emit reportExperimentChanged();
        invalidate();
    }
}

void PatternChartController::setActive(bool active) {
    if (active != active_) {
        active_ = active;
        // A hidden chart draws nothing: a running animation ends at its target, left dirty, and is drawn when
        // the chart is shown again.
        if (!active_) {
            finishAnimation();
        }
        if (experiment_) {
            experiment_->setChartShown(this, active_);
        }
        emit activeChanged();
        if (active_ && dirty_) {
            refresh();
        }
    }
}

void PatternChartController::setDark(bool dark) {
    if (dark != dark_) {
        dark_ = dark;
        emit darkChanged();
        invalidate();
    }
}

void PatternChartController::setColourScheme(const QString& scheme) {
    if (scheme != colour_scheme_) {
        colour_scheme_ = scheme;
        emit colourSchemeChanged();
        invalidate();
    }
}

edi::ColourScheme PatternChartController::scheme() const {
    return edi::colour_scheme_or_default(colour_scheme_.toStdString());
}

std::vector<edi::SeriesStyle> PatternChartController::styles() const {
    if (report_) {
        return report_->reportModel().pattern_styles;
    }
    const std::size_t experiments = experiment_ ? experiment_->colourCount() : 1;
    if (experiment_ && experiment_->showsDataset()) {
        const auto structures = experiment_->structureCount();
        const auto selected = experiment_->colourPlace();
        if (!scan_styles_ || scan_styles_->scheme != scheme() || scan_styles_->files != experiments ||
            scan_styles_->structures != structures) {
            const auto& configured = experiment_->colourPositions();
            const auto allocated = configured.size() == experiments + structures ? std::vector<std::size_t>{}
                : edi::colour_positions(scheme(), experiments, structures);
            const auto& positions = allocated.empty() ? configured : allocated;
            ScanStyles next{scheme(), experiments, structures, {},
                edi::pattern_style_table(scheme(), experiments, structures, positions, true, selected)};
            if (positions.size() == experiments + structures)
                next.structure_positions.assign(positions.begin() + static_cast<std::ptrdiff_t>(experiments), positions.end());
            scan_styles_ = std::move(next);
        }
        auto& measured = scan_styles_->table.front();
        measured.key = "meas." + std::to_string(selected);
        measured.light = edi::pattern_set_colour(scheme(), selected, experiments, scan_styles_->structure_positions, false);
        measured.dark = edi::pattern_set_colour(scheme(), selected, experiments, scan_styles_->structure_positions, true);
        return scan_styles_->table;
    }
    const std::size_t structures = experiment_ ? experiment_->structureCount() : 0;
    // A single crystal's chart shows one experiment and one structure: its magnetic part takes the colour it would in a
    // project of that structure alone, as the powder chart gives it (the owner, 2026-11-16).
    std::vector<std::size_t> spare;
    if (experiment_ && experiment_->sampleForm() == ExperimentViewModel::SingleCrystal) {
        const edi::PatternSource& source = experiment_->singleCrystalPattern(axis_, squared_);
        const std::vector<std::size_t> held = experiment_->colourPositions().size() == experiments + structures
                                                  ? experiment_->colourPositions()
                                                  : edi::colour_positions(scheme(), experiments, structures);
        const std::size_t place = experiment_->colourPlace();
        if (!experiment_->showsDataset() && !source.phases.empty() && place < experiments && source.phases.front().place < structures) {
            spare = {held[place], held[experiments + source.phases.front().place]};
        }
    }
    return edi::pattern_style_table(scheme(), experiments, structures,
                                    experiment_ ? experiment_->colourPositions() : std::vector<std::size_t>{},
                                    experiment_ != nullptr && experiment_->showsDataset(),
                                    experiment_ && experiment_->showsDataset()
                                        ? std::optional<std::size_t>(experiment_->colourPlace()) : std::nullopt,
                                    spare);
}

void PatternChartController::setPlotWidth(qreal width) {
    if (width != plot_width_) {
        plot_width_ = width;
        emit plotWidthChanged();
        // Drawn after the binding that set the width has returned: a drawing relabels the axes, which moves the plot
        // area that binding reads, and doing it inside the binding made a binding loop.
        dirty_ = true;
        QMetaObject::invokeMethod(this, [this] {
            if (dirty_ && active_) {
                refresh();
            }
        }, Qt::QueuedConnection);
    }
}

void PatternChartController::setPlotHeight(qreal height) {
    if (height != plot_height_) {
        plot_height_ = height;
        emit plotHeightChanged();
        if (scaleResidual()) fillResidualArea();
        // The y step follows the height, drawn after the binding returns as for the width.
        dirty_ = true;
        QMetaObject::invokeMethod(this, [this] {
            if (dirty_ && active_) {
                refresh();
            }
        }, Qt::QueuedConnection);
    }
}

void PatternChartController::setLabelFont(const QFont& font) {
    if (!label_font_set_ || font != label_font_) {
        label_font_ = font;
        label_font_set_ = true;
        emit labelFontChanged();
        invalidate();
    }
}

void PatternChartController::setResidualPlotHeight(qreal height) {
    if (height != residual_plot_height_) {
        residual_plot_height_ = height;
        emit residualPlotHeightChanged();
        if (scaleResidual()) fillResidualArea();
    }
}

// The residual's y range and ticks (edi ADR-0017 §15). The pane is linear on every scale (edi ADR-0021 §5), its
// range centred on 0, with three ticks: 0 and the greatest round value inside the range, on either side.
// On the linear scale the range is the main pane's scale: one intensity unit is as high as in the main pane, so
// the two panes read against each other. On the square-root and log scales the main pane has no one height for
// an intensity unit, so there is no scale to follow: the range is fitted to the residual in view, the greatest
// absolute value and a tenth beyond it. That is the range before the panes have a size, too.
bool PatternChartController::scaleResidual() {
    const bool follows = y_scale_ == Linear && plot_height_ > 0.0 && residual_plot_height_ > 0.0;
    const double greatest = std::max(std::fabs(shown_.y_residual.min), std::fabs(shown_.y_residual.max));
    const double fitted = greatest > 0.0 ? (1.0 + kFitPadding) * greatest : 1.0;
    const double reach =
        follows ? 0.5 * (shown_y_max_ - shown_y_min_) * residual_plot_height_ / plot_height_ : fitted;
    const bool moves = residual_min_ != -reach || residual_max_ != reach;
    if (moves) emptyResidualArea();
    publish(residual_min_, -reach, &PatternChartController::residualMinChanged);
    publish(residual_max_, reach, &PatternChartController::residualMaxChanged);
    // A pane lower than three tick labels shows 0 alone: the step past the range leaves no other tick, and three
    // labels ran into each other in the bottom-sidebar layout (the owner, 2026-11-21).
    const double label = label_font_set_ ? QFontMetricsF(label_font_).height() : 0.0;
    const bool crowded = residual_plot_height_ > 0.0 && residual_plot_height_ < 3.0 * label;
    publish(residual_tick_, crowded ? 4.0 * reach : round_within(reach), &PatternChartController::residualTickIntervalChanged);
    return moves;
}

void PatternChartController::emptyMainAreas(bool measured) {
    for (const BandSeries* target : {&band_series_[0], &band_series_[2]}) {
        if (target == &band_series_[0] && !measured) continue;
        replace(target->upper, {});
        replace(target->lower, {});
    }
    for (const StructureSeries& target : structure_series_) {
        replace(target.upper, {});
        replace(target.lower, {});
    }
}

void PatternChartController::emptyResidualArea() {
    replace(band_series_[1].upper, {});
    replace(band_series_[1].lower, {});
}

void PatternChartController::fillResidualArea() {
    if (drawing_ || fills_cleared_) return;  // filled at the drawing's end, or on the drag's release
    if (!active_) {
        dirty_ = true;
        return;
    }
    const auto residual = std::find_if(shown_.series.begin(), shown_.series.end(), [](const edi::PatternSeries& series) {
        return series.kind == edi::SeriesKind::Residual;
    });
    if (residual == shown_.series.end() || measured_drawing_ != QLatin1String("band") || report_) return;
    const AreaEdges area = band_of(*residual, residual_min_, 0.0).area;
    replace(band_series_[1].upper, area.upper);
    replace(band_series_[1].lower, area.lower);
}

void PatternChartController::setDevicePixelRatio(qreal ratio) {
    if (ratio != device_pixel_ratio_ && ratio > 0.0) {
        device_pixel_ratio_ = ratio;
        emit devicePixelRatioChanged();
        invalidate();
    }
}

void PatternChartController::setYScale(YScale scale) {
    if (scale != y_scale_) {
        finishAnimation();
        y_scale_ = scale;
        y_min_.reset();  // a y range chosen on one scale means nothing on another
        y_max_.reset();
        emit yScaleChanged();
        invalidate();
    }
}

QString PatternChartController::xAxis() const {
    const std::string_view token = edi::pattern_axis_token(axis_);
    return QString::fromLatin1(token.data(), static_cast<qsizetype>(token.size()));
}

// An unknown token is the native axis.
void PatternChartController::setXAxis(const QString& token) {
    const edi::PatternAxis axis = edi::pattern_axis_from_token(token.toStdString());
    if (axis == axis_) {
        return;
    }
    const bool was_d = dSpacing();
    finishAnimation();
    axis_ = axis;
    x_min_.reset();  // another axis: the view starts over
    x_max_.reset();
    y_min_.reset();
    y_max_.reset();
    if (experiment_) {
        experiment_->setChartAxis(this, axis_);
    }
    emit xAxisChanged();
    if (dSpacing() != was_d) {
        emit dSpacingChanged();
    }
    invalidate();
}

const edi::PatternSource& PatternChartController::shownSource() const {
    if (experiment_->sampleForm() == ExperimentViewModel::SingleCrystal) {
        return experiment_->singleCrystalPattern(axis_, squared_);
    }
    return experiment_->patternSource(axis_);
}

void PatternChartController::setThinBars(bool on) {
    if (on != thin_bars_) {
        thin_bars_ = on;
        emit thinBarsChanged();
        invalidate();
    }
}

void PatternChartController::setSquared(bool on) {
    if (on != squared_) {
        squared_ = on;
        y_min_.reset();  // another quantity: the y range starts over
        y_max_.reset();
        emit squaredChanged();
        invalidate();
    }
}

void PatternChartController::setDSpacing(bool on) {
    if (on != dSpacing()) {
        setXAxis(QLatin1String(on ? "d_spacing" : "native"));
    }
}

void PatternChartController::setIncludedOnly(bool on) {
    if (on != included_only_) {
        stopAnimation();
        included_only_ = on;
        // Both ranges start over: the intensity then spans the included points only, or all of them again (the owner,
        // 2026-10-27).
        x_min_.reset();
        x_max_.reset();
        y_min_.reset();
        y_max_.reset();
        emit includedOnlyChanged();
        invalidate();
    }
}

void PatternChartController::setSubtractBackground(bool on) {
    if (on != subtract_background_) {
        subtract_background_ = on;
        emit subtractBackgroundChanged();
        invalidate();
    }
}

void PatternChartController::cycleYScale() {
    setYScale(y_scale_ == Linear ? Sqrt : y_scale_ == Sqrt ? Log10 : Linear);
}

QColor PatternChartController::color(const QString& styleKey) const {
    return style_colour(styles(), styleKey.toStdString(), dark_);
}

void PatternChartController::invalidate() {
    dirty_ = true;
    if (active_) {
        refresh();
    }
}

void PatternChartController::invalidateLater() {
    // A series the chart makes is handed over while a drawing publishes the colours that made it: drawing again
    // there would replace the presentation the drawing still reads, so the next drawing waits for the event loop.
    dirty_ = true;
    QMetaObject::invokeMethod(this, [this] {
        if (dirty_ && active_) {
            refresh();
        }
    }, Qt::QueuedConnection);
}

edi::PatternView PatternChartController::view() const {
    edi::PatternView view;
    view.x_min = x_min_;
    view.x_max = x_max_;
    view.columns = plot_width_ > 0.0 ? edi::pixel_columns(plot_width_, device_pixel_ratio_) : 0;
    view.y_scale = core_scale(y_scale_);
    view.structure_curves = structure_curves_;
    view.residual_band = measured_drawing_ == QLatin1String("band") && !report_;
    view.included_only = included_only_;
    view.subtract_background = subtract_background_ && !report_;
    for (const QString& key : hidden_) {
        view.hidden.push_back(key.toStdString());
        if (key.startsWith(QLatin1String("bragg/"))) {
            view.hidden.push_back("structure/" + key.mid(6).toStdString());
        }
    }
    if (hidden_fits_range_) {
        for (const QString& key : hidden_) {
            view.uncounted.push_back(key.toStdString());
            // A structure's entry is its ticks; its curve goes with them.
            if (key.startsWith(QLatin1String("bragg/"))) {
                view.uncounted.push_back("structure/" + key.mid(6).toStdString());
            }
        }
    }
    return view;
}

bool PatternChartController::hiddenId(const std::string& id) const {
    if (hidden_.isEmpty()) {
        return false;
    }
    const QString key = QString::fromStdString(id);
    return hidden_.contains(key) ||
           (key.startsWith(QLatin1String("structure/")) && hidden_.contains(QLatin1String("bragg/") + key.mid(10)));
}

void PatternChartController::toggleSeries(const QString& key) {
    if (hidden_.contains(key)) {
        hidden_.removeAll(key);
    } else {
        hidden_.append(key);
    }
    emit hiddenSeriesChanged();
    if (hidden_fits_range_) {
        // The y range fitted once to the curves still shown.
        stopAnimation();
        y_min_.reset();
        y_max_.reset();
        held_range_.reset();
        emit viewRangesChanged();
    }
    invalidate();
}

void PatternChartController::hideAllButMeasured() {
    QStringList keys;
    for (const ChartLegendModel::Entry& entry : legend_->entries()) {
        if (!entry.key.startsWith(QLatin1String("meas"))) {
            keys.append(entry.key);
        }
    }
    hidden_ = keys;
    emit hiddenSeriesChanged();
    invalidate();
}

void PatternChartController::setHiddenFitsRange(bool on) {
    if (on != hidden_fits_range_) {
        hidden_fits_range_ = on;
        emit hiddenFitsRangeChanged();
        if (!hidden_.isEmpty()) {
            invalidate();
        }
    }
}

PatternChartController::Fills PatternChartController::fillsOf(const edi::PatternPresentation& shown, bool held,
                                                              bool clear_fills) const {
    // Every series buffer one drawing of `shown` gives, in the order refresh() gives them (a later one for the same
    // series replaces an earlier); an area a drag holds empty is left out. refresh() draws with it, and the
    // demo's trace compares what the series hold with it for the data it expects (traceMatches).
    Fills out;
    const auto put = [&out](const QPointer<QXYSeries>& series, const QList<QPointF>& points) { out.series.append({series, points}); };
    const edi::PatternSeries *measured = nullptr, *calculated = nullptr, *background = nullptr, *residual = nullptr;
    std::vector<const edi::PatternSeries*> structure_curves;
    std::vector<std::string> bragg_ids;
    for (const edi::PatternSeries& series : shown.series) {
        switch (series.kind) {
            case edi::SeriesKind::Measured: measured = &series; break;
            case edi::SeriesKind::Calculated: calculated = &series; break;
            case edi::SeriesKind::Background: background = &series; break;
            case edi::SeriesKind::Residual: residual = &series; break;
            case edi::SeriesKind::StructureCurve: structure_curves.push_back(&series); break;
            case edi::SeriesKind::BraggTicks: bragg_ids.push_back(series.id); break;
        }
    }
    // The measured style (the owner, 2026-10-22): the line, the markers with their bars, or the band, measured ± s.u.
    // with the residual drawn the same way. A report's chart draws all but the band, as the report does.
    const bool band = measured_drawing_ == QLatin1String("band") && !report_;
    // Bars (a single crystal's reflections, the owner, 2026-11-16): one filled bar per point, measured and calculated.
    const bool bars = measured_drawing_ == QLatin1String("bars") && !report_;
    const bool line = report_ || measured_drawing_ == QLatin1String("line") || measured_drawing_ == QLatin1String("linePoints");
    const bool marks = report_ || measured_drawing_ == QLatin1String("points") ||
                       measured_drawing_ == QLatin1String("linePoints") || measured_drawing_ == QLatin1String("bars");
    put(measured_series_, measured != nullptr && line ? points_of(*measured) : QList<QPointF>());
    if (measured_layer_) {
        out.marks_set = true;
        if (measured != nullptr && marks) {
            for (std::size_t i = 0; i < measured->points.size(); ++i) {
                if (!std::isnan(measured->points[i].y)) {
                    out.marks.append(QPointF(measured->points[i].x, measured->points[i].y));
                    out.marks_low.append(measured->bar_low[i]);
                    out.marks_high.append(measured->bar_high[i]);
                }
            }
        }
    }
    put(calculated_series_, calculated != nullptr && !bars ? points_of(*calculated) : QList<QPointF>());
    put(background_series_, background != nullptr ? points_of(*background) : QList<QPointF>());
    put(residual_series_, residual != nullptr && !band && !bars ? points_of(*residual) : QList<QPointF>());
    const auto fill_band = [&](const edi::PatternSeries* series, std::size_t pane, double floor, double lift) {
        const BandSeries& target = band_series_[pane];
        // While a value is dragged the residual's area waits for the release; the measured one is drawn as ever.
        const bool with_area = !held || pane == 0;
        const Band drawn = band && series != nullptr ? band_of(*series, floor, lift, with_area) : Band{};
        if (clear_fills && pane != 0) {
            put(target.upper, {});
            put(target.lower, {});
        } else if (with_area) {
            put(target.upper, drawn.area.upper);
            put(target.lower, drawn.area.lower);
        }
        put(target.top, drawn.top);
        put(target.bottom, drawn.bottom);
    };
    fill_band(measured, 0, shown_y_min_, plot_height_ > 0.0 ? 0.05 * (shown_y_max_ - shown_y_min_) / plot_height_ : 0.0);
    fill_band(residual, 1, residual_min_, 0.0);
    // Each bar spans its value and the pane's zero (or its bottom, when zero is below it): a fixed width on the axis,
    // so bars widen when zoomed in, or one pixel at any zoom with thin bars (the owner, 2026-11-16). Its fill is a line
    // barWidth wide (the bottom series) and its outline is drawn round it. One area for all the bars was not used:
    // Qt Graphs filled the gaps between them as slivers fanned from the first point.
    const bool component_bars = bars && !structure_curves.empty();
    // A single crystal with no magnetic part: the total is its one structure's contribution, so hiding that structure's
    // entry hides the bars' fill as it hides a part's, and the total keeps only its outline (none in thin lines).
    const bool contribution_hidden = bars && structure_curves.empty() && bragg_ids.size() == 1 &&
                                     !bragg_ids.front().ends_with("/magnetic") && hiddenId(bragg_ids.front());
    out.component_bars = component_bars;
    const auto fill_bars = [&](const edi::PatternSeries* series, std::size_t pane, double low_edge, double high_edge) {
        if (pane >= band_series_.size() || (held && pane == 0)) return;
        const BandSeries& target = band_series_[pane];
        const double nan = std::numeric_limits<double>::quiet_NaN();
        const double pixel = plot_width_ > 0.0 ? (shown_x_max_ - shown_x_min_) / plot_width_ : 0.0;
        // 0.006 Å⁻¹ either side in Q, the same width in sinθ/λ = Q / (4π).
        const double fixed = axis_ == edi::PatternAxis::Q ? 0.006 : 0.006 / (4.0 * std::numbers::pi);
        const double half = thin_bars_ ? 0.5 * pixel : std::max(fixed, 0.5 * pixel);
        const double zero = std::clamp(0.0, low_edge, high_edge);
        if (pixel > 0.0 && half > 0.0) out.bar_width = std::max(1.0, 2.0 * half / pixel);
        QList<QPointF> fill, outline;
        // With its parts drawn as bars of their own, the total is its outline alone; in thin lines, the parts alone.
        const bool parts = pane == 2 && (component_bars || contribution_hidden);
        if (bars && series != nullptr && half > 0.0 && !(parts && thin_bars_)) {
            for (const auto& point : series->points) {
                if (!std::isfinite(point.x) || !std::isfinite(point.y)) continue;
                const double low = std::min(point.y, zero), high = std::max(point.y, zero);
                if (!parts) {
                    fill.append(QPointF(point.x, low));
                    fill.append(QPointF(point.x, high));
                    fill.append(QPointF(nan, nan));
                }
                for (const QPointF& corner : {QPointF(point.x - half, low), QPointF(point.x - half, high),
                                              QPointF(point.x + half, high), QPointF(point.x + half, low),
                                              QPointF(point.x - half, low), QPointF(nan, nan)}) {
                    outline.append(corner);
                }
            }
        }
        if (clear_fills || !held) {
            put(target.upper, {});
            put(target.lower, {});
        }
        put(target.top, outline);
        put(target.bottom, fill);
    };
    // Measured values stay points with their error bars (the marks above); the residual is drawn as bars.
    if (bars) {
        fill_bars(residual, 1, residual_min_, residual_max_);
    }
    fill_bars(calculated, 2, shown_y_min_, shown_y_max_);
    // Each structure curve: its area between the background and the curve, and its outline.
    for (std::size_t index = 0; index < structure_curves.size(); ++index) {
        const edi::PatternSeries& series = *structure_curves[index];
        if (static_cast<qsizetype>(index) >= structure_series_.size()) {
            out.missing = true;
            continue;  // the chart makes its series and hands them over, which draws again
        }
        // A background the log scale cannot show (zero or less) is below the axis: the fill reaches the axis there.
        const double lift = plot_height_ > 0.0 ? 0.05 * (shown_y_max_ - shown_y_min_) / plot_height_ : 0.0;
        const QList<QPointF> curve = points_of(series);
        const StructureSeries& target = structure_series_[static_cast<qsizetype>(index)];
        if (component_bars) {
            // Each part a bar from what it stands on to its top, drawn as a line barWidth wide.
            QList<QPointF> segments;
            const double nan = std::numeric_limits<double>::quiet_NaN();
            for (std::size_t k = 0; k < series.points.size(); ++k) {
                const double x = series.points[k].x, y = series.points[k].y;
                const double low = k < series.bar_low.size() && std::isfinite(series.bar_low[k]) ? series.bar_low[k] : 0.0;
                if (!std::isfinite(x) || !std::isfinite(y) || y == low) continue;
                segments.append(QPointF(x, low));
                segments.append(QPointF(x, y));
                segments.append(QPointF(nan, nan));
            }
            put(target.upper, {});
            put(target.lower, {});
            put(target.outline, segments);
            continue;
        }
        if (clear_fills) {
            put(target.upper, {});
            put(target.lower, {});
        } else if (!held) {
            const AreaEdges area = area_edges(curve, series.bar_low, shown_y_min_, lift);
            put(target.upper, area.upper);
            put(target.lower, area.lower);
        }
        put(target.outline, curve);
    }
    for (qsizetype index = static_cast<qsizetype>(structure_curves.size()); index < structure_series_.size(); ++index) {
        put(structure_series_[index].upper, {});
        put(structure_series_[index].lower, {});
        put(structure_series_[index].outline, {});
    }
    return out;
}

void PatternChartController::refresh() {
    dirty_ = false;
    const bool was_drawing = std::exchange(drawing_, true);
    const auto drawn_out = qScopeGuard([this, was_drawing] { drawing_ = was_drawing; });
    // A linear axis' step leaves room for its labels as they are written, once the plot's size and font are known.
    const auto axis_step = [this](double low, double high, bool horizontal) {
        const double pixels = horizontal ? plot_width_ : plot_height_;
        return label_font_set_ && pixels > 0.0 ? labelled_step(low, high, pixels, label_font_, horizontal, kTicks)
                                               : round_step(low, high);
    };
    if (report_) {
        // The report's presentation as the model holds it; none for an experiment the model does not hold.
        const edi::ReportPattern* pattern = report_->pattern(report_experiment_);
        shown_ = pattern != nullptr ? pattern->presentation : edi::PatternPresentation{};
        // The model carries each structure's curve for a browser's toolbar; the Report figure has no such switch and
        // draws none.
        std::erase_if(shown_.series, [](const edi::PatternSeries& series) {
            return series.kind == edi::SeriesKind::StructureCurve;
        });
    } else {
        static const edi::PatternSource kNothing;
        const edi::PatternSource& source = experiment_ ? shownSource() : kNothing;
        shown_ = edi::present_pattern(source, view());
        // A range chosen on one x quantity or unit means nothing on another: the new axis starts with its full view,
        // unless the ranges held were given for the new axis (a hidden chart catching up with the shared view).
        if (shown_.x.title != presented_x_) {
            const bool changed = !presented_x_.empty();
            presented_x_ = shown_.x.title;
            if (changed && ranges_axis_ != presented_x_ && (x_min_ || x_max_ || y_min_ || y_max_)) {
                finishAnimation();
                x_min_.reset();
                x_max_.reset();
                y_min_.reset();
                y_max_.reset();
                emit viewRangesChanged();
                shown_ = edi::present_pattern(source, view());
            }
        }
        if (ranges_axis_ != presented_x_) {
            ranges_axis_ = presented_x_;
            emit viewRangesAxisChanged();
        }
        if (experiment_ && active_) {
            experiment_->notePresented();
        }
    }
    // A hidden curve is presented with no points: nothing is drawn of it and the pointer reads none of its values, while
    // the range keeps or leaves out its values as `hiddenFitsRange` says.
    for (edi::PatternSeries& series : shown_.series) {
        if (hiddenId(series.id)) {
            series.points.clear();
            series.rows.clear();
            series.bar_low.clear();
            series.bar_high.clear();
        }
    }

    const edi::PatternSeries* measured = nullptr;
    const edi::PatternSeries* calculated = nullptr;
    const edi::PatternSeries* residual = nullptr;
    std::vector<QList<QPointF>> ticks(static_cast<std::size_t>(bragg_series_.size()));
    std::vector<const edi::PatternSeries*> structure_curves;
    std::vector<std::string> bragg_ids;
    QList<ChartLegendModel::Entry> legend;
    // The style table, built once for the whole drawing.
    const std::vector<edi::SeriesStyle> table = styles();
    const auto colour_of = [&](const std::string& key) { return style_colour(table, key, dark_); };
    const auto entry = [&](const edi::PatternSeries& series) {
        const bool bragg = series.kind == edi::SeriesKind::BraggTicks;
        double width = 1.0;
        for (const edi::SeriesStyle& style : table) {
            if (style.key == series.style) {
                width = style.width_px;
            }
        }
        // The label's pieces, each in its style's colour; a plain piece (no style) is drawn in the theme's colour.
        QStringList texts, colours;
        for (const edi::TitleSegment& segment : edi::legend_label(shown_, series)) {
            texts.append(QString::fromStdString(segment.text));
            colours.append(segment.style.empty() ? QString() : colour_of(segment.style).name(QColor::HexArgb));
        }
        const QColor mark = colour_of(series.style);
        // A dashed series has a dashed sample.
        bool dashed = false;
        for (const edi::SeriesStyle& style : table) {
            dashed = dashed || (style.key == series.style && style.mark.find("dash") != std::string::npos);
        }
        legend.append({QString::fromStdString(series.label), mark,
                       bragg    ? QStringLiteral("tick")
                       : dashed ? QStringLiteral("dash")
                                : QStringLiteral("line"),
                       bragg, width, texts, colours});
        legend.back().key = QString::fromStdString(series.id);
        legend.back().hidden = hidden_.contains(legend.back().key);
        legend.back().magnetic = bragg && series.id.ends_with("/magnetic");
    };
    int rows = 0, shown_rows = 0;
    for (const edi::PatternSeries& series : shown_.series) {
        switch (series.kind) {
            case edi::SeriesKind::Measured: measured = &series; break;
            case edi::SeriesKind::Calculated: calculated = &series; break;
            case edi::SeriesKind::Background: break;
            case edi::SeriesKind::Residual: residual = &series; break;
            case edi::SeriesKind::StructureCurve:
                // A structure is in the legend once, as its Bragg peaks.
                structure_curves.push_back(&series);
                continue;
            case edi::SeriesKind::BraggTicks: {
                // A structure's ticks join the series of its colour, its own row kept.
                if (const std::size_t place = bragg_place(series.style); place < ticks.size()) {
                    ticks[place] += points_of(series);
                }
                ++rows;
                shown_rows += hiddenId(series.id) ? 0 : 1;
                bragg_ids.push_back(series.id);
                break;
            }
        }
        entry(series);
    }

    // The ranges and their ticks (edi ADR-0017 §15). A fitted main y range is what is presented and a tenth of
    // its span beyond each end; a range the user chose keeps its bounds. Either takes about five round ticks
    // inside it, as the x range does. The residual's range follows the main pane's (`scaleResidual`).
    const double x_low = shown_.x.min, x_high = shown_.x.max > shown_.x.min ? shown_.x.max : shown_.x.min + 1.0;
    double y_low = y_min_.value_or(shown_.y_main.min), y_high = y_max_.value_or(shown_.y_main.max);
    if (!(y_high > y_low)) {
        y_high = y_low + 1.0;
    }
    const bool fitted = !y_min_.has_value() && !y_max_.has_value();
    double y_step = 1.0, y_anchor = 0.0;
    if (animating_) {
        // A frame of an animation shows its ranges as they are: the decades and the padding are the end's.
        y_step = y_scale_ == Log10 ? std::max(1.0, std::ceil((y_high - y_low) / kTicks)) : axis_step(y_low, y_high, false);
        y_anchor = std::ceil(y_low / y_step) * y_step;
    } else if (y_scale_ == Log10) {
        // A log axis has its ticks at whole decades (edi ADR-0021 §5), about five of them, whatever range it
        // shows. A fitted range is the measured values' decades: from the decade at or below the least
        // measured value to the decade at or above the greatest presented one. A calculated value far below
        // the measured ones — a pattern with no background is 1e-70 between its peaks — leaves the pane at the
        // bottom instead of stretching the axis over its decades. With no measured value the range is six
        // decades. A range the user chose is widened to the whole decades that hold it, so a box drawn inside
        // one decade shows that decade, between two ticks, and never a tick between decades.
        if (fitted) {
            double least = std::numeric_limits<double>::infinity();
            if (measured != nullptr) {
                for (const edi::PresentedPoint& point : measured->points) {
                    if (std::isfinite(point.y)) {
                        least = std::min(least, point.y);
                    }
                }
            }
            y_high = std::ceil(y_high);
            y_low = std::isfinite(least) ? std::floor(least) : y_high - kLogDecades;
        } else {
            y_low = std::floor(y_low);
            y_high = std::ceil(y_high);
        }
        if (!(y_high > y_low)) {
            y_low = y_high - 1.0;
        }
        y_step = std::max(1.0, std::ceil((y_high - y_low) / kTicks));
        y_anchor = y_low;
    } else {
        if (fitted) {
            const double padding = kFitPadding * (y_high - y_low);
            y_low -= padding;
            y_high += padding;
        }
        // A single crystal's bars (or their lines) stand on zero, and its intensities are not negative: the range, fitted
        // or zoomed, starts there, whatever a weak reflection's error bar reaches (the owner, 2026-11-16). In any style a
        // fitted range of non-negative values starts at zero too, its headroom only above; the residual has its own.
        bool non_negative = experiment_ && experiment_->sampleForm() == ExperimentViewModel::SingleCrystal;
        for (const edi::PatternSeries* series : {measured, calculated}) {
            if (series == nullptr) continue;
            for (const edi::PresentedPoint& point : series->points)
                if (std::isfinite(point.y) && point.y < 0.0) non_negative = false;
        }
        if (y_high > 0.0 && ((fitted && non_negative) || (measured_drawing_ == QLatin1String("bars") && !report_))) {
            y_low = 0.0;
        }
        y_step = axis_step(y_low, y_high, false);
        y_anchor = std::ceil(y_low / y_step) * y_step;
    }
    // While a parameter's slider is held (the owner, 2026-10-25), a fitted range holds while the calculated curve stays
    // inside it and grows only when the curve leaves it; letting the slider go, another experiment, dataset, axis,
    // scale or x range, a fit and a reset fit it again.
    if (fitted && !animating_ && !report_) {
        const edi::PatternSource* source = experiment_ ? &shownSource() : nullptr;
        HeldRange now{experiment_, source != nullptr ? source->meas : nullptr, presented_x_, y_scale_, x_low,
                      x_high, y_low, y_high};
        if (held_range_ && experiment_ && experiment_->adjusting() && held_range_->experiment == now.experiment &&
            same_values(held_range_->measured, now.measured) && held_range_->axis == now.axis && held_range_->scale == now.scale &&
            held_range_->x_min == now.x_min && held_range_->x_max == now.x_max) {
            now.low = y_low = std::min(y_low, held_range_->low);
            now.high = y_high = std::max(y_high, held_range_->high);
            y_step = y_scale_ == Log10 ? std::max(1.0, std::ceil((y_high - y_low) / kTicks)) : axis_step(y_low, y_high, false);
            y_anchor = y_scale_ == Log10 ? y_low : std::ceil(y_low / y_step) * y_step;
        }
        held_range_ = now;
    } else if (!fitted) {
        held_range_.reset();
    }
    // The areas whose axes move are emptied before anything is published; the others are valid on the axes they have.
    // While a value is dragged the costly ones are emptied once and stay so until the release (edi ADR-0070).
    const bool x_moves = x_low != shown_x_min_ || x_high != shown_x_max_;
    const bool main_moves = x_moves || y_low != shown_y_min_ || y_high != shown_y_max_;
    const bool held = !report_ && experiment_ && experiment_->adjusting();
    const bool clear_fills = held && !fills_cleared_;
    fills_cleared_ = held;
    if (main_moves || clear_fills) emptyMainAreas(main_moves);
    if (x_moves || clear_fills) emptyResidualArea();
    const double x_step = axis_step(x_low, x_high, true);
    publish(shown_x_min_, x_low, &PatternChartController::xMinChanged);
    publish(shown_x_max_, x_high, &PatternChartController::xMaxChanged);
    publish(shown_y_min_, y_low, &PatternChartController::yMinChanged);
    publish(shown_y_max_, y_high, &PatternChartController::yMaxChanged);
    scaleResidual();
    publish(x_tick_, x_step, &PatternChartController::xTickIntervalChanged);
    publish(x_anchor_, std::ceil(x_low / x_step) * x_step, &PatternChartController::xTickAnchorChanged);
    publish(y_tick_, y_step, &PatternChartController::yTickIntervalChanged);
    publish(y_anchor_, y_anchor, &PatternChartController::yTickAnchorChanged);

    // The frame first (ADR-0102 rule 5): the panes the chart shows and the tick series it needs are published before
    // any series takes its points, so a frame never shows the data without its Bragg rows or residual axes. Within one
    // experiment a pane stays while a dataset's calculation is still to come (the next dataset of a scan), so the
    // layout does not move when the calculation arrives.
    // The series' colours come from the same table as the legend and the row labels, so they change whenever the
    // drawing does: another experiment or project, a structure added, a palette. More structures than tick series:
    // the chart makes the rest, each handed over in turn.
    QList<QColor> bragg_colours;
    for (const edi::SeriesStyle& style : table) {
        if (style.key.starts_with("bragg.")) {
            bragg_colours.append(colour_of(style.key));
        }
    }
    publish(bragg_colors_, bragg_colours, &PatternChartController::braggColorsChanged);
    double bragg_height = 0.0;
    for (const edi::PaneLayout& pane : shown_.layout) {
        if (pane.pane == edi::Pane::Bragg) {
            bragg_height = pane.fixed_px;
        }
    }
    // A pane whose every series is hidden goes with them: the tick rows when all are hidden, the residual's pane when
    // it is.
    const bool pending = !report_ && keeps_panes_ && measured != nullptr && calculated == nullptr;
    const int rows_now = shown_rows > 0 ? rows : 0;
    publish(bragg_rows_, pending && rows_now == 0 ? bragg_rows_ : rows_now, &PatternChartController::braggRowsChanged);
    publish(bragg_height_, pending && bragg_height == 0.0 ? bragg_height_ : bragg_height,
            &PatternChartController::braggHeightChanged);
    publish(has_residual_, (residual != nullptr && !hiddenId(residual->id)) || (pending && has_residual_),
            &PatternChartController::hasResidualChanged);
    publish(has_data_, measured != nullptr || calculated != nullptr, &PatternChartController::hasDataChanged);
    keeps_panes_ = true;
    // While a value is dragged a filled area waits for the release and a series whose points a step does not change is
    // left alone: Qt Graphs triangulates an area each time it is set, the largest part of a step (edi ADR-0070).
    const Fills fills = fillsOf(shown_, held, clear_fills);
    for (const auto& [series, points] : fills.series) {
        if (!held || !holds(series, points)) replace(series, points);
    }
    if (fills.marks_set && !(held && measured_layer_->holds(fills.marks, fills.marks_low, fills.marks_high)))
        measured_layer_->setData(fills.marks, fills.marks_low, fills.marks_high);
    if (std::isfinite(fills.bar_width) && fills.bar_width != bar_width_) {
        bar_width_ = fills.bar_width;
        emit barWidthChanged();
    }
    publish(component_bars_, fills.component_bars, &PatternChartController::componentBarsChanged);
    for (std::size_t place = 0; place < ticks.size(); ++place) {
        replace(bragg_series_[static_cast<qsizetype>(place)], ticks[place]);
    }
    QList<QColor> curve_colours, curve_fills;
    for (const edi::PatternSeries& series : shown_.series) {
        if (series.kind != edi::SeriesKind::StructureCurve) continue;
        const QColor fill = colour_of(series.style);
        QColor outline = fill;
        outline.setAlphaF(1.0F);
        curve_colours.append(outline);
        curve_fills.append(fill);
    }
    publish(structure_curve_fills_, curve_fills, &PatternChartController::structureCurveFillsChanged);
    publish(structure_curve_colors_, curve_colours, &PatternChartController::structureCurveColorsChanged);
    publish(has_calculated_, calculated != nullptr, &PatternChartController::hasCalculatedChanged);
    publish(calculated_color_, colour_of("calc"), &PatternChartController::calculatedColorChanged);
    publish(background_color_, colour_of("bkg"), &PatternChartController::backgroundColorChanged);
    publish(residual_color_, colour_of("resid"), &PatternChartController::residualColorChanged);
    publish(excluded_color_, colour_of("excluded"), &PatternChartController::excludedColorChanged);
    publish(measured_color_, colour_of(measured != nullptr ? measured->style : "meas.0"),
            &PatternChartController::measuredColorChanged);

    QList<ChartBandModel::Band> bands;
    for (const edi::ExcludedBand& excluded : shown_.excluded) {
        bands.append({excluded.x_min, excluded.x_max});
    }
    excluded_bands_->setBands(bands);
    legend_->setEntries(legend);
    publish(current_, shown_.current, &PatternChartController::currentChanged);
    publish(d_available_, report_ != nullptr || (experiment_ && experiment_->patternSource().d_available),
            &PatternChartController::dAvailableChanged);
    publish(x_title_, QString::fromStdString(shown_.x.title), &PatternChartController::xTitleChanged);
    // A y title as its coloured pieces, each series' word in its colour (the legend box being hidden by default);
    // the plain title when it has none.
    // A curve hidden by its legend entry leaves the title too, with the separator before it.
    const auto hidden_style = [this](const std::string& style) {
        return std::any_of(shown_.series.begin(), shown_.series.end(), [&](const edi::PatternSeries& series) {
            return series.style == style && hiddenId(series.id);
        });
    };
    const auto styled = [&colour_of, &hidden_style](const edi::AxisDescription& axis) {
        if (axis.segments.empty()) {
            return QString::fromStdString(axis.title).toHtmlEscaped();
        }
        QString text, separator;
        for (const edi::TitleSegment& segment : axis.segments) {
            const QString piece = QString::fromStdString(segment.text).toHtmlEscaped();
            if (segment.style.empty()) {
                separator = piece;
                continue;
            }
            if (hidden_style(segment.style)) {
                separator.clear();
                continue;
            }
            text += (text.isEmpty() ? QString() : separator) + QStringLiteral("<font color=\"%1\">%2</font>")
                                                                   .arg(colour_of(segment.style).name(QColor::HexRgb), piece);
            separator.clear();
        }
        return text;
    };
    publish(y_title_, styled(shown_.y_main), &PatternChartController::yTitleChanged);
    publish(residual_title_, styled(shown_.y_residual), &PatternChartController::residualTitleChanged);
    // Each Bragg row's label at its left: the structure's name in its colour, at the row's centre.
    QList<BraggLabel> labels;
    for (const edi::BraggRowLabel& label : shown_.bragg_labels) {
        // Hidden with its row's ticks, which share its style.
        const auto tickSeries = std::find_if(shown_.series.begin(), shown_.series.end(), [&label](const edi::PatternSeries& series) {
            return series.kind == edi::SeriesKind::BraggTicks && series.style == label.style;
        });
        labels.append({QString::fromStdString(label.text), colour_of(label.style), label.centre,
                       tickSeries != shown_.series.end() && hiddenId(tickSeries->id), label.magnetic});
    }
    publish(bragg_labels_, labels, &PatternChartController::braggLabelsChanged);
    const bool subtractable = !report_ && experiment_ != nullptr && edi::has_background(*experiment_->experiment());
    publish(background_available_, subtractable, &PatternChartController::backgroundAvailableChanged);
    ++revision_;
    emit revisionChanged();
#if EDI_UI_INSTRUMENTATION
    if (ui_trace_on()) {
        ++trace_generation_;
        const edi::PatternSource* source = !report_ && experiment_ ? &shownSource() : nullptr;
        trace_identity_ = source != nullptr ? ui_trace_identity(source->meas.get()) : QString();
        trace_series_.clear();
        for (const auto* series : {&measured_series_, &calculated_series_, &background_series_, &residual_series_})
            trace_series_.append(*series);
        for (const BandSeries& filled : band_series_) {
            for (const auto* series : {&filled.upper, &filled.lower, &filled.top, &filled.bottom}) trace_series_.append(*series);
        }
        for (const StructureSeries& curve : structure_series_) {
            for (const auto* series : {&curve.upper, &curve.lower, &curve.outline}) trace_series_.append(*series);
        }
        trace_upload_identity_ = traceBufferIdentity();
    }
#endif
}

#if EDI_UI_INSTRUMENTATION
QString PatternChartController::traceBufferIdentity() const {
    // Every point of every filled series and of the measured markers, read from the scene objects: what the scene
    // draws for this chart. Empty while no measured point is drawn: the measured data are the required fill.
    if (traceMeasuredLine().isEmpty() && traceMeasuredMarks().isEmpty() && traceMeasuredBand().isEmpty()) return {};
    // A fast hash of the same bytes: only compared for equality within the app, and SHA-256 over every drawn point at
    // every refresh held the GUI thread in the responsiveness gates (ADR-0102 R1).
    size_t hash = qHashBits("trace", 5, 0);
    bool finite = false;
    if (measured_layer_) {
        const QList<QPointF>& marks = measured_layer_->points();
        hash = qHashBits("marks", 5, hash);
        hash = qHashBits(marks.constData(), static_cast<size_t>(marks.size()) * sizeof(QPointF), hash);
    }
    for (qsizetype index = 0; index < trace_series_.size(); ++index) {
        const QPointer<QXYSeries>& series = trace_series_[index];
        hash = qHashMulti(hash, index);
        if (!series) continue;
        const QList<QPointF> points = series->points();
        for (const QPointF& point : points) finite = finite || (std::isfinite(point.x()) && std::isfinite(point.y()));
        hash = qHashBits(points.constData(), static_cast<size_t>(points.size()) * sizeof(QPointF), hash);
    }
    return finite ? QStringLiteral("%1").arg(static_cast<quint64>(hash), 16, 16, QLatin1Char('0')) : QString();
}

QList<QPointF> PatternChartController::traceMeasuredLine() const {
    QList<QPointF> points;
    if (measured_series_) {
        for (const QPointF& point : measured_series_->points())
            if (std::isfinite(point.x()) && std::isfinite(point.y())) points.append(point);
    }
    return points;
}

QList<QPointF> PatternChartController::traceMeasuredMarks() const {
    QList<QPointF> points;
    if (measured_layer_) {
        for (const QPointF& point : measured_layer_->points())
            if (std::isfinite(point.x()) && std::isfinite(point.y())) points.append(point);
    }
    return points;
}

bool PatternChartController::traceMatches(const edi::PatternPresentation& expected) const {
    // The expected data drawn as refresh() draws them, hidden series emptied as refresh() empties them, compared with
    // every series the drawing fills. A fill held while a value is dragged is not compared; a structure curve whose
    // series is not handed over yet does not match.
    edi::PatternPresentation shown = expected;
    for (edi::PatternSeries& series : shown.series) {
        if (hiddenId(series.id)) {
            series.points.clear();
            series.rows.clear();
            series.bar_low.clear();
            series.bar_high.clear();
        }
    }
    const bool held = !report_ && experiment_ && experiment_->adjusting();
    const Fills fills = fillsOf(shown, held, false);
    if (fills.missing) return false;
    const auto same = [](double a, double b) {
        return (std::isnan(a) && std::isnan(b)) || a == b || std::abs(a - b) <= 1e-9 * std::max(1.0, std::abs(b));
    };
    const auto same_points = [&](const QList<QPointF>& drawn, const QList<QPointF>& want) {
        if (drawn.size() != want.size()) return false;
        for (qsizetype i = 0; i < drawn.size(); ++i)
            if (!same(drawn[i].x(), want[i].x()) || !same(drawn[i].y(), want[i].y())) return false;
        return true;
    };
    QHash<const QXYSeries*, QList<QPointF>> wanted;
    for (const auto& [series, points] : fills.series) {
        if (!series) continue;
        // An emptied series holds one point it cannot draw (replace()).
        wanted.insert(series.data(), points.isEmpty() ? QList<QPointF>{QPointF(std::nan(""), std::nan(""))} : points);
    }
    for (auto it = wanted.cbegin(); it != wanted.cend(); ++it)
        if (!same_points(it.key()->points(), it.value())) return false;
    if (fills.marks_set) {
        if (!measured_layer_ || !same_points(measured_layer_->points(), fills.marks)) return false;
        const auto same_values = [&](const QList<double>& drawn, const QList<double>& want) {
            if (drawn.size() != want.size()) return false;
            for (qsizetype i = 0; i < drawn.size(); ++i)
                if (!same(drawn[i], want[i])) return false;
            return true;
        };
        if (!same_values(measured_layer_->lowEnds(), fills.marks_low) || !same_values(measured_layer_->highEnds(), fills.marks_high))
            return false;
    }
    return true;
}

int PatternChartController::traceExperimentPlace() const {
    return experiment_ != nullptr ? static_cast<int>(experiment_->tracePlace()) : -1;
}

QList<std::array<double, 3>> PatternChartController::traceMeasuredBand() const { return traceBand(0); }

QList<std::array<double, 3>> PatternChartController::traceBand(int pane) const {
    QList<std::array<double, 3>> edges;
    if (pane < 0 || pane >= static_cast<int>(band_series_.size())) return edges;
    const BandSeries& band = band_series_[static_cast<std::size_t>(pane)];
    if (!band.top || !band.bottom) return edges;
    const QList<QPointF> top = band.top->points(), bottom = band.bottom->points();
    for (qsizetype i = 0; i < std::min(top.size(), bottom.size()); ++i) {
        if (std::isfinite(top[i].x()) && std::isfinite(top[i].y()) && std::isfinite(bottom[i].y()) &&
            top[i].x() == bottom[i].x())
            edges.append({top[i].x(), bottom[i].y(), top[i].y()});
    }
    return edges;
}
#endif

double PatternChartController::xOf(double pixel) const {
    return plot_width_ > 0.0 ? shown_x_min_ + pixel / plot_width_ * (shown_x_max_ - shown_x_min_) : shown_x_min_;
}

void PatternChartController::zoomTo(double x0, double x1, double y0, double y1) {
    if (report_ || plot_width_ <= 0.0 || plot_height_ <= 0.0 || x0 == x1 || y0 == y1) {
        return;
    }
    const double left = xOf(std::min(x0, x1)), right = xOf(std::max(x0, x1));
    // Pixels grow downwards; the axis grows upwards.
    const auto y_of = [this](double pixel) {
        return shown_y_max_ - pixel / plot_height_ * (shown_y_max_ - shown_y_min_);
    };
    const double top = y_of(std::min(y0, y1)), bottom = y_of(std::max(y0, y1));
    animateTo(left, right, bottom, top);
}

void PatternChartController::wheelAt(double x, int angleDelta) {
    if (report_ || plot_width_ <= 0.0 || angleDelta == 0) {
        return;
    }
    // From where a running animation is going, so notches in quick succession add up.
    const double anchor = xOf(x);
    const double low = animating_ ? animation_.end()[0] : shown_x_min_, high = animating_ ? animation_.end()[1] : shown_x_max_;
    stopAnimation();
    const double factor = std::pow(kWheelFactor, angleDelta / kWheelNotch);
    animateTo(anchor - (anchor - low) * factor, anchor + (high - anchor) * factor, y_min_, y_max_);
}

void PatternChartController::panBy(double dx) {
    if (report_ || plot_width_ <= 0.0 || dx == 0.0) {
        return;
    }
    // From where a running animation is going, as a notch is.
    const double low = animating_ ? animation_.end()[0] : shown_x_min_, high = animating_ ? animation_.end()[1] : shown_x_max_;
    stopAnimation();
    const double shift = dx / plot_width_ * (high - low);
    x_min_ = low - shift;
    x_max_ = high - shift;
    emit viewRangesChanged();
    invalidate();
}

void PatternChartController::reset() {
    held_range_.reset();
    animateTo(std::nullopt, std::nullopt, std::nullopt, std::nullopt);
}

QString PatternChartController::hoverAt(double x, double y, int pane, double height) const {
    const auto found = nearest(x, y, pane, height, std::numeric_limits<double>::infinity());
    if (!found) {
        return {};
    }
    // The values drawn, with the background subtracted when it is.
    const edi::PatternSource source = edi::presented_source(shownSource(), view());
    return QString::fromStdString(edi::hover_text(source, *found->series, found->point));
}

QString PatternChartController::hoverReadout(double x, double y, int pane, double height) const {
    const auto found = nearest(x, y, pane, height, kHoverDistance);
    if (!found) {
        return {};
    }
    const edi::PatternSource source = edi::presented_source(shownSource(), view());
    QStringList lines;
    for (const edi::HoverLine& line : edi::hover_readout(source, *found->series, found->point)) {
        const auto piece = [this](const std::string& text, const std::string& style) {
            const QString escaped = QString::fromStdString(text).toHtmlEscaped();
            return style.empty() ? escaped
                                 : QStringLiteral("<span style=\"color:%1\">%2</span>")
                                       .arg(color(QString::fromStdString(style)).name(QColor::HexRgb), escaped);
        };
        if (line.segments.empty()) {
            lines.append(piece(line.text, line.style));
            continue;
        }
        QString text;
        for (const edi::TitleSegment& segment : line.segments) {
            text += piece(segment.text, segment.style);
        }
        lines.append(text);
    }
    return lines.join(QStringLiteral("<br>"));
}

QPointF PatternChartController::hoverPoint(double x, double y, int pane, double height) const {
    const auto found = nearest(x, y, pane, height, kHoverDistance);
    return found ? found->at : QPointF(-1.0, -1.0);
}

std::optional<PatternChartController::Nearest> PatternChartController::nearest(double x, double y, int pane,
                                                                               double height, double within) const {
    if (!experiment_ || plot_width_ <= 0.0 || height <= 0.0) {
        return std::nullopt;
    }
    const edi::Pane wanted = pane == 1 ? edi::Pane::Bragg : pane == 2 ? edi::Pane::Residual : edi::Pane::Main;
    const double low = pane == 1 ? 0.0 : pane == 2 ? residual_min_ : shown_y_min_;
    const double high = pane == 1 ? static_cast<double>(std::max(1, bragg_rows_))
                        : pane == 2 ? residual_max_
                                    : shown_y_max_;
    const double x_span = shown_x_max_ - shown_x_min_;
    // The nearest presented point, in pixels.
    const edi::PatternSeries* best_series = nullptr;
    std::size_t best_point = 0;
    QPointF best_at;
    double best = std::numeric_limits<double>::infinity();
    for (const edi::PatternSeries& series : shown_.series) {
        if (series.pane != wanted) {
            continue;
        }
        for (std::size_t i = 0; i < series.points.size(); ++i) {
            if (i >= series.rows.size() || series.rows[i] == edi::kNoRow) {
                continue;
            }
            const double px = (series.points[i].x - shown_x_min_) / x_span * plot_width_;
            const double py = (high - series.points[i].y) / (high - low) * height;
            // A tick is as tall as its row: only its x counts.
            const double distance = pane == 1 ? std::fabs(px - x) : std::hypot(px - x, py - y);
            if (distance < best && distance <= within) {
                best = distance;
                best_series = &series;
                best_point = i;
                best_at = QPointF(px, pane == 1 ? y : py);
            }
        }
    }
    if (best_series == nullptr) {
        return std::nullopt;
    }
    return Nearest{best_series, best_point, best_at};
}

QString PatternChartController::axisLabel(const QString& text, YScale scale) const {
    bool ok = false;
    const double display = text.toDouble(&ok);
    return ok ? QString::fromStdString(edi::axis_label(display, core_scale(scale))) : text;
}

double PatternChartController::originalValue(double display, YScale scale) const {
    return edi::from_display(display, core_scale(scale));
}

}  // namespace edi_app
