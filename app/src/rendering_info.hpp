// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_RENDERING_INFO_HPP
#define EDI_APP_RENDERING_INFO_HPP

#include <QObject>
#include <QPointer>
#include <QQuickWindow>
#include <QString>
#include <QtQml/qqmlregistration.h>

namespace edi_app {

/// What Qt Quick draws with (edi ADR-0041), named apart from Qt Quick's own attached GraphicsInfo, which the
/// structure view reads: the graphics API and, on OpenGL, the renderer, read in the first frame a
/// window renders. A software renderer (Mesa's llvmpipe and its kin, Qt Quick's own software backend) means no GPU, and
/// the Stacked view then paints its lines rather than drawing them on the GPU. The first detection is written once to
/// stderr, without Qt's debug logging.
class RenderingInfo : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON
    Q_PROPERTY(bool detected READ detected NOTIFY detectedChanged)
    // "OpenGL", "Metal", "Direct3D 11", "Direct3D 12", "Vulkan", "Software" (Qt Quick's own), empty until detected.
    Q_PROPERTY(QString api READ api NOTIFY detectedChanged)
    // The OpenGL renderer string (GL_RENDERER); empty for another API.
    Q_PROPERTY(QString renderer READ renderer NOTIFY detectedChanged)
    // Drawing without a GPU.
    Q_PROPERTY(bool software READ software NOTIFY detectedChanged)

   public:
    explicit RenderingInfo(QObject* parent = nullptr);

    bool detected() const { return detected_; }
    QString api() const { return api_; }
    QString renderer() const { return renderer_; }
    bool software() const { return software_; }

    /// Reads what `window` draws with in its next rendered frame, once a window has been read.
    Q_INVOKABLE void observe(QQuickWindow* window);

    /// Whether an API and renderer string name a software renderer.
    static bool isSoftware(const QString& api, const QString& renderer);

   signals:
    void detectedChanged();

   private:
    void setDetected(const QString& api, const QString& renderer);

    bool detected_ = false;
    QString api_, renderer_;
    bool software_ = false;
    QPointer<QQuickWindow> watched_;
};

}  // namespace edi_app

#endif  // EDI_APP_RENDERING_INFO_HPP
