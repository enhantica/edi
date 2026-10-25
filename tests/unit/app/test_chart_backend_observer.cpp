// SPDX-License-Identifier: BSD-3-Clause
#include <QCoreApplication>
#include <QObject>
#include <QQuickItem>
#include <QQuickPaintedItem>
#include <QQuickWindow>
#include <QSGRendererInterface>
#include <QtQml/qqml.h>

class ChartBackendProof : public QObject {
    Q_OBJECT
public:
    using QObject::QObject;
    Q_INVOKABLE bool painted(QObject* object) const {
        return qobject_cast<QQuickPaintedItem*>(object) != nullptr;
    }
    Q_INVOKABLE bool gpu(QQuickItem* item) const {
        if (!item || !item->window()) return false;
        const auto api = item->window()->rendererInterface()->graphicsApi();
        return api != QSGRendererInterface::Unknown && api != QSGRendererInterface::Software;
    }
};

static void registerChartBackendProof() {
    qmlRegisterSingletonType<ChartBackendProof>("ChartBackendAcceptance", 1, 0, "ChartBackendProof",
        [](QQmlEngine*, QJSEngine*) -> QObject* { return new ChartBackendProof; });
}
Q_COREAPP_STARTUP_FUNCTION(registerChartBackendProof)
#include "test_chart_backend_observer.moc"
