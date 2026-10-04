// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_MEASURED_LAYER_HPP
#define EDI_APP_MEASURED_LAYER_HPP

#include <QColor>
#include <QList>
#include <QPointF>
#include <QQuickItem>
#include <QtQml/qqmlregistration.h>

namespace edi_app {

// The measured points and their error bars as one scene-graph item (edi ADR-0017 §15): every marker and every
// bar painted into one image and drawn as one node, whatever their number, where a ScatterSeries draws one Qt
// Quick item per point. It lies behind a chart's plot area and maps the data range it is given onto its own
// size; the points and bar ends are the core's presentation, already in the display scale.
class MeasuredLayer : public QQuickItem {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(QColor color READ color WRITE setColor NOTIFY colorChanged)
    Q_PROPERTY(qreal markerSize READ markerSize WRITE setMarkerSize NOTIFY markerSizeChanged)
    Q_PROPERTY(double xMin MEMBER x_min_ NOTIFY xMinChanged)
    Q_PROPERTY(double xMax MEMBER x_max_ NOTIFY xMaxChanged)
    Q_PROPERTY(double yMin MEMBER y_min_ NOTIFY yMinChanged)
    Q_PROPERTY(double yMax MEMBER y_max_ NOTIFY yMaxChanged)
    // How many points the item holds, and how many times they were replaced.
    Q_PROPERTY(int count READ count NOTIFY countChanged)
    Q_PROPERTY(int revision READ revision NOTIFY revisionChanged)

   public:
    explicit MeasuredLayer(QQuickItem* parent = nullptr);

    QColor color() const { return color_; }
    void setColor(const QColor& color);
    qreal markerSize() const { return marker_size_; }
    void setMarkerSize(qreal size);
    int count() const { return static_cast<int>(points_.size()); }
    int revision() const { return revision_; }

    // The points, and per point the bar's low and high ends (a NaN low end runs to the bottom).
    void setData(const QList<QPointF>& points, const QList<double>& low, const QList<double>& high);
    const QList<QPointF>& points() const { return points_; }

   signals:
    void colorChanged();
    void markerSizeChanged();
    void xMinChanged();
    void xMaxChanged();
    void yMinChanged();
    void yMaxChanged();
    void countChanged();
    void revisionChanged();

   protected:
    QSGNode* updatePaintNode(QSGNode* old, UpdatePaintNodeData* data) override;

   private:
    QColor color_ = Qt::black;
    qreal marker_size_ = 4.0;
    double x_min_ = 0.0, x_max_ = 1.0, y_min_ = 0.0, y_max_ = 1.0;
    QList<QPointF> points_;
    QList<double> low_, high_;
    int revision_ = 0;
};

}  // namespace edi_app

#endif  // EDI_APP_MEASURED_LAYER_HPP
