// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_SCAN_LAYER_HPP
#define EDI_APP_SCAN_LAYER_HPP

#include <QColor>
#include <QPointer>
#include <QQuickPaintedItem>
#include <QString>
#include <QList>
#include <QtQml/qqmlregistration.h>
#include <atomic>
#include <cstdint>
#include <vector>

#include "chart_models.hpp"
#include "scan_lines.hpp"
#include "scan_view_model.hpp"

namespace edi_app {

// The scan views' drawing (edi ADR-0041), laid over a chart's plot area and mapping the ranges it is given onto its
// size: "stacked" draws every dataset as a line from its row upwards, in the dataset's colour, 2 px wide as the pattern
// chart's measured line (narrower only for rows packed tighter); "map" colours the plot from the colour map, one image
// of the plot's pixels. Each dataset's measured points are reduced for the range shown at the plot's own pixel columns
// (edi::scan_trace, edi::scan_pixel_values), so a zoomed view shows the points themselves (the owner, 2026-10-22); a
// dataset's reduction is kept until its points, the x range, the plot's width, the y scale or the included range
// change, so a new row placing, height, colour or reversal reduces nothing again. The changes of one frame are drawn
// once, at its polish. With `gpu` the stacked lines are drawn by a ScanLines child on the GPU, otherwise this item
// paints them with QPainter, the faster way without a GPU (docs/dev/design/scan-view-timings.md). Intensity is taken
// on the chart's y scale and spread over every dataset's lowest to highest value. Each dataset's excluded ranges are
// tinted over its row, as the pattern chart tints them; with `includedOnly` the points inside them are not drawn.
class ScanLayer : public QQuickPaintedItem {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(edi_app::ScanViewModel* model READ model WRITE setModel NOTIFY modelChanged)
    Q_PROPERTY(QString mode MEMBER mode_ WRITE setMode NOTIFY modeChanged)
    Q_PROPERTY(double xMin MEMBER x_min_ WRITE setXMin NOTIFY xMinChanged)
    Q_PROPERTY(double xMax MEMBER x_max_ WRITE setXMax NOTIFY xMaxChanged)
    Q_PROPERTY(double yMin MEMBER y_min_ WRITE setYMin NOTIFY yMinChanged)
    Q_PROPERTY(double yMax MEMBER y_max_ WRITE setYMax NOTIFY yMaxChanged)
    // The chart's y scale: "linear", "sqrt" or "log".
    Q_PROPERTY(QString scale MEMBER scale_ WRITE setScale NOTIFY scaleChanged)
    Q_PROPERTY(QString colourScheme MEMBER colour_scheme_ WRITE setColourScheme NOTIFY colourSchemeChanged)
    // The stacked patterns' colours, a palette's token or a colour map's name (edi::scan_colour_choices), and the map's
    // colour map (edi::scan_colour_map_names; Blue-Red starts at the theme's chart background). In a palette, each
    // pattern takes its position in `positions` (a joint fit's experiments'), or without one the next position free
    // of `takenPositions` (a scan's datasets beside the project's structures; edi::free_positions).
    Q_PROPERTY(QList<int> positions MEMBER positions_ WRITE setPositions NOTIFY positionsChanged)
    Q_PROPERTY(QList<int> takenPositions MEMBER taken_positions_ WRITE setTakenPositions NOTIFY takenPositionsChanged)
    Q_PROPERTY(QString colourMap MEMBER colour_map_ WRITE setColourMap NOTIFY colourMapChanged)
    Q_PROPERTY(QColor background MEMBER background_ WRITE setBackground NOTIFY backgroundChanged)
    // The map's colour between two datasets' rows: smooth (interpolated) or stepped (each dataset one band).
    Q_PROPERTY(bool smoothRows MEMBER smooth_rows_ WRITE setSmoothRows NOTIFY smoothRowsChanged)
    // The map's colours run from their high end at the lowest intensity, inverted (edi::scan_map_inverted resolves the
    // Map's direction).
    Q_PROPERTY(bool reversed MEMBER reversed_ WRITE setReversed NOTIFY reversedChanged)
    // The Stacked colours reversed: the last dataset takes the first colour (colourOf, so its labels and ticks too).
    Q_PROPERTY(bool stackedReversed MEMBER stacked_reversed_ WRITE setStackedReversed NOTIFY stackedReversedChanged)
    Q_PROPERTY(bool dark MEMBER dark_ WRITE setDark NOTIFY darkChanged)
    // Only the included range: the points inside an excluded region are not drawn, which leaves its tint as a gap.
    Q_PROPERTY(bool includedOnly MEMBER included_only_ WRITE setIncludedOnly NOTIFY includedOnlyChanged)
    // Every pattern drawn less its background where it has one (ScanViewModel::Pattern::background), the intensity
    // range and the colour bar's ends with it; one without is drawn as it is.
    Q_PROPERTY(bool subtractBackground MEMBER subtract_background_ WRITE setSubtractBackground NOTIFY
                   subtractBackgroundChanged)
    // The shown dataset: with `highlight`, drawn on top in its colour while every other is faded to `faded` (on the
    // map, every other row's band blended toward the background); without, the drawing does not depend on it.
    Q_PROPERTY(int current MEMBER current_ WRITE setCurrent NOTIFY currentChanged)
    Q_PROPERTY(bool highlight MEMBER highlight_ WRITE setHighlight NOTIFY highlightChanged)
    Q_PROPERTY(double faded MEMBER faded_ WRITE setFaded NOTIFY fadedChanged)
    // A fit holds the cores: the painter strokes the lines on one thread, not on every core, so the fit is not slowed.
    Q_PROPERTY(bool busy MEMBER busy_ WRITE setBusy NOTIFY busyChanged)
    // The view is on the screen. A layer not shown only notes that it is out of date, and draws once, with the latest
    // data, when it is shown again: the pattern chart's rule (PatternChartController::active).
    Q_PROPERTY(bool active MEMBER active_ WRITE setActive NOTIFY activeChanged)
    // The stacked lines on the GPU (a ScanLines child) rather than painted.
    Q_PROPERTY(bool gpu MEMBER gpu_ WRITE setGpu NOTIFY gpuChanged)
    // The stacked patterns' placing (edi ADR-0041 §4), on a vertical axis whose 0 to 1 is the plot's height: at spacing
    // s, from 0 (Overlay) to 1 (Separate), each of N patterns scaled so its lowest to highest value spans
    // height = (1 - s) + s / N, the i-th in order with its baseline at i s / N (edi::stacked_placement), so the stack
    // fills the plot exactly.
    Q_PROPERTY(double spacing MEMBER spacing_ WRITE setSpacing NOTIFY spacingChanged)
    // How tall each stacked pattern is, on the vertical axis.
    Q_PROPERTY(double patternHeight READ patternHeight NOTIFY placementChanged)
    // The top of the highest stacked pattern on the vertical axis: 1, the plot's top, with any patterns.
    Q_PROPERTY(double stackTop READ stackTop NOTIFY stackTopChanged)
    // The intensities the colour map's ends stand for, on the chart's y scale: what a colour bar labels.
    Q_PROPERTY(double displayMin READ displayMin NOTIFY displayMinChanged)
    Q_PROPERTY(double displayMax READ displayMax NOTIFY displayMaxChanged)
    // Bumped whenever the datasets' colours (colourOf) change, for what shows them to read them again.
    Q_PROPERTY(int coloursRevision READ coloursRevision NOTIFY coloursRevisionChanged)
    // Which rows' labels show, true by dataset, while `labelled`: all while they fit; when they would come closer than
    // `labelGap` pixels, an evenly spread share of them, the current dataset's always among them while `nameCurrent`;
    // off, when a shown legend marks it instead, never among them. Zooming in spreads the rows, and the rest come back as they fit. Made
    // again when what it depends on changes, announced when it differs.
    Q_PROPERTY(bool labelled MEMBER labelled_ WRITE setLabelled NOTIFY labelledChanged)
    Q_PROPERTY(bool nameCurrent MEMBER name_current_ WRITE setNameCurrent NOTIFY nameCurrentChanged)
    // The Stacked view's legend (ChartLegend; the owner, 2026-10-26): a line in each dataset's colour and its row's
    // text, in scan order, the current dataset's marked selected while highlighting; past kFullLegend datasets only the
    // first, the current and the last, then how many more there are.
    Q_PROPERTY(edi_app::ChartLegendModel* legend READ legend CONSTANT)
    Q_PROPERTY(double labelGap MEMBER label_gap_ WRITE setLabelGap NOTIFY labelGapChanged)
    Q_PROPERTY(QList<bool> shownLabels READ shownLabels NOTIFY shownLabelsChanged)
    // Diagnostics, never inputs: how many datasets were reduced (a stacked trace or a map's pixel columns), and how
    // many times the drawing was rendered.
    Q_PROPERTY(int traceBuildCount READ traceBuildCount NOTIFY traceBuildCountChanged)
    Q_PROPERTY(int redrawCount READ redrawCount NOTIFY redrawCountChanged)

