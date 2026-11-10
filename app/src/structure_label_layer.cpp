// SPDX-License-Identifier: BSD-3-Clause
#include "structure_label_layer.hpp"

#include <QFontMetricsF>
#include <QPainter>

namespace edi_app {

StructureLabelLayer::StructureLabelLayer(QQuickItem* parent) : QQuickPaintedItem(parent) {
    setAntialiasing(true);
}

void StructureLabelLayer::setTexts(QList<Text> texts) {
    const bool counted = texts.size() != texts_.size();
    texts_ = std::move(texts);
    update();
    if (counted) {
        emit countChanged();
    }
}

void StructureLabelLayer::setFont(const QFont& font) {
    if (font != font_) {
        font_ = font;
        update();
        emit fontChanged();
    }
}

void StructureLabelLayer::setLetterFont(const QFont& font) {
    if (font != letter_font_) {
        letter_font_ = font;
        update();
        emit letterFontChanged();
    }
}

QString StructureLabelLayer::textAt(int index) const {
    return index >= 0 && index < texts_.size() ? texts_[index].text : QString();
}

QPointF StructureLabelLayer::positionAt(int index) const {
    return index >= 0 && index < texts_.size() ? texts_[index].at : QPointF();
}

void StructureLabelLayer::paint(QPainter* painter) {
    const QRectF bounds(0.0, 0.0, width(), height());
    for (const Text& text : texts_) {
        const QFont& font = text.letter ? letter_font_ : font_;
        const QFontMetricsF metrics(font);
        QRectF box = metrics.boundingRect(text.text);
        box.moveCenter(text.at);
        if (!bounds.intersects(box)) {
            continue;
        }
        painter->setFont(font);
        if (!text.letter) {
            // A halo in the background colour, as diffraction-lib's text shadow: the label reads on any atom.
            painter->setPen(text.halo);
            for (const QPointF offset : {QPointF(-1, 0), QPointF(1, 0), QPointF(0, -1), QPointF(0, 1),
                                         QPointF(-1, -1), QPointF(1, 1), QPointF(-1, 1), QPointF(1, -1)}) {
                painter->drawText(box.translated(offset), Qt::AlignCenter, text.text);
            }
        }
        painter->setPen(text.color);
        painter->drawText(box, Qt::AlignCenter, text.text);
    }
}

}  // namespace edi_app
