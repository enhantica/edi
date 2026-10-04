// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_PATTERN_CHART_CONTROLLER_HPP
#define EDI_APP_PATTERN_CHART_CONTROLLER_HPP

#include <QColor>
#include <QList>
#include <QObject>
#include <QPointF>
#include <QPointer>
#include <QString>
#include <QVariantAnimation>
#include <QtGraphs/QXYSeries>
#include <QtQml/qqmlregistration.h>
#include <optional>

#include "chart_models.hpp"
#include "edi/presentation.hpp"
#include "experiment_view_model.hpp"
#include "measured_layer.hpp"

namespace edi_app {

// One pattern chart (edi ADR-0017 §15, ADR-0021). It draws what the core's edi::present_pattern
// returns and computes nothing: it owns the view (the x range, the main y range, the plot width, the y
// scale, the theme), asks the core for the presentation of the experiment's captured pattern, and
// replaces the QML-declared series with typed point lists. From a publication to QXYSeries::replace
// every step is here in C++; no QVariant and no JavaScript per point or per series.
class PatternChartController : public QObject {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(edi_app::ExperimentViewModel* experiment READ experiment WRITE setExperiment NOTIFY experimentChanged)
    // The chart is shown: a hidden chart is only marked dirty, and refreshed when it is shown again.
    Q_PROPERTY(bool active READ active WRITE setActive NOTIFY activeChanged)
    Q_PROPERTY(bool dark READ dark WRITE setDark NOTIFY darkChanged)
    // The main plot area, in logical pixels, and the window's device pixel ratio: the decimation's width.
    Q_PROPERTY(qreal plotWidth READ plotWidth WRITE setPlotWidth NOTIFY plotWidthChanged)
    Q_PROPERTY(qreal plotHeight READ plotHeight WRITE setPlotHeight NOTIFY plotHeightChanged)
    // The residual plot area's height: the residual's y range gives one intensity unit the height it has in
    // the main pane (edi ADR-0017 §15).
    Q_PROPERTY(qreal residualPlotHeight READ residualPlotHeight WRITE setResidualPlotHeight NOTIFY
                   residualPlotHeightChanged)
    Q_PROPERTY(qreal devicePixelRatio READ devicePixelRatio WRITE setDevicePixelRatio NOTIFY devicePixelRatioChanged)
    Q_PROPERTY(YScale yScale READ yScale WRITE setYScale NOTIFY yScaleChanged)
    // How long a box zoom, a wheel zoom and a reset move the axis ranges (easydiffractionbeta's
    // ChartView.SeriesAnimations, EaStyle.Times.chartAnimation), in milliseconds; 0: at once.
    Q_PROPERTY(int animationDuration READ animationDuration WRITE setAnimationDuration NOTIFY animationDurationChanged)
    // The QML-declared series this controller fills.
    Q_PROPERTY(QXYSeries* measuredSeries MEMBER measured_series_ NOTIFY measuredSeriesChanged)
    Q_PROPERTY(edi_app::MeasuredLayer* measuredLayer MEMBER measured_layer_ NOTIFY measuredLayerChanged)
    Q_PROPERTY(QXYSeries* calculatedSeries MEMBER calculated_series_ NOTIFY calculatedSeriesChanged)
    Q_PROPERTY(QXYSeries* backgroundSeries MEMBER background_series_ NOTIFY backgroundSeriesChanged)
    Q_PROPERTY(QXYSeries* residualSeries MEMBER residual_series_ NOTIFY residualSeriesChanged)
    Q_PROPERTY(QXYSeries* braggSeries0 MEMBER bragg_series_0_ NOTIFY braggSeries0Changed)
    Q_PROPERTY(QXYSeries* braggSeries1 MEMBER bragg_series_1_ NOTIFY braggSeries1Changed)
    Q_PROPERTY(QXYSeries* braggSeries2 MEMBER bragg_series_2_ NOTIFY braggSeries2Changed)
    // What the three panes show.
    Q_PROPERTY(double xMin READ xMin NOTIFY xMinChanged)
    Q_PROPERTY(double xMax READ xMax NOTIFY xMaxChanged)
    Q_PROPERTY(double yMin READ yMin NOTIFY yMinChanged)
    Q_PROPERTY(double yMax READ yMax NOTIFY yMaxChanged)
    Q_PROPERTY(double residualMin READ residualMin NOTIFY residualMinChanged)
    Q_PROPERTY(double residualMax READ residualMax NOTIFY residualMaxChanged)
    // The ticks (edi ADR-0017 §15): round values; five on the main y axis and three on the residual's (top, 0,
    // bottom) when the ranges are the fitted ones, about five along x.
    Q_PROPERTY(double xTickInterval READ xTickInterval NOTIFY xTickIntervalChanged)
    Q_PROPERTY(double xTickAnchor READ xTickAnchor NOTIFY xTickAnchorChanged)
    Q_PROPERTY(double yTickInterval READ yTickInterval NOTIFY yTickIntervalChanged)
    Q_PROPERTY(double yTickAnchor READ yTickAnchor NOTIFY yTickAnchorChanged)
    Q_PROPERTY(double residualTickInterval READ residualTickInterval NOTIFY residualTickIntervalChanged)
    Q_PROPERTY(int braggRows READ braggRows NOTIFY braggRowsChanged)
    Q_PROPERTY(double braggHeight READ braggHeight NOTIFY braggHeightChanged)
    Q_PROPERTY(bool hasResidual READ hasResidual NOTIFY hasResidualChanged)
    Q_PROPERTY(bool hasData READ hasData NOTIFY hasDataChanged)
    Q_PROPERTY(bool current READ current NOTIFY currentChanged)
    Q_PROPERTY(QString xTitle READ xTitle NOTIFY xTitleChanged)
    Q_PROPERTY(QString yTitle READ yTitle NOTIFY yTitleChanged)
    Q_PROPERTY(QString residualTitle READ residualTitle NOTIFY residualTitleChanged)
    // The legend's rows and the excluded bands, as typed models (chart_models.hpp): the controller replaces
    // their rows at each refresh.
    Q_PROPERTY(edi_app::ChartLegendModel* legend READ legend CONSTANT)
    Q_PROPERTY(edi_app::ChartBandModel* excludedBands READ excludedBands CONSTANT)
    // The style table's colours for the theme and the experiment (edi::pattern_style_table).
    Q_PROPERTY(QColor measuredColor READ measuredColor NOTIFY measuredColorChanged)
    Q_PROPERTY(QColor calculatedColor READ calculatedColor NOTIFY calculatedColorChanged)
    Q_PROPERTY(QColor backgroundColor READ backgroundColor NOTIFY backgroundColorChanged)
    Q_PROPERTY(QColor residualColor READ residualColor NOTIFY residualColorChanged)
    Q_PROPERTY(QColor excludedColor READ excludedColor NOTIFY excludedColorChanged)
    // The three tick colours, by the structure's place in the project (the palette of ADR-0017 §8).
    Q_PROPERTY(QColor braggColor0 READ braggColor0 NOTIFY braggColor0Changed)
    Q_PROPERTY(QColor braggColor1 READ braggColor1 NOTIFY braggColor1Changed)
    Q_PROPERTY(QColor braggColor2 READ braggColor2 NOTIFY braggColor2Changed)
    // How many times the series were replaced: what a test observes at a frame's synchronisation.
    Q_PROPERTY(int revision READ revision NOTIFY revisionChanged)

