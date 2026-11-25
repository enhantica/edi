// SPDX-License-Identifier: BSD-3-Clause
#include "report_view_model.hpp"
#include <QScopeGuard>

#include <QByteArray>
#include <QCoreApplication>
#include <QPointer>
#include <QDateTime>
#include <QDir>
#include <QLocale>
#include <QTimeZone>
#include <QFile>
#include <QHash>
#include <QImage>
#include <QJsonDocument>
#include <algorithm>
#include <exception>
#include <functional>
#include <memory>
#include <string>
#include <utility>

#include "background.hpp"
#include "correlation_view_model.hpp"
#include "edi/io.hpp"
#include "edi/report_html.hpp"
#include "edi/report_save.hpp"
#include "fit_view_model.hpp"
#include "project_view_model.hpp"
#include "report_pdf.hpp"
#include "ui_probe.hpp"
#include "web_files.hpp"

namespace edi_app {

ReportViewModel::ReportViewModel(ProjectViewModel& project, QObject* parent)
    : QObject(parent), project_(project), colour_scheme_(project.colourScheme()) {
    connect(this, &ReportViewModel::modelChanged, this, &ReportViewModel::modelRevisionChanged);
    connect(this, &ReportViewModel::savedReportsChanged, this, &ReportViewModel::lastSavedFiguresChanged);
    // The project marks the report stale before it announces the end of a calculation, so a save waiting for that
    // end rebuilds from the outcome. A fit's end is announced by the project once the fit has published.
    connect(&project_, &ProjectViewModel::calculatingChanged, this, &ReportViewModel::calculatingChanged);
    // The structure figures take the structure view's element colours.
    if (StructureViewOptions* view = project_.structureViewOptions()) {
        connect(view, &StructureViewOptions::colorSchemeChanged, this, &ReportViewModel::refresh);
    }
    // The charts take each block's colour at its position in the palette, as the app's pages do.
    connect(&project_, &ProjectViewModel::colourPositionsChanged, this, &ReportViewModel::refresh);
    refresh();
}

bool ReportViewModel::calculating() const {
    // A fit counts until it ends: between its own calculations the project is idle, but the report is not yet the
    // fit's outcome.
    const FitViewModel* fit = project_.fit();
    return project_.calculating() || (fit != nullptr && fit->running());
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
        if (!active_) {
            supersede();  // a hidden page takes no model; it catches up when shown
        } else if (!current()) {
            refresh();
        }
    }
}

void ReportViewModel::supersede() const {
    if (!building_ || adopted_generation_ == build_generation_) return;
    const std::uint64_t old = build_generation_;
    wanted_->store(++build_generation_);
    dirty_ = true;
    rebuild_owed_ = false;
    EDI_UI_TRACE("cancel", {{"builder", "report"}, {"view", "V12/report"}, {"generation", static_cast<double>(old)}});
}

void ReportViewModel::refresh() {
    project_.invalidateSnapshots();  // whatever asked for the refresh changed what the report reads
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
    // A hidden page waits: its saved reports' states need the model, and building it for every change of a running
    // scan made each fitted dataset rebuild the whole report. The page builds once when shown (setActive); a build
    // running when the change came is superseded.
    if (!active_) {
        supersede();
        return;
    }
    requestBuild();
}

void ReportViewModel::ensureBuilt() const {
    // A read asks a worker for the model and reads the last one until the new one lands (ADR-0102 rule 3): the
    // preview reads the model as its page is shown, before the page's active binding has turned. Only a save builds
    // here (saveReport).
    // A hidden page's read takes the last model: only a shown page asks for a build (rule 1).
    if (active_ && dirty_ && !building_) {
        const_cast<ReportViewModel*>(this)->requestBuild();  // NOLINT(cppcoreguidelines-pro-type-const-cast)
    }
}

void ReportViewModel::publishModel() {
    emit modelChanged();
    const QString stem = fileStem();
    if (stem != published_file_stem_) {
        published_file_stem_ = stem;
        emit fileStemChanged();
    }
}

