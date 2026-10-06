// SPDX-License-Identifier: BSD-3-Clause
#include "evolution_view_model.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <map>

namespace edi_app {

namespace {

// A point is drawn only when it and its error bar's ends are finite numbers.
bool drawable(double x, double y, double error) {
    return std::isfinite(x) && std::isfinite(y) && std::isfinite(error) && error >= 0.0 && std::isfinite(y - error) &&
           std::isfinite(y + error);
}

// The bucket of `x` among `buckets` over a range starting at `half_low` (halved values, so the widest finite range
// does not overflow) with halved width `half_span`; the first bucket for a share that is not a finite number.
int bucket_of(double x, double half_low, double half_span, int buckets) {
    const double share = half_span > 0.0 ? (x / 2.0 - half_low) / half_span : 0.0;
    return std::isfinite(share) ? std::min(buckets - 1, static_cast<int>(std::clamp(share, 0.0, 1.0) * buckets)) : 0;
}

// `value` moved by `pad`, or left where it is when that would leave the finite numbers.
double padded(double value, double pad) {
    const double moved = value + pad;
    return std::isfinite(moved) ? moved : value;
}

}  // namespace

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
    if (extracted_title != extracted_title_) {
        extracted_title_ = extracted_title;
        emit xTitleChanged();
    }
    syncNames();
    rebuild();
}

