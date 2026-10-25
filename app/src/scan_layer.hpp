// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_SCAN_LAYER_HPP
#define EDI_APP_SCAN_LAYER_HPP

#include <QColor>
#include <QPointer>
#include <QQuickPaintedItem>
#include <QString>
#include <QtQml/qqmlregistration.h>
#include <atomic>
#include <cstdint>
#include <vector>

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
    // The map's colours, one of edi::scan_colour_choices; a ramp starts at `background`. `colourScheme` may name a
    // ramp too (`ramp:<scheme>`), for the stacked patterns.
    Q_PROPERTY(QString colourMap MEMBER colour_map_ WRITE setColourMap NOTIFY colourMapChanged)
    Q_PROPERTY(QColor background MEMBER background_ WRITE setBackground NOTIFY backgroundChanged)
    // The map's colour between two datasets' rows: smooth (interpolated) or stepped (each dataset one band).
    Q_PROPERTY(bool smoothRows MEMBER smooth_rows_ WRITE setSmoothRows NOTIFY smoothRowsChanged)
    // The map's colours run from their high end at the lowest intensity, reversed.
    Q_PROPERTY(bool reversed MEMBER reversed_ WRITE setReversed NOTIFY reversedChanged)
    // The Stacked colours reversed: the last dataset takes the first colour (colourOf, so its labels and ticks too).
    Q_PROPERTY(bool stackedReversed MEMBER stacked_reversed_ WRITE setStackedReversed NOTIFY stackedReversedChanged)
    Q_PROPERTY(bool dark MEMBER dark_ WRITE setDark NOTIFY darkChanged)
    // Only the included range: the points inside an excluded region are not drawn, which leaves its tint as a gap.
    Q_PROPERTY(bool includedOnly MEMBER included_only_ WRITE setIncludedOnly NOTIFY includedOnlyChanged)
    // The shown dataset. The drawing does not depend on it.
    Q_PROPERTY(int current MEMBER current_ WRITE setCurrent NOTIFY currentChanged)
    // The stacked lines on the GPU (a ScanLines child) rather than painted.
    Q_PROPERTY(bool gpu MEMBER gpu_ WRITE setGpu NOTIFY gpuChanged)
    // The intensities the colour map's ends stand for, on the chart's y scale: what a colour bar labels.
    Q_PROPERTY(double displayMin READ displayMin NOTIFY displayMinChanged)
    Q_PROPERTY(double displayMax READ displayMax NOTIFY displayMaxChanged)
    // Bumped whenever the datasets' colours (colourOf) change, for what shows them to read them again.
    Q_PROPERTY(int coloursRevision READ coloursRevision NOTIFY coloursRevisionChanged)
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
    void setGpu(bool on);
    // On the stacked view, how high a dataset's line reaches over the x range shown, on the vertical axis; NaN when it
    // draws nothing there.
    Q_INVOKABLE double peakOf(int dataset) const;
    // The colour the stacked view draws a dataset's line in, by the colour choice: what its row label takes.
    Q_INVOKABLE QColor colourOf(int dataset) const;
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
    void gpuChanged();
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
    void measure();
    void reduce();
    void recolour();
    void feedLines();
    ReductionKey reductionKey() const;

    QPointer<ScanViewModel> model_;
    QString mode_ = QStringLiteral("stacked");
    double x_min_ = 0.0, x_max_ = 1.0, y_min_ = 0.0, y_max_ = 1.0;
    QString scale_ = QStringLiteral("linear");
    QString colour_scheme_;
    QString colour_map_ = QStringLiteral("viridis");
    QColor background_ = Qt::white;
    bool smooth_rows_ = true;
    bool reversed_ = false;
    bool stacked_reversed_ = false;
    bool dark_ = false;
    int current_ = -1;
    bool included_only_ = false;
    bool gpu_ = false;
    double display_min_ = 0.0, display_max_ = 1.0;

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
    // The GPU lines, and the reductions and order they were last given.
    ScanLines* lines_ = nullptr;
    int lines_fed_builds_ = -1;
    int reduction_changes_ = 0;  // bumped whenever any dataset's reduction changes
    std::vector<std::size_t> lines_order_;
};

// The map's colour bar: the map's colours from the low end at the bottom to the high end at the top, each pixel row
// coloured by the lookup the map's own pixels take (edi::scan_colour_table), so the key and the image agree.
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
    QString colour_map_ = QStringLiteral("viridis");
    QColor background_ = Qt::white;
    bool dark_ = false;
    bool reversed_ = false;
};

}  // namespace edi_app

#endif  // EDI_APP_SCAN_LAYER_HPP
