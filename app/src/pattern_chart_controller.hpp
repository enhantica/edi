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
#include <array>
#include <optional>
#include <vector>

#include "chart_models.hpp"
#include "edi/presentation.hpp"
#include "experiment_view_model.hpp"
#include "measured_layer.hpp"
#include "report_view_model.hpp"

namespace edi_app {

// One Bragg row's label (edi::BraggRowLabel): the structure's name, its colour, and the row's centre in rows from the
// bottom. QML reads a list of them as an array.
struct BraggLabel {
    Q_GADGET
    QML_VALUE_TYPE(braggLabel)
    Q_PROPERTY(QString text MEMBER text CONSTANT)
    Q_PROPERTY(QColor color MEMBER color CONSTANT)
    Q_PROPERTY(double centre MEMBER centre CONSTANT)

   public:
    QString text;
    QColor color;
    double centre = 0.0;
    bool operator==(const BraggLabel&) const = default;
};

// One pattern chart (edi ADR-0017 §15, ADR-0021). It draws what the core's edi::present_pattern
// returns and computes nothing: it owns the view (the x range, the main y range, the plot width, the y
// scale, the theme), asks the core for the presentation of the experiment's captured pattern, and
// replaces the QML-declared series with typed point lists. From a publication to QXYSeries::replace
// every step is here in C++; no QVariant and no JavaScript per point or per series.
class PatternChartController : public QObject {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(edi_app::ExperimentViewModel* experiment READ experiment WRITE setExperiment NOTIFY experimentChanged)
    // The report's input (edi ADR-0036): with `report` set the chart draws the report model's presentation of
    // `reportExperiment` as it is, instead of presenting an experiment. It has no view to change, so the zoom, the
    // pan and the hover read-out do nothing.
    Q_PROPERTY(edi_app::ReportViewModel* report READ report WRITE setReport NOTIFY reportChanged)
    Q_PROPERTY(QString reportExperiment READ reportExperiment WRITE setReportExperiment NOTIFY reportExperimentChanged)
    // The chart is shown: a hidden chart is only marked dirty, and refreshed when it is shown again.
    Q_PROPERTY(bool active READ active WRITE setActive NOTIFY activeChanged)
    Q_PROPERTY(bool dark READ dark WRITE setDark NOTIFY darkChanged)
    // The colour scheme, a token of edi::colour_scheme_from_name (data/palettes): the experiments' and structures'
    // colours.
    Q_PROPERTY(QString colourScheme READ colourScheme WRITE setColourScheme NOTIFY colourSchemeChanged)
    // The structures' own colour scheme (the Bragg ticks and the structure curves), when the app's Structures colours
    // differ from its Patterns colours (the owner, 2026-10-22); empty: colourScheme's.
    Q_PROPERTY(QString structureColourScheme READ structureColourScheme WRITE setStructureColourScheme NOTIFY
                   structureColourSchemeChanged)
    // The main plot area, in logical pixels, and the window's device pixel ratio: the decimation's width.
    Q_PROPERTY(qreal plotWidth READ plotWidth WRITE setPlotWidth NOTIFY plotWidthChanged)
    Q_PROPERTY(qreal plotHeight READ plotHeight WRITE setPlotHeight NOTIFY plotHeightChanged)
    // The residual plot area's height: the residual's y range gives one intensity unit the height it has in
    // the main pane (edi ADR-0017 §15).
    Q_PROPERTY(qreal residualPlotHeight READ residualPlotHeight WRITE setResidualPlotHeight NOTIFY
                   residualPlotHeightChanged)
    Q_PROPERTY(qreal devicePixelRatio READ devicePixelRatio WRITE setDevicePixelRatio NOTIFY devicePixelRatioChanged)
    Q_PROPERTY(YScale yScale READ yScale WRITE setYScale NOTIFY yScaleChanged)
    // The x axis: d-spacing, or the experiment's own (2θ or time-of-flight). On d the pattern is the d-spacing capture
    // (edi::capture_pattern), which needs a calculated pattern; until then the chart stays on the experiment's axis.
    Q_PROPERTY(bool dSpacing READ dSpacing WRITE setDSpacing NOTIFY dSpacingChanged)
    // Whether the shown experiment has a current d column: until a calculation gives one, d cannot be chosen.
    Q_PROPERTY(bool dAvailable READ dAvailable NOTIFY dAvailableChanged)
    // How long a box zoom, a wheel zoom and a reset move the axis ranges (easydiffractionbeta's
    // ChartView.SeriesAnimations, EaStyle.Times.chartAnimation), in milliseconds; 0: at once.
    Q_PROPERTY(int animationDuration READ animationDuration WRITE setAnimationDuration NOTIFY animationDurationChanged)
    // The QML-declared series this controller fills.
    Q_PROPERTY(QXYSeries* measuredSeries MEMBER measured_series_ NOTIFY measuredSeriesChanged)
    Q_PROPERTY(edi_app::MeasuredLayer* measuredLayer MEMBER measured_layer_ NOTIFY measuredLayerChanged)
    Q_PROPERTY(QXYSeries* calculatedSeries MEMBER calculated_series_ NOTIFY calculatedSeriesChanged)
    Q_PROPERTY(QXYSeries* backgroundSeries MEMBER background_series_ NOTIFY backgroundSeriesChanged)
    Q_PROPERTY(QXYSeries* residualSeries MEMBER residual_series_ NOTIFY residualSeriesChanged)
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
    // The Bragg rows' labels (edi::BraggRowLabel): maps of `text`, `color` and `centre`, the row's middle in the
    // Bragg pane's units (row k from the bottom spans k to k + 1).
    Q_PROPERTY(QList<edi_app::BraggLabel> braggLabels READ braggLabels NOTIFY braggLabelsChanged)
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
    // The tick colours: the scheme's structure colours, one series each (no scheme has more than five), by the
    // structure's place in the project taken round the scheme's colours, as the structure lists take them.
    // Each structure's tick colour, by its place: one per `bragg.<place>` row of the style table.
    Q_PROPERTY(QList<QColor> braggColors READ braggColors NOTIFY braggColorsChanged)
    // Each structure's curve over the background (edi ADR-0017 §15): whether it is drawn, and, for each one drawn,
    // in presentation order, its outline colour and its fill colour, index for index.
    Q_PROPERTY(bool structureCurves READ structureCurves WRITE setStructureCurves NOTIFY structureCurvesChanged)
    Q_PROPERTY(QList<QColor> structureCurveColors READ structureCurveColors NOTIFY structureCurveColorsChanged)
    Q_PROPERTY(QList<QColor> structureCurveFills READ structureCurveFills NOTIFY structureCurveFillsChanged)
    // How the measured pattern is drawn (the owner, 2026-10-22): "band", measured ± s.u. as two lines with a fill
    // between them, the residual drawn the same way; "line"; "points", markers with error bars; "linePoints", all
    // three. Anything else is "band".
    Q_PROPERTY(QString measuredStyle READ measuredStyle WRITE setMeasuredStyle NOTIFY measuredStyleChanged)
    // Whether the chart presents a calculated pattern, which the structure curves need.
    Q_PROPERTY(bool hasCalculated READ hasCalculated NOTIFY hasCalculatedChanged)
    // The view the chart is showing or going to: [x min, x max, y min, y max], each a number or NaN for the data's own
    // range, and the title of the x axis they are on. Several charts that follow one view share it (edi ADR-0017
    // §15); setting it draws without an animation.
    Q_PROPERTY(QList<double> viewRanges READ viewRanges WRITE setViewRanges NOTIFY viewRangesChanged)
    Q_PROPERTY(QString viewRangesAxis READ viewRangesAxis WRITE setViewRangesAxis NOTIFY viewRangesAxisChanged)
    // How many times the series were replaced: what a test observes at a frame's synchronisation.
    Q_PROPERTY(int revision READ revision NOTIFY revisionChanged)