ReportViewModel::Inputs ReportViewModel::prepare() const {
    // The project's report settings (ADR-0036 §7) and the app's choices, given as the CLI and Python give them: the
    // Preferences' palette and, of a fit of several experiments, the experiment the Analysis page shows; then the
    // blocks' positions in the palette and the structure view's element colours.
    const edi::Project& project = project_.project();
    Inputs inputs;
    edi::ReportOverrides& choices = inputs.choices;
    if (edi::colour_scheme_from_name(colour_scheme_.toStdString())) {
        choices.colour_scheme = colour_scheme_.toStdString();
    }
    // The pattern chart's x axis, also one the project file cannot name yet (Q, sinθ/λ).
    choices.x_axis = project_.patternXAxis().toStdString();
    const int shown = project_.currentExperimentIndex();
    if (!project_.scan() && shown > 0 && static_cast<std::size_t>(shown) < project.experiments.size()) {
        choices.correlation_experiment = project.experiments[static_cast<std::size_t>(shown)]->name.value();
    }
    const StructureViewOptions* view = project_.structureViewOptions();
    inputs.vesta = view != nullptr && view->colorScheme() == QLatin1String("vesta");
    inputs.colour_positions = project_.colourPositions();
    // Shared, not copied here: a scan's template copy is made again only when the template changes (ADR-0102 rule 3).
    inputs.input = project_.reportSnapshot();
    const QDir reports(reportsDirectory());
    for (const auto& file : project.report_files) {
        if (reports.exists(QString::fromStdString(file->name.value()))) {
            inputs.formats.push_back(file->format.value());
        }
    }
    inputs.embed = embedLibraries();
    if (inputs.embed) {
        if (const edi::ReportLibraries* read = libraries()) {
            inputs.libraries = std::make_shared<const edi::ReportLibraries>(*read);
        }
    }
    return inputs;
}

namespace {

QStringList figure_gaps(const edi::Project& project, const edi::ReportModel& report) {
    QStringList gaps;
    for (const auto& experiment : project.experiments) {
        if (experiment->linked_structures.size() == 0) continue;
        for (const edi::ReportExperiment& shown : report.experiments) {
            if (shown.id != experiment->name.value()) continue;
            const auto& series = shown.pattern.presentation.series;
            const bool calc = std::any_of(series.begin(), series.end(),
                                          [](const edi::PatternSeries& one) { return one.id == "calc"; });
            if (!calc) gaps << QStringLiteral("experiment %1: no calculated pattern").arg(QString::fromStdString(shown.id));
        }
    }
    for (const auto& structure : project.structures) {
        if (structure->atom_sites.size() == 0) continue;
        for (const edi::ReportStructure& shown : report.structures) {
            if (shown.id == structure->name.value() && shown.scene.atoms.empty()) {
                gaps << QStringLiteral("structure %1: no atoms in its view").arg(QString::fromStdString(shown.id));
            }
        }
    }
    return gaps;
}

}  // namespace

