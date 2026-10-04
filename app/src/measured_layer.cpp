// SPDX-License-Identifier: BSD-3-Clause
#include "measured_layer.hpp"

#include <QImage>
#include <QLineF>
#include <QPainter>
#include <QQuickWindow>
#include <QSGImageNode>
#include <QSGTexture>
#include <cmath>

namespace edi_app {

MeasuredLayer::MeasuredLayer(QQuickItem* parent) : QQuickItem(parent) {
    setFlag(ItemHasContents, true);
    for (const auto changed : {&MeasuredLayer::xMinChanged, &MeasuredLayer::xMaxChanged, &MeasuredLayer::yMinChanged,
                               &MeasuredLayer::yMaxChanged}) {
        connect(this, changed, this, &QQuickItem::update);
    }
    connect(this, &QQuickItem::widthChanged, this, &QQuickItem::update);
    connect(this, &QQuickItem::heightChanged, this, &QQuickItem::update);
}

void MeasuredLayer::setColor(const QColor& color) {
    if (color != color_) {
        color_ = color;
        emit colorChanged();
        update();
    }
}

void MeasuredLayer::setMarkerSize(qreal size) {
    if (size != marker_size_) {
        marker_size_ = size;
        emit markerSizeChanged();
        update();
    }
}

void MeasuredLayer::setData(const QList<QPointF>& points, const QList<double>& low, const QList<double>& high) {
    const bool resized = points.size() != points_.size();
    points_ = points;
    low_ = low;
    high_ = high;
    ++revision_;
    if (resized) {
        emit countChanged();
    }
    emit revisionChanged();
    update();
}

// Every marker and every bar is painted into one image, which the scene graph draws as one textured node.
// An image node is drawn by every Qt Quick renderer, the software one included; a geometry node of this
// item's own is not (nothing was drawn on the offscreen platform).
QSGNode* MeasuredLayer::updatePaintNode(QSGNode* old, UpdatePaintNodeData* /*data*/) {
    auto* node = static_cast<QSGImageNode*>(old);
    const qreal ratio = window() != nullptr ? window()->effectiveDevicePixelRatio() : 1.0;
    const QSize pixels(static_cast<int>(std::ceil(width() * ratio)), static_cast<int>(std::ceil(height() * ratio)));
    const double x_span = x_max_ - x_min_, y_span = y_max_ - y_min_;
    if (window() == nullptr || pixels.isEmpty() || !(x_span > 0.0) || !(y_span > 0.0)) {
        delete node;
        return nullptr;
    }
    QImage image(pixels, QImage::Format_ARGB32_Premultiplied);
    image.fill(Qt::transparent);
    const double w = pixels.width(), h = pixels.height();
    const auto px = [&](double x) { return (x - x_min_) / x_span * w; };
    const auto py = [&](double y) { return (y_max_ - y) / y_span * h; };
    {
        QPainter painter(&image);
        const bool with_bars = low_.size() == points_.size() && high_.size() == points_.size();
        if (with_bars) {
            QList<QLineF> bars;
            bars.reserve(points_.size());
            for (qsizetype i = 0; i < points_.size(); ++i) {
                const double x = std::floor(px(points_[i].x())) + 0.5;
                // A lower end that cannot be drawn on this scale runs to the bottom of the pane.
                const double bottom = std::isnan(low_[i]) ? h : py(low_[i]);
                const double top = std::isnan(high_[i]) ? py(points_[i].y()) : py(high_[i]);
                bars.append(QLineF(x, bottom, x, top));
            }
            painter.setPen(QPen(color_, std::max(1.0, ratio)));
            painter.drawLines(bars);
        }
        // One marker, drawn once with smooth edges and then stamped at every point.
        const int size = std::max(1, static_cast<int>(std::lround(marker_size_ * ratio)));
        QImage marker(size, size, QImage::Format_ARGB32_Premultiplied);
        marker.fill(Qt::transparent);
        {
            QPainter stamp(&marker);
            stamp.setRenderHint(QPainter::Antialiasing);
            stamp.setPen(Qt::NoPen);
            stamp.setBrush(color_);
            stamp.drawEllipse(QRectF(0, 0, size, size));
        }
        const double half = size / 2.0;
        for (const QPointF& point : points_) {
            painter.drawImage(QPointF(std::round(px(point.x()) - half), std::round(py(point.y()) - half)), marker);
        }
    }
    if (node == nullptr) {
        node = window()->createImageNode();
        node->setOwnsTexture(true);
        node->setFiltering(QSGTexture::Nearest);
    }
    node->setTexture(window()->createTextureFromImage(image, QQuickWindow::TextureHasAlphaChannel));
    node->setRect(0, 0, width(), height());
    return node;
}

}  // namespace edi_app
