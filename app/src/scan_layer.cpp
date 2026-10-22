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
void ScanLayer::setReversed(bool reversed) { assign(reversed_, reversed, &ScanLayer::reversedChanged); }
void ScanLayer::setDark(bool dark) { assign(dark_, dark, &ScanLayer::darkChanged); }
void ScanLayer::setCurrent(int dataset) { assign(current_, dataset, &ScanLayer::currentChanged); }
void ScanLayer::setIncludedOnly(bool on) { assign(included_only_, on, &ScanLayer::includedOnlyChanged); }

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
        for (const ScanViewModel::Pattern& pattern : model_->patterns()) {
            for (const double value : pattern.intensity) {
                const double shown = edi::to_display(value, scale);
                if (std::isfinite(shown)) {
                    low = std::min(low, shown);
                    high = std::max(high, shown);
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
    const std::vector<ScanViewModel::Pattern>& patterns = model_->patterns();
    const std::vector<double>& rows = model_->rows();
    const std::vector<edi::ScanRowSpan>& spans = model_->spans();
    const edi::YScale scale = scale_of(scale_);
    const double span = display_max_ - display_min_;
    const auto px = [this](double x) { return (x - x_min_) / (x_max_ - x_min_) * width(); };
    const auto py = [this](double y) { return (y_max_ - y) / (y_max_ - y_min_) * height(); };
    const std::size_t count = std::min({patterns.size(), rows.size(), spans.size()});
    // The plot's own pixel columns: what each dataset is reduced to for the range shown.
    const int pixel_columns = std::max(1, static_cast<int>(std::ceil(width())));
    const int pixel_rows = std::max(1, static_cast<int>(std::ceil(height())));

    // The excluded ranges (edi ADR-0021 §4), each over its dataset's row, on whole pixels so that two rows' bands meet
    // without a line between them; a scan's datasets share the template's ranges, so its bands run the plot's height.
    const auto excluded = [&](const QColor& colour) {
        const auto band = [&](double a, double b, int top, int bottom) {
            const int left = std::clamp(static_cast<int>(std::lround(px(std::min(a, b)))), 0, pixel_columns);
            const int right = std::clamp(static_cast<int>(std::lround(px(std::max(a, b)))), 0, pixel_columns);
            if (right > left && bottom > top) {
                painter->fillRect(QRect(left, top, right - left, bottom - top), colour);
            }
        };
        if (!model_->joint()) {
            for (std::size_t d = 0; d < count; ++d) {
                if (!patterns[d].x.empty()) {
                    for (const auto& [a, b] : patterns[d].excluded_shown) {
                        band(a, b, 0, pixel_rows);
                    }
                    return;
                }
            }
            return;
        }
        for (std::size_t d = 0; d < count; ++d) {
            const int top = std::clamp(static_cast<int>(std::lround(py(spans[d].high))), 0, pixel_rows);
            const int bottom = std::clamp(static_cast<int>(std::lround(py(spans[d].low))), 0, pixel_rows);
            for (const auto& [a, b] : patterns[d].excluded_shown) {
                band(a, b, top, bottom);
            }
        }
    };

    // The pattern chart's tint of an excluded region (edi::pattern_style_table's `excluded`).
    QColor tint;
    for (const edi::SeriesStyle& style : edi::pattern_style_table()) {
        if (style.key == "excluded") {
            tint = QColor(QString::fromStdString(dark_ ? style.dark : style.light));
            tint.setAlphaF(static_cast<float>(style.opacity));
        }
    }
    // With only the included range, a dataset's points inside its excluded regions are taken out, so neither view draws
    // or joins across them.
    const auto intensity_of = [this](const ScanViewModel::Pattern& pattern) {
        if (!included_only_ || pattern.excluded_shown.empty()) {
            return pattern.intensity;
        }
        std::vector<double> out = pattern.intensity;
        for (std::size_t i = 0; i < out.size() && i < pattern.shown.size(); ++i) {
            if (ScanViewModel::excludedAt(pattern, pattern.shown[i])) {
                out[i] = std::numeric_limits<double>::quiet_NaN();
            }
        }
        return out;
    };

    if (mode_ == QLatin1String("map")) {
        // The datasets read, in row order, each as its pixel columns' values on the y scale.
        std::vector<std::size_t> order;
        for (std::size_t d = 0; d < count; ++d) {
            if (!patterns[d].x.empty() && std::isfinite(rows[d])) {
                order.push_back(d);
            }
        }
        std::sort(order.begin(), order.end(), [&rows](std::size_t a, std::size_t b) { return rows[a] < rows[b]; });
        if (order.empty()) {
            return;
        }
        std::vector<std::vector<float>> values(order.size());
        for (std::size_t i = 0; i < order.size(); ++i) {
            const ScanViewModel::Pattern& pattern = patterns[order[i]];
            values[i] = edi::scan_pixel_values(pattern.shown, intensity_of(pattern), x_min_, x_max_,
                                               static_cast<std::size_t>(pixel_columns));
            for (float& value : values[i]) {
                value = static_cast<float>(edi::to_display(value, scale));
            }
        }
        std::vector<edi::ScanMapColour> table =
            edi::scan_colour_table(colour_map_.toStdString(), background_.name().toStdString(), dark_);
        if (reversed_) {
            std::reverse(table.begin(), table.end());
        }
        // One image pixel per plot pixel, so no row of the plot is drawn twice and nothing shows between datasets. Up,
        // between two datasets' rows the value is interpolated linearly, so the colour changes smoothly, or, stepped,
        // is the nearer dataset's, each dataset one band out to halfway to its neighbours; beyond the first or the last
        // row, out to its extent, it is that dataset's. A column one of the two leaves empty takes the other's value,
        // and one both leave empty stays clear.
        QImage image(pixel_columns, pixel_rows, QImage::Format_ARGB32);
        image.fill(Qt::transparent);
        const double low_edge = spans[order.front()].low, high_edge = spans[order.back()].high;
        // The datasets' rows in rising order; each pixel row finds the pair around its own scan value, whatever the
        // order the pixel rows are visited in.
        std::vector<double> placed(order.size());
        for (std::size_t i = 0; i < order.size(); ++i) {
            placed[i] = rows[order[i]];
        }
        for (int j = 0; j < pixel_rows; ++j) {
            const double y = y_max_ - (static_cast<double>(j) + 0.5) / static_cast<double>(pixel_rows) * (y_max_ - y_min_);
            if (y < low_edge || y > high_edge) {
                continue;
            }
            const edi::ScanRowPair pair = edi::scan_row_pair(placed, y, smooth_rows_);
            const std::vector<float>& a = values[pair.first];
            const std::vector<float>& b = values[pair.second];
            const double f = pair.share;
            QRgb* line = reinterpret_cast<QRgb*>(image.scanLine(j));
            for (int i = 0; i < pixel_columns; ++i) {
                const double va = a[static_cast<std::size_t>(i)], vb = b[static_cast<std::size_t>(i)];
                const double value = !std::isfinite(va) ? vb : !std::isfinite(vb) ? va : va + (vb - va) * f;
                const edi::ScanMapColour colour = edi::scan_table_colour(table, (value - display_min_) / span);
                line[i] = qRgba(colour.r, colour.g, colour.b, colour.a);
            }
        }
        painter->drawImage(QRectF(0, 0, static_cast<double>(pixel_columns), static_cast<double>(pixel_rows)), image);
        // Over the colours, the excluded ranges wash them towards the plot's background, as a band greys a pattern;
        // with only the included range they hold no colours, and take the pattern chart's tint as empty gaps.
        QColor wash = background_;
        wash.setAlphaF(0.6F);
        excluded(included_only_ ? tint : wash);
        return;
    }

    // Stacked: the excluded bands under the patterns, as on the pattern chart.
    excluded(tint);
    // Each dataset over the range shown at the plot's pixel columns: the measured points joined while they are no
    // more than the columns, else each column a vertical stroke from its lowest to its highest value, joined column to
    // column, so a narrow peak stays at its height whatever the width.
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
        const ScanViewModel::Pattern& pattern = patterns[d];
        if (pattern.x.empty()) {
            return;
        }
        const edi::ScanTrace trace = edi::scan_trace(pattern.shown, intensity_of(pattern), x_min_, x_max_,
                                                     static_cast<std::size_t>(pixel_columns));
        QPainterPath path;
        bool open = false;
        for (std::size_t k = 0; k < trace.x.size(); ++k) {
            const double low = edi::to_display(trace.low[k], scale), high = edi::to_display(trace.high[k], scale);
            const double x = px(trace.x[k]);
            if (!std::isfinite(low) || !std::isfinite(high) || !std::isfinite(x)) {
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
            if (y_high != y_low) {
                path.lineTo(x, y_high);
            }
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
    std::sort(order.begin(), order.end(), [&rows](std::size_t a, std::size_t b) { return rows[a] > rows[b]; });
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

void ScanColourBar::setReversed(bool reversed) {
    if (reversed != reversed_) {
        reversed_ = reversed;
        emit reversedChanged();
        update();
    }
}

void ScanColourBar::paint(QPainter* painter) {
    const int rows = static_cast<int>(std::ceil(height()));
    if (rows <= 0 || width() <= 0.0) {
        return;
    }
    std::vector<edi::ScanMapColour> table =
        edi::scan_colour_table(colour_map_.toStdString(), background_.name().toStdString(), dark_);
    if (reversed_) {
        std::reverse(table.begin(), table.end());
    }
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