   public:
    explicit ScanLayer(QQuickItem* parent = nullptr);

    ScanViewModel* model() const { return model_; }
    void setModel(ScanViewModel* model);
    void setMode(const QString& mode);
    void setXMin(double value);
    void setXMax(double value);
    void setYMin(double value);
    void setYMax(double value);
    void setScale(const QString& scale);
    void setColourScheme(const QString& scheme);
    void setColourMap(const QString& map);
    void setBackground(const QColor& colour);
    void setSmoothRows(bool smooth);
    void setReversed(bool reversed);
    void setStackedReversed(bool reversed);
    void setDark(bool dark);
    void setCurrent(int dataset);
    void setIncludedOnly(bool on);
    void setSubtractBackground(bool on);
    void setPositions(const QList<int>& positions);
    void setTakenPositions(const QList<int>& positions);
    void setGpu(bool on);
    void setHighlight(bool on);
    void setFaded(double opacity);
    void setBusy(bool busy);
    void setActive(bool active);
    void setSpacing(double spacing);
    void setLabelled(bool labelled);
    void setNameCurrent(bool on);
    ChartLegendModel* legend() const { return legend_; }
    // The most datasets the legend lists in full.
    static constexpr int kFullLegend = 15;
    void setLabelGap(double gap);
    QList<bool> shownLabels() const;
    double patternHeight() const { return pattern_height_; }
    double stackTop() const { return stack_top_; }
    // Each stacked pattern's extent on the vertical axis, baseline to top, by dataset: NaN for one with no place.
    std::vector<edi::ScanRowSpan> stackedSpans() const;
    // A dataset's row on the vertical axis: on the stacked view its baseline, on the map its scan value or place (the
    // model's). NaN when it has none. The labels, the ticks and the clicks all take it from here.
    Q_INVOKABLE double rowOf(int dataset) const;
    // The dataset a click at (x, y) on the axes points at: on the stacked view the one whose line passes nearest,
    // on the map the one whose band holds y. -1 for none.
    Q_INVOKABLE int datasetNear(double x, double y) const;
    // On the stacked view, how high a dataset's line reaches over the x range shown, on the vertical axis; NaN when it
    // draws nothing there.
    Q_INVOKABLE double peakOf(int dataset) const;
    // The colour the stacked view draws a dataset's line in, by the colour choice: what its row label takes.
    Q_INVOKABLE QColor colourOf(int dataset) const;
    // A line's colour faded to `faded` over the background, opaque.
    QColor fadedColour(const QColor& colour) const;
    double displayMin() const { return display_min_; }
    double displayMax() const { return display_max_; }
    int coloursRevision() const { return colours_revision_; }
    int traceBuildCount() const { return trace_builds_; }
    int redrawCount() const { return redraws_.load(); }
    // The colour map's colour at `t` in [0, 1].
    Q_INVOKABLE QColor mapColour(double t) const;

