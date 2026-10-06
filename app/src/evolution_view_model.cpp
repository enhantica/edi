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

void EvolutionViewModel::setScan(const ScanSession* session, const edi::Project* project,
                                 const QString& extracted_title) {
    session_ = session;
    project_ = project;
    extracted_title_ = extracted_title;
    QStringList names;
    if (session_ != nullptr) {
        for (const edi::ScanParameterColumns& parameter : session_->index().parameters) {
            names.append(QString::fromStdString(parameter.name));
        }
    }
    const QString shown = current_ >= 0 && current_ < names_.size() ? names_[current_] : QString();
    if (names != names_) {
        names_ = names;
        parameters_->setNames(names_);
    }
    current_ = names_.isEmpty() ? -1 : std::max(0, static_cast<int>(names_.indexOf(shown)));
    rebuild();
}

std::optional<double> EvolutionViewModel::xOf(int dataset, const std::vector<std::string>* extracted) const {
    if (x_mode_ == 0 && !extracted_title_.isEmpty()) {
        double x = 0.0;
        if (extracted == nullptr || extracted->empty() || !edi::parse_scan_number(extracted->front(), x) ||
            !std::isfinite(x)) {
            return std::nullopt;
        }
        return x;
    }
    return static_cast<double>(dataset + 1);
}

void EvolutionViewModel::addRow(int dataset, const std::vector<std::string>& cells) {
    if (session_ == nullptr || current_ < 0) {
        return;
    }
    const std::string name = names_[current_].toStdString();
    for (const edi::ScanParameterColumns& parameter : session_->index().parameters) {
        if (parameter.name != name || parameter.uncertainty >= cells.size()) {
            continue;
        }
        const std::vector<std::string> extracted(cells.begin() + 4,
                                                 cells.begin() + 4 + static_cast<std::ptrdiff_t>(
                                                                         project_->sequential_fit.extract.size()));
        Point point;
        point.dataset = dataset;
        const std::optional<double> x = xOf(dataset, &extracted);
        if (!x || !edi::parse_scan_number(cells[parameter.value], point.y) ||
            !edi::parse_scan_number(cells[parameter.uncertainty], point.error) || !std::isfinite(point.y) ||
            !std::isfinite(point.error) || point.error < 0.0) {
            return;
        }
        point.x = *x;
        points_.push_back(point);
        finish();
        return;
    }
}

void EvolutionViewModel::setOutOfDate(bool out_of_date) {
    if (out_of_date != out_of_date_) {
        out_of_date_ = out_of_date;
        emit outOfDateChanged();
    }
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
    if (session_ != nullptr && project_ != nullptr && current_ >= 0) {
        // The column read from the file once; a value, an uncertainty or an x that is not a finite number (or an
        // uncertainty below zero) leaves its point out.
        session_->column(*project_, names_[current_].toStdString(), [this](int dataset, double value, double error) {
            const std::optional<double> x = xOf(dataset, session_->extracted(dataset));
            if (x && std::isfinite(value) && std::isfinite(error) && error >= 0.0) {
                points_.push_back({*x, value, error, dataset});
            }
        });
    }
    finish();
}

void EvolutionViewModel::finish() {
    // Above the limit: per x bucket only the lowest and the highest point, so every excursion stays visible.
    if (points_.size() > static_cast<std::size_t>(kThinningLimit)) {
        const auto [low, high] = std::minmax_element(points_.begin(), points_.end(),
                                                     [](const Point& a, const Point& b) { return a.x < b.x; });
        const double x0 = low->x, span = std::max(high->x - low->x, std::numeric_limits<double>::min());
        const int buckets = kThinningLimit / 2;
        std::vector<int> lowest(buckets, -1), highest(buckets, -1);
        for (std::size_t i = 0; i < points_.size(); ++i) {
            const double share = std::clamp((points_[i].x - x0) / span, 0.0, 1.0);
            const int bucket = std::min(buckets - 1, static_cast<int>(share * buckets));
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
