// SPDX-License-Identifier: BSD-3-Clause
#include "pattern_chart_controller.hpp"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <limits>
#include <QStringList>
#include <utility>

namespace edi_app {
namespace {

const double kNaN = std::numeric_limits<double>::quiet_NaN();
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
    // Qt Charts' series animation easing, as easydiffractionbeta's charts moved.
    animation_.setStartValue(0.0);
    animation_.setEndValue(1.0);
    animation_.setEasingCurve(QEasingCurve::OutQuart);
    connect(&animation_, &QVariantAnimation::valueChanged, this,
            [this](const QVariant& value) { animationFrame(value.toDouble()); });
    connect(&animation_, &QAbstractAnimation::finished, this, &PatternChartController::finishAnimation);
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
    std::copy(std::begin(from), std::end(from), std::begin(from_));
    std::copy(std::begin(to), std::end(to), std::begin(to_));
    target_[0] = x_min;
    target_[1] = x_max;
    target_[2] = y_min;
    target_[3] = y_max;
    animating_ = true;
    animationFrame(0.0);
    animation_.setDuration(animation_duration_);
    animation_.start();
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
        same = same && (values[i] ? std::isfinite(now[i]) && now[i] == *values[i] : !std::isfinite(now[i]));
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

void PatternChartController::animationFrame(double progress) {
    if (!animating_) {
        return;
    }
    if (!active_) {
        finishAnimation();  // never a frame of a hidden chart
        return;
    }
    const auto at = [this, progress](int i) { return from_[i] + (to_[i] - from_[i]) * progress; };
    x_min_ = at(0);
    x_max_ = at(1);
    y_min_ = at(2);
    y_max_ = at(3);
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

void PatternChartController::publishColors() {
    emit measuredColorChanged();
    emit calculatedColorChanged();
    emit backgroundColorChanged();
    emit residualColorChanged();
    emit excludedColorChanged();
    bragg_colour_count_ = braggColors().size();
    emit braggColorsChanged();
}

QList<QColor> PatternChartController::braggColors() const {
    QList<QColor> colours;
    const std::vector<edi::SeriesStyle> table = styles();
    for (const edi::SeriesStyle& style : table) {
        if (style.key.starts_with("bragg.")) {
            colours.append(style_colour(table, style.key, dark_));
        }
    }
    return colours;
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
                                  style == QLatin1String("linePoints")
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
    if (experiment == experiment_) {
        return;
    }
    if (experiment_) {
        disconnect(experiment_, nullptr, this, nullptr);
        experiment_->setChartShown(this, false);
        experiment_->setChartAxis(this, edi::PatternAxis::Native);
    }
    experiment_ = experiment;
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
            publishColors();
            invalidate();  // the legend's colours
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
        connect(report_, &ReportViewModel::modelChanged, this, [this] {
            publishColors();
            invalidate();
        });
    }
    emit reportChanged();
    publishColors();
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
        publishColors();
        invalidate();  // the legend's colours
    }
}

void PatternChartController::setColourScheme(const QString& scheme) {
    if (scheme != colour_scheme_) {
        colour_scheme_ = scheme;
        emit colourSchemeChanged();
        publishColors();
        invalidate();  // the legend's colours
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
    return edi::pattern_style_table(scheme(), experiments, experiment_ ? experiment_->structureCount() : 0,
                                    experiment_ ? experiment_->colourPositions() : std::vector<std::size_t>{},
                                    experiment_ != nullptr && experiment_->showsDataset());
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
        scaleResidual();
    }
}

void PatternChartController::setResidualPlotHeight(qreal height) {
    if (height != residual_plot_height_) {
        residual_plot_height_ = height;
        emit residualPlotHeightChanged();
        scaleResidual();
    }
}

// The residual's y range and ticks (edi ADR-0017 §15). The pane is linear on every scale (edi ADR-0021 §5), its
// range centred on 0, with three ticks: 0 and the greatest round value inside the range, on either side.
// On the linear scale the range is the main pane's scale: one intensity unit is as high as in the main pane, so
// the two panes read against each other. On the square-root and log scales the main pane has no one height for
// an intensity unit, so there is no scale to follow: the range is fitted to the residual in view, the greatest
// absolute value and a tenth beyond it. That is the range before the panes have a size, too.
void PatternChartController::scaleResidual() {
    const bool follows = y_scale_ == Linear && plot_height_ > 0.0 && residual_plot_height_ > 0.0;
    const double greatest = std::max(std::fabs(shown_.y_residual.min), std::fabs(shown_.y_residual.max));
    const double fitted = greatest > 0.0 ? (1.0 + kFitPadding) * greatest : 1.0;
    const double reach =
        follows ? 0.5 * (shown_y_max_ - shown_y_min_) * residual_plot_height_ / plot_height_ : fitted;
    publish(residual_min_, -reach, &PatternChartController::residualMinChanged);
    publish(residual_max_, reach, &PatternChartController::residualMaxChanged);
    publish(residual_tick_, round_within(reach), &PatternChartController::residualTickIntervalChanged);
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

void PatternChartController::setDSpacing(bool on) {
    if (on != d_spacing_) {
        finishAnimation();
        d_spacing_ = on;
        x_min_.reset();  // another axis: the view starts over
        x_max_.reset();
        y_min_.reset();
        y_max_.reset();
        if (experiment_) {
            experiment_->setChartAxis(this, axis());
        }
        emit dSpacingChanged();
        invalidate();
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

void PatternChartController::setHiddenFitsRange(bool on) {
    if (on != hidden_fits_range_) {
        hidden_fits_range_ = on;
        emit hiddenFitsRangeChanged();
        if (!hidden_.isEmpty()) {
            invalidate();
        }
    }
}

void PatternChartController::refresh() {
    dirty_ = false;
    if (report_) {
        // The report's presentation as the model holds it; none for an experiment the model does not hold.
        const edi::ReportPattern* pattern = report_->pattern(report_experiment_);
        shown_ = pattern != nullptr ? pattern->presentation : edi::PatternPresentation{};
    } else {
        static const edi::PatternSource kNothing;
        const edi::PatternSource& source = experiment_ ? experiment_->patternSource(axis()) : kNothing;
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
    const edi::PatternSeries* background = nullptr;
    const edi::PatternSeries* residual = nullptr;
    std::vector<QList<QPointF>> ticks(static_cast<std::size_t>(bragg_series_.size()));
    std::vector<const edi::PatternSeries*> structure_curves;
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
    };
    int rows = 0;
    for (const edi::PatternSeries& series : shown_.series) {
        switch (series.kind) {
            case edi::SeriesKind::Measured: measured = &series; break;
            case edi::SeriesKind::Calculated: calculated = &series; break;
            case edi::SeriesKind::Background: background = &series; break;
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
        y_step = y_scale_ == Log10 ? std::max(1.0, std::ceil((y_high - y_low) / kTicks)) : round_step(y_low, y_high);
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
        y_step = round_step(y_low, y_high);
        y_anchor = std::ceil(y_low / y_step) * y_step;
    }
    // While a parameter's slider is held (the owner, 2026-10-25), a fitted range holds while the calculated curve stays
    // inside it and grows only when the curve leaves it; letting the slider go, another experiment, dataset, axis,
    // scale or x range, a fit and a reset fit it again.
    if (fitted && !animating_ && !report_) {
        const edi::PatternSource* source = experiment_ ? &experiment_->patternSource(axis()) : nullptr;
        HeldRange now{experiment_, source != nullptr ? source->meas : nullptr, presented_x_, y_scale_, x_low,
                      x_high, y_low, y_high};
        if (held_range_ && experiment_ && experiment_->adjusting() && held_range_->experiment == now.experiment &&
            same_values(held_range_->measured, now.measured) && held_range_->axis == now.axis && held_range_->scale == now.scale &&
            held_range_->x_min == now.x_min && held_range_->x_max == now.x_max) {
            now.low = y_low = std::min(y_low, held_range_->low);
            now.high = y_high = std::max(y_high, held_range_->high);
            y_step = y_scale_ == Log10 ? std::max(1.0, std::ceil((y_high - y_low) / kTicks)) : round_step(y_low, y_high);
            y_anchor = y_scale_ == Log10 ? y_low : std::ceil(y_low / y_step) * y_step;
        }
        held_range_ = now;
    } else if (!fitted) {
        held_range_.reset();
    }
    const double x_step = round_step(x_low, x_high);
    publish(shown_x_min_, x_low, &PatternChartController::xMinChanged);
    publish(shown_x_max_, x_high, &PatternChartController::xMaxChanged);
    publish(shown_y_min_, y_low, &PatternChartController::yMinChanged);
    publish(shown_y_max_, y_high, &PatternChartController::yMaxChanged);
    scaleResidual();
    publish(x_tick_, x_step, &PatternChartController::xTickIntervalChanged);
    publish(x_anchor_, std::ceil(x_low / x_step) * x_step, &PatternChartController::xTickAnchorChanged);
    publish(y_tick_, y_step, &PatternChartController::yTickIntervalChanged);
    publish(y_anchor_, y_anchor, &PatternChartController::yTickAnchorChanged);

    // The measured style (the owner, 2026-10-22): the line, the markers with their bars, or the band, measured ± s.u.
    // with the residual drawn the same way. A report's chart draws all but the band, as the report does.
    const bool band = measured_drawing_ == QLatin1String("band") && !report_;
    const bool line = report_ || measured_drawing_ == QLatin1String("line") || measured_drawing_ == QLatin1String("linePoints");
    const bool marks = report_ || measured_drawing_ == QLatin1String("points") || measured_drawing_ == QLatin1String("linePoints");
    replace(measured_series_, measured != nullptr && line ? points_of(*measured) : QList<QPointF>());
    if (measured_layer_) {
        QList<QPointF> points;
        QList<double> low, high;
        if (measured != nullptr && marks) {
            for (std::size_t i = 0; i < measured->points.size(); ++i) {
                if (!std::isnan(measured->points[i].y)) {
                    points.append(QPointF(measured->points[i].x, measured->points[i].y));
                    low.append(measured->bar_low[i]);
                    high.append(measured->bar_high[i]);
                }
            }
        }
        measured_layer_->setData(points, low, high);
    }
    replace(calculated_series_, calculated != nullptr ? points_of(*calculated) : QList<QPointF>());
    replace(background_series_, background != nullptr ? points_of(*background) : QList<QPointF>());
    replace(residual_series_, residual != nullptr && !band ? points_of(*residual) : QList<QPointF>());
    // A band: its area and its two edges, each point's ends (the presentation gives a point without a finite s.u. its
    // ends at the point, so only a finite interval reaching below the log scale's domain takes the pane's bottom).
    const auto fill_band = [&](const edi::PatternSeries* series, std::size_t pane, double floor, double lift) {
        const BandSeries& target = band_series_[pane];
        QList<QPointF> top, bottom;
        if (band && series != nullptr) {
            const double nan = std::numeric_limits<double>::quiet_NaN();
            for (std::size_t k = 0; k < series->points.size(); ++k) {
                const double x = series->points[k].x, y = series->points[k].y;
                if (!std::isfinite(y)) {
                    top.append(QPointF(nan, nan));
                    bottom.append(QPointF(nan, nan));
                    continue;
                }
                const double high = k < series->bar_high.size() && std::isfinite(series->bar_high[k]) ? series->bar_high[k] : y;
                const double low = k < series->bar_low.size() ? series->bar_low[k] : y;
                top.append(QPointF(x, high));
                bottom.append(QPointF(x, std::isfinite(low) ? low : floor));
            }
        }
        std::vector<double> base;
        base.reserve(static_cast<std::size_t>(bottom.size()));
        for (const QPointF& point : bottom) {
            base.push_back(point.y());
        }
        const AreaEdges area = area_edges(top, base, floor, lift);
        replace(target.upper, area.upper);
        replace(target.lower, area.lower);
        replace(target.top, top);
        replace(target.bottom, bottom);
    };
    fill_band(measured, 0, shown_y_min_, plot_height_ > 0.0 ? 0.05 * (shown_y_max_ - shown_y_min_) / plot_height_ : 0.0);
    fill_band(residual, 1, residual_min_, 0.0);
    for (std::size_t place = 0; place < ticks.size(); ++place) {
        replace(bragg_series_[static_cast<qsizetype>(place)], ticks[place]);
    }
    // Each structure curve: its area between the background and the curve, and its outline.
    QList<QColor> curve_colours, curve_fills;
    for (std::size_t index = 0; index < structure_curves.size(); ++index) {
        const edi::PatternSeries& series = *structure_curves[index];
        const QColor fill = colour_of(series.style);
        QColor outline = fill;
        outline.setAlphaF(1.0F);
        curve_colours.append(outline);
        curve_fills.append(fill);
        if (static_cast<qsizetype>(index) >= structure_series_.size()) {
            continue;  // the chart makes its series and hands them over, which draws again
        }
        // A background the log scale cannot show (zero or less) is below the axis: the fill reaches the axis there.
        const double lift = plot_height_ > 0.0 ? 0.05 * (shown_y_max_ - shown_y_min_) / plot_height_ : 0.0;
        const QList<QPointF> curve = points_of(series);
        const AreaEdges area = area_edges(curve, series.bar_low, shown_y_min_, lift);
        const QList<QPointF>& upper = area.upper;
        const QList<QPointF>& lower = area.lower;
        const StructureSeries& target = structure_series_[static_cast<qsizetype>(index)];
        replace(target.upper, upper);
        replace(target.lower, lower);
        replace(target.outline, curve);
    }
    for (qsizetype index = static_cast<qsizetype>(structure_curves.size()); index < structure_series_.size(); ++index) {
        replace(structure_series_[index].upper, {});
        replace(structure_series_[index].lower, {});
        replace(structure_series_[index].outline, {});
    }
    publish(structure_curve_fills_, curve_fills, &PatternChartController::structureCurveFillsChanged);
    publish(structure_curve_colors_, curve_colours, &PatternChartController::structureCurveColorsChanged);
    publish(has_calculated_, calculated != nullptr, &PatternChartController::hasCalculatedChanged);
    // More structures than tick series: the chart makes the rest, each handed over in turn.
    if (const auto count = static_cast<qsizetype>(std::ranges::count_if(table, [](const edi::SeriesStyle& style) { return style.key.starts_with("bragg."); }));
        count != bragg_colour_count_) {
        bragg_colour_count_ = count;
        emit braggColorsChanged();
    }

    QList<ChartBandModel::Band> bands;
    for (const edi::ExcludedBand& band : shown_.excluded) {
        bands.append({band.x_min, band.x_max});
    }
    double bragg_height = 0.0;
    for (const edi::PaneLayout& pane : shown_.layout) {
        if (pane.pane == edi::Pane::Bragg) {
            bragg_height = pane.fixed_px;
        }
    }
    excluded_bands_->setBands(bands);
    legend_->setEntries(legend);
    publish(bragg_rows_, rows, &PatternChartController::braggRowsChanged);
    publish(bragg_height_, bragg_height, &PatternChartController::braggHeightChanged);
    publish(has_residual_, residual != nullptr, &PatternChartController::hasResidualChanged);
    publish(has_data_, measured != nullptr || calculated != nullptr, &PatternChartController::hasDataChanged);
    publish(current_, shown_.current, &PatternChartController::currentChanged);
    publish(d_available_, report_ != nullptr || (experiment_ && experiment_->patternSource().d_available),
            &PatternChartController::dAvailableChanged);
    publish(x_title_, QString::fromStdString(shown_.x.title), &PatternChartController::xTitleChanged);
    // A y title as its coloured pieces, each series' word in its colour (the legend box being hidden by default);
    // the plain title when it has none.
    const auto styled = [&colour_of](const edi::AxisDescription& axis) {
        if (axis.segments.empty()) {
            return QString::fromStdString(axis.title).toHtmlEscaped();
        }
        QString text;
        for (const edi::TitleSegment& segment : axis.segments) {
            const QString piece = QString::fromStdString(segment.text).toHtmlEscaped();
            text += segment.style.empty() ? piece
                                          : QStringLiteral("<font color=\"%1\">%2</font>")
                                                .arg(colour_of(segment.style).name(QColor::HexRgb), piece);
        }
        return text;
    };
    publish(y_title_, styled(shown_.y_main), &PatternChartController::yTitleChanged);
    publish(residual_title_, styled(shown_.y_residual), &PatternChartController::residualTitleChanged);
    // Each Bragg row's label at its left: the structure's name in its colour, at the row's centre.
    QList<BraggLabel> labels;
    for (const edi::BraggRowLabel& label : shown_.bragg_labels) {
        // Hidden with its row's ticks, which share its style.
        const auto ticks = std::find_if(shown_.series.begin(), shown_.series.end(), [&label](const edi::PatternSeries& series) {
            return series.kind == edi::SeriesKind::BraggTicks && series.style == label.style;
        });
        labels.append({QString::fromStdString(label.text), colour_of(label.style), label.centre,
                       ticks != shown_.series.end() && hiddenId(ticks->id)});
    }
    publish(bragg_labels_, labels, &PatternChartController::braggLabelsChanged);
    const bool subtractable = !report_ && experiment_ != nullptr && edi::has_background(*experiment_->experiment());
    publish(background_available_, subtractable, &PatternChartController::backgroundAvailableChanged);
    // Past the palette's own colours the count sets every experiment's colour, the measured key's too.
    if (const std::size_t count = experiment_ ? experiment_->colourCount() : 1; count != colour_count_) {
        colour_count_ = count;
        emit measuredColorChanged();
    }
    publish(measured_style_,
            measured != nullptr ? QString::fromStdString(measured->style) : QStringLiteral("meas.0"),
            &PatternChartController::measuredColorChanged);
    ++revision_;
    emit revisionChanged();
}

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
    const double low = animating_ ? to_[0] : shown_x_min_, high = animating_ ? to_[1] : shown_x_max_;
    stopAnimation();
    const double factor = std::pow(kWheelFactor, angleDelta / kWheelNotch);
    animateTo(anchor - (anchor - low) * factor, anchor + (high - anchor) * factor, y_min_, y_max_);
}

void PatternChartController::panBy(double dx) {
    if (report_ || plot_width_ <= 0.0 || dx == 0.0) {
        return;
    }
    // From where a running animation is going, as a notch is.
    const double low = animating_ ? to_[0] : shown_x_min_, high = animating_ ? to_[1] : shown_x_max_;
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
    return found ? QString::fromStdString(edi::hover_text(experiment_->patternSource(axis()), *found->series, found->point))
                 : QString();
}

QString PatternChartController::hoverReadout(double x, double y, int pane, double height) const {
    const auto found = nearest(x, y, pane, height, kHoverDistance);
    if (!found) {
        return {};
    }
    QStringList lines;
    for (const edi::HoverLine& line :
         edi::hover_readout(experiment_->patternSource(axis()), *found->series, found->point)) {
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