bool EvolutionViewModel::syncNames() {
    // The parameters results.csv records, the shown one kept, else the first (every recorded parameter is free).
    QStringList names;
    if (session_ != nullptr) {
        for (const edi::ScanParameterColumns& parameter : session_->index().parameters) {
            names.append(QString::fromStdString(parameter.name));
        }
    }
    const QString shown = current_ >= 0 && current_ < names_.size() ? names_[current_] : QString();
    const bool changed = names != names_;
    if (changed) {
        names_ = names;
        parameters_->setNames(names_);
    }
    const int current = names_.isEmpty() ? -1 : std::max(0, static_cast<int>(names_.indexOf(shown)));
    if (current != current_ || changed) {
        current_ = current;
        emit currentParameterChanged();
        emit yTitleChanged();
    }
    return changed;
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
    if (session_ == nullptr) {
        return;
    }
    // A fresh run's first row brings the header, and with it the parameters: they are listed then, and the points
    // read once; every later row adds its own point.
    if (current_ < 0 || names_.size() != static_cast<qsizetype>(session_->index().parameters.size())) {
        syncNames();
        rebuild();
        return;
    }
    const std::string name = names_[current_].toStdString();
    for (const edi::ScanParameterColumns& parameter : session_->index().parameters) {
        if (parameter.name != name || parameter.uncertainty >= cells.size()) {
            continue;
        }
        std::vector<std::string> extracted;
        for (const std::ptrdiff_t column : session_->index().extract) {
            extracted.push_back(column < 0 ? std::string() : cells[static_cast<std::size_t>(column)]);
        }
        Point point;
        point.dataset = dataset;
        const std::optional<double> x = xOf(dataset, &extracted);
        if (!x || !edi::parse_scan_number(cells[parameter.value], point.y) ||
            !edi::parse_scan_number(cells[parameter.uncertainty], point.error) ||
            !drawable(*x, point.y, point.error)) {
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
        emit currentParameterChanged();
        emit yTitleChanged();
        rebuild();
    }
}

void EvolutionViewModel::setXMode(int mode) {
    if (mode != x_mode_ && (mode == 0 || mode == 1)) {
        x_mode_ = mode;
        emit xModeChanged();
        emit xTitleChanged();
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
        // Two reads of the column. The first finds the drawable points' x range and count; above the drawing limit
        // the second keeps per bucket of that range only the lowest and the highest point: the points thinning the
        // whole column keeps, without ever holding it. A value, an uncertainty or an x that is not a finite
        // number, or an error bar that leaves the finite numbers, leaves its point out.
        const std::string name = names_[current_].toStdString();
        double low = std::numeric_limits<double>::infinity(), high = -low;
        std::size_t count = 0;
        session_->column(*project_, name, [&](int dataset, double value, double error) {
            const std::optional<double> x = xOf(dataset, session_->extracted(dataset));
            if (x && drawable(*x, value, error)) {
                low = std::min(low, *x);
                high = std::max(high, *x);
                ++count;
            }
        });
        if (count <= static_cast<std::size_t>(kThinningLimit)) {
            session_->column(*project_, name, [this](int dataset, double value, double error) {
                const std::optional<double> x = xOf(dataset, session_->extracted(dataset));
                if (x && drawable(*x, value, error)) {
                    points_.push_back({*x, value, error, dataset});
                }
            });
        } else {
            const int buckets = kThinningLimit / 2;
            const double x0 = low / 2.0, span = high / 2.0 - low / 2.0;
            std::vector<std::optional<Point>> lowest(buckets), highest(buckets);
            session_->column(*project_, name, [&](int dataset, double value, double error) {
                const std::optional<double> x = xOf(dataset, session_->extracted(dataset));
                if (!x || !drawable(*x, value, error)) {
                    return;
                }
                const Point point{*x, value, error, dataset};
                const int bucket = bucket_of(point.x, x0, span, buckets);
                if (!lowest[bucket] || point.y < lowest[bucket]->y) {
                    lowest[bucket] = point;
                }
                if (!highest[bucket] || point.y > highest[bucket]->y) {
                    highest[bucket] = point;
                }
            });
            for (int bucket = 0; bucket < buckets; ++bucket) {
                for (const std::optional<Point>& point : {lowest[bucket], highest[bucket]}) {
                    if (point && (points_.empty() || points_.back().dataset != point->dataset)) {
                        points_.push_back(*point);
                    }
                }
            }
        }
    }
    finish();
}

void EvolutionViewModel::thin() {
    // Above the limit: per x bucket only the lowest and the highest point, so every excursion stays visible. The
    // shares are taken on halved values, so the widest finite x range does not overflow.
    if (points_.size() <= static_cast<std::size_t>(kThinningLimit)) {
        return;
    }
    const auto [low, high] =
        std::minmax_element(points_.begin(), points_.end(), [](const Point& a, const Point& b) { return a.x < b.x; });
    const double x0 = low->x / 2.0, span = high->x / 2.0 - low->x / 2.0;
    const int buckets = kThinningLimit / 2;
    std::vector<int> lowest(buckets, -1), highest(buckets, -1);
    for (std::size_t i = 0; i < points_.size(); ++i) {
        const int bucket = bucket_of(points_[i].x, x0, span, buckets);
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

void EvolutionViewModel::finish() {
    thin();
    double x_min = 0.0, x_max = 1.0, y_min = 0.0, y_max = 1.0;
    if (!points_.empty()) {
        x_min = y_min = std::numeric_limits<double>::infinity();
        x_max = y_max = -std::numeric_limits<double>::infinity();
        for (const Point& point : points_) {
            x_min = std::min(x_min, point.x);
            x_max = std::max(x_max, point.x);
            y_min = std::min(y_min, point.y - point.error);
            y_max = std::max(y_max, point.y + point.error);
        }
        // The margins from halved values, so a range near the largest finite numbers does not overflow.
        const double x_pad = std::max((x_max / 2.0 - x_min / 2.0) * 0.06, 0.5);
        const double y_pad = std::max((y_max / 2.0 - y_min / 2.0) * 0.16, std::abs(y_max) * 1e-6 + 1e-12);
        x_min = padded(x_min, -x_pad);
        x_max = padded(x_max, x_pad);
        y_min = padded(y_min, -y_pad);
        y_max = padded(y_max, y_pad);
    }
    // Only what changed is announced: a viewport the user zoomed stays as it is while rows arrive.
    const auto update = [this](double& field, double value, void (EvolutionViewModel::*signal)()) {
        if (value != field) {
            field = value;
            emit(this->*signal)();
        }
    };
    update(x_min_, x_min, &EvolutionViewModel::xMinChanged);
    update(x_max_, x_max, &EvolutionViewModel::xMaxChanged);
    update(y_min_, y_min, &EvolutionViewModel::yMinChanged);
    update(y_max_, y_max, &EvolutionViewModel::yMaxChanged);
    if (static_cast<int>(points_.size()) != published_count_) {
        published_count_ = static_cast<int>(points_.size());
        emit countChanged();
    }
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
    if (!picking_) {
        return -1;
    }
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
    // From the dataset itself, not from the drawn points: thinning may leave its point out, and the shown dataset's
    // line must not come and go with it.
    if (session_ == nullptr || dataset < 0 || dataset >= static_cast<int>(session_->datasets().files.size())) {
        return std::numeric_limits<double>::quiet_NaN();
    }
    const std::optional<double> x = xOf(dataset, session_->extracted(dataset));
    return x ? *x : std::numeric_limits<double>::quiet_NaN();
}

}  // namespace edi_app