    void paint(QPainter* painter) override;

   signals:
    void modelChanged();
    void labelledChanged();
    void nameCurrentChanged();
    void labelGapChanged();
    void shownLabelsChanged();
    void modeChanged();
    void xMinChanged();
    void xMaxChanged();
    void yMinChanged();
    void yMaxChanged();
    void scaleChanged();
    void colourSchemeChanged();
    void colourMapChanged();
    void backgroundChanged();
    void smoothRowsChanged();
    void reversedChanged();
    void stackedReversedChanged();
    void darkChanged();
    void currentChanged();
    void includedOnlyChanged();
    void subtractBackgroundChanged();
    void positionsChanged();
    void takenPositionsChanged();
    void gpuChanged();
    void highlightChanged();
    void fadedChanged();
    void busyChanged();
    void activeChanged();
    void spacingChanged();
    void placementChanged();
    void stackTopChanged();
    void displayMinChanged();
    void displayMaxChanged();
    void coloursRevisionChanged();
    void traceBuildCountChanged();
    void redrawCountChanged();

   protected:
    void updatePolish() override;
    QSGNode* updatePaintNode(QSGNode* old, UpdatePaintNodeData* data) override;
    void geometryChange(const QRectF& next, const QRectF& previous) override;

   private:
    // One property's value and its own signal, and a drawing again when it changed.
    template <typename T>
    void assign(T& member, const T& value, void (ScanLayer::*changed)()) {
        if (!(member == value)) {
            member = value;
            emit(this->*changed)();
            redraw();
        }
    }
    // What the reductions depend on besides each dataset's own points.
    struct ReductionKey {
        double x_min = 0.0, x_max = 0.0;
        int columns = 0;
        bool included_only = false;
        bool subtract_background = false;
        int scale = 0;
        bool operator==(const ReductionKey&) const = default;
    };
    // A dataset's reduction: a stacked trace (x in item pixels, the value on the y scale; a NaN on either side of a
    // break) or a map's pixel columns (the value on the y scale, NaN where empty).
    struct Reduction {
        std::uint64_t generation = 0;  // the dataset's ScanViewModel::Pattern::generation it was made from; 0: none
        std::vector<float> x, v;
    };
    bool lines_on_gpu() const { return gpu_ && mode_ == QLatin1String("stacked"); }
    // Asks for this frame's drawing: the reductions and the GPU lines at the polish, the painting after it.
    void redraw();
    // While the view is not shown: notes that its drawing is out of date and says to do no work, whatever asked for it
    // (a change, a polish or paint already queued, a resize).
    bool deferred();
    // The GPU lines are in the scene while they draw the view; while it is not shown they do no work of their own
    // (ScanLines::setActive).
    void showLines();
    void measure();
    void place();
    // A stacked dataset's value on the vertical axis, as its line is drawn.
    double stackedY(std::size_t dataset, double value) const;
    void reduce();
    void recolour();
    void feedLines();
    ReductionKey reductionKey() const;

