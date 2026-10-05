// SPDX-License-Identifier: BSD-3-Clause
#include "evolution_view_model.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <map>

namespace edi_app {

EvolutionParameterListModel::EvolutionParameterListModel(QObject* parent) : RowTableModel({"name", "label"}, parent) {}

void EvolutionParameterListModel::setNames(const QStringList& names) {
    QList<Row> rows;
    for (int i = 0; i < names.size(); ++i) {
        rows.append({reinterpret_cast<const void*>(static_cast<std::uintptr_t>(i + 1)), {names[i], names[i]}});
    }
    setTableRows(rows);
}

EvolutionViewModel::EvolutionViewModel(QObject* parent)
    : QObject(parent), parameters_(new EvolutionParameterListModel(this)) {}

void EvolutionViewModel::setScan(const edi::ScanDatasets& datasets, const edi::ScanResults& results,
                                 std::size_t extract_rules, const QString& extracted_title) {
    files_ = datasets.files;
    results_ = results;
    extract_rules_ = extract_rules;
    extracted_title_ = extracted_title;
    // A results row: file_path, reduced χ², success, iterations, the extract rules' values, then each fitted
    // parameter's value and uncertainty.
    QStringList names;
    for (std::size_t i = 4 + extract_rules; i < results.header.size(); ++i) {
        const QString column = QString::fromStdString(results.header[i]);
        if (!column.endsWith(QLatin1String(".uncertainty"))) {
            names.append(column);
        }
    }
    const QString shown = current_ >= 0 && current_ < names_.size() ? names_[current_] : QString();
    names_ = names;
    parameters_->setNames(names_);
    current_ = names_.isEmpty() ? -1 : std::max(0, static_cast<int>(names_.indexOf(shown)));
    rebuild();
}

void EvolutionViewModel::setCurrentParameter(int index) {
    if (index != current_ && index >= 0 && index < names_.size()) {
        current_ = index;
        rebuild();
    }
}

void EvolutionViewModel::setXMode(int mode) {
    if (mode != x_mode_ && (mode == 0 || mode == 1)) {
        x_mode_ = mode;
        rebuild();
    }
}

QStringList EvolutionViewModel::xModes() const {
    return {extracted_title_.isEmpty() ? tr("value") : extracted_title_, tr("file index")};
}

QString EvolutionViewModel::xTitle() const { return xModes().value(x_mode_); }

QString EvolutionViewModel::yTitle() const { return current_ >= 0 ? names_.value(current_) : QString(); }

void EvolutionViewModel::setLayer(MeasuredLayer* layer) {
    if (layer != layer_) {
        layer_ = layer;
        emit layerChanged();
        draw();
    }
}

void EvolutionViewModel::rebuild() {
    points_.clear();
    if (current_ >= 0) {
        std::map<std::string, std::size_t> column;
        for (std::size_t i = 0; i < results_.header.size(); ++i) {
            column.emplace(results_.header[i], i);
        }
        const std::string name = names_[current_].toStdString();
        const auto value_column = column.find(name);
        const auto error_column = column.find(name + ".uncertainty");
        for (std::size_t index = 0; index < files_.size(); ++index) {
            const auto row = results_.rows.find(files_[index]);
            if (row == results_.rows.end() || value_column == column.end()) {
                continue;
            }
            const std::vector<std::string>& cells = row->second;
            Point point;
            bool ok = false;
            point.y = QString::fromStdString(cells[value_column->second]).toDouble(&ok);
            if (!ok) {
                continue;
            }
            if (error_column != column.end()) {
                point.error = QString::fromStdString(cells[error_column->second]).toDouble(&ok);
                point.error = ok && std::isfinite(point.error) ? point.error : 0.0;
            }
            if (x_mode_ == 0 && extract_rules_ > 0) {
                point.x = QString::fromStdString(cells[4]).toDouble(&ok);
                if (!ok) {
                    continue;
                }
            } else {
                point.x = static_cast<double>(index + 1);
            }
            point.dataset = static_cast<int>(index);
            points_.push_back(point);
        }
    }
    // Above the limit: per x bucket only the lowest and the highest point, so every excursion stays visible.
    if (points_.size() > static_cast<std::size_t>(kThinningLimit)) {
        const auto [low, high] = std::minmax_element(points_.begin(), points_.end(),
                                                     [](const Point& a, const Point& b) { return a.x < b.x; });
        const double x0 = low->x, span = std::max(high->x - low->x, std::numeric_limits<double>::min());
        const int buckets = kThinningLimit / 2;
        std::vector<int> lowest(buckets, -1), highest(buckets, -1);
        for (std::size_t i = 0; i < points_.size(); ++i) {
            const int bucket = std::min(buckets - 1, static_cast<int>((points_[i].x - x0) / span * buckets));
            if (lowest[bucket] < 0 || points_[i].y < points_[static_cast<std::size_t>(lowest[bucket])].y) {
                lowest[bucket] = static_cast<int>(i);
            }
            if (highest[bucket] < 0 || points_[i].y > points_[static_cast<std::size_t>(highest[bucket])].y) {
                highest[bucket] = static_cast<int>(i);
            }
        }
        std::vector<Point> kept;
        for (int bucket = 0; bucket < buckets; ++bucket) {
            for (const int i : {lowest[bucket], highest[bucket]}) {
                if (i >= 0 && (kept.empty() || kept.back().dataset != points_[static_cast<std::size_t>(i)].dataset)) {
                    kept.push_back(points_[static_cast<std::size_t>(i)]);
                }
            }
        }
        points_ = std::move(kept);
    }
    if (points_.empty()) {
        x_min_ = 0.0, x_max_ = 1.0, y_min_ = 0.0, y_max_ = 1.0;
    } else {
        x_min_ = y_min_ = std::numeric_limits<double>::infinity();
        x_max_ = y_max_ = -std::numeric_limits<double>::infinity();
        for (const Point& point : points_) {
            x_min_ = std::min(x_min_, point.x);
            x_max_ = std::max(x_max_, point.x);
            y_min_ = std::min(y_min_, point.y - point.error);
            y_max_ = std::max(y_max_, point.y + point.error);
        }
        const double x_pad = std::max((x_max_ - x_min_) * 0.03, 0.5);
        const double y_pad = std::max((y_max_ - y_min_) * 0.08, std::abs(y_max_) * 1e-6 + 1e-12);
        x_min_ -= x_pad;
        x_max_ += x_pad;
        y_min_ -= y_pad;
        y_max_ += y_pad;
    }
    emit currentParameterChanged();
    emit xModeChanged();
    emit xTitleChanged();
    emit yTitleChanged();
    emit xMinChanged();
    emit xMaxChanged();
    emit yMinChanged();
    emit yMaxChanged();
    emit countChanged();
    draw();
}

void EvolutionViewModel::draw() {
    if (!layer_) {
        return;
    }
    QList<QPointF> points;
    QList<double> low, high;
    for (const Point& point : points_) {
        points.append(QPointF(point.x, point.y));
        low.append(point.y - point.error);
        high.append(point.y + point.error);
    }
    layer_->setData(points, low, high);
}

int EvolutionViewModel::datasetAt(double x, double y, double x_tolerance, double y_tolerance) const {
    int best = -1;
    double best_distance = std::numeric_limits<double>::infinity();
    for (const Point& point : points_) {
        const double dx = (point.x - x) / x_tolerance, dy = (point.y - y) / y_tolerance;
        const double distance = dx * dx + dy * dy;
        if (distance <= 1.0 && distance < best_distance) {
            best_distance = distance;
            best = point.dataset;
        }
    }
    return best;
}

double EvolutionViewModel::datasetX(int dataset) const {
    for (const Point& point : points_) {
        if (point.dataset == dataset) {
            return point.x;
        }
    }
    return std::numeric_limits<double>::quiet_NaN();
}

}  // namespace edi_app
