// SPDX-License-Identifier: BSD-3-Clause
#include "report_view_model.hpp"

#include <QByteArray>
#include <QJsonDocument>
#include <algorithm>
#include <exception>
#include <string>

#include "correlation_view_model.hpp"
#include "project_view_model.hpp"

namespace edi_app {

ReportViewModel::ReportViewModel(const ProjectViewModel& project, QObject* parent)
    : QObject(parent), project_(project) {
    refresh();
}

void ReportViewModel::refresh() {
    // The Analysis page's correlation level, while its tab has a matrix to filter; else the five most correlated.
    const CorrelationViewModel* correlations = project_.correlations();
    options_.correlation_level.reset();
    if (correlations != nullptr && correlations->available() >= 2) {
        options_.correlation_level = correlations->level();
    }
    QVariantMap next;
    try {
        // A scan's report is its template dataset's (edi ADR-0035 §3).
        const edi::Project* scan_template = project_.scanTemplate();
        const edi::ReportModel model =
            edi::build_report(scan_template != nullptr ? *scan_template : project_.project(), options_);
        const std::string json = edi::report_to_json(model);
        next = QJsonDocument::fromJson(QByteArray::fromStdString(json)).toVariant().toMap();
    } catch (const std::exception&) {  // NOLINT(bugprone-empty-catch) — a project the builder refuses shows no report
    }
    if (next != model_) {
        model_ = next;
        emit modelChanged();
    }
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
