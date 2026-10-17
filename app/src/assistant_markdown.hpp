// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QObject>
#include <QColor>
#include <QFont>
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
    Q_PROPERTY(QColor accentColor READ accentColor WRITE setAccentColor)
    Q_PROPERTY(QFont bodyFont READ bodyFont WRITE setBodyFont)
    Q_PROPERTY(QString monoFontFamily READ monoFontFamily WRITE setMonoFontFamily)
    Q_PROPERTY(QColor tableBorderColor READ tableBorderColor WRITE setTableBorderColor)
    Q_PROPERTY(QColor tableShadeColor READ tableShadeColor WRITE setTableShadeColor)
 public:
    explicit AssistantMarkdown(QObject* parent = nullptr);
    QQuickTextDocument* document() const;
    QString source() const;
    bool markdown() const;
    QColor accentColor() const;
    void setAccentColor(const QColor& color);
    QFont bodyFont() const;
    QString monoFontFamily() const;
    QColor tableBorderColor() const;
    QColor tableShadeColor() const;
    void setBodyFont(const QFont& font);
    void setMonoFontFamily(const QString& family);
    void setTableBorderColor(const QColor& color);
    void setTableShadeColor(const QColor& color);
    void setDocument(QQuickTextDocument* document);
    void setSource(const QString& source);
    void setMarkdown(bool markdown);
 private:
    void render() noexcept;
    void formatPresentation();
    QPointer<QQuickTextDocument> target_;
    QPointer<QTextDocument> document_;
    QString source_;
    bool markdown_ = false;
    QColor accent_color_, table_border_color_, table_shade_color_;
    QFont body_font_;
    QString mono_font_family_;
    bool body_font_set_ = false;
};
} // namespace edi_app
