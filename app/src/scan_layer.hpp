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
// size: "stacked" draws every dataset's columns as a line from its row upwards, in the dataset's measured colour,
// the shown dataset last and wider; "map" fills each dataset's row with its columns' colours from the colour map.
// Intensity is taken on the chart's y scale and spread over every dataset's lowest to highest value.
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
    Q_PROPERTY(bool dark MEMBER dark_ WRITE setDark NOTIFY darkChanged)
    // The shown dataset, drawn over the others in the stacked view.
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
    void setDark(bool dark);
    void setCurrent(int dataset);
    double displayMin() const { return display_min_; }
    double displayMax() const { return display_max_; }
    // The colour map's colour at `t` in [0, 1], for a colour bar beside the map.
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
    void darkChanged();
    void currentChanged();
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
    bool dark_ = false;
    int current_ = -1;
    double display_min_ = 0.0, display_max_ = 1.0;
};

}  // namespace edi_app

#endif  // EDI_APP_SCAN_LAYER_HPP
