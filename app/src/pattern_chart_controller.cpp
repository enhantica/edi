// SPDX-License-Identifier: BSD-3-Clause
#include "pattern_chart_controller.hpp"

#include <algorithm>
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

void replace(const QPointer<QXYSeries>& target, const QList<QPointF>& list) {
    if (target) {
        target->replace(list);
    }
}

}  // namespace

PatternChartController::PatternChartController(QObject* parent)
    : QObject(parent), legend_(new ChartLegendModel(this)), excluded_bands_(new ChartBandModel(this)) {
    // A series the QML just handed over is filled at once.
    for (const auto changed :
         {&PatternChartController::measuredSeriesChanged, &PatternChartController::measuredLayerChanged,
          &PatternChartController::calculatedSeriesChanged, &PatternChartController::backgroundSeriesChanged,
          &PatternChartController::residualSeriesChanged, &PatternChartController::braggSeries0Changed,
          &PatternChartController::braggSeries1Changed, &PatternChartController::braggSeries2Changed}) {
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

void PatternChartController::setAnimationDuration(int milliseconds) {
    milliseconds = std::max(0, milliseconds);
    if (milliseconds != animation_duration_) {
        animation_duration_ = milliseconds;
        emit animationDurationChanged();
    }
}

void PatternChartController::animateTo(std::optional<double> x_min, std::optional<double> x_max,
                                       std::optional<double> y_min, std::optional<double> y_max) {
    finishAnimation();
    const double from[4] = {shown_x_min_, shown_x_max_, shown_y_min_, shown_y_max_};
    x_min_ = x_min;
    x_max_ = x_max;
    y_min_ = y_min;
    y_max_ = y_max;
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
    if (!animating_) {
        return;
    }
    animating_ = false;
    animation_.stop();
    x_min_ = target_[0];
    x_max_ = target_[1];
    y_min_ = target_[2];
    y_max_ = target_[3];
    invalidate();
}

void PatternChartController::publishColors() {
    emit measuredColorChanged();
    emit calculatedColorChanged();
    emit backgroundColorChanged();
    emit residualColorChanged();
    emit excludedColorChanged();
    emit braggColor0Changed();
    emit braggColor1Changed();
    emit braggColor2Changed();
}

void PatternChartController::setExperiment(ExperimentViewModel* experiment) {
    if (experiment == experiment_) {
        return;
    }
    if (experiment_) {
        disconnect(experiment_, nullptr, this, nullptr);
    }
    experiment_ = experiment;
    if (experiment_) {
        connect(experiment_, &ExperimentViewModel::patternSourceChanged, this, &PatternChartController::invalidate);
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
    invalidate();
}

void PatternChartController::setActive(bool active) {
    if (active != active_) {
        active_ = active;
        // A hidden chart draws nothing: a running animation ends at its target, left dirty, and is drawn when
        // the chart is shown again.
        if (!active_) {
            finishAnimation();
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

void PatternChartController::setPlotWidth(qreal width) {
    if (width != plot_width_) {
        plot_width_ = width;
        emit plotWidthChanged();
        invalidate();
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

void PatternChartController::cycleYScale() {
    setYScale(y_scale_ == Linear ? Sqrt : y_scale_ == Sqrt ? Log10 : Linear);
}

QColor PatternChartController::color(const QString& styleKey) const {
    const std::string key = styleKey.toStdString();
    for (const edi::SeriesStyle& style : edi::pattern_style_table()) {
        if (style.key == key) {
            QColor out(QString::fromStdString(dark_ ? style.dark : style.light));
            out.setAlphaF(static_cast<float>(style.opacity));
            return out;
        }
    }
    return {};
}

void PatternChartController::invalidate() {
    dirty_ = true;
    if (active_) {
        refresh();
    }
}

edi::PatternView PatternChartController::view() const {
    edi::PatternView view;
    view.x_min = x_min_;
    view.x_max = x_max_;
    view.columns = plot_width_ > 0.0 ? edi::pixel_columns(plot_width_, device_pixel_ratio_) : 0;
    view.y_scale = core_scale(y_scale_);
    return view;
}

void PatternChartController::refresh() {
    dirty_ = false;
    static const edi::PatternSource kNothing;
    const edi::PatternSource& source = experiment_ ? experiment_->patternSource() : kNothing;
    shown_ = edi::present_pattern(source, view());

    const edi::PatternSeries* measured = nullptr;
    const edi::PatternSeries* calculated = nullptr;
    const edi::PatternSeries* background = nullptr;
    const edi::PatternSeries* residual = nullptr;
    QList<QPointF> ticks[3];
    QList<ChartLegendModel::Entry> legend;
    const auto entry = [&](const edi::PatternSeries& series) {
        const bool bragg = series.kind == edi::SeriesKind::BraggTicks;
        const bool thin = series.kind == edi::SeriesKind::Background;
        legend.append({QString::fromStdString(series.label), color(QString::fromStdString(series.style)),
                       bragg ? QStringLiteral("│") : thin ? QStringLiteral("─") : QStringLiteral("━"), bragg});
    };
    int rows = 0;
    for (const edi::PatternSeries& series : shown_.series) {
        switch (series.kind) {
            case edi::SeriesKind::Measured: measured = &series; break;
            case edi::SeriesKind::Calculated: calculated = &series; break;
            case edi::SeriesKind::Background: background = &series; break;
            case edi::SeriesKind::Residual: residual = &series; break;
            case edi::SeriesKind::BraggTicks: {
                // The three tick series are the palette's three colours; a fourth structure shares the
                // first one's colour and keeps its own row.
                const int slot = series.style.empty() ? 0 : (series.style.back() - '0') % 3;
                ticks[slot] += points_of(series);
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

    replace(measured_series_, measured != nullptr ? points_of(*measured) : QList<QPointF>());
    if (measured_layer_) {
        QList<QPointF> points;
        QList<double> low, high;
        if (measured != nullptr) {
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
    replace(residual_series_, residual != nullptr ? points_of(*residual) : QList<QPointF>());
    replace(bragg_series_0_, ticks[0]);
    replace(bragg_series_1_, ticks[1]);
    replace(bragg_series_2_, ticks[2]);

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
    publish(x_title_, QString::fromStdString(shown_.x.title), &PatternChartController::xTitleChanged);
    publish(y_title_, QString::fromStdString(shown_.y_main.title), &PatternChartController::yTitleChanged);
    publish(residual_title_, QString::fromStdString(shown_.y_residual.title),
            &PatternChartController::residualTitleChanged);
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
    if (plot_width_ <= 0.0 || plot_height_ <= 0.0 || x0 == x1 || y0 == y1) {
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
    if (plot_width_ <= 0.0 || angleDelta == 0) {
        return;
    }
    // From where a running animation is going, so notches in quick succession add up.
    const double anchor = xOf(x);
    finishAnimation();
    const double factor = std::pow(kWheelFactor, angleDelta / kWheelNotch);
    animateTo(anchor - (anchor - shown_x_min_) * factor, anchor + (shown_x_max_ - anchor) * factor, y_min_, y_max_);
}

void PatternChartController::panBy(double dx) {
    if (plot_width_ <= 0.0 || dx == 0.0) {
        return;
    }
    finishAnimation();
    const double shift = dx / plot_width_ * (shown_x_max_ - shown_x_min_);
    x_min_ = shown_x_min_ - shift;
    x_max_ = shown_x_max_ - shift;
    invalidate();
}

void PatternChartController::reset() { animateTo(std::nullopt, std::nullopt, std::nullopt, std::nullopt); }

QString PatternChartController::hoverAt(double x, double y, int pane, double height) const {
    const auto found = nearest(x, y, pane, height, std::numeric_limits<double>::infinity());
    return found ? QString::fromStdString(edi::hover_text(experiment_->patternSource(), *found->series, found->point))
                 : QString();
}

QString PatternChartController::hoverReadout(double x, double y, int pane, double height) const {
    const auto found = nearest(x, y, pane, height, kHoverDistance);
    if (!found) {
        return {};
    }
    QStringList lines;
    for (const edi::HoverLine& line :
         edi::hover_readout(experiment_->patternSource(), *found->series, found->point)) {
        const QString text = QString::fromStdString(line.text).toHtmlEscaped();
        lines.append(line.style.empty() ? text
                                        : QStringLiteral("<span style=\"color:%1\">%2</span>")
                                              .arg(color(QString::fromStdString(line.style)).name(QColor::HexRgb), text));
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

}  // namespace edi_app
