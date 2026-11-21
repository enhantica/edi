// SPDX-License-Identifier: BSD-3-Clause
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
#include "engine_setup.hpp"
Q_IMPORT_QML_PLUGIN(edi_appPlugin)

class ChartHoverTests : public QObject {
    Q_OBJECT
private slots:
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
            auto* area = new QAreaSeries(view);
            QVERIFY(QMetaObject::invokeMethod(view, "addSeries", Q_ARG(QObject*, area)));
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
