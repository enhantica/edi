// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_SCAN_LAYER_HPP
#define EDI_APP_SCAN_LAYER_HPP

#include <QColor>
#include <QPointer>
#include <QQuickPaintedItem>
#include <QString>
#include <QtQml/qqmlregistration.h>

#include "scan_view_model.hpp"

namespace edi_app {

// The scan views' drawing (edi ADR-0041), laid over a chart's plot area and mapping the ranges it is given onto its
// size: "stacked" draws every dataset as a line from its row upwards, in the dataset's colour, 2 px wide as the pattern
// chart's measured line (narrower only for rows packed tighter); "map" colours the plot from the colour map, each
// pixel row taking the intensity between the two datasets whose rows it lies between, in proportion to its distance
// from each, so the colour changes smoothly from one dataset to the next. Both reduce each dataset's measured points for the range shown at the plot's own pixel
// columns every time they draw, so a zoomed view shows the points themselves (the owner, 2026-10-22). Intensity is
// taken on the chart's y scale and spread over every dataset's lowest to highest value. Each dataset's excluded ranges
// are tinted over its row, as the pattern chart tints them; with `includedOnly` the points inside them are not drawn.
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
    // The shown dataset; the chart marks it with its selected-pattern line.
    Q_PROPERTY(int current MEMBER current_ WRITE setCurrent NOTIFY currentChanged)
    // The intensities the colour map's ends stand for, on the chart's y scale: what a colour bar labels.
    Q_PROPERTY(double displayMin READ displayMin NOTIFY displayMinChanged)
    Q_PROPERTY(double displayMax READ displayMax NOTIFY displayMaxChanged)

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
    // On the stacked view, how high a dataset's line reaches over the x range shown, on the vertical axis; NaN when it
    // draws nothing there.
    Q_INVOKABLE double peakOf(int dataset) const;
    // The colour the stacked view draws a dataset's line in, by the colour choice: what its row label takes.
    Q_INVOKABLE QColor colourOf(int dataset) const;
    double displayMin() const { return display_min_; }
    double displayMax() const { return display_max_; }
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
    void displayMinChanged();
    void displayMaxChanged();

   private:
    // One property's value and its own signal, and a drawing again when it changed.
    template <typename T>
    void assign(T& member, const T& value, void (ScanLayer::*changed)()) {
        if (!(member == value)) {
            member = value;
            emit(this->*changed)();
            update();
        }
    }
    void measure();

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
    double display_min_ = 0.0, display_max_ = 1.0;
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