ReportViewModel::Built ReportViewModel::make(const Inputs& inputs) {
    Built built;
    // A project's computed state (its calculated patterns, its structures' computed categories) does not survive a
    // copy, and the input is the project's shared copy: one that is not a scan is calculated here first, as the report
    // builder calculates a scan's template itself. Built from the copy alone, a joint TOF project's report drew only
    // its measured data and empty structure views (the owner, 2026-11-21).
    std::optional<edi::Project> calculated;
    if (!edi::fits_a_scan(*inputs.input)) {
        calculated.emplace(*inputs.input);
        try {
            edi::apply_relations(*calculated);
            calculated->calculate();
        } catch (const std::exception&) {  // NOLINT(bugprone-empty-catch) — a refused calculation reports what it has
        }
    }
    const edi::Project& source = calculated ? *calculated : *inputs.input;
    try {
        built.options = edi::effective_report_options(source, inputs.choices);
        built.options.element_colours = inputs.vesta ? edi::ColorScheme::Vesta : edi::ColorScheme::Jmol;
        built.options.colour_positions = inputs.colour_positions;
        built.report = edi::build_report(source, built.options);
        built.figure_gaps = figure_gaps(source, built.report);
    } catch (const std::exception&) {  // NOLINT(bugprone-empty-catch) — a project the builder refuses shows no report
        built.options = {};
        built.report = {};
    }
    built.json = edi::report_to_json(built.report);
    // The text sections' values for QML; the charts read report_ through their controllers.
    edi::ReportModel text = built.report;
    for (edi::ReportStructure& structure : text.structures) {
        structure.scene = {};
        structure.view = {};
        structure.drawing = {};
    }
    for (edi::ReportExperiment& experiment : text.experiments) {
        experiment.pattern = {};
    }
    built.model = QJsonDocument::fromJson(QByteArray::fromStdString(edi::report_to_json(text))).toVariant().toMap();
    // A long table's rows leave the QML model: converting thousands of rows to QML values was most of a shown
    // Report's cost (ADR-0102 rule 2). The table keeps its key and count, and its rows are read from rowsModel.
    std::function<void(QVariant&, const QString&)> strip = [&](QVariant& value, const QString& path) {
        if (value.typeId() == QMetaType::QVariantMap) {
            QVariantMap map = value.toMap();
            if (auto table = map.find(QStringLiteral("table")); table != map.end() && table->typeId() == QMetaType::QVariantMap) {
                QVariantMap fields = table->toMap();
                const QVariantList rows = fields.value(QStringLiteral("rows")).toList();
                if (rows.size() > 100) {
                    QStringList joined;
                    joined.reserve(rows.size());
                    for (const QVariant& row : rows) joined.append(row.toStringList().join(QChar(0x1f)));
                    built.rows.insert(path, joined);
                    fields.insert(QStringLiteral("rows"), QVariantList());
                    fields.insert(QStringLiteral("rows_key"), path);
                    fields.insert(QStringLiteral("row_count"), rows.size());
                    *table = fields;
                }
            }
            for (auto it = map.begin(); it != map.end(); ++it) strip(it.value(), path + QLatin1Char('/') + it.key());
            value = map;
        } else if (value.typeId() == QMetaType::QVariantList) {
            QVariantList list = value.toList();
            for (qsizetype i = 0; i < list.size(); ++i) strip(list[i], path + QLatin1Char('/') + QString::number(i));
            value = list;
        }
    };
    QVariant root = built.model;
    strip(root, QString());
    built.model = root.toMap();
    // The pattern style table holds a style per dataset (tens of thousands for a long scan, most of the model); the
    // QML preview reads only the measured style, the charts read the table from reportModel().
    QVariantList measured;
    for (const QVariant& style : built.model.value(QStringLiteral("pattern_styles")).toList()) {
        if (style.toMap().value(QStringLiteral("key")).toString() == QLatin1String("meas.0")) measured.append(style);
    }
    built.model.insert(QStringLiteral("pattern_styles"), measured);
    // The saved reports are judged against what each format's writer would write now (savedReports).
    const edi::ReportModel* judged = &built.report;
    if (edi::chooses_presentation(built.options)) {
        try {
            built.judged = edi::build_report(source, edi::report_file_options(built.options));
        } catch (const std::exception&) {  // NOLINT(bugprone-empty-catch) — as above: no report
            built.judged = edi::ReportModel{};
        }
        judged = &*built.judged;
    }
    static const edi::ReportLibraries kOnline;
    for (const std::string& format : inputs.formats) {
        const QString key = QString::fromStdString(format);
        if (built.digests.contains(key)) continue;
        if (format == "cif") {
            try {
                built.cif_digest = edi::fnv1a64(edi::cif_report_text(source));
            } catch (const std::exception&) {  // NOLINT(bugprone-empty-catch) — no CIF report: judged out of date
                built.cif_digest = std::string();
            }
            built.digests.insert(key, QString::fromStdString(*built.cif_digest));
        } else {
            const edi::ReportLibraries& used = format == "html" && inputs.libraries ? *inputs.libraries : kOnline;
            built.digests.insert(key, QString::fromStdString(edi::report_digest(*judged, format, used)));
        }
    }
    return built;
}

bool ReportViewModel::adopt(Built&& built) const {
    options_ = std::move(built.options);
    judged_ = std::move(built.judged);
    cif_digest_ = std::move(built.cif_digest);
    digests_ = std::move(built.digests);
    figure_gaps_ = std::move(built.figure_gaps);
    if (built.json == json_) {
        return false;
    }
    rows_ = std::move(built.rows);
    for (auto it = rows_models_.begin(); it != rows_models_.end(); ++it) it.value()->setRows(rows_.value(it.key()));
    json_ = std::move(built.json);
    report_ = std::move(built.report);
    model_ = std::move(built.model);
    ++model_revision_;
    return true;
}