   public:
    enum YScale { Linear, Sqrt, Log10 };
    Q_ENUM(YScale)

    explicit PatternChartController(QObject* parent = nullptr);
    ~PatternChartController() override;

    ExperimentViewModel* experiment() const { return experiment_; }
    void setExperiment(ExperimentViewModel* experiment);
    ReportViewModel* report() const { return report_; }
    void setReport(ReportViewModel* report);
    QString reportExperiment() const { return report_experiment_; }
    void setReportExperiment(const QString& experiment);
    bool active() const { return active_; }
    void setActive(bool active);
    bool dark() const { return dark_; }
    void setDark(bool dark);
    QString colourScheme() const { return colour_scheme_; }
    QString structureColourScheme() const { return structure_colour_scheme_; }
    void setStructureColourScheme(const QString& scheme);
    void setColourScheme(const QString& scheme);
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
    bool dSpacing() const { return d_spacing_; }
    bool dAvailable() const { return d_available_; }
    void setDSpacing(bool on);
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
    QList<BraggLabel> braggLabels() const { return bragg_labels_; }
    ChartLegendModel* legend() const { return legend_; }
    ChartBandModel* excludedBands() const { return excluded_bands_; }
    QColor measuredColor() const { return color(measured_style_); }
    QColor calculatedColor() const { return color(QStringLiteral("calc")); }
    QColor backgroundColor() const { return color(QStringLiteral("bkg")); }
    QColor residualColor() const { return color(QStringLiteral("resid")); }
    QColor excludedColor() const { return color(QStringLiteral("excluded")); }
    QList<QColor> braggColors() const;
    bool structureCurves() const { return structure_curves_; }
    void setStructureCurves(bool on);
    QList<QColor> structureCurveColors() const { return structure_curve_colors_; }
    QList<QColor> structureCurveFills() const { return structure_curve_fills_; }
    bool hasCalculated() const { return has_calculated_; }
    QList<double> viewRanges() const;
    void setViewRanges(const QList<double>& ranges);
    QString viewRangesAxis() const;
    void setViewRangesAxis(const QString& axis);
    // The area (filled between its upper and lower series) and the outline of the structure curve at `index`, in
    // presentation order: the chart makes them as `structureCurveColors` grows and hands each over here.
    Q_INVOKABLE void setStructureSeries(int index, QXYSeries* upper, QXYSeries* lower, QXYSeries* outline);
    // A band's area (between its upper and lower series) and its two edges: pane 0 the measured band, 1 the
    // residual's.
    Q_INVOKABLE void setBandSeries(int pane, QXYSeries* upper, QXYSeries* lower, QXYSeries* top, QXYSeries* bottom);
    QString measuredStyle() const { return measured_drawing_; }
    void setMeasuredStyle(const QString& style);
    // The structures' tick series, one per `bragg.<place>` row of the style table, in place order: the chart makes
    // them as `braggColors` grows and hands each over here.
    Q_INVOKABLE void setBraggSeries(int place, QXYSeries* series);
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
    // The original value of a display value on `scale`, for a y label NumberText writes.
    Q_INVOKABLE double originalValue(double display, YScale scale) const;
    Q_INVOKABLE void refresh();

