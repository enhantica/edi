// SPDX-License-Identifier: BSD-3-Clause
#include "graphics_info.hpp"

#include <QOpenGLContext>
#include <QOpenGLFunctions>
#include <QQuickWindow>
#include <QSGRendererInterface>
#include <cstdio>
#include <memory>

namespace edi_app {

namespace {

QString api_name(QSGRendererInterface::GraphicsApi api) {
    switch (api) {
        case QSGRendererInterface::OpenGL:
            return QStringLiteral("OpenGL");
        case QSGRendererInterface::Metal:
            return QStringLiteral("Metal");
        case QSGRendererInterface::Direct3D11:
            return QStringLiteral("Direct3D 11");
        case QSGRendererInterface::Direct3D12:
            return QStringLiteral("Direct3D 12");
        case QSGRendererInterface::Vulkan:
            return QStringLiteral("Vulkan");
        case QSGRendererInterface::Software:
            return QStringLiteral("Software");
        default:
            return QStringLiteral("Unknown");
    }
}

}  // namespace

GraphicsInfo::GraphicsInfo(QObject* parent) : QObject(parent) {}

bool GraphicsInfo::isSoftware(const QString& api, const QString& renderer) {
    if (api == QLatin1String("Software")) {
        return true;
    }
    // Mesa's CPU rasterisers, Google's SwiftShader (WebGL without a GPU) and Microsoft's.
    for (const char* name : {"llvmpipe", "softpipe", "swrast", "software rasterizer", "swiftshader", "lavapipe",
                             "microsoft basic render"}) {
        if (renderer.contains(QLatin1String(name), Qt::CaseInsensitive)) {
            return true;
        }
    }
    return false;
}

void GraphicsInfo::observe(QQuickWindow* window) {
    if (window == nullptr || detected_ || watched_ == window) {
        return;
    }
    watched_ = window;
    // On the render thread, while the GUI thread waits: read once, hand over to the GUI thread.
    auto connection = std::make_shared<QMetaObject::Connection>();
    *connection = connect(
        window, &QQuickWindow::beforeRendering, window,
        [this, window, connection] {
            QObject::disconnect(*connection);
            const QSGRendererInterface* renderer_interface = window->rendererInterface();
            const QSGRendererInterface::GraphicsApi api =
                renderer_interface != nullptr ? renderer_interface->graphicsApi() : QSGRendererInterface::Unknown;
            QString renderer;
            if (api == QSGRendererInterface::OpenGL && QOpenGLContext::currentContext() != nullptr) {
                const auto* text = reinterpret_cast<const char*>(
                    QOpenGLContext::currentContext()->functions()->glGetString(GL_RENDERER));
                renderer = QString::fromLatin1(text != nullptr ? text : "");
            }
            const QString name = api_name(api);
            QMetaObject::invokeMethod(this, [this, name, renderer] { setDetected(name, renderer); }, Qt::QueuedConnection);
        },
        Qt::DirectConnection);
    window->update();
}

void GraphicsInfo::setDetected(const QString& api, const QString& renderer) {
    if (detected_) {
        return;
    }
    detected_ = true;
    api_ = api;
    renderer_ = renderer;
    software_ = isSoftware(api, renderer);
    std::fprintf(stderr, "edi: graphics: %s%s%s, %s\n", qPrintable(api_), renderer_.isEmpty() ? "" : ", renderer ",
                 qPrintable(renderer_), software_ ? "software rendering (no GPU)" : "hardware rendering");
    std::fflush(stderr);
    emit detectedChanged();
}

}  // namespace edi_app
