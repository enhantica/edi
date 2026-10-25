// SPDX-License-Identifier: BSD-3-Clause
#include <QCoreApplication>
#include <QHash>
#include <QDir>
#include <QFileInfo>
#include <QObject>
#include <QMutex>
#include <QMutexLocker>
#include <QOpenGLContext>
#include <QOpenGLFunctions>
#include <QJsonDocument>
#include <QQuickItem>
#include <QQuickPaintedItem>
#include <QQuickWindow>
#include <QSGRendererInterface>
#include <QSettings>
#include <QUrl>
#include <QVariantMap>
#include <QQmlContext>
#include <QQmlEngine>
#include <QtQml/qqml.h>
#include "engine_setup.hpp"

class ChartBackendProof : public QObject {
    Q_OBJECT
public:
    explicit ChartBackendProof(QQmlEngine* engine) : QObject(engine), engine_(engine) {}
    Q_INVOKABLE bool painted(QObject* object) const {
        return qobject_cast<QQuickPaintedItem*>(object) != nullptr;
    }
    Q_INVOKABLE bool gpu(QQuickItem* item) const {
        if (!item || !item->window()) return false;
        const auto api = item->window()->rendererInterface()->graphicsApi();
        return api != QSGRendererInterface::Unknown && api != QSGRendererInterface::Software;
    }
    Q_INVOKABLE void watch(QQuickItem* item) {
        auto* window = item ? item->window() : nullptr;
        if (!window || window->property("chartAcceptanceWatched").toBool()) return;
        window->setProperty("chartAcceptanceWatched", true);
        connect(window, &QQuickWindow::beforeRendering, this, [this, window] {
            const auto api = window->rendererInterface()->graphicsApi();
            const char* name = "Unknown";
            switch (api) {
                case QSGRendererInterface::Software: name = "Software"; break;
                case QSGRendererInterface::OpenVG: name = "OpenVG"; break;
                case QSGRendererInterface::OpenGL: name = "OpenGL"; break;
                case QSGRendererInterface::Direct3D11: name = "Direct3D11"; break;
                case QSGRendererInterface::Vulkan: name = "Vulkan"; break;
                case QSGRendererInterface::Metal: name = "Metal"; break;
                case QSGRendererInterface::Null: name = "Null"; break;
                case QSGRendererInterface::Direct3D12: name = "Direct3D12"; break;
                default: break;
            }
            QString renderer;
            if (api == QSGRendererInterface::OpenGL) {
                auto* context = QOpenGLContext::currentContext();
                const auto* value = context ? context->functions()->glGetString(GL_RENDERER) : nullptr;
                if (value) renderer = QString::fromUtf8(reinterpret_cast<const char*>(value));
            }
            const QVariantMap observed{{"api", QString::fromLatin1(name ? name : "Unknown")},
                                       {"renderer", renderer}};
            QMutexLocker guard(&mutex_);
            if (facts_.value(window) == observed) return;
            facts_[window] = observed;
            qInfo().noquote() << "RENDERING_REFERENCE " + QJsonDocument::fromVariant(observed).toJson(QJsonDocument::Compact);
        }, Qt::DirectConnection);
        connect(window, &QObject::destroyed, this, [this, window] {
            QMutexLocker guard(&mutex_);
            facts_.remove(window);
        });
        window->update();
    }
    Q_INVOKABLE QVariantMap facts(QQuickItem* item) const {
        QMutexLocker guard(&mutex_);
        return item && item->window() ? facts_.value(item->window()) : QVariantMap{};
    }
    Q_INVOKABLE QUrl store() const {
        return QUrl::fromLocalFile(qEnvironmentVariable("EDI_RENDER_ACCEPTANCE_STORE"));
    }
    Q_INVOKABLE void useStore() {
        if (qEnvironmentVariableIsEmpty("EDI_RENDER_ACCEPTANCE_STORE")) return;
        QDir root = QFileInfo(store().toLocalFile()).absoluteDir();
        root.cdUp();
        QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, root.absolutePath());
        edi_app::configure_engine(*engine_);
    }
    Q_INVOKABLE QString phase() const { return qEnvironmentVariable("EDI_RENDER_ACCEPTANCE_PHASE"); }
    Q_INVOKABLE QString choice() const { return qEnvironmentVariable("EDI_RENDER_ACCEPTANCE_CHOICE"); }

private:
    mutable QMutex mutex_;
    QHash<QQuickWindow*, QVariantMap> facts_;
    QQmlEngine* engine_;
};

static void registerChartBackendProof() {
    qmlRegisterSingletonType<ChartBackendProof>("ChartBackendAcceptance", 1, 0, "ChartBackendProof",
        [](QQmlEngine* engine, QJSEngine*) -> QObject* { return new ChartBackendProof(engine); });
}
Q_COREAPP_STARTUP_FUNCTION(registerChartBackendProof)
#include "test_chart_backend_observer.moc"
