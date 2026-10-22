// SPDX-License-Identifier: BSD-3-Clause
#include "scan_layer.hpp"

#include <QColor>
#include <QImage>
#include <QPainter>
#include <QPainterPath>
#include <QPen>
#include <algorithm>
#include <cmath>
#include <limits>

#include "edi/palette.hpp"
#include "edi/presentation.hpp"
#include "edi/scan_views.hpp"

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
void ScanLayer::setColourMap(const QString& map) { assign(colour_map_, map, &ScanLayer::colourMapChanged); }
void ScanLayer::setBackground(const QColor& colour) { assign(background_, colour, &ScanLayer::backgroundChanged); }
void ScanLayer::setSmoothRows(bool smooth) { assign(smooth_rows_, smooth, &ScanLayer::smoothRowsChanged); }
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
    const edi::ScanMapColour colour = edi::scan_table_colour(
        edi::scan_colour_table(colour_map_.toStdString(), background_.name().toStdString(), dark_), t);
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
    const std::vector<double>& edges = model_->edges();
    const auto px = [this](double x) { return (x - x_min_) / (x_max_ - x_min_) * width(); };
    const auto py = [this](double y) { return (y_max_ - y) / (y_max_ - y_min_) * height(); };
    const std::size_t count = all.size();

    if (mode_ == QLatin1String("map")) {
        // The datasets read, in row order, each as its columns' values on the y scale.
        std::vector<std::size_t> order;
        for (std::size_t d = 0; d < count && d < rows.size() && d < spans.size(); ++d) {
            if (all[d].high.size() == ScanViewModel::kColumns && std::isfinite(rows[d])) {
                order.push_back(d);
            }
        }
        std::sort(order.begin(), order.end(), [&rows](std::size_t a, std::size_t b) { return rows[a] < rows[b]; });
        if (order.empty()) {
            return;
        }
        std::vector<std::vector<float>> values(order.size(), std::vector<float>(ScanViewModel::kColumns));
        for (std::size_t i = 0; i < order.size(); ++i) {
            for (std::size_t c = 0; c < ScanViewModel::kColumns; ++c) {
                values[i][c] = static_cast<float>(edi::to_display(all[order[i]].high[c], scale));
            }
        }
        const std::vector<edi::ScanMapColour> table =
            edi::scan_colour_table(colour_map_.toStdString(), background_.name().toStdString(), dark_);
        // One image pixel per plot pixel, so no row of the plot is drawn twice and nothing shows between datasets. Across,
        // each pixel takes the column its x falls in, on the axis shown (so on d-spacing too). Up, between two datasets'
        // rows the value is interpolated linearly, so the colour changes smoothly, or, stepped, is the nearer dataset's,
        // each dataset one band out to halfway to its neighbours; beyond the first or the last row, out to its extent,
        // it is that dataset's. A column one of the two leaves empty takes the other's value, and one both leave empty
        // stays clear.
        const int pixel_rows = std::max(1, static_cast<int>(std::ceil(height())));
        const int pixel_columns = std::max(1, static_cast<int>(std::ceil(width())));
        std::vector<int> column_of(static_cast<std::size_t>(pixel_columns));
        for (int i = 0; i < pixel_columns; ++i) {
            const double x = x_min_ + (static_cast<double>(i) + 0.5) / static_cast<double>(pixel_columns) * (x_max_ - x_min_);
            column_of[static_cast<std::size_t>(i)] = model_->columnAt(x);
        }
        QImage image(pixel_columns, pixel_rows, QImage::Format_ARGB32);
        image.fill(Qt::transparent);
        const double low_edge = spans[order.front()].low, high_edge = spans[order.back()].high;
        std::size_t below = 0;
        for (int j = 0; j < pixel_rows; ++j) {
            const double y = y_max_ - (static_cast<double>(j) + 0.5) / static_cast<double>(pixel_rows) * (y_max_ - y_min_);
            if (y < low_edge || y > high_edge) {
                continue;
            }
            while (below + 1 < order.size() && rows[order[below + 1]] <= y) {
                ++below;
            }
            std::size_t a = below, b = below;
            double f = 0.0;
            if (y > rows[order[below]] && below + 1 < order.size()) {
                b = below + 1;
                f = (y - rows[order[a]]) / (rows[order[b]] - rows[order[a]]);
                if (!smooth_rows_) {
                    f = f < 0.5 ? 0.0 : 1.0;
                }
            }
            QRgb* line = reinterpret_cast<QRgb*>(image.scanLine(j));
            for (int i = 0; i < pixel_columns; ++i) {
                const int c = column_of[static_cast<std::size_t>(i)];
                if (c < 0) {
                    continue;
                }
                const double va = values[a][static_cast<std::size_t>(c)], vb = values[b][static_cast<std::size_t>(c)];
                const double value = !std::isfinite(va) ? vb : !std::isfinite(vb) ? va : va + (vb - va) * f;
                const edi::ScanMapColour colour = edi::scan_table_colour(table, (value - display_min_) / span);
                line[i] = qRgba(colour.r, colour.g, colour.b, colour.a);
            }
        }
        painter->drawImage(QRectF(0, 0, static_cast<double>(pixel_columns), static_cast<double>(pixel_rows)), image);
        return;
    }

    // Stacked: each column a vertical stroke from its lowest to its highest value, joined column to column, so a
    // narrow peak stays at its height whatever the width.
    const double lift = model_->stackHeight();
    // The patterns' colours: a scheme's (ADR-0038); or a colour map's, a dataset at its place along the scan between
    // a tenth and nine tenths of the map, whose ends can be as dark or as light as a background; or a ramp from the
    // background to a scheme's first colour, starting a quarter of the way so the first pattern shows.
    const std::string choice = colour_scheme_.toStdString();
    const bool ramp = choice.starts_with("ramp:");
    const std::vector<std::string>& maps = edi::scan_colour_map_names();
    const bool map = std::find(maps.begin(), maps.end(), choice) != maps.end();
    const edi::ColourScheme scheme = edi::colour_scheme_or_default(ramp ? choice.substr(5) : choice);
    const std::vector<edi::ScanMapColour> table = ramp || map
                                                      ? edi::scan_colour_table(choice, background_.name().toStdString(), dark_)
                                                      : std::vector<edi::ScanMapColour>();
    const auto colour_of = [&](std::size_t d) {
        if (!ramp && !map) {
            return QColor(QString::fromStdString(edi::pattern_colour(scheme, d, count, dark_)));
        }
        const double place = count > 1 ? static_cast<double>(d) / static_cast<double>(count - 1) : 1.0;
        const edi::ScanMapColour c = edi::scan_table_colour(table, ramp ? 0.25 + 0.75 * place : 0.1 + 0.8 * place);
        return QColor(c.r, c.g, c.b);
    };
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
            const double x = px((edges[c] + edges[c + 1]) / 2.0);
            if (!std::isfinite(x)) {
                open = false;
                continue;
            }
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
        QPen pen(colour_of(d));
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