   public:
    enum YScale { Linear, Sqrt, Log10 };
    Q_ENUM(YScale)

    explicit PatternChartController(QObject* parent = nullptr);

    ExperimentViewModel* experiment() const { return experiment_; }
    void setExperiment(ExperimentViewModel* experiment);
    bool active() const { return active_; }
    void setActive(bool active);
    bool dark() const { return dark_; }
    void setDark(bool dark);
    qreal plotWidth() const { return plot_width_; }
    void setPlotWidth(qreal width);
    qreal plotHeight() const { return plot_height_; }
    void setPlotHeight(qreal height);
    qreal residualPlotHeight() const { return residual_plot_height_; }
    void setResidualPlotHeight(qreal height);
    qreal devicePixelRatio() const { return device_pixel_ratio_; }
    void setDevicePixelRatio(qreal ratio);
    YScale yScale() const { return y_scale_; }
    void setYScale(YScale scale);
    int animationDuration() const { return animation_duration_; }
    void setAnimationDuration(int milliseconds);

    double xMin() const { return shown_x_min_; }
    double xMax() const { return shown_x_max_; }
    double yMin() const { return shown_y_min_; }
    double yMax() const { return shown_y_max_; }
    double residualMin() const { return residual_min_; }
    double residualMax() const { return residual_max_; }
    double xTickInterval() const { return x_tick_; }
    double xTickAnchor() const { return x_anchor_; }
    double yTickInterval() const { return y_tick_; }
    double yTickAnchor() const { return y_anchor_; }
    double residualTickInterval() const { return residual_tick_; }
    int braggRows() const { return bragg_rows_; }
    double braggHeight() const { return bragg_height_; }
    bool hasResidual() const { return has_residual_; }
    bool hasData() const { return has_data_; }
    bool current() const { return current_; }
    QString xTitle() const { return x_title_; }
    QString yTitle() const { return y_title_; }
    QString residualTitle() const { return residual_title_; }
    ChartLegendModel* legend() const { return legend_; }
    ChartBandModel* excludedBands() const { return excluded_bands_; }
    QColor measuredColor() const { return color(measured_style_); }
    QColor calculatedColor() const { return color(QStringLiteral("calc")); }
    QColor backgroundColor() const { return color(QStringLiteral("bkg")); }
    QColor residualColor() const { return color(QStringLiteral("resid")); }
    QColor excludedColor() const { return color(QStringLiteral("excluded")); }
    QColor braggColor0() const { return color(QStringLiteral("bragg.0")); }
    QColor braggColor1() const { return color(QStringLiteral("bragg.1")); }
    QColor braggColor2() const { return color(QStringLiteral("bragg.2")); }
    int revision() const { return revision_; }