    QPointer<ScanViewModel> model_;
    QString mode_ = QStringLiteral("stacked");
    double x_min_ = 0.0, x_max_ = 1.0, y_min_ = 0.0, y_max_ = 1.0;
    QString scale_ = QStringLiteral("linear");
    QString colour_scheme_;
    QString colour_map_ = QStringLiteral("blue-red");
    QColor background_ = Qt::white;
    bool smooth_rows_ = true;
    bool reversed_ = false;
    bool stacked_reversed_ = false;
    bool dark_ = false;
    int current_ = -1;
    bool included_only_ = false;
    bool subtract_background_ = false;
    QList<int> positions_, taken_positions_;
    bool gpu_ = false;
    bool highlight_ = false;
    double faded_ = 0.3;
    bool busy_ = false;
    bool active_ = true, stale_ = false;
    double spacing_ = 0.75;  // Wide
    bool labelled_ = false;
    bool name_current_ = true;
    ChartLegendModel* legend_ = nullptr;
    void syncLegend();
    // At Separate on the Stacked view each pattern spans its values in the x range shown (measure).
    bool fitsShownRange() const;
    double label_gap_ = 1.0;
    // shownLabels, and whether what it depends on changed since it was made.
    mutable QList<bool> shown_labels_;
    mutable bool shown_labels_stale_ = true;
    void labelsMoved();
    double display_min_ = 0.0, display_max_ = 1.0;
    // By dataset: its lowest and highest value on the y scale, and its stacked baseline (NaN while it has no row).
    std::vector<double> lows_, highs_, baselines_;
    double pattern_height_ = 1.0;
    double stack_top_ = 1.0;

