// SPDX-License-Identifier: BSD-3-Clause
#include <QCoreApplication>
#include <QMutex>
#include <QMutexLocker>
#include <QPointer>
#include <QQuickItem>
#include <QQuickWindow>
#include <QQmlListReference>
#include <QVariantMap>
#include <QtGraphs/QAreaSeries>
#include <QtGraphs/QValueAxis>
#include <QtQml/qqml.h>

#include <algorithm>
#include <cmath>

class PatternAreaLayouts final : public QObject {
    Q_OBJECT
public:
    Q_INVOKABLE void attach(QQuickItem* main, QQuickItem* residual) {
        stop();
        main_ = main;
        residual_ = residual;
        if (!main || !residual || !main->window()) return;
        mainLayout_ = connect(main, SIGNAL(plotAreaChanged()), this, SLOT(layout()), Qt::DirectConnection);
        residualLayout_ = connect(residual, SIGNAL(plotAreaChanged()), this, SLOT(layout()), Qt::DirectConnection);
        frame_ = connect(main->window(), &QQuickWindow::beforeSynchronizing, this, [this] {
            QMutexLocker lock(&mutex_);
            ++frames_;
            observe(main_);
            observe(residual_);
        }, Qt::DirectConnection);
    }

    Q_INVOKABLE void stop() {
        disconnect(frame_);
        disconnect(mainLayout_);
        disconnect(residualLayout_);
        for (const auto& watch : shapes_) disconnect(watch.connection);
        shapes_.clear();
    }

    Q_INVOKABLE void begin() {
        QMutexLocker lock(&mutex_);
        frames_ = 0;
        layouts_ = 0;
        drawnShapes_ = 0;
        worst_ = 0;
        areas_.clear();
        nonempty_.clear();
        detail_.clear();
    }

    Q_INVOKABLE QVariantMap result() const {
        QMutexLocker lock(&mutex_);
        return {{"frames", frames_}, {"layouts", layouts_}, {"drawnShapes", drawnShapes_},
                {"areas", areas_}, {"nonempty", nonempty_},
                {"worst", worst_}, {"detail", detail_}};
    }

private slots:
    void layout() {
        QMutexLocker lock(&mutex_);
        ++layouts_;
        observe(qobject_cast<QQuickItem*>(sender()), true);
    }
    void shapeLayout() {
        auto* shape = qobject_cast<QQuickItem*>(sender());
        auto* renderer = shape ? shape->parentItem() : nullptr;
        auto* pane = renderer ? renderer->parentItem() : nullptr;
        if (!pane) return;
        QMutexLocker lock(&mutex_);
        observeShape(pane, shape, pane->property("plotArea").toRectF());
    }

private:
    void observeShape(QQuickItem* pane, QQuickItem* shape, const QRectF& plot) {
        const auto bounds = shape->property("boundingRect").toRectF();
        if (bounds.isEmpty() || plot.isEmpty()) return;
        ++drawnShapes_;
        const auto inPane = shape->mapRectToItem(pane, bounds);
        const double excess = std::max({0.0, (plot.left() - inPane.left()) / plot.width(),
            (inPane.right() - plot.right()) / plot.width(), (plot.top() - inPane.top()) / plot.height(),
            (inPane.bottom() - plot.bottom()) / plot.height()});
        if (excess <= worst_) return;
        worst_ = excess;
        detail_ = QStringLiteral("%1 filled shape extends %2 plot spans beyond its pane")
                      .arg(pane->objectName()).arg(excess);
    }

    void observe(QQuickItem* pane, bool layoutChanged = false) {
        if (!pane || (!layoutChanged && !pane->isVisible())) return;
        const auto plot = pane->property("plotArea").toRectF();
        if (plot.width() <= 0 || plot.height() <= 0) return;
        for (auto* renderer : pane->childItems()) {
            if (!renderer->inherits("AreaRenderer")) continue;
            for (auto* shape : renderer->childItems()) {
                if (!shape->inherits("QQuickShape")) continue;
                if (std::none_of(shapes_.cbegin(), shapes_.cend(), [shape](const ShapeWatch& watch) {
                        return watch.item == shape;
                    })) {
                    shapes_.append({shape, connect(shape, SIGNAL(boundingRectChanged()), this,
                                                  SLOT(shapeLayout()), Qt::DirectConnection)});
                }
                observeShape(pane, shape, plot);
            }
        }
        const QQmlListReference series(pane, "seriesList");
        if (!series.isValid()) return;
        const auto* paneX = qobject_cast<QValueAxis*>(pane->property("axisX").value<QObject*>());
        const auto* paneY = qobject_cast<QValueAxis*>(pane->property("axisY").value<QObject*>());
        for (qsizetype i = 0; i < series.count(); ++i) {
            const auto* area = qobject_cast<QAreaSeries*>(series.at(i));
            if (!area) continue;
            areas_.insert(area->objectName(), true);
            const auto* x = area->axisX() ? qobject_cast<QValueAxis*>(area->axisX()) : paneX;
            const auto* y = area->axisY() ? qobject_cast<QValueAxis*>(area->axisY()) : paneY;
            if (!x || !y || x->max() <= x->min() || y->max() <= y->min()) continue;
            for (const auto* edge : {area->upperSeries(), area->lowerSeries()}) {
                if (!edge || edge->count() == 0) continue;
                nonempty_.insert(area->objectName(), true);
                for (const auto& point : edge->points()) {
                    const double u = (point.x() - x->min()) / (x->max() - x->min());
                    const double v = (point.y() - y->min()) / (y->max() - y->min());
                    if (!std::isfinite(u) || !std::isfinite(v)) continue;
                    const double excess = std::max({0.0, -u, u - 1.0, -v, v - 1.0});
                    if (excess <= worst_) continue;
                    worst_ = excess;
                    detail_ = QStringLiteral("%1 point (%2,%3), x [%4,%5], y [%6,%7], outside by %8 plot spans")
                                  .arg(area->objectName()).arg(point.x()).arg(point.y()).arg(x->min())
                                  .arg(x->max()).arg(y->min()).arg(y->max()).arg(excess);
                }
            }
        }
    }

    mutable QMutex mutex_;
    struct ShapeWatch { QPointer<QQuickItem> item; QMetaObject::Connection connection; };
    QList<ShapeWatch> shapes_;
    QMetaObject::Connection frame_, mainLayout_, residualLayout_;
    QPointer<QQuickItem> main_, residual_;
    int frames_ = 0;
    int layouts_ = 0;
    int drawnShapes_ = 0;
    double worst_ = 0;
    QString detail_;
    QVariantMap areas_, nonempty_;
};

static void registerPatternAreaLayouts() {
    qmlRegisterSingletonType<PatternAreaLayouts>("PatternAreaLayoutAcceptance", 1, 0, "AreaLayouts",
        [](QQmlEngine*, QJSEngine*) -> QObject* { return new PatternAreaLayouts; });
}
Q_COREAPP_STARTUP_FUNCTION(registerPatternAreaLayouts)
#include "test_pattern_area_layouts.moc"
