// SPDX-License-Identifier: BSD-3-Clause
#include "evolution_view_model.hpp"

#include <QCoreApplication>
#include <QMetaObject>
#include <QPointer>
#include <algorithm>
#include <set>
#include <cmath>
#include <cstdint>
#include <exception>
#include <functional>
#include <limits>
#include <optional>
#include <map>
#include <tuple>

#include "background.hpp"
#include "edi/categories.hpp"
#include "edi/scan.hpp"
#include "edi/sharing.hpp"

namespace edi_app {

namespace {

// A point is drawn only when it and its error bar's ends are finite numbers within ±1e300, so every difference the
// chart takes between them (its spans, ticks, hit tests and zoom boxes) is finite too. An undefined s.u. (NaN: a
// direction the data do not determine) draws the value without a bar; an infinite or negative one is not drawn.
bool drawable(double x, double y, double error) {
    constexpr double kLimit = edi::kScanChartLimit;
    const double bar = std::isnan(error) ? 0.0 : error;
    return std::isfinite(x) && std::isfinite(y) && std::isfinite(bar) && bar >= 0.0 && std::abs(x) <= kLimit &&
           std::abs(y - bar) <= kLimit && std::abs(y + bar) <= kLimit;
}

// The half-length of a point's bar: none for an undefined s.u.
double bar_of(double error) { return std::isfinite(error) ? error : 0.0; }

// The bucket of `x` among `buckets` over a range starting at `half_low` (halved values, so the widest finite range
// does not overflow) with halved width `half_span`; the first bucket for a share that is not a finite number.
std::size_t bucket_of(double x, double half_low, double half_span, std::size_t buckets) {
    const double share = half_span > 0.0 ? (x / 2.0 - half_low) / half_span : 0.0;
    return std::isfinite(share)
               ? std::min(buckets - 1, static_cast<std::size_t>(std::clamp(share, 0.0, 1.0) * static_cast<double>(buckets)))
               : 0;
}

// `value` moved by `pad`, or left where it is when that would leave the finite numbers.
double padded(double value, double pad) {
    const double moved = value + pad;
    return std::isfinite(moved) ? moved : value;
}

}  // namespace

EvolutionParameterListModel::EvolutionParameterListModel(QObject* parent) : RowTableModel({"name", "label", "group"}, parent) {}

void EvolutionParameterListModel::setNames(const QStringList& names, const QStringList& labels, const QStringList& groups) {
    QList<Row> rows;
    for (int i = 0; i < names.size(); ++i) {
        const QString label = i < labels.size() && !labels[i].isEmpty() ? labels[i] : names[i];
        rows.append({reinterpret_cast<const void*>(static_cast<std::uintptr_t>(i + 1)), {names[i], label, groups.value(i)}});
    }
    setTableRows(rows);
}

namespace {
constexpr int kRowRedrawMs = 250;
}  // namespace

EvolutionViewModel::EvolutionViewModel(QObject* parent)
    : QObject(parent), parameters_(new EvolutionParameterListModel(this)) {
    row_redraw_.setSingleShot(true);
    row_redraw_.setInterval(kRowRedrawMs);
    connect(&row_redraw_, &QTimer::timeout, this, [this] {
        if (row_redraw_due_) {
            row_redraw_due_ = false;
            if (finish()) {
                row_redraw_.start();
            }
        }
    });
}

void EvolutionViewModel::finishRow() {
    if (row_redraw_.isActive()) {
        row_redraw_due_ = true;
        return;
    }
    if (finish()) {  // false: an observer deleted this view while it published
        row_redraw_.start();
    }
}

void EvolutionViewModel::showIterate(const edi::ParametricIterate& iterate) {
    live_ = iterate;
    syncFitted();
    finishRow();
}

void EvolutionViewModel::clearIterate() {
    if (!live_) return;
    live_.reset();
    syncFitted();
    rebuild();
}

std::vector<EvolutionViewModel::Point> EvolutionViewModel::livePoints() const {
    std::vector<Point> live;
    if (!live_ || session_ == nullptr || current_ < 0 || current_ >= names_.size()) {
        return live;
    }
    const std::string name = names_[current_].toStdString();
    // Per experiment a row names an experiment's parameter; the iterate names it by its full name, the experiment's
    // first: the shown experiment's, or each one's when every bank is shown.
    std::vector<std::pair<std::string, int>> keys;
    if (per_experiment_) {
        for (int e = 0; e < experiments_.size(); ++e) {
            if (current_experiment_ >= 0 && e != current_experiment_) continue;
            keys.emplace_back(experiments_[e].toStdString() + "." + name, allBanks() ? e : -1);
        }
    } else {
        keys.emplace_back(name, -1);
    }
    for (const edi::ParametricIterate::IteratePoint& each : live_->points) {
        const int dataset = session_->place(each.name);
        if (dataset < 0) continue;
        const std::optional<double> x = xOf(dataset, session_->extracted(dataset));
        for (const auto& [key, bank] : keys) {
            const auto value = each.values.find(key);
            if (value == each.values.end()) continue;
            Point point;
            point.dataset = dataset;
            point.bank = bank;
            point.error = std::numeric_limits<double>::quiet_NaN();
            point.y = edi::scan_display_value(name, value->second);
            if (!x || !drawable(*x, point.y, point.error)) continue;
            point.x = *x;
            live.push_back(point);
        }
    }
    return live;
}

void EvolutionViewModel::setScan(const ScanSession* session, const edi::Project* project,
                                 const QString& extracted_title) {
    session_ = session;
    project_ = project;
    if (extracted_title != extracted_title_) {
        extracted_title_ = extracted_title;
        emit xModesChanged();
        emit xTitleChanged();
    }
    syncNames();
    syncFitted();
    rebuild();
}

void EvolutionViewModel::syncParameters() {
    // A publish after a fit of the template (or an edit of it) can bring or move its point.
    const bool names = syncNames();
    const std::optional<Point> point = templatePoint();
    if (names || point != template_point_) {
        syncFitted();
        rebuild();
    }
}

bool EvolutionViewModel::scanRows() const {
    if (session_ == nullptr || !session_->index().error.empty()) {
        return false;
    }
    const auto& rows = session_->index().rows;
    return std::any_of(rows.begin(), rows.end(), [](const auto& row) { return row.offset >= 0; });
}

std::optional<EvolutionViewModel::Point> EvolutionViewModel::templatePoint() const {
    if (session_ == nullptr || project_ == nullptr || current_ < 0 || scanRows()) {
        return std::nullopt;
    }
    const edi::Project& model = template_ != nullptr ? *template_ : *project_;
    const edi::FitResultRecord& result = model.fit_result;
    if (!result.held() || !result.success) {
        return std::nullopt;
    }
    const auto place = session_->places().find(model.sequential_fit.template_file);
    if (place == session_->places().end()) {
        return std::nullopt;
    }
    const int dataset = static_cast<int>(place->second);
    const std::optional<double> x = xOf(dataset, session_->extracted(dataset));
    const std::string name = names_[current_].toStdString();
    for (const edi::NamedParameter& parameter : edi::named_parameters(model)) {
        if (parameter.unique_name != name) {
            continue;
        }
        const double y = parameter.parameter->value;
        const std::optional<double> su = parameter.parameter->uncertainty;
        const double error = su.value_or(0.0);
        if (!x || !drawable(*x, y, error)) {
            return std::nullopt;
        }
        return Point{*x, y, error, dataset};
    }
    return std::nullopt;
}

void EvolutionViewModel::syncFitted() {
    // A running parametric fit's iterate counts as fitted values (ADR-0107).
    const bool fitted = scanRows() || templatePoint().has_value() || live_.has_value();
    if (fitted != fitted_) {
        fitted_ = fitted;
        emit fittedChanged();
    }
}

void EvolutionViewModel::syncExperiments() {
    QStringList names;
    if (project_ != nullptr && project_->sequential_fit.joint()) {
        for (const auto& experiment : project_->experiments) names.append(QString::fromStdString(experiment->name));
    }
    if (names != experiments_) {
        experiments_ = names;
        if (experiments_.isEmpty()) per_experiment_ = false;
        current_experiment_ = std::min(current_experiment_, static_cast<int>(experiments_.size()) - 1);
        emit seriesChanged();
        emit experimentsChanged();
        emit perExperimentChanged();
        emit currentExperimentChanged();
        emit xModesChanged();
        emit xTitleChanged();  // a series that records nothing is placed by its runs
    }
}

void EvolutionViewModel::setPerExperiment(bool on) {
    on = on && series();
    if (on == per_experiment_) return;
    per_experiment_ = on;
    emit perExperimentChanged();
    syncNames();
    rebuild();
}

void EvolutionViewModel::setCurrentExperiment(int index) {
    if (index == current_experiment_ || index < -1 || index >= experiments_.size()) return;
    current_experiment_ = index;
    emit currentExperimentChanged();
    if (per_experiment_) rebuild();
}

QStringList EvolutionViewModel::ordered(const QStringList& columns, QStringList& groups) const {
    enum Kind { Parameter, Derived, Quality };
    struct Entry {
        QString name, group;
        Kind kind = Parameter;
        int block = std::numeric_limits<int>::max(), row = 0;
    };
    const std::vector<Place> places = placer_ ? placer_(columns, per_experiment_) : std::vector<Place>{};
    std::vector<Entry> entries;
    entries.reserve(static_cast<std::size_t>(columns.size()));
    std::map<QString, int> blocks;  // each datablock's first row in the Analysis table
    for (qsizetype i = 0; i < columns.size(); ++i) {
        Entry entry{columns[i], {}};
        if (columns[i].startsWith(QLatin1String("fit_result."))) {
            entry.kind = Quality;
            entry.group = tr("Fit quality");
        } else if (edi::scan_derived_column(columns[i].toStdString())) {
            entry.kind = Derived;
            entry.group = tr("Derived values");
        } else {
            const Place place = static_cast<std::size_t>(i) < places.size() ? places[static_cast<std::size_t>(i)] : Place{};
            // A bank's own columns are every bank's: they name no datablock.
            entry.group = per_experiment_ ? tr("Each bank") : place.block;
            entry.row = place.row;
            const auto [found, added] = blocks.emplace(entry.group, place.row);
            if (!added) found->second = std::min(found->second, place.row);
        }
        entries.push_back(std::move(entry));
    }
    for (Entry& entry : entries) {
        if (entry.kind == Parameter) entry.block = blocks.at(entry.group);
    }
    std::stable_sort(entries.begin(), entries.end(), [](const Entry& a, const Entry& b) {
        return std::tie(a.kind, a.block, a.group, a.row) < std::tie(b.kind, b.block, b.group, b.row);
    });
    QStringList names;
    groups.clear();
    for (const Entry& entry : entries) {
        names.append(entry.name);
        groups.append(entry.group);
    }
    return names;
}

bool EvolutionViewModel::syncNames() {
    syncExperiments();
    // The core's list (edi::evolution_parameters), the report's too: every free parameter, listed before any dataset
    // is fitted, then the ones results.csv records that are no longer free; in groups here (ordered), the shown one
    // kept, else the first. Per experiment, the columns results_experiments.csv records
    // (edi::evolution_experiment_parameters).
    QStringList columns;
    // ADR-0089 point 1: an experiment parameter tied equal across experiments is listed once, under Shared, and read
    // from its leader's rows; Per experiment leaves it out.
    shared_paths_.clear();
    if (project_ != nullptr && series()) {
        for (const auto& [path, leader] : edi::experiment_shared_paths(*project_)) {
            shared_paths_.insert(QString::fromStdString(path), static_cast<int>(leader));
        }
    }
    if (project_ != nullptr && per_experiment_) {
        for (const std::string& name : edi::evolution_experiment_parameters(*project_)) {
            if (!shared_paths_.contains(QString::fromStdString(name))) columns.append(QString::fromStdString(name));
        }
    } else if (project_ != nullptr) {
        static const edi::ScanResultIndex kNoResults;
        // ADR-0107: a parameter shared across the series has one value, so it is no curve.
        std::set<std::string> series_shared;
        if (project_->fitting_mode == "parametric") {
            for (const auto& row : project_->sequential_fit.shared) series_shared.insert(row->parameter_unique_name.value());
        }
        for (const std::string& name :
             edi::evolution_parameters(*project_, session_ != nullptr ? session_->index() : kNoResults)) {
            if (!series_shared.contains(name)) columns.append(QString::fromStdString(name));
        }
        const std::vector<std::string> recorded = edi::evolution_experiment_parameters(*project_);
        for (auto shared = shared_paths_.cbegin(); shared != shared_paths_.cend(); ++shared) {
            if (std::find(recorded.begin(), recorded.end(), shared.key().toStdString()) != recorded.end()) {
                columns.append(shared.key());
            }
        }
    }
    const QString shown = current_ >= 0 && current_ < names_.size() ? names_[current_] : QString();
    const bool changed = columns != columns_;
    if (changed) {
        columns_ = columns;
        QStringList groups;
        names_ = ordered(columns_, groups);
        QStringList labels;
        for (const QString& name : names_)
            labels.append(labeller_ ? labeller_(name, per_experiment_ || shared_paths_.contains(name)) : QString());
        labels_ = labels;
        parameters_->setNames(names_, labels, groups);
    }
    const int current = names_.isEmpty() ? -1 : std::max(0, static_cast<int>(names_.indexOf(shown)));
    if (current != current_ || changed) {
        current_ = current;
        emit currentParameterChanged();
        emit yTitleChanged();
        emit yLabelChanged();
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
    // A fresh run's first row brings the header, and with it the axes and any recorded parameter not listed yet: the
    // points are read once then; every later row adds its own point.
    // The template's own point, shown before the scan had rows, gives way to the scan's points.
    if (!fitted_ || current_ < 0 || template_point_) {
        syncNames();
        syncFitted();
        rebuild();
        return;
    }
    // Per experiment the row's points are in results_experiments.csv, written before the point's row: that point's
    // rows alone are read (edi ADR-0089 point 7), as the rebuild would read them.
    if (per_experiment_) {
        const auto& files = session_->datasets().files;
        if (project_ == nullptr || dataset < 0 || dataset >= static_cast<int>(files.size())) {
            return;
        }
        const bool by_value = x_mode_ == 0 && !extracted_title_.isEmpty();
        bool added = false;
        try {
            edi::evolution_experiment_point(
                *project_, session_->places(), session_->index(), session_->bankRule(*project_), session_->datasets(),
                names_[current_].toStdString(), by_value, files[static_cast<std::size_t>(dataset)],
                [&](std::size_t experiment, const edi::EvolutionPoint& point) {
                    if (current_experiment_ >= 0 && experiment != static_cast<std::size_t>(current_experiment_)) {
                        return;
                    }
                    points_.push_back({point.x, point.y, point.su, static_cast<int>(point.dataset),
                                       allBanks() ? static_cast<int>(experiment) : -1});
                    added = true;
                });
        } catch (const std::exception& refusal) {
            emit refused(QString::fromUtf8(refusal.what()));
            return;
        }
        if (added) {
            finishRow();
        }
        return;
    }
    if (shared_paths_.contains(names_[current_])) {  // read from the leader's rows, as the rebuild does
        rebuild();
        return;
    }
    const std::string name = names_[current_].toStdString();
    // The reduced χ² and the agreement factors have a value and no s.u.
    std::optional<std::size_t> factor;
    if (name == "fit_result.reduced_chi_square") factor = session_->index().chi;
    for (const edi::ScanFactorColumn& column : session_->index().factors) {
        if (column.name == name) factor = column.value;
    }
    if (factor && *factor < cells.size()) {
        std::vector<std::string> extracted;
        for (const std::ptrdiff_t column : session_->index().extract) {
            extracted.push_back(column < 0 ? std::string() : cells[static_cast<std::size_t>(column)]);
        }
        Point point;
        point.dataset = dataset;
        point.error = std::numeric_limits<double>::quiet_NaN();
        const std::optional<double> x = xOf(dataset, &extracted);
        if (!x || cells[session_->index().chi] == "nan" || !edi::parse_scan_number(cells[*factor], point.y)) {
            return;
        }
        point.y = edi::scan_display_value(name, point.y);  // an agreement factor in percent
        if (!drawable(*x, point.y, point.error)) {
            return;
        }
        point.x = *x;
        points_.push_back(point);
        finishRow();
        return;
    }
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
        // An undefined s.u. (`nan`, or empty in an older file) keeps the value, drawn without a bar.
        const std::string& su_cell = cells[parameter.uncertainty];
        if (su_cell == "nan" || su_cell.empty()) {
            point.error = std::numeric_limits<double>::quiet_NaN();
        } else if (!edi::parse_scan_number(su_cell, point.error)) {
            return;
        }
        if (!x || cells[session_->index().chi] == "nan" || !edi::parse_scan_number(cells[parameter.value], point.y) ||
            !drawable(*x, point.y, point.error)) {
            return;
        }
        point.x = *x;
        points_.push_back(point);
        finishRow();
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
        emit yLabelChanged();
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
    // A series that records nothing is placed by its runs (the owner, 2026-11-16).
    return {extracted_title_.isEmpty() ? (series() ? tr("Run") : tr("value")) : extracted_title_, tr("file index")};
}

QString EvolutionViewModel::xTitle() const { return xModes().value(x_mode_); }

QString EvolutionViewModel::yTitle() const { return current_ >= 0 ? names_.value(current_) : QString(); }

QString EvolutionViewModel::yLabel() const {
    const QString label = current_ >= 0 ? labels_.value(current_) : QString();
    return label.isEmpty() ? yTitle() : label;
}

void EvolutionViewModel::setLayer(MeasuredLayer* layer) {
    if (layer != layer_) {
        layer_ = layer;
        emit layerChanged();
        if (layer_ && rebuild_owed_) {
            rebuild();
            return;
        }
        draw();
    }
}

void EvolutionViewModel::rebuild() {
    // No chart shows the points (the chart sets its layer only while its tab is shown; the per-bank layers stay set):
    // the read waits until one does, so a series' runs and a fit's end cost nothing here while it is hidden
    // (ADR-0102 rule 1).
    if (!layer_) {
        rebuild_owed_ = true;
        ++rebuild_request_;  // a read in flight is no longer wanted
        return;
    }
    rebuild_owed_ = false;
    const std::uint64_t request = ++rebuild_request_;
    points_.clear();
    template_point_ = per_experiment_ ? std::nullopt : templatePoint();
    if (template_point_) {
        points_.push_back(*template_point_);
    }
    if (template_point_ || session_ == nullptr || project_ == nullptr || current_ < 0) {
        finish();
        return;
    }
    // The points are read on a worker from a copy of what they come from (edi ADR-0089 point 7): a series' files can
    // be long, and the chart keeps its last drawing until they are in. Rows a fit adds meanwhile are read again.
    Read read;
    read.project = std::make_shared<const edi::Project>(*project_);
    read.places = session_->places();
    read.index = session_->indexSnapshot();  // shared, not copied: a long scan's index is large
    read.datasets = session_->datasets();
    read.name = names_[current_].toStdString();
    read.leader = per_experiment_ ? -1 : shared_paths_.value(names_[current_], -1);
    if (per_experiment_ || read.leader >= 0) {
        read.rule = session_->bankRule(*project_);
    }
    read.by_value = x_mode_ == 0 && !extracted_title_.isEmpty();
    read.per_experiment = per_experiment_;
    read.experiment = current_experiment_;
    read.all_banks = allBanks();
    const std::int64_t end = read.index->end;
    const QPointer<EvolutionViewModel> self(this);
    run_in_background([self, request, end, read = std::move(read)]() {
        std::vector<Point> points;
        QString error;
        try {
            points = readPoints(read);
        } catch (const std::exception& refusal) {
            points.clear();
            error = QString::fromUtf8(refusal.what());
        }
        QMetaObject::invokeMethod(
            QCoreApplication::instance(),
            [self, request, end, points = std::move(points), error]() mutable {
                if (!self || request != self->rebuild_request_) {
                    return;  // a newer read was asked for, or the view is gone
                }
                self->points_ = std::move(points);
                if (!error.isEmpty()) {
                    emit self->refused(error);
                    if (!self || request != self->rebuild_request_) return;  // deleted or superseded by an observer
                }
                self->finish();
                if (!self || request != self->rebuild_request_) return;
                if (self->session_ != nullptr && self->session_->index().end != end) {
                    self->rebuild();
                }
            },
            Qt::QueuedConnection);
    });
}

std::vector<EvolutionViewModel::Point> EvolutionViewModel::readPoints(const Read& read) {
    std::vector<Point> found_points;
    // The core's points (edi::evolution_series), the report's too, read twice. The first read finds their x range and
    // count; above the drawing limit the second keeps per bucket of that range only the lowest and the highest point:
    // the points thinning the whole column keeps, without ever holding it.
    int bank = -1;
    const auto points = [&](const std::function<void(const edi::EvolutionPoint&)>& visit) {
        if (read.leader >= 0) {  // a shared experiment parameter: its leader's rows
            edi::evolution_experiment_series(*read.project, read.places, *read.index, read.rule, read.datasets,
                                             read.name, read.by_value,
                                             [&](std::size_t experiment, const edi::EvolutionPoint& point) {
                                                 if (experiment == static_cast<std::size_t>(read.leader)) visit(point);
                                             });
            return;
        }
        if (read.per_experiment) {
            edi::evolution_experiment_series(*read.project, read.places, *read.index, read.rule, read.datasets,
                                             read.name, read.by_value,
                                             [&](std::size_t experiment, const edi::EvolutionPoint& point) {
                                                 if (read.experiment < 0 ||
                                                     experiment == static_cast<std::size_t>(read.experiment)) {
                                                     bank = static_cast<int>(experiment);
                                                     visit(point);
                                                 }
                                             });
            return;
        }
        edi::evolution_series(*read.project, read.places, *read.index, read.name, read.by_value, visit);
    };
    double low = std::numeric_limits<double>::infinity(), high = -low;
    std::size_t count = 0;
    points([&](const edi::EvolutionPoint& point) {
        low = std::min(low, point.x);
        high = std::max(high, point.x);
        ++count;
    });
    if (count <= static_cast<std::size_t>(kThinningLimit)) {
        points([&](const edi::EvolutionPoint& point) {
            found_points.push_back({point.x, point.y, point.su, static_cast<int>(point.dataset), read.all_banks ? bank : -1});
        });
        return found_points;
    }
    // Per bank its own extrema (one curve each): every bank keeps its excursions, and each point its bank.
    const auto buckets = static_cast<std::size_t>(kThinningLimit / 2);
    const double x0 = low / 2.0, span = high / 2.0 - low / 2.0;
    std::map<int, std::pair<std::vector<std::optional<Point>>, std::vector<std::optional<Point>>>> by_bank;
    points([&](const edi::EvolutionPoint& found) {
        const Point point{found.x, found.y, found.su, static_cast<int>(found.dataset), read.all_banks ? bank : -1};
        auto& [lowest, highest] = by_bank[point.bank];
        if (lowest.empty()) {
            lowest.resize(buckets);
            highest.resize(buckets);
        }
        const std::size_t bucket = bucket_of(point.x, x0, span, buckets);
        if (!lowest[bucket] || point.y < lowest[bucket]->y) {
            lowest[bucket] = point;
        }
        if (!highest[bucket] || point.y > highest[bucket]->y) {
            highest[bucket] = point;
        }
    });
    for (const auto& [key, extrema] : by_bank) {
        const auto& [lowest, highest] = extrema;
        std::optional<int> last;
        for (std::size_t bucket = 0; bucket < buckets; ++bucket) {
            for (const std::optional<Point>& point : {lowest[bucket], highest[bucket]}) {
                if (point && last != point->dataset) {
                    found_points.push_back(*point);
                    last = point->dataset;
                }
            }
        }
    }
    return found_points;
}

void EvolutionViewModel::thin() {
    // Above the limit: per x bucket only the lowest and the highest point, so every excursion stays visible; each
    // bank's points on their own, so every bank's curve keeps its own (a point keeps its dataset and bank). The shares
    // are taken on halved values, so the widest finite x range does not overflow.
    if (points_.size() <= static_cast<std::size_t>(kThinningLimit)) {
        return;
    }
    const auto [low, high] =
        std::minmax_element(points_.begin(), points_.end(), [](const Point& a, const Point& b) { return a.x < b.x; });
    const double x0 = low->x / 2.0, span = high->x / 2.0 - low->x / 2.0;
    const auto buckets = static_cast<std::size_t>(kThinningLimit / 2);
    std::map<int, std::pair<std::vector<int>, std::vector<int>>> by_bank;
    for (std::size_t i = 0; i < points_.size(); ++i) {
        auto& [lowest, highest] = by_bank[points_[i].bank];
        if (lowest.empty()) {
            lowest.assign(buckets, -1);
            highest.assign(buckets, -1);
        }
        const std::size_t bucket = bucket_of(points_[i].x, x0, span, buckets);
        if (lowest[bucket] < 0 || points_[i].y < points_[static_cast<std::size_t>(lowest[bucket])].y) {
            lowest[bucket] = static_cast<int>(i);
        }
        if (highest[bucket] < 0 || points_[i].y > points_[static_cast<std::size_t>(highest[bucket])].y) {
            highest[bucket] = static_cast<int>(i);
        }
    }
    std::vector<Point> kept;
    for (const auto& [bank, extrema] : by_bank) {
        const auto& [lowest, highest] = extrema;
        std::optional<int> last;
        for (std::size_t bucket = 0; bucket < buckets; ++bucket) {
            for (const int i : {lowest[bucket], highest[bucket]}) {
                if (i >= 0 && last != points_[static_cast<std::size_t>(i)].dataset) {
                    kept.push_back(points_[static_cast<std::size_t>(i)]);
                    last = points_[static_cast<std::size_t>(i)].dataset;
                }
            }
        }
    }
    points_ = std::move(kept);
}

bool EvolutionViewModel::finish() {
    // A running parametric fit's latest iterate is what the chart shows, also right after it is opened or rebuilt.
    if (std::vector<Point> live = livePoints(); !live.empty()) {
        template_point_.reset();
        points_ = std::move(live);
    }
    thin();
    double x_min = 0.0, x_max = 1.0, y_min = 0.0, y_max = 1.0;
    if (!points_.empty()) {
        x_min = y_min = std::numeric_limits<double>::infinity();
        x_max = y_max = -std::numeric_limits<double>::infinity();
        for (const Point& point : points_) {
            x_min = std::min(x_min, point.x);
            x_max = std::max(x_max, point.x);
            // The range fits the values only unless the project asks for their error bars too (edi ADR-0017 §19).
            const double error = range_with_errors() ? bar_of(point.error) : 0.0;
            y_min = std::min(y_min, point.y - error);
            y_max = std::max(y_max, point.y + error);
        }
        // The margins from halved values, so a range near the largest finite numbers does not overflow.
        const double x_pad = std::max((x_max / 2.0 - x_min / 2.0) * 0.06, 0.5);
        double y_pad = std::max((y_max / 2.0 - y_min / 2.0) * 0.16, std::abs(y_max) * 1e-6 + 1e-12);
        if (points_.size() == 1) {
            // One point (the fitted template before a scan): its error bar and a little more stay in view.
            y_pad = std::max({y_pad, 1.5 * bar_of(points_.front().error), std::abs(points_.front().y) * 1e-4});
        }
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
    // An observer may delete this view in any notification: nothing is touched after that.
    const QPointer<EvolutionViewModel> self(this);
    update(x_min_, x_min, &EvolutionViewModel::xMinChanged);
    if (!self) return false;
    update(x_max_, x_max, &EvolutionViewModel::xMaxChanged);
    if (!self) return false;
    update(y_min_, y_min, &EvolutionViewModel::yMinChanged);
    if (!self) return false;
    update(y_max_, y_max, &EvolutionViewModel::yMaxChanged);
    if (!self) return false;
    if (static_cast<int>(points_.size()) != published_count_) {
        published_count_ = static_cast<int>(points_.size());
        emit countChanged();
        if (!self) return false;
    }
    draw();
    return static_cast<bool>(self);
}

void EvolutionViewModel::draw() {
    if (!layer_) {
        return;
    }
    QList<QPointF> points;
    QList<double> low, high;
    const bool bars = project_ == nullptr || project_->evolution_error_bars.value_or(true);
    for (const Point& point : points_) {
        points.append(QPointF(point.x, point.y));
        if (bars) {
            low.append(point.y - bar_of(point.error));
            high.append(point.y + bar_of(point.error));
        }
    }
    // Every bank shown: each bank's points on its own layer, the chart's own layer empty.
    if (allBanks()) {
        for (int bank = 0; bank < bank_layers_.size(); ++bank) {
            if (!bank_layers_[bank]) continue;
            QList<QPointF> own;
            QList<double> own_low, own_high;
            for (const Point& point : points_) {
                if (point.bank != bank) continue;
                own.append(QPointF(point.x, point.y));
                if (bars) {
                    own_low.append(point.y - bar_of(point.error));
                    own_high.append(point.y + bar_of(point.error));
                }
            }
            bank_layers_[bank]->setData(own, own_low, own_high);
        }
        layer_->setData({}, {}, {});
        return;
    }
    for (const QPointer<MeasuredLayer>& layer : bank_layers_) {
        if (layer) layer->setData({}, {}, {});
    }
    layer_->setData(points, low, high);
}

void EvolutionViewModel::setBankLayer(int bank, MeasuredLayer* layer) {
    if (bank < 0) return;
    if (bank >= bank_layers_.size()) bank_layers_.resize(bank + 1);
    bank_layers_[bank] = layer;
    draw();
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
