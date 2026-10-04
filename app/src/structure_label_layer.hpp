// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_STRUCTURE_LABEL_LAYER_HPP
#define EDI_APP_STRUCTURE_LABEL_LAYER_HPP

#include <QColor>
#include <QFont>
#include <QList>
#include <QPointF>
#include <QQuickPaintedItem>
#include <QString>
#include <QtQml/qqmlregistration.h>

namespace edi_app {

// The structure view's text over the 3D scene (edi ADR-0017 §16): the atom labels and the three axis
// letters, as one painted item, at the places the core's edi::project gives — the same projection the camera
// draws with, so a label stays on its atom in both cameras. No QML object per label. Only text inside the
// item is painted.
class StructureLabelLayer : public QQuickPaintedItem {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(QFont font READ font WRITE setFont NOTIFY fontChanged)
    Q_PROPERTY(QFont letterFont READ letterFont WRITE setLetterFont NOTIFY letterFontChanged)
    Q_PROPERTY(int count READ count NOTIFY countChanged)

   public:
    struct Text {
        QPointF at;
        QString text;
        QColor color, halo;
        bool letter = false;  // an axis letter: the letter font, no halo
    };

    explicit StructureLabelLayer(QQuickItem* parent = nullptr);

    void setTexts(QList<Text> texts);
    void paint(QPainter* painter) override;
    QFont font() const { return font_; }
    void setFont(const QFont& font);
    QFont letterFont() const { return letter_font_; }
    void setLetterFont(const QFont& font);
    int count() const { return static_cast<int>(texts_.size()); }
    Q_INVOKABLE QString textAt(int index) const;
    Q_INVOKABLE QPointF positionAt(int index) const;

   signals:
    void fontChanged();
    void letterFontChanged();
    void countChanged();

   private:
    QList<Text> texts_;
    QFont font_, letter_font_;
};

}  // namespace edi_app

#endif  // EDI_APP_STRUCTURE_LABEL_LAYER_HPP
