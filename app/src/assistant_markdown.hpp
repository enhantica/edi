// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QObject>
#include <QPointer>
#include <QQuickTextDocument>
#include <QString>
#include <QtQml/qqmlregistration.h>

namespace edi_app {
/// Passive presentation of an already-retained reply, never a file/network resource door.
class AssistantMarkdown : public QObject {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(QQuickTextDocument* document READ document WRITE setDocument)
    Q_PROPERTY(QString source READ source WRITE setSource)
    Q_PROPERTY(bool markdown READ markdown WRITE setMarkdown)
 public:
    explicit AssistantMarkdown(QObject* parent = nullptr);
    QQuickTextDocument* document() const;
    QString source() const;
    bool markdown() const;
    void setDocument(QQuickTextDocument* document);
    void setSource(const QString& source);
    void setMarkdown(bool markdown);
 private:
    void render() noexcept;
    QPointer<QQuickTextDocument> target_;
    QPointer<QTextDocument> document_;
    QString source_;
    bool markdown_ = false;
};
} // namespace edi_app
