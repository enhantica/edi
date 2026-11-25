// SPDX-License-Identifier: BSD-3-Clause
#include <limits>
#include <memory>
#include <vector>
#include <QGuiApplication>
#include <QHoverEvent>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QQuickItem>
#include <QQuickWindow>
#include <QtGraphs/QAreaSeries>
#include <QtGraphs/QLineSeries>
#include <QtTest/QtTest>
#include <QtQml/qqmlextensionplugin.h>
#include "chart_area.hpp"
#include "engine_setup.hpp"
Q_IMPORT_QML_PLUGIN(edi_appPlugin)

class ChartHoverTests : public QObject {
    Q_OBJECT
private slots:
    // Qt fills an area by triangulating all of it: a point far outside the plot crashed that.
    void areasEndOneRangeOutsideThePlot() {
        constexpr double inf = std::numeric_limits<double>::infinity(), nan = std::numeric_limits<double>::quiet_NaN();
        const edi_app::AreaRange range{0.0, 10.0, 0.0, 1.0};
        const QList<QPointF> curve{{-1e9, 0.5}, {1.0, 0.2}, {2.0, 1e12}, {3.0, 0.4},
                                   {4.0, inf}, {5.0, nan}, {6.0, 0.3}, {1e9, 0.3}};
        const std::vector<double> base{0.0, 0.0, 0.0, -1e12, 0.0, 0.0, -inf, 0.0};
        const edi_app::AreaEdges area = edi_app::area_edges(curve, base, 0.0, 0.01, range);
        QCOMPARE(area.upper.size(), area.lower.size());
        for (qsizetype k = 0; k < area.upper.size(); ++k) {
            const QPointF up = area.upper[k], low = area.lower[k];
            QCOMPARE(up.x(), low.x());
            QVERIFY(up.x() >= -10.0 && up.x() <= 20.0 && (k == 0 || up.x() >= area.upper[k - 1].x()));
            QVERIFY(low.y() >= -1.0 && up.y() <= 2.0 && up.y() >= low.y());
        }
        // What is inside the plot is drawn where it was.
        QVERIFY(area.upper.contains(QPointF(1.0, 0.2)) && area.upper.contains(QPointF(3.0, 0.4)));
        // No finite range, no area.
        QVERIFY(edi_app::area_edges(curve, base, 0.0, 0.01, {0.0, 10.0, 0.0, inf}).upper.isEmpty());
        QVERIFY(edi_app::area_edges(curve, base, 0.0, 0.01, {5.0, 5.0, 0.0, 1.0}).upper.isEmpty());
        // A curve within its range keeps its points.
        const QList<QPointF> plain{{0.0, 0.1}, {5.0, 0.9}, {10.0, 0.1}};
        QCOMPARE(edi_app::area_edges(plain, {}, 0.0, 0.01, range).upper, plain);
    }
    void removedSeriesNeverReachNativeHover() {
        QQmlEngine engine;
        edi_app::configure_engine(engine);
        QQmlComponent component(&engine);
        component.setData(R"(
            import QtQuick
            import QtGraphs
            import edi.app
            ChartView {
                width: 480; height: 320
                axisX: ValueAxis { min: 0; max: 10 }
                axisY: ValueAxis { min: 0; max: 10 }
            }
        )", QUrl());
        QQuickWindow window;
        window.resize(480, 320);
        window.show();
        QVERIFY(QTest::qWaitForWindowExposed(&window));
        for (int viewIndex = 0; viewIndex < 4; ++viewIndex) {
            QScopedPointer<QObject> object(component.create());
            QVERIFY2(object, qPrintable(component.errorString()));
            auto* view = qobject_cast<QQuickItem*>(object.data());
            QVERIFY(view);
            view->setParentItem(window.contentItem());
            QVERIFY(!view->acceptHoverEvents());
            // Held until the view takes it, so a failed add does not leak it.
            auto added = std::make_unique<QAreaSeries>(view);
            QVERIFY(QMetaObject::invokeMethod(view, "addSeries", Q_ARG(QObject*, added.get())));
            auto* area = added.release();
            for (int index = 0; index < 50; ++index) {
                auto* upper = new QLineSeries(area);
                auto* lower = new QLineSeries(area);
                upper->append(0, 4); upper->append(10, 8);
                lower->append(0, 1); lower->append(10, 2);
                upper->setHoverable(true);
                lower->setHoverable(true);
                area->setUpperSeries(upper);
                area->setLowerSeries(lower);
                auto* line = new QLineSeries(view);
                line->append(0, 0); line->append(10, 10);
                line->setHoverable(true);
                QVERIFY(QMetaObject::invokeMethod(view, "addSeries", Q_ARG(QObject*, line)));
                QVERIFY(QTest::qWaitForWindowActive(&window));
                view->ensurePolished();
                QTest::qWait(1);
                QVERIFY(QMetaObject::invokeMethod(view, "removeSeries", Q_ARG(QObject*, line)));
                delete line;
                area->setUpperSeries(nullptr);
                area->setLowerSeries(nullptr);
                delete upper;
                delete lower;
                // No event processing/polish between deletion and these events.
                for (auto type : {QEvent::HoverEnter, QEvent::HoverMove, QEvent::HoverLeave}) {
                    QHoverEvent event(type, QPointF(200, 150), QPointF(200, 150), QPointF(190, 150));
                    QCoreApplication::sendEvent(view, &event);
                    QVERIFY(!event.isAccepted());
                }
            }
            // Destroy the chart while its renderer has series, then deliver an ordinary mouse move.
            object.reset();
            QTest::mouseMove(&window, QPoint(205, 155));
            QCoreApplication::processEvents();
        }
    }
};
int main(int argc, char** argv) {
    QGuiApplication app(argc, argv);
    ChartHoverTests tests;
    return QTest::qExec(&tests, argc, argv);
}
#include "chart_hover_tests.moc"
