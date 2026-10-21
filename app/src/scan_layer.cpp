// SPDX-License-Identifier: BSD-3-Clause
#include "scan_layer.hpp"

#include <QColor>
#include <QImage>
#include <QPainter>
#include <QPainterPath>
#include <QPen>
#include <cmath>
#include <limits>

#include "edi/palette.hpp"
#include "edi/presentation.hpp"

namespace edi_app {

namespace {

edi::YScale scale_of(const QString& scale) {
    return scale == QLatin1String("log")    ? edi::YScale::Log10
           : scale == QLatin1String("sqrt") ? edi::YScale::Sqrt
                                            : edi::YScale::Linear;
}

}  // namespace

ScanLayer::ScanLayer(QQuickItem* parent) : QQuickPaintedItem(parent) { setAntialiasing(true); }

void ScanLayer::setModel(ScanViewModel* model) {
    if (model == model_) {
        return;
    }
    if (model_) {
        disconnect(model_, nullptr, this, nullptr);
    }
    model_ = model;
    if (model_) {
        connect(model_, &ScanViewModel::revisionChanged, this, [this] {
            measure();
            update();
        });
    }
    measure();
    emit modelChanged();
    update();
}

void ScanLayer::setMode(const QString& mode) { assign(mode_, mode, &ScanLayer::modeChanged); }
void ScanLayer::setXMin(double value) { assign(x_min_, value, &ScanLayer::xMinChanged); }
void ScanLayer::setXMax(double value) { assign(x_max_, value, &ScanLayer::xMaxChanged); }
void ScanLayer::setYMin(double value) { assign(y_min_, value, &ScanLayer::yMinChanged); }
void ScanLayer::setYMax(double value) { assign(y_max_, value, &ScanLayer::yMaxChanged); }
void ScanLayer::setColourScheme(const QString& scheme) { assign(colour_scheme_, scheme, &ScanLayer::colourSchemeChanged); }
void ScanLayer::setDark(bool dark) { assign(dark_, dark, &ScanLayer::darkChanged); }
void ScanLayer::setCurrent(int dataset) { assign(current_, dataset, &ScanLayer::currentChanged); }

void ScanLayer::setScale(const QString& scale) {
    if (scale != scale_) {
        scale_ = scale;
        measure();
        emit scaleChanged();
        update();
    }
}

// Every read dataset's lowest and highest value on the y scale: the ends of the intensity the views spread.
void ScanLayer::measure() {
    double low = std::numeric_limits<double>::infinity(), high = -low;
    if (model_) {
        const edi::YScale scale = scale_of(scale_);
        for (const edi::ScanColumns& columns : model_->columns()) {
            for (std::size_t i = 0; i < columns.high.size(); ++i) {
                const double a = edi::to_display(columns.low[i], scale), b = edi::to_display(columns.high[i], scale);
                if (std::isfinite(a)) {
                    low = std::min(low, a);
                }
                if (std::isfinite(b)) {
                    high = std::max(high, b);
                }
            }
        }
    }
    if (!(high > low)) {
        low = 0.0;
        high = 1.0;
    }
    if (low != display_min_) {
        display_min_ = low;
        emit displayMinChanged();
    }
    if (high != display_max_) {
        display_max_ = high;
        emit displayMaxChanged();
    }
}

QColor ScanLayer::mapColour(double t) const {
    const edi::ScanMapColour colour = edi::scan_map_colour(t);
    return QColor(colour.r, colour.g, colour.b, colour.a);
}

void ScanLayer::paint(QPainter* painter) {
    if (!model_ || !(x_max_ > x_min_) || !(y_max_ > y_min_) || width() <= 0.0 || height() <= 0.0) {
        return;
    }
    const std::vector<edi::ScanColumns>& all = model_->columns();
    const std::vector<double>& rows = model_->rows();
    const std::vector<edi::ScanRowSpan>& spans = model_->spans();
    const edi::YScale scale = scale_of(scale_);
    const double span = display_max_ - display_min_;
    const double x_left = model_->xMin(), x_width = (model_->xMax() - model_->xMin()) / ScanViewModel::kColumns;
    const auto px = [this](double x) { return (x - x_min_) / (x_max_ - x_min_) * width(); };
    const auto py = [this](double y) { return (y_max_ - y) / (y_max_ - y_min_) * height(); };
    const std::size_t count = all.size();

    if (mode_ == QLatin1String("map")) {
        // One image row per dataset, stretched over the dataset's row extent; a column with no point is left clear.
        QImage image(static_cast<int>(ScanViewModel::kColumns), 1, QImage::Format_ARGB32);
        painter->setRenderHint(QPainter::SmoothPixmapTransform, false);
        const QRectF source(0, 0, static_cast<qreal>(ScanViewModel::kColumns), 1);
        const QRectF across(px(x_left), 0, px(model_->xMax()) - px(x_left), 0);
        for (std::size_t d = 0; d < count && d < spans.size(); ++d) {
            const edi::ScanColumns& columns = all[d];
            if (columns.high.size() != ScanViewModel::kColumns) {
                continue;
            }
            for (std::size_t c = 0; c < ScanViewModel::kColumns; ++c) {
                const double value = edi::to_display(columns.high[c], scale);
                const edi::ScanMapColour colour = edi::scan_map_colour((value - display_min_) / span);
                image.setPixel(static_cast<int>(c), 0, qRgba(colour.r, colour.g, colour.b, colour.a));
            }
            const double top = py(spans[d].high), bottom = py(spans[d].low);
            painter->drawImage(QRectF(across.x(), top, across.width(), std::max(1.0, bottom - top)), image, source);
        }
        return;
    }

    // Stacked: each column a vertical stroke from its lowest to its highest value, joined column to column, so a
    // narrow peak stays at its height whatever the width.
    const double lift = model_->stackHeight();
    const edi::ColourScheme scheme = edi::colour_scheme_or_default(colour_scheme_.toStdString());
    const auto draw = [&](std::size_t d, qreal width_px) {
        const edi::ScanColumns& columns = all[d];
        if (columns.high.size() != ScanViewModel::kColumns || d >= rows.size()) {
            return;
        }
        QPainterPath path;
        bool open = false;
        for (std::size_t c = 0; c < ScanViewModel::kColumns; ++c) {
            const double low = edi::to_display(columns.low[c], scale), high = edi::to_display(columns.high[c], scale);
            if (!std::isfinite(low) || !std::isfinite(high)) {
                open = false;
                continue;
            }
            const double x = px(x_left + (static_cast<double>(c) + 0.5) * x_width);
            const double y_low = py(rows[d] + (low - display_min_) / span * lift);
            const double y_high = py(rows[d] + (high - display_min_) / span * lift);
            if (open) {
                path.lineTo(x, y_low);
            } else {
                path.moveTo(x, y_low);
                open = true;
            }
            path.lineTo(x, y_high);
        }
        QPen pen(QColor(QString::fromStdString(edi::pattern_colour(scheme, d, count, dark_))));
        pen.setWidthF(width_px);
        pen.setCosmetic(true);
        painter->setPen(pen);
        painter->setBrush(Qt::NoBrush);
        painter->drawPath(path);
    };
    // From the top row down, so a lower pattern is drawn over the ones it rises into.
    std::vector<std::size_t> order(count);
    for (std::size_t d = 0; d < count; ++d) {
        order[d] = d;
    }
    std::sort(order.begin(), order.end(), [&rows](std::size_t a, std::size_t b) {
        return a < rows.size() && b < rows.size() ? rows[a] > rows[b] : a < b;
    });
    for (const std::size_t d : order) {
        if (static_cast<int>(d) != current_) {
            draw(d, 1.0);
        }
    }
    if (current_ >= 0 && static_cast<std::size_t>(current_) < count) {
        draw(static_cast<std::size_t>(current_), 2.0);
    }
}

}  // namespace edi_app
