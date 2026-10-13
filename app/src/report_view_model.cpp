// SPDX-License-Identifier: BSD-3-Clause
#include "report_view_model.hpp"

#include <QByteArray>
#include <QJsonDocument>
#include <algorithm>
#include <exception>
#include <string>
#include <utility>

#include "correlation_view_model.hpp"
#include "project_view_model.hpp"

namespace edi_app {

ReportViewModel::ReportViewModel(const ProjectViewModel& project, QObject* parent)
    : QObject(parent), project_(project) {
    refresh();
}

void ReportViewModel::setActive(bool active) {
    if (active != active_) {
        active_ = active;
        emit activeChanged();
        if (active_ && dirty_) {
            refresh();
        }
    }
}

void ReportViewModel::refresh() {
    dirty_ = true;
    if (active_ && build()) {
        emit modelChanged();
    }
}

void ReportViewModel::ensureBuilt() const {
    if (dirty_ && build()) {
        auto* self = const_cast<ReportViewModel*>(this);  // NOLINT(cppcoreguidelines-pro-type-const-cast)
        QMetaObject::invokeMethod(self, [self] { emit self->modelChanged(); }, Qt::QueuedConnection);
    }
}

bool ReportViewModel::build() const {
    dirty_ = false;
    // The Analysis page's correlation level, while its tab has a matrix to filter; else the five most correlated.
    edi::ReportOptions options = options_;
    const CorrelationViewModel* correlations = project_.correlations();
    options.correlation_level.reset();
    if (correlations != nullptr && correlations->available() >= 2) {
        options.correlation_level = correlations->level();
    }
    // And of a fit of several experiments, the one the tab shows.
    const int shown = project_.currentExperimentIndex();
    options.correlation_experiment = !project_.scan() && shown > 0 ? static_cast<std::size_t>(shown) : 0;
    edi::ReportModel next;
    try {
        // A scan's report is its template dataset's (edi ADR-0035 §3).
        const edi::Project* scan_template = project_.scanTemplate();
        next = edi::build_report(scan_template != nullptr ? *scan_template : project_.project(), options);
    } catch (const std::exception&) {  // NOLINT(bugprone-empty-catch) — a project the builder refuses shows no report
        next = {};
    }
    std::string json = edi::report_to_json(next);
    if (json == json_) {
        return false;
    }
    json_ = std::move(json);
    report_ = std::move(next);
    // The text sections' values for QML; the charts read report_ through their controllers.
    edi::ReportModel text = report_;
    for (edi::ReportStructure& structure : text.structures) {
        structure.scene = {};
        structure.view = {};
        structure.drawing = {};
    }
    for (edi::ReportExperiment& experiment : text.experiments) {
        experiment.pattern = {};
    }
    model_ = QJsonDocument::fromJson(QByteArray::fromStdString(edi::report_to_json(text))).toVariant().toMap();
    return true;
}

const edi::ReportPattern* ReportViewModel::pattern(const QString& experiment) const {
    ensureBuilt();
    const std::string id = experiment.toStdString();
    for (const edi::ReportExperiment& item : report_.experiments) {
        if (item.id == id) {
            return &item.pattern;
        }
    }
    return nullptr;
}

const edi::ReportStructure* ReportViewModel::structure(const QString& id) const {
    ensureBuilt();
    const std::string wanted = id.toStdString();
    for (const edi::ReportStructure& item : report_.structures) {
        if (item.id == wanted) {
            return &item;
        }
    }
    return nullptr;
}

QStringList ReportViewModel::hidden() const {
    QStringList keys;
    for (const std::string& key : options_.hidden) {
        keys.append(QString::fromStdString(key));
    }
    return keys;
}

void ReportViewModel::setHidden(const QStringList& keys) {
    std::vector<std::string> next;
    for (const QString& key : keys) {
        if (std::find(next.begin(), next.end(), key.toStdString()) == next.end()) {
            next.push_back(key.toStdString());
        }
    }
    if (next != options_.hidden) {
        options_.hidden = std::move(next);
        emit hiddenChanged();
        refresh();
    }
}

void ReportViewModel::setIncluded(const QString& key, bool included) {
    QStringList keys = hidden();
    keys.removeAll(key);
    if (!included) {
        keys.append(key);
    }
    setHidden(keys);
}

void ReportViewModel::setEmbedLibraries(bool on) {
    if (on != embed_libraries_) {
        embed_libraries_ = on;
        emit embedLibrariesChanged();
    }
}

}  // namespace edi_app
