// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QQuickItem>
#include <QRectF>
#include <vector>
#include <cstdint>
#include <QColor>
#include <QFont>
#include <QPointer>
#include <QQuickTextDocument>
#include <QString>
#include <QtQml/qqmlregistration.h>

namespace edi_app {
/// Passive presentation of an already-retained reply, never a file/network resource door.
class AssistantMarkdown : public QQuickItem {
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
    Q_PROPERTY(QColor tableBaseColor READ tableBaseColor WRITE setTableBaseColor)
 public:
    explicit AssistantMarkdown(QQuickItem* parent = nullptr);
    QQuickTextDocument* document() const;
    QString source() const;
    bool markdown() const;
    QColor accentColor() const;
    void setAccentColor(const QColor& color);
    QFont bodyFont() const;
    QString monoFontFamily() const;
    QColor tableBorderColor() const;
    QColor tableShadeColor() const;
    QColor tableBaseColor() const;
    void setBodyFont(const QFont& font);
    void setMonoFontFamily(const QString& family);
    void setTableBorderColor(const QColor& color);
    void setTableShadeColor(const QColor& color);
    void setTableBaseColor(const QColor& color);
    void setDocument(QQuickTextDocument* document);
    void setSource(const QString& source);
    void setMarkdown(bool markdown);
 protected:
    void updatePolish() override;
    QSGNode* updatePaintNode(QSGNode*, UpdatePaintNodeData*) override;
    void geometryChange(const QRectF&, const QRectF&) override;
 private:
    struct Decoration { QRectF rect; QColor color; };
    std::vector<Decoration> decorations_;
    std::size_t decoration_high_water_ = 0;
    std::uint64_t presentation_revision_ = 0;
    void render() noexcept;
    void formatPresentation();
    QPointer<QQuickTextDocument> target_;
    QPointer<QTextDocument> document_;
    QString source_;
    bool markdown_ = false;
    QColor accent_color_, table_border_color_, table_shade_color_, table_base_color_;
    QFont body_font_;
    QString mono_font_family_;
    bool body_font_set_ = false;
};
} // namespace edi_app