    // A style key's colour in the current theme, with the table's opacity.
    Q_INVOKABLE QColor color(const QString& styleKey) const;
    Q_INVOKABLE void cycleYScale();
    // The pointer, in logical pixels inside the main plot area (edi ADR-0017 §15).
    Q_INVOKABLE void zoomTo(double x0, double x1, double y0, double y1);  // a dragged box
    Q_INVOKABLE void wheelAt(double x, int angleDelta);                   // one notch is 120
    Q_INVOKABLE void panBy(double dx);                                    // a drag to the right is positive
    Q_INVOKABLE void reset();
    // The nearest presented point's text; `pane` is 0 main, 1 Bragg, 2 residual, and `height` that pane's.
    Q_INVOKABLE QString hoverAt(double x, double y, int pane, double height) const;
    // The read-out of the point under the pointer as diffraction-lib's plotly chart shows it
    // (edi::hover_readout): rich text, a line per value, each in its series' colour. Only a presented point
    // within plotly's default hover distance of the pointer (kHoverDistance pixels; a Bragg tick by its x
    // alone) is read; otherwise empty.
    Q_INVOKABLE QString hoverReadout(double x, double y, int pane, double height) const;
    // Where that point is in the pane, in the pointer's coordinates, for the label to sit by; (-1, -1)
    // when none is near. A Bragg tick's is at the pointer's height.
    Q_INVOKABLE QPointF hoverPoint(double x, double y, int pane, double height) const;
    // An axis label: the original value of a display value Qt Graphs printed on `scale`. The scale is an
    // argument so that a label bound to `yScale` is printed again when the scale changes.
    Q_INVOKABLE QString axisLabel(const QString& text, YScale scale) const;
    Q_INVOKABLE void refresh();