ScanColourBar::ScanColourBar(QQuickItem* parent) : QQuickPaintedItem(parent) {}

void ScanColourBar::setColourMap(const QString& map) {
    if (map != colour_map_) {
        colour_map_ = map;
        emit colourMapChanged();
        update();
    }
}

void ScanColourBar::setBackground(const QColor& colour) {
    if (colour != background_) {
        background_ = colour;
        emit backgroundChanged();
        update();
    }
}

void ScanColourBar::setDark(bool dark) {
    if (dark != dark_) {
        dark_ = dark;
        emit darkChanged();
        update();
    }
}

void ScanColourBar::paint(QPainter* painter) {
    const int rows = static_cast<int>(std::ceil(height()));
    if (rows <= 0 || width() <= 0.0) {
        return;
    }
    const std::vector<edi::ScanMapColour> table =
        edi::scan_colour_table(colour_map_.toStdString(), background_.name().toStdString(), dark_);
    QImage image(1, rows, QImage::Format_ARGB32);
    for (int j = 0; j < rows; ++j) {
        const double t = rows == 1 ? 1.0 : 1.0 - static_cast<double>(j) / static_cast<double>(rows - 1);
        const edi::ScanMapColour colour = edi::scan_table_colour(table, t);
        image.setPixel(0, j, qRgba(colour.r, colour.g, colour.b, colour.a));
    }
    painter->setRenderHint(QPainter::SmoothPixmapTransform, false);
    painter->drawImage(QRectF(0, 0, width(), static_cast<double>(rows)), image);
}

}  // namespace edi_app
