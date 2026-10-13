// SPDX-License-Identifier: BSD-3-Clause
#include "report_view_model.hpp"

#include <QByteArray>
#include <QJsonDocument>
#include <algorithm>
#include <cmath>
#include <exception>
#include <string>

#include "project_view_model.hpp"

namespace edi_app {

ReportViewModel::ReportViewModel(const ProjectViewModel& project, QObject* parent)
    : QObject(parent), project_(project) {
    refresh();
}

void ReportViewModel::refresh() {
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

void ReportViewModel::changed(void (ReportViewModel::*signal)()) {
    emit(this->*signal)();
    refresh();
}

QStringList ReportViewModel::sections() const {
    QStringList names;
    for (edi::ReportSection section : options_.sections) {
        names.append(QString::fromLatin1(edi::report_section_name(section)));
    }
    return names;
}

void ReportViewModel::setSections(const QStringList& names) {
    std::vector<edi::ReportSection> chosen;
    for (const QString& name : names) {
        if (const auto section = edi::report_section_from_name(name.toStdString())) {
            chosen.push_back(*section);
        }
    }
    if (chosen != options_.sections) {
        options_.sections = chosen;
        changed(&ReportViewModel::sectionsChanged);
    }
}

void ReportViewModel::setFreeParametersOnly(bool only) {
    if (only != options_.free_parameters_only) {
        options_.free_parameters_only = only;
        changed(&ReportViewModel::freeParametersOnlyChanged);
    }
}

void ReportViewModel::setAutomaticLevel(bool automatic) {
    if (automatic == automaticLevel()) {
        return;
    }
    options_.correlation_level = automatic ? std::nullopt : std::optional<double>(level_);
    emit automaticLevelChanged();
    changed(&ReportViewModel::correlationLevelChanged);
}

void ReportViewModel::setCorrelationLevel(double level) {
    if (!std::isfinite(level)) {
        return;
    }
    level = std::clamp(level, 0.0, 1.0);
    if (level == level_ && options_.correlation_level == std::optional<double>(level)) {
        return;
    }
    level_ = level;
    options_.correlation_level = level;
    emit automaticLevelChanged();
    changed(&ReportViewModel::correlationLevelChanged);
}

QStringList ReportViewModel::experiments() const {
    QStringList ids;
    for (const std::string& id : options_.experiments) {
        ids.append(QString::fromStdString(id));
    }
    return ids;
}

void ReportViewModel::setExperiments(const QStringList& ids) {
    std::vector<std::string> chosen;
    for (const QString& id : ids) {
        chosen.push_back(id.toStdString());
    }
    if (chosen != options_.experiments) {
        options_.experiments = chosen;
        changed(&ReportViewModel::experimentsChanged);
    }
}

void ReportViewModel::setDSpacing(bool on) {
    if (on != options_.d_spacing) {
        options_.d_spacing = on;
        changed(&ReportViewModel::dSpacingChanged);
    }
}

void ReportViewModel::setResidual(bool on) {
    if (on != options_.residual) {
        options_.residual = on;
        changed(&ReportViewModel::residualChanged);
    }
}

void ReportViewModel::setBraggTicks(bool on) {
    if (on != options_.bragg_ticks) {
        options_.bragg_ticks = on;
        changed(&ReportViewModel::braggTicksChanged);
    }
}

void ReportViewModel::setEmbedLibraries(bool on) {
    if (on != embed_libraries_) {
        embed_libraries_ = on;
        emit embedLibrariesChanged();
    }
}

}  // namespace edi_app