   signals:
    void experimentChanged();
    void activeChanged();
    void darkChanged();
    void plotWidthChanged();
    void plotHeightChanged();
    void residualPlotHeightChanged();
    void devicePixelRatioChanged();
    void yScaleChanged();
    void animationDurationChanged();
    void measuredSeriesChanged();
    void measuredLayerChanged();
    void calculatedSeriesChanged();
    void backgroundSeriesChanged();
    void residualSeriesChanged();
    void braggSeries0Changed();
    void braggSeries1Changed();
    void braggSeries2Changed();
    void xMinChanged();
    void xMaxChanged();
    void yMinChanged();
    void yMaxChanged();
    void residualMinChanged();
    void residualMaxChanged();
    void xTickIntervalChanged();
    void xTickAnchorChanged();
    void yTickIntervalChanged();
    void yTickAnchorChanged();
    void residualTickIntervalChanged();
    void braggRowsChanged();
    void braggHeightChanged();
    void hasResidualChanged();
    void hasDataChanged();
    void currentChanged();
    void xTitleChanged();
    void yTitleChanged();
    void residualTitleChanged();
    void revisionChanged();
    void measuredColorChanged();
    void calculatedColorChanged();
    void backgroundColorChanged();
    void residualColorChanged();
    void excludedColorChanged();
    void braggColor0Changed();
    void braggColor1Changed();
    void braggColor2Changed();

   private:
    void invalidate();
    // One property's value and its own signal: only what changed notifies (the app's per-property rule).
    template <typename T>
    void publish(T& member, const T& value, void (PatternChartController::*changed)()) {
        if (!(member == value)) {
            member = value;
            emit(this->*changed)();
        }
    }
    void publishColors();
    void scaleResidual();
    edi::PatternView view() const;
    // The view moves to these ranges (unset: fitted) over `animationDuration`. Each frame is an ordinary
    // refresh at that frame's ranges — the pattern presented and decimated for them — so no point of a frame's
    // range is missing, and a frame costs what any refresh costs. A hidden chart, or a duration of 0, moves at
    // once.
    void animateTo(std::optional<double> x_min, std::optional<double> x_max, std::optional<double> y_min,
                   std::optional<double> y_max);
    // A running animation ends at once at its target: what changes the view another way starts from there.
    void finishAnimation();
    void animationFrame(double progress);
    // The presented point nearest the pointer in `pane` and no farther than `within` pixels, or none.
    struct Nearest {
        const edi::PatternSeries* series = nullptr;
        std::size_t point = 0;
        QPointF at;
    };
    std::optional<Nearest> nearest(double x, double y, int pane, double height, double within) const;
    // Plotly's default `hoverdistance`, which diffraction-lib's charts keep.
    static constexpr double kHoverDistance = 20.0;
    double xOf(double pixel) const;

    QPointer<ExperimentViewModel> experiment_;
    bool active_ = true, dark_ = false, dirty_ = true;
    qreal plot_width_ = 0.0, plot_height_ = 0.0, residual_plot_height_ = 0.0, device_pixel_ratio_ = 1.0;
    YScale y_scale_ = Linear;
    // The view: unset means the data's full x range, and y ranges fitted to what is presented.
    std::optional<double> x_min_, x_max_, y_min_, y_max_;
    // The animation: its ranges at the start and the end, as shown, and the view it ends in.
    QVariantAnimation animation_;
    int animation_duration_ = 250;
    bool animating_ = false;
    double from_[4] = {}, to_[4] = {};
    std::optional<double> target_[4];
    QPointer<QXYSeries> measured_series_, calculated_series_, background_series_, residual_series_,
        bragg_series_0_, bragg_series_1_, bragg_series_2_;
    QPointer<MeasuredLayer> measured_layer_;
    edi::PatternPresentation shown_;
    double shown_x_min_ = 0.0, shown_x_max_ = 1.0, shown_y_min_ = 0.0, shown_y_max_ = 1.0;
    double residual_min_ = -1.0, residual_max_ = 1.0, bragg_height_ = 0.0;
    double x_tick_ = 0.0, x_anchor_ = 0.0, y_tick_ = 0.0, y_anchor_ = 0.0, residual_tick_ = 0.0;
    int bragg_rows_ = 0, revision_ = 0;
    bool has_residual_ = false, has_data_ = false, current_ = false;
    QString x_title_, y_title_, residual_title_, measured_style_ = QStringLiteral("meas.0");
    ChartLegendModel* legend_;
    ChartBandModel* excluded_bands_;
};

}  // namespace edi_app

#endif  // EDI_APP_PATTERN_CHART_CONTROLLER_HPP