    // The reductions, by dataset, and what they were made for.
    std::vector<Reduction> reductions_;
    ReductionKey reduced_for_;
    QString reduced_mode_;
    int trace_builds_ = 0;
    std::atomic<int> redraws_{0};
    // The stacked colours by dataset, and what they were chosen for.
    std::vector<QColor> colours_;
    QString coloured_for_;
    int colours_revision_ = 0;
    // Whether the drawing marks a dataset: highlighting and one shown.
    int highlighted() const;
    // The GPU lines, the highlighted one's line drawn over them (their child, so hiding the lines hides it), and the
    // reductions and order they were last given.
    ScanLines* lines_ = nullptr;
    ScanLines* top_ = nullptr;
    int top_dataset_ = -1;
    int top_fed_builds_ = -1;
    int lines_fed_builds_ = -1;
    int reduction_changes_ = 0;  // bumped whenever any dataset's reduction changes
    std::vector<std::size_t> lines_order_;
};

// The map's colour bar: the map's colours from the low end at the bottom to the high end at the top, each pixel row
// coloured by the lookup the map's own pixels take (edi::scan_colour_table), so the key and the image agree.
// A short tick at each dataset's row just right of the plot, in the dataset's Stacked colour (the owner, 2026-10-22):
// one item for every row, the layer's rows and colours, each tick a scene-graph rectangle a pixel high, as a QML
// Rectangle draws it, on the plot's pixel rows and kept between its top and bottom rows, so a row a fraction of a pixel
// past an axis end is not drawn beyond it.
class ScanRowTicks : public QQuickItem {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(edi_app::ScanLayer* scanLayer READ scanLayer WRITE setScanLayer NOTIFY scanLayerChanged)
    Q_PROPERTY(double tickWidth MEMBER tick_width_ WRITE setTickWidth NOTIFY tickWidthChanged)
    // The plot's height, which the rows are placed on.
    Q_PROPERTY(double plotHeight MEMBER plot_height_ WRITE setPlotHeight NOTIFY plotHeightChanged)

   public:
    explicit ScanRowTicks(QQuickItem* parent = nullptr);
    ScanLayer* scanLayer() const { return layer_; }
    void setScanLayer(ScanLayer* layer);
    void setTickWidth(double width);
    void setPlotHeight(double height);

   signals:
    void scanLayerChanged();
    void tickWidthChanged();
    void plotHeightChanged();

   private:
    QPointer<ScanLayer> layer_;
    double tick_width_ = 1.0;
    double plot_height_ = 0.0;

   protected:
    QSGNode* updatePaintNode(QSGNode* old, UpdatePaintNodeData* data) override;
};

class ScanColourBar : public QQuickPaintedItem {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(QString colourMap MEMBER colour_map_ WRITE setColourMap NOTIFY colourMapChanged)
    Q_PROPERTY(QColor background MEMBER background_ WRITE setBackground NOTIFY backgroundChanged)
    Q_PROPERTY(bool dark MEMBER dark_ WRITE setDark NOTIFY darkChanged)
    Q_PROPERTY(bool reversed MEMBER reversed_ WRITE setReversed NOTIFY reversedChanged)

   public:
    explicit ScanColourBar(QQuickItem* parent = nullptr);
    void setReversed(bool reversed);
    void setColourMap(const QString& map);
    void setBackground(const QColor& colour);
    void setDark(bool dark);
    void paint(QPainter* painter) override;

   signals:
    void colourMapChanged();
    void backgroundChanged();
    void darkChanged();
    void reversedChanged();

   private:
    QString colour_map_ = QStringLiteral("blue-red");
    QColor background_ = Qt::white;
    bool dark_ = false;
    bool reversed_ = false;
};

}  // namespace edi_app

#endif  // EDI_APP_SCAN_LAYER_HPP
