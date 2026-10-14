// SPDX-License-Identifier: BSD-3-Clause
#include "report_view_model.hpp"

#include <QByteArray>
#include <QDateTime>
#include <QDir>
#include <QLocale>
#include <QTimeZone>
#include <QFile>
#include <QHash>
#include <QImage>
#include <QJsonDocument>
#include <QSaveFile>
#include <algorithm>
#include <exception>
#include <memory>
#include <string>
#include <utility>

#include "correlation_view_model.hpp"
#include "edi/io.hpp"
#include "edi/report_html.hpp"
#include "project_view_model.hpp"
#include "report_pdf.hpp"
#include "web_files.hpp"

namespace edi_app {

ReportViewModel::ReportViewModel(ProjectViewModel& project, QObject* parent) : QObject(parent), project_(project) {
    refresh();
}

void ReportViewModel::setColourScheme(const QString& scheme) {
    if (scheme != colour_scheme_) {
        colour_scheme_ = scheme;
        emit colourSchemeChanged();
        refresh();
    }
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
    // The settings the project now states, announced when they changed (an edit, or its undo).
    if (const QStringList keys = hidden(); keys != published_hidden_) {
        published_hidden_ = keys;
        emit hiddenChanged();
    }
    if (const bool embedded = embedLibraries(); embedded != published_embed_) {
        published_embed_ = embedded;
        emit embedLibrariesChanged();
    }
    const auto publish = [this](bool& published, bool now, void (ReportViewModel::*signal)()) {
        if (now != published) {
            published = now;
            emit(this->*signal)();
        }
    };
    publish(published_writes_html_, writesHtml(), &ReportViewModel::writesHtmlChanged);
    publish(published_writes_pdf_, writesPdf(), &ReportViewModel::writesPdfChanged);
    publish(published_writes_cif_, writesCif(), &ReportViewModel::writesCifChanged);
    dirty_ = true;
    if (active_ && build()) {
        emit modelChanged();
    }
    emit savedReportsChanged();
}

void ReportViewModel::ensureBuilt() const {
    if (dirty_ && build()) {
        auto* self = const_cast<ReportViewModel*>(this);  // NOLINT(cppcoreguidelines-pro-type-const-cast)
        QMetaObject::invokeMethod(self, [self] { emit self->modelChanged(); }, Qt::QueuedConnection);
    }
}

bool ReportViewModel::build() const {
    dirty_ = false;
    // The project's report settings (ADR-0035 §7); of a fit of several experiments, the one the tab shows.
    edi::ReportOptions options = edi::effective_report_options(project_.project());
    options.colour_scheme = edi::colour_scheme_from_name(colour_scheme_.toStdString()).value_or(edi::ColourScheme::Default);
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

QString ReportViewModel::reliability(const QString& experiment) const {
    const edi::ReportPattern* found = pattern(experiment);
    return found != nullptr ? QString::fromStdString(found->reliability) : QString();
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
    for (const std::string& key : edi::effective_report_options(project_.project()).hidden) {
        keys.append(QString::fromStdString(key));
    }
    return keys;
}

void ReportViewModel::setHidden(const QStringList& keys) {
    QStringList next;
    for (const QString& key : keys) {
        if (!next.contains(key)) {
            next.append(key);
        }
    }
    if (next != hidden()) {
        project_.setReportExcluded(next.join(QLatin1Char(' ')));
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

bool ReportViewModel::embedLibraries() const {
    return edi::effective_report_options(project_.project()).embed_libraries;
}

void ReportViewModel::setEmbedLibraries(bool on) {
    if (on != embedLibraries()) {
        project_.setReportHtmlOffline(on);
    }
}

bool ReportViewModel::writes(const char* format) const {
    const edi::Project& project = project_.project();
    const std::string_view name(format);
    if (name == "html") {
        return project.report_html.value_or(true);
    }
    return name == "pdf" ? project.report_pdf.value_or(false) : project.report_cif.value_or(false);
}

void ReportViewModel::setWrites(const char* format, bool on) {
    if (on != writes(format)) {
        project_.setReportFormat(QString::fromLatin1(format), on);
    }
}

const edi::ReportLibraries* ReportViewModel::libraries() const {
    if (libraries_) {
        return &*libraries_;
    }
    // The vendored libraries: the app's own copies on the desktop, the site's in the browser, so the web app's
    // download stays small. Read once.
    edi::ReportLibraries read;
    std::string* texts[] = {&read.plotly, &read.three, &read.orbit_controls};
    const auto& files = edi::report_library_files();
    for (std::size_t i = 0; i < files.size(); ++i) {
        const QString path = QString::fromLatin1(files[i]);
        QByteArray text;
        if (WebFiles::available()) {
            text = WebFiles::siteFile(path);
        } else {
            QFile resource(QStringLiteral(":/edi/") + path);
            if (resource.open(QIODevice::ReadOnly)) {
                text = resource.readAll();
            }
        }
        if (text.isEmpty()) {
            return nullptr;
        }
        *texts[i] = text.toStdString();
    }
    libraries_ = std::move(read);
    return &*libraries_;
}

QString ReportViewModel::reportsDirectory() const {
    return QDir(QString::fromStdString(project_.project().path)).filePath(QStringLiteral("reports"));
}

QVariantList ReportViewModel::savedReports() const {
    ensureBuilt();
    const edi::Project& project = project_.project();
    QVariantList rows;
    const QDir reports(reportsDirectory());
    for (const auto& file : project.report_files) {
        const QString name = QString::fromStdString(file->name.value());
        const std::string format = file->format.value();
        QString state = QStringLiteral("current");
        if (!reports.exists(name)) {
            state = QStringLiteral("missing");
        } else {
            // The digest of what the format's writer would write now, the HTML with the libraries the project embeds.
            const edi::ReportLibraries* embedded = format == "html" && embedLibraries() ? libraries() : nullptr;
            static const edi::ReportLibraries kOnline;
            if (edi::report_digest(report_, format, embedded != nullptr ? *embedded : kOnline) !=
                file->digest.value()) {
                state = QStringLiteral("out of date");
            }
        }
        // Shown in the user's local time, in the pattern of the project's own dates.
        const QString saved = QString::fromStdString(file->saved.value());
        const QDateTime when = QDateTime::fromString(saved, Qt::ISODate);
        rows.append(QVariantMap{{QStringLiteral("name"), name},
                                {QStringLiteral("format"), QString::fromStdString(format)},
                                {QStringLiteral("saved"),
                                 when.isValid()
                                     ? QLocale::c().toString(when.toLocalTime(), QStringLiteral("dd MMM yyyy HH:mm:ss"))
                                     : saved},
                                {QStringLiteral("state"), state}});
    }
    return rows;
}

void ReportViewModel::saveReport(const QVariantMap& figures, const QString& fontFamily) {
    ensureBuilt();
    const edi::Project& project = project_.project();
    const QString base = QString::fromStdString(report_.name.empty() ? std::string("report") : report_.name);
    const QDir reports(reportsDirectory());
    if (project.path.empty() || !QDir().mkpath(reports.path())) {
        emit saveFailed(tr("The report folder %1 could not be made").arg(reports.path()));
        return;
    }
    QStringList written;
    // Each ticked format: its bytes, written into reports/ (the browser also downloads them), then its row.
    std::vector<edi::ReportFile> rows;
    const auto write = [&](const char* format, const QByteArray& bytes, const std::string& digest) {
        const QString name = base + QLatin1Char('.') + QLatin1String(format);
        QSaveFile out(reports.filePath(name));
        if (bytes.isEmpty() || !out.open(QIODevice::WriteOnly) || out.write(bytes) != bytes.size() || !out.commit()) {
            emit saveFailed(tr("The report could not be written to %1").arg(reports.filePath(name)));
            return false;
        }
        if (WebFiles::available()) {
            WebFiles::download(bytes, name);
        }
        edi::ReportFile row;
        row.name = name.toStdString();
        row.format = std::string(format);
        // Both times as ISO 8601 UTC, machine-readable as the files' other times; the project's from its STAR stamp.
        row.saved = QDateTime::currentDateTimeUtc().toString(Qt::ISODate).toStdString();
        QDateTime modified = QLocale::c().toDateTime(QString::fromStdString(project.metadata.last_modified),
                                                     QStringLiteral("dd MMM yyyy HH:mm:ss"));
        modified.setTimeZone(QTimeZone::UTC);
        row.project_last_modified = modified.isValid() ? modified.toString(Qt::ISODate).toStdString()
                                                       : project.metadata.last_modified;
        row.digest = digest;
        rows.push_back(std::move(row));
        written.append(reports.filePath(name));
        return true;
    };
    try {
        if (writes("html")) {
            const edi::ReportLibraries* embedded = embedLibraries() ? libraries() : nullptr;
            if (embedLibraries() && embedded == nullptr) {
                emit saveFailed(tr("The chart libraries could not be read"));
                return;
            }
            static const edi::ReportLibraries kOnline;
            const edi::ReportLibraries& used = embedded != nullptr ? *embedded : kOnline;
            if (!write("html", QByteArray::fromStdString(edi::report_html(report_, used)),
                       edi::report_digest(report_, "html", used))) {
                return;
            }
        }
        if (writes("pdf")) {
            QHash<QString, QImage> images;
            for (auto it = figures.cbegin(); it != figures.cend(); ++it) {
                const QImage image = it.value().value<QImage>();
                if (!image.isNull()) {
                    images.insert(it.key(), image);
                }
            }
            if (!write("pdf", reportPdf(report_, images, fontFamily), edi::report_digest(report_, "pdf"))) {
                return;
            }
        }
        // The rows, in reports/report.edi alone; the project's other files are left as they are.
        project_.recordReportFiles(std::move(rows));
    } catch (const std::exception& error) {
        emit saveFailed(QString::fromUtf8(error.what()));
        return;
    }
    emit savedReportsChanged();
    emit saved(written.join(QStringLiteral(", ")));
}

}  // namespace edi_app
