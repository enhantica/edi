// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_SCAN_LINES_HPP
#define EDI_APP_SCAN_LINES_HPP

#include <QColor>
#include <QQuickItem>
#include <QRectF>
#include <QtQml/qqmlregistration.h>
#include <vector>

namespace edi_app {

/// The Stacked view's pattern lines on the GPU (edi ADR-0041): the patterns drawn as scene-graph nodes of quads, one quad
/// per segment of a pattern's reduced trace, 64 patterns to a node, which a shader places at each pattern's row and
/// height and draws antialiased at the line width. New traces rebuild the vertices; a new row, height, y range, colour or
/// width changes only what the shader is given. The lines are drawn in the order given, a later one over an earlier one,
/// over the bands (filled rectangles: the excluded regions' tint). Qt Quick's software renderer does not draw them.
class ScanLines : public QQuickItem {
    Q_OBJECT
    QML_ELEMENT
    // The vertical axis shown: a line's row and height are on it.
    Q_PROPERTY(double yMin READ yMin WRITE setYMin NOTIFY yMinChanged)
    Q_PROPERTY(double yMax READ yMax WRITE setYMax NOTIFY yMaxChanged)
    // The width of every line, in item pixels.
    Q_PROPERTY(double lineWidth READ lineWidth WRITE setLineWidth NOTIFY lineWidthChanged)

   public:
    /// One pattern's trace: x in item pixels, v a value the style scales, a NaN on either side of a break.
    struct Trace {
        std::vector<float> x, v;
    };
    /// Where and how a trace is drawn: up from `row` by `lift` times v, on the vertical axis, and its colour.
    struct Style {
        double row = 0.0, lift = 1.0;
        QColor colour;
    };

    explicit ScanLines(QQuickItem* parent = nullptr);

    /// Replaces every trace; the styles keep their places, a trace without one is not drawn.
    void setTraces(std::vector<Trace> traces);
    /// Replaces every style, trace for trace.
    void setStyles(std::vector<Style> styles);
    const std::vector<Style>& styles() const { return styles_; }
    /// Replaces the bands, in item pixels, all in one colour.
    void setBands(std::vector<QRectF> bands, const QColor& colour);

    double yMin() const { return y_min_; }
    double yMax() const { return y_max_; }
    double lineWidth() const { return line_width_; }
    void setYMin(double value);
    void setYMax(double value);
    void setLineWidth(double width);
    /// Whether the owning view is shown. While it is not, a scene update (one asked for before it was hidden, or a
    /// resize) leaves the lines as they were drawn, and comes once the view is shown again.
    void setActive(bool active);

   signals:
    void yMinChanged();
    void yMaxChanged();
    void lineWidthChanged();
    /// The lines were drawn again. Emitted on the render thread.
    void rendered();

   protected:
    QSGNode* updatePaintNode(QSGNode* old, UpdatePaintNodeData* data) override;

   private:
    std::vector<Trace> traces_;
    std::vector<Style> styles_;
    std::vector<QRectF> bands_;
    QColor band_colour_;
    double y_min_ = 0.0, y_max_ = 1.0;
    double line_width_ = 2.0;
    bool traces_changed_ = true;
    bool bands_changed_ = true;
    bool active_ = true, pending_ = false;
};

}  // namespace edi_app

#endif  // EDI_APP_SCAN_LINES_HPP
