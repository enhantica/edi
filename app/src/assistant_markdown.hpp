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
#include <QVariantMap>
#include <QtQml/qqmlregistration.h>

namespace edi_app {
/// Passive presentation of an already-retained reply, never a file/network resource door.
class AssistantMarkdown : public QQuickItem {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(QQuickTextDocument* document READ document WRITE setDocument NOTIFY documentChanged)
    Q_PROPERTY(QQuickItem* editor READ editor WRITE setEditor NOTIFY editorChanged)
    Q_PROPERTY(QString source READ source WRITE setSource NOTIFY sourceChanged)
    Q_PROPERTY(bool markdown READ markdown WRITE setMarkdown NOTIFY markdownChanged)
    Q_PROPERTY(QColor textColor READ textColor WRITE setTextColor NOTIFY textColorChanged)
    Q_PROPERTY(QColor accentColor READ accentColor WRITE setAccentColor NOTIFY accentColorChanged)
    Q_PROPERTY(QFont bodyFont READ bodyFont WRITE setBodyFont NOTIFY bodyFontChanged)
    Q_PROPERTY(QString monoFontFamily READ monoFontFamily WRITE setMonoFontFamily NOTIFY monoFontFamilyChanged)
    Q_PROPERTY(QColor tableBorderColor READ tableBorderColor WRITE setTableBorderColor NOTIFY tableBorderColorChanged)
    Q_PROPERTY(QColor tableShadeColor READ tableShadeColor WRITE setTableShadeColor NOTIFY tableShadeColorChanged)
    Q_PROPERTY(QColor tableBaseColor READ tableBaseColor WRITE setTableBaseColor NOTIFY tableBaseColorChanged)
 public:
    explicit AssistantMarkdown(QQuickItem* parent = nullptr);
    QQuickTextDocument* document() const;
    QQuickItem* editor() const;
    void setEditor(QQuickItem* editor);
    QString source() const;
    bool markdown() const;
    QColor textColor() const;
    void setTextColor(const QColor&);
    /// Copy retained TeX for a selected generated formula; whole selection preserves the original message.
    Q_INVOKABLE QString selectedSource(int start,int end) const;
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
 signals:
    void documentChanged();
    void editorChanged();
    void sourceChanged();
    void markdownChanged();
    void textColorChanged();
    void accentColorChanged();
    void bodyFontChanged();
    void monoFontFamilyChanged();
    void tableBorderColorChanged();
    void tableShadeColorChanged();
    void tableBaseColorChanged();
 protected:
    bool eventFilter(QObject*,QEvent*) override;
    void updatePolish() override;
    QSGNode* updatePaintNode(QSGNode*, UpdatePaintNodeData*) override;
    void geometryChange(const QRectF&, const QRectF&) override;
 private:
    struct Decoration { QRectF rect; QColor color; };
    std::vector<Decoration> decorations_;
    std::size_t decoration_high_water_ = 0;
    std::uint64_t presentation_revision_ = 0;
    QVariantMap property_notifications_;
    quint64 beginPropertyNotification(const QString& name, const QVariant& before);
    void completePropertyNotification(const QString& name, quint64 publication, const QVariant& value,
                                      void (AssistantMarkdown::*signal)());
    void render() noexcept;
    void restoreClipboardSource(int mode) noexcept;
    QPointer<QQuickItem> editor_;
    QMetaObject::Connection editor_destroyed_;
    bool copying_=false;
    void formatPresentation();
    QPointer<QQuickTextDocument> target_;
    QMetaObject::Connection target_destroyed_;
    QPointer<QTextDocument> document_;
    QString source_;
    bool markdown_ = false;
    QPointer<QQuickWindow> observed_window_;
    QColor text_color_;
    QColor accent_color_, table_border_color_, table_shade_color_, table_base_color_;
    QFont body_font_;
    QString mono_font_family_;
    bool body_font_set_ = false;
    qreal math_text_width_ = -1;
};
} // namespace edi_app