bool ReportViewModel::build() const {
    // A running build is superseded: this one is newer. Its result is dropped when it returns.
    dirty_ = false;
    rebuild_owed_ = false;
    const std::uint64_t generation = ++build_generation_;
    wanted_->store(generation);
    judged_.reset();
    cif_digest_.reset();
    digests_.clear();
    const bool changed = adopt(make(prepare()));
    adopted_generation_ = generation;
    return changed;
}

void ReportViewModel::requestBuild() {
    dirty_ = false;
    if (building_) {
        // One build at a time: the running one is superseded and one more is owed, started when it returns.
        const std::uint64_t old = build_generation_;
        wanted_->store(++build_generation_);
        rebuild_owed_ = true;
        EDI_UI_TRACE("supersede", {{"builder", "report"}, {"view", "V12/report"}, {"old", static_cast<double>(old)},
                                   {"replacement", static_cast<double>(build_generation_)}});
        return;
    }
    const std::uint64_t generation = ++build_generation_;
    wanted_->store(generation);
    building_ = true;
    EDI_UI_TRACE("request", {{"builder", "report"}, {"view", "V12/report"}, {"generation", static_cast<double>(generation)}});
    const QPointer<ReportViewModel> self(this);
    run_in_background([self, generation, wanted = wanted_, inputs = prepare()]() {
        // A build superseded while it waited for a worker is not made.
        std::shared_ptr<Built> built;
        if (wanted->load() == generation) {
            EDI_UI_TRACE("build", {{"builder", "report"}, {"view", "V12/report"}, {"thread", ui_trace_thread()},
                                   {"scales", true}, {"generation", static_cast<double>(generation)}});
            built = std::make_shared<Built>(make(inputs));
        }
        QMetaObject::invokeMethod(
            QCoreApplication::instance(),
            [self, generation, built]() {
                if (!self) return;  // the page is gone
                self->building_ = false;
                EDI_UI_TRACE("result-arrival", {{"builder", "report"}, {"view", "V12/report"},
                                                {"generation", static_cast<double>(generation)}});
                // Only the newest wanted build, on a shown page, becomes the model.
                if (built && generation == self->build_generation_ && self->active_) {
                    EDI_UI_TRACE("deliver", {{"builder", "report"}, {"view", "V12/report"},
                                             {"generation", static_cast<double>(generation)}});
                    const bool changed = self->adopt(std::move(*built));
                    self->adopted_generation_ = generation;
                    if (changed) {
                        self->publishModel();
                        if (!self) return;
                    }
                    emit self->savedReportsChanged();
                    return;
                }
                EDI_UI_TRACE("discard", {{"builder", "report"}, {"view", "V12/report"},
                                         {"generation", static_cast<double>(generation)}});
                if (std::exchange(self->rebuild_owed_, false)) {
                    if (self->active_) self->requestBuild();
                    else self->dirty_ = true;
                }
            },
            Qt::QueuedConnection);
    });
}

void ReportRowsModel::setRows(const QStringList& rows) {
    if (rows == rows_) return;
    beginResetModel();  // the table's row set is replaced by a new build
    rows_ = rows;
    endResetModel();
}

QVariant ReportRowsModel::data(const QModelIndex& index, int role) const {
    if (role != Qt::UserRole + 1 || !index.isValid() || index.row() >= rows_.size()) return {};
    return rows_.at(index.row());
}

QObject* ReportViewModel::rowsModel(const QString& key) {
    ReportRowsModel*& model = rows_models_[key];
    if (model == nullptr) {
        model = new ReportRowsModel(this);
        model->setRows(rows_.value(key));
    }
    return model;
}