   signals:
    void experimentChanged();
    void reportChanged();
    void reportExperimentChanged();
    void activeChanged();
    void darkChanged();
    void colourSchemeChanged();
    void structureColourSchemeChanged();
    void plotWidthChanged();
    void plotHeightChanged();
    void residualPlotHeightChanged();
    void devicePixelRatioChanged();
    void yScaleChanged();
    void dSpacingChanged();
    void dAvailableChanged();
    void animationDurationChanged();
    void measuredSeriesChanged();
    void measuredLayerChanged();
    void calculatedSeriesChanged();
    void backgroundSeriesChanged();
    void residualSeriesChanged();
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
    void braggLabelsChanged();
    void residualTitleChanged();
    void revisionChanged();
    void measuredColorChanged();
    void calculatedColorChanged();
    void backgroundColorChanged();
    void residualColorChanged();
    void excludedColorChanged();
    void braggColorsChanged();
    void structureCurvesChanged();
    void measuredStyleChanged();
    void structureCurveColorsChanged();
    void structureCurveFillsChanged();
    void hasCalculatedChanged();
    void viewRangesChanged();
    void viewRangesAxisChanged();

   private:
    void invalidate();
    void invalidateLater();
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
    // The same without drawing, for a caller that draws next.
    void stopAnimation();
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
    QPointer<ReportViewModel> report_;
    QString report_experiment_;
    bool active_ = true, dark_ = false, dirty_ = true;
    QString colour_scheme_ = QStringLiteral("ediNatural");
    QString structure_colour_scheme_;
    // The style table the chart draws with: the report model's own in a report figure, else the palette's for the
    // project's experiments in the colour scheme.
    std::vector<edi::SeriesStyle> styles() const;
    // The colour scheme the chart is drawn in.
    edi::ColourScheme scheme() const;
    qreal plot_width_ = 0.0, plot_height_ = 0.0, residual_plot_height_ = 0.0, device_pixel_ratio_ = 1.0;
    YScale y_scale_ = Linear;
    bool d_spacing_ = false, d_available_ = false;
    edi::PatternAxis axis() const { return d_spacing_ ? edi::PatternAxis::DSpacing : edi::PatternAxis::Native; }
    // The view: unset means the data's full x range, and y ranges fitted to what is presented.
    std::optional<double> x_min_, x_max_, y_min_, y_max_;
    // The animation: its ranges at the start and the end, as shown, and the view it ends in.
    QVariantAnimation animation_;
    int animation_duration_ = 250;
    bool animating_ = false;
    double from_[4] = {}, to_[4] = {};
    std::optional<double> target_[4];
    QPointer<QXYSeries> measured_series_, calculated_series_, background_series_, residual_series_;
    QList<QPointer<QXYSeries>> bragg_series_;
    struct StructureSeries {
        QPointer<QXYSeries> upper, lower, outline;
    };
    QList<StructureSeries> structure_series_;
    struct BandSeries {
        QPointer<QXYSeries> upper, lower, top, bottom;
    };
    std::array<BandSeries, 2> band_series_;
    QString measured_drawing_ = QStringLiteral("band");  // how the measured data are drawn (measuredStyle)
    bool structure_curves_ = false, has_calculated_ = false;
    QList<QColor> structure_curve_colors_, structure_curve_fills_;
    std::string presented_x_;  // the x axis last presented, its quantity and unit
    std::string ranges_axis_;  // the x axis the ranges were given on, empty when they were not given
    QPointer<MeasuredLayer> measured_layer_;
    edi::PatternPresentation shown_;
    double shown_x_min_ = 0.0, shown_x_max_ = 1.0, shown_y_min_ = 0.0, shown_y_max_ = 1.0;
    double residual_min_ = -1.0, residual_max_ = 1.0, bragg_height_ = 0.0;
    double x_tick_ = 0.0, x_anchor_ = 0.0, y_tick_ = 0.0, y_anchor_ = 0.0, residual_tick_ = 0.0;
    int bragg_rows_ = 0, revision_ = 0;
    bool has_residual_ = false, has_data_ = false, current_ = false;
    QString x_title_, y_title_, residual_title_, measured_style_ = QStringLiteral("meas.0");
    std::size_t colour_count_ = 0;
    qsizetype bragg_colour_count_ = 0;
    QList<BraggLabel> bragg_labels_;
    ChartLegendModel* legend_;
    ChartBandModel* excluded_bands_;
};

}  // namespace edi_app

#endif  // EDI_APP_PATTERN_CHART_CONTROLLER_HPP