QStringList ReportViewModel::sampleRows(const QString& key) const {
    // Each row's cells joined by U+001F, as stored; the table splits the few it measures.
    const QStringList rows = rows_.value(key);
    constexpr qsizetype kSample = 200;
    QStringList sample;
    const qsizetype count = std::min(rows.size(), kSample);
    for (qsizetype k = 0; k < count; ++k) {
        const qsizetype index = rows.size() > kSample ? k * rows.size() / kSample : k;
        sample.append(rows.at(index));
    }
    return sample;
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
    return found != nullptr ? QString::fromStdString(found->title) : QString();
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
    const edi::ReportOptions options = edi::effective_report_options(project_.project());
    for (const std::string& key : options.hidden) {
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

const edi::Project& ReportViewModel::reportInput() const {
    // A scan's report is its template dataset's (edi ADR-0036 §3).
    const edi::Project* scan_template = project_.scanTemplate();
    return scan_template != nullptr ? *scan_template : project_.project();
}

const edi::ReportModel& ReportViewModel::judged() const {
    ensureBuilt();
    if (!edi::chooses_presentation(options_)) {
        return report_;
    }
    if (!judged_) {
        try {
            judged_ = edi::build_report(reportInput(), edi::report_file_options(options_));
        } catch (const std::exception&) {  // NOLINT(bugprone-empty-catch) — as build(): no report
            judged_ = edi::ReportModel{};
        }
    }
    return *judged_;
}

const std::string& ReportViewModel::cifDigest() const {
    ensureBuilt();
    if (!cif_digest_) {
        try {
            cif_digest_ = edi::fnv1a64(edi::cif_report_text(reportInput()));
        } catch (const std::exception&) {  // NOLINT(bugprone-empty-catch) — no CIF report: judged out of date
            cif_digest_ = std::string();
        }
    }
    return *cif_digest_;
}

QString ReportViewModel::fileStem() const {
    ensureBuilt();
    return QString::fromStdString(report_.name.empty() ? std::string("report") : report_.name);
}

QList<SavedReport> ReportViewModel::savedReports() const {
    ensureBuilt();
    const edi::Project& project = project_.project();
    QList<SavedReport> rows;
    const QDir reports(reportsDirectory());
    for (const auto& file : project.report_files) {
        const QString name = QString::fromStdString(file->name.value());
        const std::string format = file->format.value();
        QString state = QStringLiteral("current");
        if (!reports.exists(name)) {
            state = QStringLiteral("missing");
        } else {
            // The digest of what the format's writer would write now, made with the last build when it judged this
            // format, else here (a read before any build).
            const QString known = digests_.value(QString::fromStdString(format));
            std::string digest = known.toStdString();
            if (!digests_.contains(QString::fromStdString(format))) {
                const edi::ReportLibraries* embedded = format == "html" && embedLibraries() ? libraries() : nullptr;
                static const edi::ReportLibraries kOnline;
                digest = format == "cif" ? cifDigest()
                                         : edi::report_digest(judged(), format, embedded != nullptr ? *embedded : kOnline);
            }
            if (digest != file->digest.value()) {
                state = QStringLiteral("out of date");
            }
        }
        // Shown in the user's local time, in the pattern of the project's own dates.
        const QString saved = QString::fromStdString(file->saved.value());
        const QDateTime when = QDateTime::fromString(saved, Qt::ISODate);
        rows.append({name, QString::fromStdString(format),
                     when.isValid() ? QLocale::c().toString(when.toLocalTime(), QStringLiteral("dd MMM yyyy HH:mm:ss"))
                                    : saved,
                     state});
    }
    return rows;
}

void ReportViewModel::prepareSave() {
    if (!current() && build()) {
        publishModel();  // at once: the preview draws this model before its figures are taken
    }
    figures_generation_ = adopted_generation_;
    figures_.clear();
}

void ReportViewModel::setFigure(const QString& name, const QImage& image) {
    if (!image.isNull()) {
        figures_.insert(name, image);
    }
}

void ReportViewModel::saveReport(const QString& fontFamily) {
    const ProjectViewModel::PublicationScope publication(project_);
    if (const auto refusal = project_.criticalEditRefusal(); !refusal.isEmpty()) { emit saveFailed(refusal); return; }
    if (const auto refusal = project_.saveRefusal(); !refusal.isEmpty()) { emit saveFailed(refusal); return; }
    project_.editing_ = true;
    const auto release = qScopeGuard([this] { project_.editing_ = false; });
    project_.notifyProjectEdited();
    if (project_.retired_) return;
    // The figures belong to this save only, whatever it ends in.
    const QHash<QString, QImage> images = std::exchange(figures_, {});
    last_saved_figures_.clear();
    for (auto it = images.cbegin(); it != images.cend(); ++it)
        if (!it.value().isNull()) last_saved_figures_.append(it.key());
    last_saved_figures_.sort();
    // The PDF's figures were taken from the model prepareSave brought up to date; a change since would write them with
    // another build's text and digest, so the save is refused and is made again.
    if (!images.isEmpty() && (!current() || adopted_generation_ != figures_generation_)) {
        emit saveFailed(tr("The report changed while its figures were taken; save it again"));
        return;
    }
    // A save writes what the project is now: it builds here when the model is not the newest.
    if (!current() && build()) {
        QMetaObject::invokeMethod(this, [this] { publishModel(); }, Qt::QueuedConnection);
    }
    const edi::Project& project = project_.project();
    const QString base = fileStem();
    const QDir reports(reportsDirectory());
    // The reports folder is made as project output when the first file is written (ADR-0039).
    if (project.path.empty()) {
        emit saveFailed(tr("The report folder %1 could not be made").arg(reports.path()));
        return;
    }
    QStringList written;
    // In the browser the saved files are also downloaded, together once all are written.
    QList<QPair<QString, QByteArray>> downloads;
    // Each ticked format: its bytes, written into reports/, then its row.
    std::vector<edi::ReportFile> rows;
    const auto write = [&](const char* format, const QByteArray& bytes, const std::string& digest) {
        const QString name = base + QLatin1Char('.') + QLatin1String(format);
        // Through the core's writer, as the command line writes: nothing behind a link in reports/ is written.
        bool stored = !bytes.isEmpty();
        if (stored && project_.fit() != nullptr) project_.fit()->noteTrialFile(reports.filePath(name));
        if (stored) {
            try {
                edi::write_report_file(project.path, name.toStdString(), bytes.toStdString());
            } catch (const std::exception&) {
                stored = false;
            }
        }
        if (!stored) {
            emit saveFailed(tr("The report could not be written to %1").arg(reports.filePath(name)));
            return false;
        }
        downloads.append({name, bytes});
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
    // Each format is written whole or not at all; a failure stops the formats after it, and the files written before
    // it keep their rows and, in the browser, are downloaded.
    bool failed = false;
    try {
        if (writes("html")) {
            const edi::ReportLibraries* embedded = embedLibraries() ? libraries() : nullptr;
            if (embedLibraries() && embedded == nullptr) {
                emit saveFailed(tr("The chart libraries could not be read"));
                failed = true;
            } else {
                static const edi::ReportLibraries kOnline;
                const edi::ReportLibraries& used = embedded != nullptr ? *embedded : kOnline;
                failed = !write("html", QByteArray::fromStdString(edi::report_html(report_, used)),
                                edi::report_digest(judged(), "html", used));
            }
        }
        if (!failed && writes("pdf")) {
            failed = !write("pdf", reportPdf(report_, images, fontFamily), edi::report_digest(judged(), "pdf"));
        }
        if (!failed && writes("cif")) {
            const std::string text = edi::cif_report_text(reportInput());
            failed = !write("cif", QByteArray::fromStdString(text), edi::fnv1a64(text));
        }
    } catch (const std::exception& error) {
        emit saveFailed(QString::fromUtf8(error.what()));
        failed = true;
    }
    // The rows, in reports/report.edi alone; the project's other files are left as they are.
    if (!rows.empty()) {
        if (project_.fit() != nullptr) project_.fit()->noteTrialFile(reports.filePath(QStringLiteral("report.edi")));
        try {
            project_.recordReportFiles(rows, true);
        } catch (const std::exception& error) {
            emit saveFailed(QString::fromUtf8(error.what()));
            failed = true;
        }
    }
    // One format downloads as its file, several as <project name>-reports.zip holding reports/<name>.<ext>, as the
    // project save hands the browser a zip (the owner, 2026-10-14). The files also stay in the in-browser reports/.
    if (WebFiles::available() && downloads.size() == 1) {
        WebFiles::download(downloads.front().second, downloads.front().first);
    } else if (WebFiles::available() && downloads.size() > 1) {
        QList<QPair<QString, QByteArray>> entries;
        for (const auto& [name, bytes] : downloads) {
            entries.append({QStringLiteral("reports/") + name, bytes});
        }
        WebFiles::download(WebFiles::packFiles(entries), base + QStringLiteral("-reports.zip"));
    }
    emit savedReportsChanged();
    if (!failed) {
        emit saved(written.join(QStringLiteral(", ")));
    }
}

}  // namespace edi_app
