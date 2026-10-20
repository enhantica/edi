// SPDX-License-Identifier: BSD-3-Clause
#include <utility>
#include "project_view_model.hpp"

#include <QCoreApplication>
#include <QJsonArray>
#include <QHash>
#include <QMetaObject>
#include <QPointer>
#include <QGuiApplication>
#include <QQuickWindow>
#include <QScopeGuard>
#include <QTemporaryDir>
#include <QFile>
#include <QFileInfo>
#include <QSettings>
#include <QUrl>
#include <string_view>
#include <algorithm>
#include <memory>
#include <limits>
#include <cctype>
#include <map>
#include <fstream>
#include <filesystem>

#include "background.hpp"
#include "../../core/src/assistant_relation_edits.hpp"
#include "edi/assistant_limits.hpp"
#include "edi/assistant_files.hpp"
#include "background_input.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/categories.hpp"
#include "engine_setup.hpp"
#include "edi/edits.hpp"
#include "edi/io.hpp"
#include "edi/presentation.hpp"
#include "edi/persistence.hpp"
#include "edi/report_model.hpp"
#include "edi/scan.hpp"
#include "edi/selectors.hpp"
#include "edi/su_text.hpp"
#include "parameter_item.hpp"
#include "parameter_registry.hpp"
#include "report_view_model.hpp"

namespace edi_app {

// ---- StructureListModel / ExperimentListModel ---------------------------------------------------

namespace {

// Original assistant-owned control receipts have a finite diagnostic role.
// Ordinary manual loaders keep their existing diagnostic presentation.
QString original_input_error(const char* text) {
    std::size_t length=0;
    while (length<edi::assistant::Limits::error_bytes && text[length]) ++length;
    return QString::fromUtf8(text,static_cast<qsizetype>(length));
}
// The same native byte bound used by individual result/context projection.
// Empty native names retain the original short canonical category fallback.
// No parser, normalization, truncation or extra identifier domain is introduced.
bool assistant_result_name(const std::string& name) noexcept {
    return name.size() <= edi::assistant::Limits::id_bytes;
}
bool assistant_result_experiment(const edi::BraggPdExperiment& experiment) noexcept {
    if (!assistant_result_name(experiment.name.value())) return false;
    for (const auto& link : experiment.linked_structures)
        if (!link || !assistant_result_name(link->structure_id.value())) return false;
    return true;
}
// A name as a save tells names apart: saved files are compared without letter case (crysta refuses
// two datablock names that differ only by case, as one file on a case-insensitive filesystem).
std::string folded_name(std::string name) {
    std::transform(name.begin(), name.end(), name.begin(),
                   [](unsigned char c) { return c >= 'A' && c <= 'Z' ? static_cast<char>(c - 'A' + 'a') : static_cast<char>(c); });
    return name;
}
// A block's selector entry: its name, a dot, and the file it is saved as in the project.
QString block_label(const QString& name, const QString& fallback) {
    const QString key = name.isEmpty() ? fallback : name;
    return key + QStringLiteral(" · ") + key + QStringLiteral(".edi");
}
}  // namespace

StructureListModel::StructureListModel(QObject* parent)
    : RowTableModel({"name", "label", "structure", "colorIndex"}, parent) {}

void StructureListModel::setStructures(const QList<StructureViewModel*>& structures) {
    QList<Row> rows;
    for (int i = 0; i < structures.size(); ++i) {
        rows.append({structures[i],
                     {structures[i]->name(), block_label(structures[i]->name(), QStringLiteral("structure")),
                      QVariant::fromValue<QObject*>(structures[i]), i}});
    }
    setTableRows(rows);
}

ExperimentListModel::ExperimentListModel(QObject* parent)
    : RowTableModel({"name", "label", "experiment", "fitOutcome", "file", "extracted", "isTemplate"}, parent) {}

void ExperimentListModel::setExperiments(const QList<ExperimentViewModel*>& experiments, const edi::Project& project) {
    // A fit records each fitted experiment's share (`_fit_result_bank`); a single fit recorded before that has none
    // and fitted the first.
    const QString outcome = recorded_outcome(project.fit_result);
    const bool shares = std::any_of(project.experiments.begin(), project.experiments.end(),
                                    [](const auto& experiment) { return experiment->fit_prof_wr_factor.has_value(); });
    dataset_row_ = nullptr;
    dataset_experiment_ = nullptr;
    QList<Row> rows;
    for (int i = 0; i < experiments.size(); ++i) {
        ExperimentViewModel* experiment = experiments[i];
        const bool fitted = shares ? experiment->experiment()->fit_prof_wr_factor.has_value() : i == 0;
        experiment->setFitOutcome(fitted ? outcome : QString());
        // Its last fit's reliability follows its name and file on the selector's line (Rwp and χ²).
        const std::string reliability = fitted ? edi::reliability_text(project, static_cast<std::size_t>(i)) : std::string();
        QString label = block_label(experiment->name(), QStringLiteral("experiment"));
        if (!reliability.empty()) {
            label += QStringLiteral(" · ") + QString::fromStdString(reliability);
        }
        rows.append({experiment,
                     {experiment->name(), label,
                      QVariant::fromValue<QObject*>(experiment), experiment->fitOutcome(),
                      experiment->dataFile().isEmpty() ? experiment->name() + QStringLiteral(".edi")
                                                       : experiment->dataFile(),
                      QStringList(), false}});
    }
    setTableRows(rows);
}

void ExperimentListModel::setColumns(const QStringList& columns) {
    if (columns != columns_) {
        columns_ = columns;
        emit columnsChanged();
    }
}

namespace {

QList<QVariant> dataset_values(ExperimentViewModel* experiment, const ExperimentListModel::Dataset& dataset) {
    const QString name = experiment != nullptr ? experiment->name() : QString();
    QString label = name + QStringLiteral(" · ") + dataset.file;
    for (const QString& value : dataset.extracted) {
        if (!value.isEmpty()) {
            label += QStringLiteral(" · ") + value;
        }
    }
    if (!dataset.reliability.isEmpty()) {
        label += QStringLiteral(" · ") + dataset.reliability;
    }
    return {name, label, QVariant::fromValue<QObject*>(experiment), dataset.outcome, dataset.file, dataset.extracted,
            dataset.is_template};
}

}  // namespace

void ExperimentListModel::setDatasets(ExperimentViewModel* experiment, int count, std::function<Dataset(int)> row) {
    // The rows are brought to the new count with no provider: a row read during a removal or insertion notification
    // reads as empty, never through a file list that may already be the new one. The provider comes after.
    dataset_row_ = nullptr;
    dataset_experiment_ = experiment;
    QList<Row> rows;
    rows.reserve(count);
    for (int i = 0; i < count; ++i) {
        // A dataset row is keyed by its place in the scan: one template experiment shows them all.
        rows.append({reinterpret_cast<const void*>(static_cast<std::uintptr_t>(i + 1)), {}});
    }
    setTableRows(rows);
    dataset_row_ = std::move(row);
    datasetsChanged();
}

QList<QVariant> ExperimentListModel::rowValues(int row) const {
    return dataset_row_ ? dataset_values(dataset_experiment_.data(), dataset_row_(row)) : RowTableModel::rowValues(row);
}

QVariant ExperimentListModel::data(const QModelIndex& index, int role) const {
    if (shown_ && index.isValid()) {
        shown_(index.row());
    }
    return RowTableModel::data(index, role);
}

// ---- ProjectViewModel ---------------------------------------------------------------------------

ProjectViewModel::ProjectViewModel(edi::Project project, QObject* parent)
    : QObject(parent),
      project_(std::make_unique<edi::Project>(std::move(project))),
      registry_(new ParameterRegistry(*this, this)),
      structure_list_(new StructureListModel(this)),
      experiment_list_(new ExperimentListModel(this)),
      parameters_(nullptr),
      analysis_(nullptr),
      metadata_text_(nullptr),
      project_text_(nullptr),
      report_(nullptr),
      structure_view_options_(new StructureViewOptions(this)) {
    const edi::Project& model = *project_;
    completeSymmetry();
    registry_->rebuild(*project_);
    parameters_ = new ParameterTableModel(*registry_, this);
    const SavedFile saved = [this](const std::string& relative) { return savedFile(relative); };
    analysis_ = new AnalysisViewModel(*project_, *this, saved, this);
    (void)model;
    metadata_text_ = new BlockText([this] { return savedFile("project.edi"); }, this);
    report_text_ = new BlockText([this] { return edi::report_settings_text(*project_); }, this);
    project_text_ = new BlockText(
        [this] {
            std::string text;
            for (const auto& [path, body] : savedFiles()) {
                text += (text.empty() ? "" : "\n") + std::string("# ") + path + "\n" + body;
            }
            return text;
        },
        this);
    render_wait_.setSingleShot(true);
    connect(&render_wait_, &QTimer::timeout, this, [this] { followRendered(false); });
    loadScan();
    correlations_ = new CorrelationViewModel(this);
    connect(this, &ProjectViewModel::currentExperimentIndexChanged, this, &ProjectViewModel::syncCorrelations);
    connect(this, &ProjectViewModel::currentExperimentIndexChanged, this, &ProjectViewModel::syncPatternColours);
    syncBlocks();
    report_ = new ReportViewModel(*this, this);
    // The report filters its correlations by the Analysis page's level, and in a fit of several experiments shows the
    // one the page shows.
    connect(correlations_, &CorrelationViewModel::levelChanged, report_, &ReportViewModel::refresh);
    // A level or count the tab is given becomes the project's threshold (ADR-0036 §7).
    connect(correlations_, &CorrelationViewModel::levelAsked, this, &ProjectViewModel::setReportCorrelationThreshold);
    connect(this, &ProjectViewModel::currentExperimentIndexChanged, report_, &ReportViewModel::refresh);
    current_structure_ = structure_models_.isEmpty() ? -1 : 0;
    current_experiment_ = experiment_models_.isEmpty() ? -1 : 0;
    syncParameterTable();
    syncCorrelations();
    published_name_ = name();
    published_title_ = title();
    published_description_ = description();
    published_authors_ = authors();
    published_su_rule_ = suRule();
    published_pattern_d_spacing_ = patternDSpacing();
    published_last_modified_ = lastModified();
    published_structure_index_ = current_structure_;
    published_experiment_index_ = current_experiment_;
    published_structure_ = currentStructure();
    published_experiment_ = currentExperiment();
    published_can_load_structure_ = canLoadStructure();
    published_can_create_experiment_ = canCreateExperiment();
    worker_ = std::make_unique<edi::work::Worker>([this](edi::work::Delivery delivery) {
        QMetaObject::invokeMethod(this, std::move(delivery), Qt::QueuedConnection);
    });
    edi::LivePreview::Hooks hooks;
    hooks.edited = [this] {
        if (retired_) return;
        if (fit_) fit_->invalidateFitUndo(); // Actual edit, before any model/Qt publication.
        try { completeSymmetry(); }
        catch (...) { finishRecordedEdit(); throw; }
        finishRecordedEdit();
        publish(pending_structural_);
        if (retired_) return;
        // An admitted edit, whatever it wrote: every pattern shows a calculation of the state before it, and
        // says so until the newest request publishes. A refused edit never gets here.
        for (ExperimentViewModel* experiment : experiment_models_) {
            experiment->markPatternStale();
            if (retired_) return;
        }
        // A structure whose geometry the edit changed shows its last published frame, reported as not current,
        // until the newest request publishes.
        for (StructureViewModel* structure : structure_models_) {
            if (!structure->structure()->geometry_current()) {
                structure->markSceneStale();
                if (retired_) return;
            }
        }
    };
    hooks.published = [this](const edi::PreviewResult& result) { published(result); };
    hooks.calculating = [this](std::uint64_t /*generation*/) { emit calculationStarted(); };
    hooks.calculated = [this](std::uint64_t /*generation*/) { emit calculationFinished(); };
    preview_ = std::make_unique<edi::LivePreview>(*project_, *worker_, std::move(hooks));
    fit_ = new FitViewModel(*project_, *worker_, *this, this);
    // A fit is the newest undoable change once it ends with a result (finished, cancelled or stopped
    // early), as is a fit start state the loaded project already holds; its undo is one level, so a
    // second fit in a row is the same entry.
    const auto note_fit = [this] {
        if (fit_->canUndo() &&
            (undo_history_.empty() || !std::holds_alternative<std::monostate>(undo_history_.back()))) {
            undo_history_.emplace_back(std::monostate{});
        }
        syncUndo();
    };
    connect(fit_, &FitViewModel::finished, this, [this, note_fit] {
        // An older completion tail must not put a fit above an edit/new completion
        // delivered synchronously during its own publication.
        if (fit_->finished_attempt_ && fit_->history_attempt_ == fit_->finished_attempt_) note_fit();
    });
    connect(fit_, &FitViewModel::outOfDateChanged, this, [this] { evolution_->setOutOfDate(fit_->outOfDate()); });
    // A single fit on a scan dataset makes its result the template, and that dataset the template dataset
    // (`_sequential_fit.template_file`; edi ADR-0017 §19): the shown state is the template from now on. The
    // designation before it is kept for the fit's Undo.
    connect(fit_, &FitViewModel::runningChanged, this, [this] {
        if (scan_ && fit_->running() && !fit_->scanning()) {
            fit_template_before_ = TemplateState{scanTemplateOrModel().sequential_fit.template_file, scan_template_};
            fit_template_before_->run_file_known = scan_session_->runFile(*project_, fit_template_before_->run_file);
            if (projected_dataset_ >= 0) {
                const std::string& file = scan_session_->datasets().files[static_cast<std::size_t>(projected_dataset_)];
                fit_template_before_->pairs_file = file;
                const edi::FitResultRecord& record = scanTemplateOrModel().fit_result;
                fit_template_before_->results = record.scan_results;
                for (const auto& row : record.correlations) {
                    if (!row->file_path.empty()) {
                        fit_template_before_->rows.push_back(*row);
                    }
                }
            }
        }
    });
    connect(fit_, &FitViewModel::finished, this, [this] {
        if (!scan_ || !fit_template_before_ || projected_dataset_ < 0) {
            return;
        }
        fit_template_undo_ = std::move(fit_template_before_);
        fit_template_before_.reset();
        scan_template_.reset();
        project_->sequential_fit.template_file =
            scan_session_->datasets().files[static_cast<std::size_t>(projected_dataset_)];
        // The fit's correlations are this dataset's now, shown and saved as its own; the other datasets keep theirs,
        // shared from the record as it was, and rows read with one keep their ids (ADR-0034 I7).
        const std::string& file = project_->sequential_fit.template_file;
        std::vector<edi::FitParameterCorrelation> rows;
        for (const auto& row : project_->fit_result.correlations) {
            if (row->file_path.empty()) {
                rows.push_back(*row);
                rows.back().file_path = file;
            }
        }
        project_->fit_result.scan_results = fit_template_undo_->results;
        project_->fit_result.scan_results.erase(file);
        edi::hold_template_rows(project_->fit_result, std::move(rows), fit_template_undo_->rows, file);
        syncCorrelations();
        // The last run is this fit now: a reopened project shows its record, not the scan's summary.
        if (scanProcessed()) {
            ScanSession::Run run = scan_session_->run();
            run.last_single = true;
            if (const QString refusal = scan_session_->writeRun(*project_, run); !refusal.isEmpty()) {
                setLastError(refusal);
            }
        }
        publishTemplate();
    });
    connect(fit_, &FitViewModel::canUndoChanged, this, [this] { syncUndo(); });
    connect(fit_, &FitViewModel::runningChanged, this, [this] { syncUndo(); });
    note_fit();
    if (scan_session_ != nullptr) {
        showScanResults();
    }
    // ADR-0031 §1: the project opens on the structure and experiment last selected in it (the app's settings, keyed
    // by its folder); a scan on the dataset last selected, found by its file name, else on its template dataset.
    // Restoring never changes the template.
    const QStringList selection = storedSelection();
    for (int i = 0; i < structure_models_.size() && !selection.value(0).isEmpty(); ++i) {
        if (structure_models_[i]->name() == selection.value(0)) {
            setCurrentStructureIndex(i);
        }
    }
    if (scan_) {
        scan_template_ = *project_;
        int shown = std::max(0, templateIndex());
        const std::vector<std::string>& files = scan_session_ ? scan_session_->datasets().files : std::vector<std::string>();
        for (std::size_t i = 0; i < files.size() && !selection.value(2).isEmpty(); ++i) {
            if (QString::fromStdString(files[i]) == selection.value(2)) {
                shown = static_cast<int>(i);
            }
        }
        viewDatasetNow(shown, true);
    } else {
        for (int i = 0; i < experiment_models_.size() && !selection.value(1).isEmpty(); ++i) {
            if (experiment_models_[i]->name() == selection.value(1)) {
                setCurrentExperimentIndex(i);
            }
        }
    }
    selection_restored_ = true;
    storeSelection();
    preview_->recalculate();
    publishCalculating();
}

void ProjectViewModel::retire() noexcept {
    if (retired_) return;
    retired_ = true;
    // apply/recalculate own a local shared State and stop when the destructor
    // closes it. No worker request may continue from a retired publication hook.
    preview_.reset();
}

void ProjectViewModel::holdPublicationFailure(const QString& warning) noexcept {
    if (retired_) return;
    edit_publication_failed_ = true;
    try { setLastError(warning); } catch (...) { /* already prepared warning/outcome ownership remains */ }
}

ProjectViewModel::~ProjectViewModel() {
    // No delivery after this: the fit and the preview first, then the worker, which waits for the job in flight.
    if (fit_ != nullptr) {
        fit_->close();
    }
    preview_.reset();
    worker_.reset();
    // The view-models read the core model and this object's block lists: they go first, while both
    // are alive (QObject would delete them only after this object's members are gone).
    structure_models_.clear();
    experiment_models_.clear();
    current_structure_ = current_experiment_ = -1;
    const QObjectList owned = children();
    for (QObject* child : owned) {
        delete child;
    }
}

QString ProjectViewModel::name() const { return QString::fromStdString(project_->metadata.name); }
QString ProjectViewModel::title() const { return QString::fromStdString(project_->metadata.title); }
QString ProjectViewModel::description() const { return QString::fromStdString(project_->metadata.description); }
QString ProjectViewModel::lastModified() const { return QString::fromStdString(project_->metadata.last_modified); }
QString ProjectViewModel::authors() const { return QString::fromStdString(project_->metadata.authors); }
QString ProjectViewModel::suRule() const { return QString::fromStdString(project_->su_rule); }

UncertaintyText ProjectViewModel::suText(double value, double su) const {
    if (!std::isfinite(value) || !std::isfinite(su) || su == 0.0) {
        return {};
    }
    const edi::SuText text = edi::su_text(value, su, project_->su_rule);
    return {QString::fromStdString(text.value), QString::fromStdString(text.su), QString::fromStdString(text.bracket)};
}

void ProjectViewModel::setName(const QString& name) {
    edi::Project& project = *project_;
    apply_setting(edi::Edit::project_name(project, name.toStdString()));
}

void ProjectViewModel::setTitle(const QString& title) {
    edi::Project& project = *project_;
    apply_setting(edi::Edit::assign(project.metadata.title, title.toStdString()));
}

void ProjectViewModel::setDescription(const QString& description) {
    edi::Project& project = *project_;
    apply_setting(edi::Edit::assign(project.metadata.description, description.toStdString()));
}

void ProjectViewModel::setAuthors(const QString& authors) {
    edi::Project& project = *project_;
    apply_setting(edi::Edit::assign(project.metadata.authors, authors.toStdString()));
}

void ProjectViewModel::setSuRule(const QString& rule) {
    if (rule != QStringLiteral("iucr_19") && rule != QStringLiteral("iucr_99")) {
        return;
    }
    edi::Project& project = *project_;
    apply_setting(edi::Edit::assign(project.su_rule, rule.toStdString()));
}

void ProjectViewModel::setReportExcluded(const QString& keys) {
    edi::Project& project = *project_;
    const std::optional<std::string> value = keys.simplified().toStdString();
    if (value != project.report_excluded) {
        apply_report_setting(edi::Edit::assign(project.report_excluded, value));
    }
}

void ProjectViewModel::setReportFormat(const QString& format, bool on) {
    edi::Project& project = *project_;
    std::optional<bool>* field = format == QLatin1String("html")  ? &project.report_html
                                 : format == QLatin1String("pdf") ? &project.report_pdf
                                 : format == QLatin1String("cif") ? &project.report_cif
                                                                  : nullptr;
    if (field != nullptr && std::optional<bool>(on) != *field) {
        apply_report_setting(edi::Edit::assign(*field, std::optional<bool>(on)));
    }
}

void ProjectViewModel::recordReportFiles(std::vector<edi::ReportFile> rows) {
    edi::Project& project = *project_;
    // The open project's rows change with reports/report.edi, or not at all.
    const edi::ItemVec<edi::ReportFile> before = project.report_files;
    for (edi::ReportFile& row : rows) {
        const std::string key = row.name.value();
        const auto found = std::find_if(project.report_files.begin(), project.report_files.end(),
                                        [&key](const auto& file) { return file->name.value() == key; });
        if (found != project.report_files.end()) {
            project.report_files.replace_at(static_cast<std::size_t>(found - project.report_files.begin()),
                                            std::make_shared<edi::ReportFile>(std::move(row)));
        } else {
            project.report_files.push_back(std::move(row));
        }
    }
    try {
        edi::save_report_settings(project, project.path);
    } catch (...) {
        project.report_files = before;
        throw;
    }
}

void ProjectViewModel::setReportHtmlOffline(bool embedded) {
    edi::Project& project = *project_;
    if (std::optional<bool>(embedded) != project.report_html_offline) {
        apply_report_setting(edi::Edit::assign(project.report_html_offline, std::optional<bool>(embedded)));
    }
}

void ProjectViewModel::setReportCorrelationThreshold(double threshold) {
    edi::Project& project = *project_;
    const std::optional<double> value = std::clamp(threshold, 0.0, 1.0);
    if (value != project.correlation_threshold) {
        apply_report_setting(edi::Edit::assign(project.correlation_threshold, value));
    }
}

void ProjectViewModel::setPatternDSpacing(bool on) {
    edi::Project& project = *project_;
    if (on != patternDSpacing()) {
        apply_report_setting(edi::Edit::assign(project.pattern_x_axis,
                                        std::optional<std::string>(on ? "d_spacing" : "native")));
    }
}

bool ProjectViewModel::patternDSpacing() const { return project_->pattern_x_axis.value_or("native") == "d_spacing"; }

void ProjectViewModel::setCurrentStructureIndex(int index) {
    if (index != current_structure_ && index >= -1 && index < structure_models_.size()) {
        current_structure_ = index;
        publishCurrent();
    }
}

void ProjectViewModel::setCurrentExperimentIndex(int index) {
    if (scan_) {
        // A choice while a scan runs stops following it; the chosen dataset is shown as its row gives it.
        if (fit_ != nullptr && fit_->scanning()) {
            fit_->setFollowing(false);
        }
        viewDataset(index);
        return;
    }
    if (index != current_experiment_ && index >= -1 && index < experiment_models_.size()) {
        current_experiment_ = index;
        publishCurrent();
    }
}

QStringList ProjectViewModel::storedSelection() const {
    if (project_->path.empty() || settings_file_path().isEmpty()) {
        return {};
    }
    QSettings store(settings_file_path(), QSettings::IniFormat);
    store.beginGroup(QStringLiteral("Selections"));
    return store.value(selectionKey()).toStringList();
}

void ProjectViewModel::storeSelection() const {
    if (!selection_restored_ || project_->path.empty() || settings_file_path().isEmpty()) {
        return;
    }
    const StructureViewModel* structure = currentStructure();
    const ExperimentViewModel* experiment = scan_ ? nullptr : currentExperiment();
    QString dataset;
    if (scan_ && scan_session_ != nullptr && current_dataset_ >= 0 &&
        current_dataset_ < static_cast<int>(scan_session_->datasets().files.size())) {
        dataset = QString::fromStdString(scan_session_->datasets().files[static_cast<std::size_t>(current_dataset_)]);
    }
    QSettings store(settings_file_path(), QSettings::IniFormat);
    store.beginGroup(QStringLiteral("Selections"));
    store.setValue(selectionKey(), QStringList{structure ? structure->name() : QString(),
                                               experiment ? experiment->name() : QString(), dataset});
}

QString ProjectViewModel::selectionKey() const {
    // The project's folder, percent-encoded so its slashes do not make groups of the ini file.
    return QString::fromLatin1(
        QUrl::toPercentEncoding(QFileInfo(QString::fromStdString(project_->path)).absoluteFilePath()));
}

void ProjectViewModel::publishCurrent() {
    const PublicationScope publication(*this);
    if (retired_) return;
    storeSelection();
    if (current_structure_ != published_structure_index_) {
        published_structure_index_ = current_structure_;
        emit currentStructureIndexChanged();
        if (retired_) return;
    }
    if (currentStructure() != published_structure_) {
        published_structure_ = currentStructure();
        emit currentStructureChanged();
        if (retired_) return;
    }
    if (currentExperiment() != published_experiment_) {
        syncParameterTable();  // a scan mode lists the selected experiment's parameters; before the signals
        if (retired_) return;
    }
    if (currentExperimentIndex() != published_experiment_index_) {
        published_experiment_index_ = currentExperimentIndex();
        emit currentExperimentIndexChanged();
        if (retired_) return;
    }
    if (currentExperiment() != published_experiment_) {
        published_experiment_ = currentExperiment();
        emit currentExperimentChanged();
        if (retired_) return;
    }
}

void ProjectViewModel::publishMetadata() {
    const PublicationScope publication(*this);
    if (retired_) return;
    const auto update = [this](QString& published, const QString& current, void (ProjectViewModel::*signal)()) {
        if (current != published) {
            published = current;
            emit(this->*signal)();
            if (retired_) return;
        }
    };
    update(published_name_, name(), &ProjectViewModel::nameChanged);
    if (retired_) return;
    update(published_title_, title(), &ProjectViewModel::titleChanged);
    if (retired_) return;
    update(published_description_, description(), &ProjectViewModel::descriptionChanged);
    if (retired_) return;
    update(published_authors_, authors(), &ProjectViewModel::authorsChanged);
    if (retired_) return;
    update(published_su_rule_, suRule(), &ProjectViewModel::suRuleChanged);
    if (retired_) return;
    update(published_last_modified_, lastModified(), &ProjectViewModel::lastModifiedChanged);
    if (retired_) return;
    if (patternDSpacing() != published_pattern_d_spacing_) {
        published_pattern_d_spacing_ = patternDSpacing();
        emit patternDSpacingChanged();
        if (retired_) return;
    }
}

std::shared_ptr<ProjectViewModel::WidgetCreationInput> ProjectViewModel::prepareWidgetCreation(const CreationAction& action) {
    if (widget_creation_input_ || widget_file_input_) throw std::runtime_error("An original input is already prearmed");
    if (const auto refusal = editReadinessRefusal(false); !refusal.isEmpty()) throw std::runtime_error(refusal.toStdString());
    auto input = std::make_shared<WidgetCreationInput>(); input->expected = action;
    input->outcome.message = tr("The original creation control did not commit");
    widget_creation_input_ = input; return input;
}
void ProjectViewModel::finishWidgetCreation(const std::shared_ptr<WidgetCreationInput>& input) noexcept {
    if (widget_creation_input_ == input) widget_creation_input_.reset();
}
QString ProjectViewModel::apply_creation_control(const edi::Edit& change, bool structural, const CreationAction& actual) {
    const PublicationScope publication(*this);
    const QPointer<ProjectViewModel> self(this);
    const auto input = widget_creation_input_;
    if (widget_input_ || widget_relation_input_ || widget_background_input_ || widget_file_input_)
        return tr("A different original input is still being completed");
    const bool generated_atom = actual.kind == CreationAction::Kind::AtomAppend;
    if (input) {
        const auto& expected=input->expected;
        if (input->consumed || expected.kind!=actual.kind || expected.row!=actual.row || expected.field!=actual.field ||
            (!generated_atom && expected.text!=actual.text) || expected.number!=actual.number)
            return tr("A different creation control cannot enter this original input");
        if (generated_atom && input->bounded_result &&
            (actual.text.isEmpty() || actual.text.contains(QChar(0)) || actual.text.toUtf8().size()>edi::assistant::Limits::id_bytes)) {
            input->consumed=true;input->result_identity_refused=true;
            input->outcome.message=tr("The generated atom identity exceeds the assistant result limit; no edit was made");
            return input->outcome.message;
        }
    }
    const bool previous=widget_input_executing_;
    const auto release=qScopeGuard([self,previous]{if(self)self->widget_input_executing_=previous;});
    if(input){input->consumed=true;widget_input_executing_=true;}
    using Kind=CreationAction::Kind;
    const bool scalar_control=actual.kind==Kind::AbsorptionType || actual.kind==Kind::CutoffFwhm || actual.kind==Kind::DatasetWeight;
    const bool phase_control=actual.kind==Kind::PhaseAppend || actual.kind==Kind::PhaseRetarget ||
        actual.kind==Kind::PhaseEnabled || actual.kind==Kind::PhaseRemove;
    const bool experiment_control=phase_control || scalar_control || actual.kind==Kind::PeakProfile || actual.kind==Kind::ExclusionAppend ||
        actual.kind==Kind::ExclusionStart || actual.kind==Kind::ExclusionEnd || actual.kind==Kind::ExclusionRemove;
    if(experiment_control) {
        edi::ExperimentBase* experiment=nullptr;const edi::ExcludedRegion* region=nullptr;const edi::LinkedStructure* link=nullptr;
        for(const auto& held:project_->experiments) {
            if((scalar_control || actual.kind==Kind::PeakProfile || actual.kind==Kind::ExclusionAppend || actual.kind==Kind::PhaseAppend) && held.get()==actual.row)experiment=held.get();
            if(!phase_control)for(const auto& row:held->excluded_regions)if(row.get()==actual.row){experiment=held.get();region=row.get();}
            if(phase_control && actual.kind!=Kind::PhaseAppend)
                for(const auto& row:held->linked_structures)if(row.get()==actual.row){experiment=held.get();link=row.get();}
        }
        if(!experiment) {
            const auto message=tr("The original experiment control member is unavailable");if(input)input->outcome.message=message;return message;
        }
        // Cached Qt row counts/keys are not scientific membership authority.
        // Reentrant publication must refuse before even an equal-value result.
        if(const auto pending=editReadinessRefusal(false);!pending.isEmpty()){if(input)input->outcome.message=pending;return pending;}
        if(phase_control) {
            QString refusal;
            if(actual.kind==Kind::PhaseRetarget) {
                const auto id=actual.text.toStdString();bool offered=false;
                for(const auto& structure:project_->structures) {
                    const auto& raw=structure->name.value();
                    if((raw.empty()?std::string_view("structure"):std::string_view(raw))==id)offered=true;
                }
                if(!link || !link->enabled.get() || !offered)refusal=tr("The linked structure target is unavailable or disabled");
            } else if(actual.kind==Kind::PhaseRemove && experiment->linked_structures.size()<=1)
                refusal=tr("The final linked structure cannot be removed");
            else if(actual.kind==Kind::PhaseEnabled && actual.number!=0 && actual.number!=1)
                refusal=tr("The linked structure flag must be boolean");
            else if(actual.kind==Kind::PhaseAppend) {
                std::string next;
                for(const auto& structure:project_->structures) {
                    const auto& raw=structure->name.value();
                    const std::string_view id=raw.empty()?std::string_view("structure"):std::string_view(raw);
                    if(std::none_of(experiment->linked_structures.begin(),experiment->linked_structures.end(),[&](const auto& row){return (row->structure_id.value().empty()?std::string_view("structure"):std::string_view(row->structure_id.value()))==id;})){next=std::string(id);break;}
                }
                if(next.empty() || next!=actual.text.toStdString())refusal=tr("The original linked structure append offer changed");
                if(input && input->bounded_result && !assistant_result_name(next)) {
                    input->result_identity_refused=true;
                    refusal=tr("The linked structure identity exceeds the assistant result limit; no edit was made");
                }
            }
            if(!refusal.isEmpty()){if(input)input->outcome.message=refusal;return refusal;}
        }
        const bool equal=actual.kind==Kind::PhaseRetarget?link && edi::KeyTraits<edi::LinkedStructure>::canonical(link->structure_id.value())==actual.text.toStdString():
            actual.kind==Kind::PhaseEnabled?link && link->enabled.get()==bool(actual.number):
            actual.kind==Kind::AbsorptionType?(experiment->absorption.type?std::string_view(*experiment->absorption.type):std::string_view("none"))==actual.text.toStdString():
            actual.kind==Kind::CutoffFwhm?experiment->peak.cutoff_fwhm==actual.number:
            actual.kind==Kind::DatasetWeight?experiment->dataset_weight==actual.number:
            actual.kind==Kind::PeakProfile?edi::effective_peak_type(*experiment)==actual.text.toStdString():
            actual.kind==Kind::ExclusionStart?region && region->first.get()==actual.number:
            actual.kind==Kind::ExclusionEnd?region && region->second.get()==actual.number:false;
        if(equal)return {};
        auto before=phase_control?edi::capture_experiment_links(*project_,*experiment):scalar_control?edi::capture_experiment_scalar(*project_,*experiment,
            actual.kind==Kind::AbsorptionType?edi::ExperimentScalarControl::Absorption:
            actual.kind==Kind::CutoffFwhm?edi::ExperimentScalarControl::CutoffFwhm:edi::ExperimentScalarControl::DatasetWeight):
            edi::capture_experiment_controls(*project_,*experiment,actual.kind==Kind::PeakProfile);
        undo_history_.reserve(undo_history_.size()+1);undo_history_.emplace_back(std::move(before));
        EditOutcome result;
        try {result=applyEdit(change,structural);}catch(...){if(self)undo_history_.pop_back();throw;}
        if(input)input->outcome=result;
        if(!self)return result.applied?QString{}:result.message;
        if(!result.applied)undo_history_.pop_back();
        if(!retired_) {
            const bool publishing_before=editing_;editing_=true;
            const auto restore=qScopeGuard([self,publishing_before]{if(self)self->editing_=publishing_before;});
            try {syncUndo();}catch(...){if(!result.applied)throw;result.published=false;result.message=tr("The edit was applied, but its presentation could not be completed. Undo or reopen the project before further changes.");if(input)input->outcome=result;if(self)holdPublicationFailure(result.message);}
        }
        return result.applied?QString{}:result.message;
    }
    const bool structure_metadata=actual.kind==Kind::SpaceGroupName || actual.kind==Kind::SpaceGroupNumber || actual.kind==Kind::SpaceGroupSetting;
    const bool site_edit=actual.kind==Kind::AtomAppend || actual.kind==Kind::AtomText || actual.kind==Kind::AtomRemove || actual.kind==Kind::AtomAdpType;
    if(!structure_metadata && !site_edit) {
        if(!input)return apply(change,structural);
        input->outcome=applyEdit(change,structural);
        return input->outcome.applied?QString{}:input->outcome.message;
    }
    const edi::Structure* structure=nullptr;const edi::AtomSite* atom=nullptr;
    for(const auto& held:project_->structures) {
        if((structure_metadata || actual.kind==Kind::AtomAppend) && held.get()==actual.row)structure=held.get();
        if(site_edit && actual.kind!=Kind::AtomAppend)
            for(const auto& site:held->atom_sites)if(site.get()==actual.row){structure=held.get();atom=site.get();}
    }
    const auto refuse=[&](const QString& message) {
        if(input)input->outcome.message=message;
        else setLastError(message);
        return message;
    };
    if(!structure)return refuse(tr("The original structure or atom is no longer in this project"));
    const auto text=actual.text.toStdString();bool equal=false;
    if(actual.kind==Kind::SpaceGroupName)equal=edi::same_space_group_name(structure->space_group.name_h_m.value(),text);
    else if(actual.kind==Kind::SpaceGroupNumber)equal=actual.number>0?
        structure->space_group.it_number && *structure->space_group.it_number==actual.number:!structure->space_group.it_number;
    else if(actual.kind==Kind::SpaceGroupSetting)equal=structure->space_group.coord_system_code.value()==text;
    else if(atom && actual.kind==Kind::AtomAdpType)equal=atom->adp_type.value()==text;
    else if(atom && actual.kind==Kind::AtomText) {
        if(actual.field=="label")equal=atom->id.value()==text;
        else if(actual.field=="typeSymbol")equal=atom->type_symbol.value()==text;
        else if(actual.field=="wyckoffLetter")equal=atom->wyckoff_letter.value()==text;
        else if(actual.field=="adpType")equal=atom->adp_type.value()==text;
    }
    if(equal)return {}; // No setter/write/history or publication for stored no-op.
    if(const auto pending=editReadinessRefusal(false);!pending.isEmpty())return refuse(pending);
    const auto warning=tr("The structure edit was applied and Undo retained, but its presentation could not be completed");
    auto before=edi::capture_structure_edit(*project_);
    undo_history_.reserve(undo_history_.size()+1);
    undo_history_.emplace_back(std::move(before)); // Same original history, BEFORE live Edit/observers.
    EditOutcome result;
    try {result=applyEdit(change,structural);}
    catch(...) {if(self)undo_history_.pop_back();throw;} // applyEdit contains post-write failures.
    if(input)input->outcome=result;
    if(!self)return result.applied?QString{}:result.message;
    if(!result.applied)undo_history_.pop_back();
    if(retired_)return result.applied?QString{}:result.message;
    const bool publishing_before=editing_;editing_=true;
    const auto publish_release=qScopeGuard([self,publishing_before]{if(self)self->editing_=publishing_before;});
    try {syncUndo();}
    catch(...) {
        if(!result.applied)throw;
        result.published=false;result.message=warning;
        if(input)input->outcome=result;
        holdPublicationFailure(warning);
    }
    if(self && !retired_ && !result.applied)setLastError(result.message);
    return result.applied?QString{}:result.message;
}

std::shared_ptr<ProjectViewModel::WidgetFileInput> ProjectViewModel::prepareWidgetStructureFile(
    const QUrl& path, std::shared_ptr<const edi::assistant::SelectedFile> source) {
    if (widget_file_input_ || widget_creation_input_) throw std::runtime_error("An original input is already prearmed");
    if (const auto refusal = editReadinessRefusal(false); !refusal.isEmpty()) throw std::runtime_error(refusal.toStdString());
    if (!path.isLocalFile() || !source || source->bytes.empty() || source->bytes.size() > edi::assistant::SelectedFileLimits::file_bytes)
        throw std::invalid_argument("The admitted original structure input is unavailable");
    auto input = std::make_shared<WidgetFileInput>(); input->path = path; input->source = std::move(source);
    input->outcome.message = tr("The original Structure Load did not commit");
    widget_file_input_ = input; return input;
}
std::shared_ptr<ProjectViewModel::WidgetFileInput> ProjectViewModel::prepareWidgetMeasurementFile(
    const QUrl& path, std::shared_ptr<const edi::assistant::SelectedFile> source, ExperimentViewModel* model) {
    if (widget_file_input_ || widget_creation_input_) throw std::runtime_error("An original input is already prearmed");
    if (const auto refusal = editReadinessRefusal(false); !refusal.isEmpty()) throw std::runtime_error(refusal.toStdString());
    const auto index = experiment_models_.indexOf(model);
    if (index < 0 || !path.isLocalFile() || !source || source->bytes.empty() || source->bytes.size() > edi::assistant::SelectedFileLimits::file_bytes)
        throw std::invalid_argument("The admitted original measurement input is unavailable");
    auto input = std::make_shared<WidgetFileInput>(); input->kind = WidgetFileInput::Kind::Measurement;
    input->experiment = project_->experiments[static_cast<std::size_t>(index)].get();
    input->path = path; input->source = std::move(source);
    input->outcome.message = tr("The original Load data control did not commit");
    widget_file_input_ = input; return input;
}
void ProjectViewModel::finishWidgetFile(const std::shared_ptr<WidgetFileInput>& input) noexcept {
    if (widget_file_input_ == input) widget_file_input_.reset();
}

bool ProjectViewModel::loadStructure(const QUrl& file) {
    const PublicationScope publication(*this);
    const QPointer<ProjectViewModel> self(this);
    if (retired_) return false;
    if (!file.isLocalFile()) {
        emit refused(QStringLiteral("not a local file: %1").arg(file.toString()));
        return false;
    }
    EditOutcome result;
    const auto input = widget_file_input_;
    const bool previous = widget_input_executing_;
    const auto release = qScopeGuard([self, previous] { if (self) self->widget_input_executing_ = previous; });
    bool reserved_undo = false;
    try {
        if (input) {
            if (input->kind != WidgetFileInput::Kind::Structure || input->consumed || input->path != file || !input->source)
                throw std::invalid_argument("The chosen structure does not match its admitted original file");
            const bool sourceCurrent=!input->source_current || input->source_current();
            if(!self || retired_ || widget_file_input_!=input)return false;
            if(!sourceCurrent) { input->source_changed=true;throw std::invalid_argument("The original attached structure changed or is unavailable"); }
            input->consumed = true; widget_input_executing_ = true;
        }
        // The app-owned file receipt carries the admitted capture. Its immutable
        // bytes are the authority, not a second path read after genuine input.
        // Ordinary manual Load keeps its existing native/CIF file-reader door.
        auto structure = input ? edi::structure_from_edi_text(std::string(
            reinterpret_cast<const char*>(input->source->bytes.data()), input->source->bytes.size()))
            : edi::load_structure_file(file.toLocalFile().toStdString());
        if (input && input->bounded_result && !assistant_result_name(structure.name.value())) {
            input->consumed = true; // The original refused input is one-shot before notifying.
            input->result_identity_refused = true;
            input->outcome.message = tr("The parsed structure identity exceeds the assistant result limit; no edit was made");
            const auto message = input->outcome.message;
            setLastError(message);
            if (self && !retired_) emit refused(message);
            return false;
        }
        if (const QString refusal = editReadinessRefusal(false); !refusal.isEmpty()) {
            emit refused(refusal); return false;
        }
        if(input) {
            const bool sourceCurrent=!input->source_current || input->source_current();
            if(!self || retired_ || widget_file_input_!=input)return false;
            if(!sourceCurrent) { input->source_changed=true;throw std::invalid_argument("The original attached structure changed or is unavailable"); }
        }
        auto before = edi::capture_structures(*project_);
        undo_history_.reserve(undo_history_.size() + 1);
        undo_history_.emplace_back(std::move(before)); reserved_undo = true;
        result = applyEdit(edi::Edit::add_structure(*project_, std::move(structure)), true);
        if (input) input->outcome = result;
        if (!self || retired_) return result.applied;
        if (!result.applied) { undo_history_.pop_back(); reserved_undo = false; }
        if (result.applied) {
            syncUndo();
            if (!self || retired_) return true;
            setCurrentStructureIndex(static_cast<int>(structure_models_.size()) - 1);
            return true; // Actual addition; calculation/presentation is separate.
        }
    } catch (const std::exception& refusal) {
        if (!self || retired_) return result.applied;
        if (input && input->outcome.applied) result = input->outcome;
        if (reserved_undo && !result.applied) undo_history_.pop_back();
        if (result.applied) {
            result.published = false;
            result.message = tr("The structure and its Undo were retained; final presentation was incomplete");
            if (input) input->outcome = result;
            holdPublicationFailure(result.message);
            return true;
        }
        result.message = input ? original_input_error(refusal.what()) : QString::fromUtf8(refusal.what());
    }
    if (input) input->outcome = result;
    if (!self || retired_) return result.applied;
    const auto message = result.message;
    setLastError(message);
    if (self && !retired_) emit refused(message);
    return false;
}

bool ProjectViewModel::loadExperiments(const QList<QUrl>& files) {
    std::vector<std::string> paths;
    for (const QUrl& file : files) {
        if (!file.isLocalFile()) {
            emit refused(QStringLiteral("not a local file: %1").arg(file.toString()));
            return false;
        }
        paths.push_back(file.toLocalFile().toStdString());
    }
    edi::Project& project = *project_;
    // The files are read and checked as a batch first: a refused file adds nothing, and the batch is one edit.
    QString error;
    try {
        error = apply(edi::Edit::add_experiments(project, edi::load_experiment_edi_files(project, paths)), true);
    } catch (const std::exception& refusal) {
        error = QString::fromUtf8(refusal.what());
        setLastError(error);
    }
    if (!error.isEmpty()) {
        emit refused(error);
        return false;
    }
    noteAddedExperiments(project.experiments.size() - paths.size());
    setCurrentExperimentIndex(static_cast<int>(experiment_models_.size()) - 1);
    return true;
}

bool ProjectViewModel::canCreateExperiment() const {
    // A scan project holds its one template experiment (edi::Edit refuses another).
    return !(project_->sequential_fit.declared() && !project_->experiments.empty());
}

bool ProjectViewModel::createExperiment() {
    const PublicationScope publication(*this);
    const QPointer<ProjectViewModel> self(this);
    const auto input = widget_creation_input_;
    edi::Project& project = *project_;
    // The first free name of the form experiment1, experiment2, …
    std::string name;
    for (int n = 1; name.empty(); ++n) {
        const std::string candidate = "experiment" + std::to_string(n);
        const bool held = std::any_of(project.experiments.begin(), project.experiments.end(), [&candidate](const auto& item) {
            return folded_name(edi::KeyTraits<edi::BraggPdExperiment>::canonical(item->name)) == candidate;
        });
        name = held ? std::string() : candidate;
    }
    std::vector<std::string> structures;
    for (const auto& structure : project.structures) {
        structures.emplace_back(structure->name.value());
    }
    if (input && input->bounded_result && (!assistant_result_name(name) ||
        !std::all_of(structures.begin(), structures.end(), assistant_result_name))) {
        input->consumed = true; // The original refused input is one-shot before notifying.
        input->result_identity_refused = true;
        input->outcome.message = tr("The experiment or phase identity exceeds the assistant result limit; no edit was made");
        const auto message = input->outcome.message;
        setLastError(message);
        if (self && !retired_) emit refused(message);
        return false;
    }
    AddedExperiments added;
    added.experiments.push_back(nullptr); // exact one new member, no post-write vector growth
    undo_history_.reserve(undo_history_.size()+1);
    undo_history_.emplace_back(std::move(added));
    const auto historyIndex=undo_history_.size()-1;
    const auto before=project.experiments.size();
    QString error;
    try {
        error = apply_creation_control(edi::Edit::create_experiment(project, edi::simulation_experiment(name, {}, structures)), true,
            {CreationAction::Kind::ExperimentAppend});
    } catch (const std::exception& refusal) {
        error = input ? original_input_error(refusal.what()) : QString::fromUtf8(refusal.what());
    }
    if (!self || retired_) return input && input->outcome.applied;
    if (project.experiments.size()==before+1 && error.isEmpty())
        std::get<AddedExperiments>(undo_history_[historyIndex]).experiments[0]=project.experiments.back().get();
    else undo_history_.pop_back();
    if (!error.isEmpty()) {
        setLastError(error);
        if (self && !retired_) emit refused(error);
        return false;
    }
    syncLoadState();
    if (!self || retired_) return true;
    syncUndo();
    if (!self || retired_) return true;
    setCurrentExperimentIndex(static_cast<int>(experiment_models_.size()) - 1);
    return true;
}

bool ProjectViewModel::duplicateExperiment() {
    edi::Project& project = *project_;
    if (current_experiment_ < 0 || current_experiment_ >= static_cast<int>(project.experiments.size())) {
        return false;
    }
    QString error;
    try {
        const edi::BraggPdExperiment& source = *project.experiments[static_cast<std::size_t>(current_experiment_)];
        error = apply(edi::Edit::create_experiment(project, edi::experiment_copy(project, source)), true);
    } catch (const std::exception& refusal) {
        error = QString::fromUtf8(refusal.what());
        setLastError(error);
    }
    if (!error.isEmpty()) {
        emit refused(error);
        return false;
    }
    syncLoadState();
    noteAddedExperiments(project.experiments.size() - 1);
    setCurrentExperimentIndex(static_cast<int>(experiment_models_.size()) - 1);
    return true;
}

bool ProjectViewModel::setExperimentType(int index, const QString& axis, const QString& token) {
    const PublicationScope publication(*this);
    const QPointer<ProjectViewModel> self(this);
    const auto input=widget_creation_input_;
    if (index < 0 || index >= experiment_models_.size()) {
        return false;
    }
    edi::Project& project = *project_;
    const edi::ExperimentBase& experiment = *project.experiments[static_cast<std::size_t>(index)];
    edi::ExperimentTypeTokens type{edi::token(experiment.experiment_type.effective_sample_form()),
                                   edi::token(experiment.effective_beam_mode()),
                                   edi::token(experiment.experiment_type.effective_radiation_probe()),
                                   edi::token(experiment.experiment_type.effective_scattering_type())};
    const std::string value = token.toStdString();
    if (axis == QLatin1String("sampleForm")) {
        type.sample_form = value;
    } else if (axis == QLatin1String("beamMode")) {
        type.beam_mode = value;
    } else if (axis == QLatin1String("radiationProbe")) {
        type.radiation_probe = value;
    } else if (axis == QLatin1String("scatteringType")) {
        type.scattering_type = value;
    } else {
        return false;
    }
    std::vector<std::string> structures;
    for (const auto& link : experiment.linked_structures) {
        structures.emplace_back(link->structure_id.value());
    }
    QString error;
    try {
        edi::BraggPdExperiment replacement = edi::simulation_experiment(experiment.name, type, structures);
        // Within one beam mode the grid stays as it was set.
        if (replacement.effective_beam_mode() == experiment.effective_beam_mode() && experiment.data.has_value()) {
            replacement.data = experiment.data;
        }
        if (input && input->bounded_result && !assistant_result_experiment(replacement)) {
            input->consumed = true; // The original refused input is one-shot before notifying.
            input->result_identity_refused = true;
            input->outcome.message = tr("The replacement experiment or phase identity exceeds the assistant result limit; no edit was made");
            const auto message = input->outcome.message;
            setLastError(message);
            if (self && !retired_) emit refused(message);
            return false;
        }
        const edi::ExperimentBase* before = &experiment;
        error = apply_creation_control(edi::Edit::replace_experiment(project, experiment, std::move(replacement)), true,
            {CreationAction::Kind::ExperimentType, &experiment, axis, token});
        if (!self || retired_) return input && input->outcome.applied;
        if (error.isEmpty()) {
            // Undo of the experiment's creation removes it in its new type.
            experimentReplaced(before, project.experiments[static_cast<std::size_t>(index)].get());
            if (!self || retired_) return true;
            syncDatasets();
        }
    } catch (const std::exception& refusal) {
        error = input ? original_input_error(refusal.what()) : QString::fromUtf8(refusal.what());
        if (self && !retired_) setLastError(error);
    }
    if (!self || retired_) return input && input->outcome.applied;
    if (!error.isEmpty()) {
        emit refused(error);
        return false;
    }
    return true;
}

void ProjectViewModel::experimentReplaced(const edi::ExperimentBase* before, const edi::ExperimentBase* after) {
    for (UndoRecord& record : undo_history_) {
        if (auto* added = std::get_if<AddedExperiments>(&record)) {
            std::replace(added->experiments.begin(), added->experiments.end(), before, after);
        } else if (auto* loaded = std::get_if<LoadedData>(&record)) {
            loaded->experiment = loaded->experiment == before ? after : loaded->experiment;
        } else if (auto* control = std::get_if<edi::ExperimentControlsUndo>(&record)) {
            if(control->experiment==before)control->experiment=after;
        } else if (auto* structures = std::get_if<edi::StructuresUndo>(&record)) {
            for (auto& rows : structures->experiments) {
                rows.experiment = rows.experiment == before ? after : rows.experiment;
            }
        }
    }
    syncLoadState();
}

void ProjectViewModel::syncLoadState() {
    // Every experiment but a scan's takes Load data, made in this session or read from its file (the owner,
    // 2026-10-11): a scan's datasets take their data from the scan's files.
    for (ExperimentViewModel* model : experiment_models_) {
        model->setCanLoadData(!scan_);
    }
}

QString ProjectViewModel::replaceData(int index, edi::BraggPdExperiment replacement, bool restoring) {
    const PublicationScope publication(*this);
    const QPointer<ProjectViewModel> self(this);
    const auto input = widget_file_input_;
    edi::Project& project = *project_;
    const edi::ExperimentBase* before = project.experiments[static_cast<std::size_t>(index)].get();
    QString error;
    try {
        const EditOutcome result = applyEdit(edi::Edit::load_data(project, *before, std::move(replacement)), true, restoring);
        if (input && input->consumed) input->outcome = result;
        error = result.applied ? QString{} : result.message;
        if (!self || retired_) return error;
    } catch (const std::exception& refusal) {
        error = input ? original_input_error(refusal.what()) : QString::fromUtf8(refusal.what());
        if (self && !retired_) setLastError(error);
    }
    if (!error.isEmpty()) {
        return error;
    }
    if (!self || retired_) return error;
    experimentReplaced(before, project.experiments[static_cast<std::size_t>(index)].get());
    if (!self || retired_) return error;
    syncDatasets();
    return {};
}

bool ProjectViewModel::loadData(int index, const QUrl& file) {
    const PublicationScope publication(*this);
    const QPointer<ProjectViewModel> self(this);
    const auto input = widget_file_input_;
    const bool previous = widget_input_executing_;
    const auto release = qScopeGuard([self, previous] { if (self) self->widget_input_executing_ = previous; });
    const auto refuse = [this, self, input](const QString& refusal) {
        if (input && !input->outcome.applied) input->outcome.message = refusal;
        if (!self || retired_) return false;
        setLastError(refusal);
        if (self && !retired_) emit refused(refusal);
        return false;
    };
    if (index < 0 || index >= experiment_models_.size()) {
        return false;
    }
    if (!file.isLocalFile()) {
        return refuse(QStringLiteral("not a local file: %1").arg(file.toString()));
    }
    edi::Project& project = *project_;
    const edi::BraggPdExperiment& experiment = *project.experiments[static_cast<std::size_t>(index)];
    if (scan_) {
        return refuse(tr("A scan's datasets take their data from the scan's files; '%1' loads none of its own")
                          .arg(QString::fromStdString(experiment.name)));
    }
    if (input) {
        if (input->kind != WidgetFileInput::Kind::Measurement || input->consumed || input->path != file ||
            input->experiment != &experiment || !input->source)
            return refuse(tr("The chosen data does not match its admitted original experiment/file"));
        const bool sourceCurrent=!input->source_current || input->source_current();
        if(!self || retired_ || widget_file_input_!=input || static_cast<std::size_t>(index)>=project_->experiments.size() || project_->experiments[static_cast<std::size_t>(index)].get()!=&experiment)return false;
        if(!sourceCurrent) { input->source_changed=true;return refuse(tr("The original attached data changed or is unavailable")); }
        input->consumed = true; widget_input_executing_ = true;
    }
    // A name the user has not changed (experiment1, experiment2, …) gives way to the file's.
    const std::string& name = experiment.name.value();
    const bool default_name = name.size() > 10 && name.starts_with("experiment") &&
                              std::all_of(name.begin() + 10, name.end(), [](char c) { return c >= '0' && c <= '9'; });
    std::optional<edi::PlainDataLoad> read;
    try {
        if(input) {
            if(!input->reader_path.isLocalFile())return refuse(tr("The approved data reader input is unavailable"));
            read.emplace(edi::experiment_with_plain_data(experiment,input->reader_path.toLocalFile().toStdString(),file.toLocalFile().toStdString(),default_name));
        } else read.emplace(edi::experiment_with_plain_data(experiment, file.toLocalFile().toStdString(), default_name));
    } catch (const std::exception& refusal) {
        return refuse(input ? original_input_error(refusal.what()) : QString::fromUtf8(refusal.what()));
    }
    edi::PlainDataLoad& load = *read;
    // A file name another experiment already has, in any letter case (saved files are told apart without it),
    // keeps the experiment's own.
    const std::string wanted = folded_name(load.experiment.name);
    for (const auto& held : project.experiments) {
        if (held.get() != &experiment && folded_name(held->name) == wanted) {
            load.experiment.name = name;
        }
    }
    if (input && input->bounded_result && !assistant_result_experiment(load.experiment)) {
        input->consumed = true; // The original refused input is one-shot before notifying.
        input->result_identity_refused = true;
        return refuse(tr("The parsed data or phase identity exceeds the assistant result limit; no edit was made"));
    }
    if(input) {
        const bool sourceCurrent=!input->source_current || input->source_current();
        if(!self || retired_ || widget_file_input_!=input || static_cast<std::size_t>(index)>=project_->experiments.size() || project_->experiments[static_cast<std::size_t>(index)].get()!=&experiment)return false;
        if(!sourceCurrent) { input->source_changed=true;return refuse(tr("The original attached data changed or is unavailable")); }
    }
    const QString file_name = QString::fromStdString(load.file_name);
    LoadedData record{&experiment, std::make_shared<const edi::BraggPdExperiment>(experiment)};
    const QString loaded_name = QString::fromStdString(load.experiment.name);
    // Own the original experiment snapshot/history node before core publication.
    // experimentReplaced updates this same record with the actual new member.
    undo_history_.reserve(undo_history_.size() + 1);
    undo_history_.emplace_back(std::move(record));
    if (input) {
        input->points = load.points; input->skipped = load.skipped; input->nonpositive = load.nonpositive;
        input->duplicates = load.duplicates; input->reordered = load.reordered; input->derived = load.derived;
    }
    const auto error = replaceData(index, std::move(load.experiment));
    if (!self || retired_) return input && input->outcome.applied;
    if (!error.isEmpty()) {
        if (!input || !input->outcome.applied) undo_history_.pop_back();
        return refuse(error);
    }
    syncUndo();
    if (!self || retired_) return true;
    // One message: the points, then what the reader skipped or changed.
    QStringList notes;
    if (load.skipped != 0) {
        notes.append(tr("%n line(s) skipped that are not two or three numbers", nullptr, static_cast<int>(load.skipped)));
    }
    if (load.nonpositive != 0) {
        notes.append(tr("%n row(s) with intensity ≤ 0 skipped", nullptr, static_cast<int>(load.nonpositive)));
    }
    if (load.duplicates != 0) {
        notes.append(tr("%n row(s) with a repeated x skipped (the first kept)", nullptr, static_cast<int>(load.duplicates)));
    }
    if (load.reordered != 0) {
        notes.append(tr("%n row(s) reordered by x", nullptr, static_cast<int>(load.reordered)));
    }
    if (load.derived != 0) {
        notes.append(tr("σ = √max(y, 1) used for %n row(s) without a σ column", nullptr, static_cast<int>(load.derived)));
    }
    QString text = tr("%1 loaded into '%2': %n point(s)", nullptr, static_cast<int>(load.points)).arg(file_name, loaded_name);
    if (!notes.isEmpty()) {
        text += QStringLiteral("; ") + notes.join(QStringLiteral("; "));
    }
    emit message(text);
    if (!self || retired_) return true;
    setCurrentExperimentIndex(index);
    return true;
}

bool ProjectViewModel::loadDataInto(ExperimentViewModel* experiment, const QUrl& file) {
    const int index = experiment != nullptr ? static_cast<int>(experiment_models_.indexOf(experiment)) : -1;
    if (index < 0) {
        const QString refusal = tr("The experiment the file was chosen for is no longer in the project");
        setLastError(refusal);
        emit refused(refusal);
        return false;
    }
    return loadData(index, file);
}

bool ProjectViewModel::createStructure() {
    const PublicationScope publication(*this);
    const QPointer<ProjectViewModel> self(this);
    const auto input = widget_creation_input_;
    const CreationAction actual{CreationAction::Kind::StructureAppend};
    // Refuse a new invocation before factory/history work. A consumed receipt
    // belongs to the earlier invocation, even if its outcome was successful.
    if (widget_input_executing_ || widget_input_ || widget_relation_input_ || widget_background_input_ || widget_file_input_)
        return false;
    if (input && (input->consumed || input->expected.kind != actual.kind || input->expected.row != actual.row ||
        input->expected.field != actual.field || input->expected.text != actual.text || input->expected.number != actual.number))
        return false;
    QString readiness;
    {
        // Only this exact unconsumed input may enter its original readiness
        // check; restore execution before any publication or factory work.
        const bool previous = widget_input_executing_;
        const auto release = qScopeGuard([self, previous] { if (self) self->widget_input_executing_ = previous; });
        widget_input_executing_ = bool(input);
        readiness = editReadinessRefusal(false);
    }
    if (!readiness.isEmpty()) {
        setLastError(readiness);
        if (self && !retired_) emit refused(readiness);
        return false;
    }
    edi::Project& project = *project_;
    // The first free name of the form structure1, structure2, …
    std::string name;
    for (int n = 1; name.empty(); ++n) {
        const std::string candidate = "structure" + std::to_string(n);
        const bool held = std::any_of(project.structures.begin(), project.structures.end(), [&candidate](const auto& item) {
            return folded_name(edi::KeyTraits<edi::Structure>::canonical(item->name)) == candidate;
        });
        name = held ? std::string() : candidate;
    }
    // easydiffractionbeta's default phase (easyDiffractionApp/Logic/Model.py, _DEFAULT_CIF_BLOCK), under the new name.
    // The block names no Wyckoff letter; the site at the origin is P b n m's position a.
    const std::string text = "data_" + name +
                             "\n\n_edi.schema_version 3\n\n_space_group.name_h_m \"P b n m\"\n\n"
                             "_cell.length_a 10.\n_cell.length_b 6.\n_cell.length_c 5.\n"
                             "_cell.angle_alpha 90.\n_cell.angle_beta 90.\n_cell.angle_gamma 90.\n\n"
                             "loop_\n_atom_site.id\n_atom_site.type_symbol\n_atom_site.fract_x\n_atom_site.fract_y\n"
                             "_atom_site.fract_z\n_atom_site.wyckoff_letter\n_atom_site.occupancy\n_atom_site.adp_type\n"
                             "_atom_site.adp_iso\nO O 0. 0. 0. a 1. Biso 0.\n";
    bool reserved = false;
    QString error;
    try {
        auto structure = edi::structure_from_edi_text(text);
        if (input && input->bounded_result && !assistant_result_name(structure.name.value())) {
            input->consumed = true; input->result_identity_refused = true;
            input->outcome.message = tr("The generated structure identity exceeds the assistant result limit; no edit was made");
            return false;
        }
        auto before = edi::capture_structures(project);
        undo_history_.reserve(undo_history_.size()+1);
        undo_history_.emplace_back(std::move(before)); reserved = true;
        error = apply_creation_control(edi::Edit::add_structure(project, std::move(structure)), true, actual);
    } catch (const std::exception& refusal) {
        error = input ? original_input_error(refusal.what()) : QString::fromUtf8(refusal.what());
    }
    const bool applied = input ? input->outcome.applied : error.isEmpty();
    if (self && reserved && !applied) undo_history_.pop_back();
    if (!self || retired_) return applied;
    if (!error.isEmpty()) { setLastError(error); if (self && !retired_) emit refused(error); return applied; }
    {
        // History availability is part of this publication, including manual
        // Create: a synchronous observer cannot start another edit or Undo it.
        const bool previous = editing_;
        const auto release = qScopeGuard([self, previous] { if (self) self->editing_ = previous; });
        editing_ = true;
        syncUndo();
    }
    if (!self || retired_) return applied;
    setCurrentStructureIndex(static_cast<int>(structure_models_.size()) - 1);
    return applied;
}

bool ProjectViewModel::namePointsByPosition() {
    const PublicationScope publication(*this);
    const QPointer<ProjectViewModel> self(this);
    const auto input = widget_background_input_;
    const bool previous = widget_input_executing_;
    const auto release = qScopeGuard([self, previous] { if (self) self->widget_input_executing_ = previous; });
    if (current_experiment_ < 0 || current_experiment_ >= static_cast<int>(project_->experiments.size())) {
        return false;
    }
    edi::ExperimentBase& experiment = *project_->experiments[static_cast<std::size_t>(current_experiment_)];
    if (input) {
        if (!input->names || input->consumed || input->experiment != &experiment || input->members.size() != experiment.background.size()) return false;
        for (std::size_t i=0;i<input->members.size();++i)
            if (input->members[i] != experiment.background[i].get()) return false;
        input->consumed = true; widget_input_executing_ = true;
    }
    PointIds record{&experiment, {}};
    for (const auto& point : experiment.background) {
        record.before.push_back(point->id.value());
    }
    std::vector<std::string> ids = edi::position_point_ids(experiment);
    if (ids == record.before) {
        return true;
    }
    const auto edit = edi::Edit::background_point_ids(experiment, std::move(ids));
    undo_history_.reserve(undo_history_.size()+1);
    undo_history_.emplace_back(std::move(record)); // Actual Undo owner precedes the live edit.
    EditOutcome result;
    try { result = applyEdit(edit, true); }
    catch (...) { if(self)undo_history_.pop_back(); throw; }
    if (input) input->outcome=result;
    if (!self || retired_) return result.applied;
    if (!result.applied) undo_history_.pop_back();
    try { syncUndo(); }
    catch (...) {
        if (!result.applied) throw;
        result.published=false;result.message=tr("Background IDs and Undo were retained; presentation was incomplete");
        if(input)input->outcome=result;
        holdPublicationFailure(result.message);
    }
    if (!result.applied) { emit refused(result.message); return false; }
    return true;
}

bool ProjectViewModel::setParametersFree(const QList<ParameterItem*>& parameters, bool free) {
    const PublicationScope publication(*this);
    const QPointer<ProjectViewModel> self(this);
    const auto input = widget_input_;
    const bool previous = widget_input_executing_;
    const auto release = qScopeGuard([self, previous] { if(self)self->widget_input_executing_=previous; });
    if (input) {
        if(input->field!=WidgetParameterInput::Field::FreeGroup || input->consumed || input->free!=free ||
            input->members.size()!=static_cast<std::size_t>(parameters.size()))return false;
        for(qsizetype i=0;i<parameters.size();++i) {
            const auto* item=parameters[i];
            if(!registry_->items().contains(const_cast<ParameterItem*>(item)) || !item->isFittable() || !item->isRefinable() ||
                std::count(input->members.begin(),input->members.end(),item->parameter())!=1 ||
                std::count(parameters.begin(),parameters.end(),item)!=1)return false;
        }
        input->consumed=true;widget_input_executing_=true;
    }
    std::map<const edi::Parameter*, std::string> names;
    for (const edi::NamedSlot& slot : edi::named_slots(*project_)) {
        names.emplace(slot.parameter, slot.unique_name);
    }
    std::vector<std::pair<std::string, bool>> flags;
    for (const ParameterItem* item : parameters) {
        if (item == nullptr || !item->isFittable() || !item->isRefinable()) {
            continue;
        }
        const auto found = names.find(item->parameter());
        if (found == names.end() || item->isFree() == free) {
            continue;
        }
        flags.emplace_back(found->second, free);
    }
    if (flags.empty()) {
        return true;
    }
    const EditOutcome result = applyRecordedEdit(edi::Edit::set_free(*project_, std::move(flags)), false);
    if(input)input->outcome=result;
    if (!self || retired_) return result.applied;
    if (!result.applied) { emit refused(result.message); return false; }
    return true;
}

bool ProjectViewModel::duplicateStructure() {
    edi::Project& project = *project_;
    if (current_structure_ < 0 || current_structure_ >= static_cast<int>(project.structures.size())) {
        return false;
    }
    edi::StructuresUndo before = edi::capture_structures(project);
    QString error;
    try {
        const edi::Structure& source = *project.structures[static_cast<std::size_t>(current_structure_)];
        error = apply(edi::Edit::add_structure(project, edi::structure_copy(project, source)), true);
    } catch (const std::exception& refusal) {
        error = QString::fromUtf8(refusal.what());
        setLastError(error);
    }
    if (!error.isEmpty()) {
        emit refused(error);
        return false;
    }
    undo_history_.emplace_back(std::move(before));
    syncUndo();
    setCurrentStructureIndex(static_cast<int>(structure_models_.size()) - 1);
    return true;
}

void ProjectViewModel::loadScan() {
    evolution_ = new EvolutionViewModel(this);
    connect(evolution_, &EvolutionViewModel::refused, this, [this](const QString& message) {
        setLastError(message);
        emit refused(message);
    });
    const edi::Project& project = *project_;
    if (!project.sequential_fit.declared()) {
        return;
    }
    for (const auto& rule : project.sequential_fit.extract) {
        const QString id = QString::fromStdString(rule->id.value());
        const QString unit = QString::fromStdString(edi::scan_target_unit(rule->target));
        scan_columns_.append(unit.isEmpty() ? id : QStringLiteral("%1 (%2)").arg(id, unit));
    }
    scan_session_ = new ScanSession(this);
    connect(scan_session_, &ScanSession::metadataLoaded, this, [this](int first, int last) {
        for (int index = first; index <= last; ++index) {
            syncDataset(index);
        }
    });
    scan_refusal_ = scan_session_->load(project);
    // Results no run of the app described (no provenance file at all) are taken as this template's: an edit from
    // here marks them out of date, and the provenance is written with the next save. A provenance file that is
    // there but does not read is no such run: its results are shown out of date, and the reason given.
    if (scan_session_->run().invalid) {
        setLastError(scan_session_->run().error);
    } else if (scan_session_->run().identity.empty() && scanProcessed()) {
        scan_session_->assumeIdentity(ScanSession::templateIdentity(project));
    }
    syncScanAdmission();
    // A dataset row a view shows gets its extract values read, if its results row has none.
    experiment_list_->setShownHook([this](int row) {
        if (scan_) {
            scan_session_->want(row);
        }
    });
}

void ProjectViewModel::syncScanAdmission() {
    // A scan fits one template experiment against each listed file: with another experiment loaded beside it, or
    // no scan to list, the datasets are not shown and the scan modes do not run.
    const bool listed = scan_session_ != nullptr && !scan_session_->datasets().files.empty();
    const bool scan = scan_session_ != nullptr && project_->experiments.size() == 1 && listed;
    if (scan != scan_) {
        scan_ = scan;
        if (!scan_) {
            current_dataset_ = -1;
            projected_dataset_ = -1;
            scan_template_.reset();
        }
        emit scanChanged();
    }
}

QString ProjectViewModel::scanRefusal() const {
    if (scan_session_ == nullptr) {
        return tr("This project declares no scan (_sequential_fit)");
    }
    if (project_->experiments.size() != 1) {
        return tr("A scan fits one template experiment against each file; this project has %1 experiments")
            .arg(project_->experiments.size());
    }
    if (scan_session_->datasets().files.empty()) {
        return scan_refusal_.isEmpty() ? tr("The scan lists no data file") : scan_refusal_;
    }
    // A results file that does not read as this scan's is neither continued nor replaced by a run; Reset fits
    // clears it (one Undo step).
    if (!scan_session_->index().error.empty()) {
        return tr("The scan's results cannot be read (%1): Reset fits clears them")
            .arg(QString::fromStdString(scan_session_->index().error));
    }
    if (scan_session_->run().invalid) {
        return tr("The scan's run record cannot be read (%1): Reset fits clears it").arg(scan_session_->run().error);
    }
    return {};
}

int ProjectViewModel::templateIndex() const {
    return scan_ ? scan_session_->place(scanTemplateOrModel().sequential_fit.template_file) : -1;
}

ExperimentListModel::Dataset ProjectViewModel::datasetRow(int index) const {
    ExperimentListModel::Dataset dataset;
    const auto& files = scan_session_->datasets().files;
    // A row the list still holds while the session already lists fewer files (a re-list after save or Undo, before
    // the list follows) reads as empty.
    if (index < 0 || static_cast<std::size_t>(index) >= files.size()) {
        return dataset;
    }
    dataset.file = QString::fromStdString(files[static_cast<std::size_t>(index)]);
    dataset.is_template = files[static_cast<std::size_t>(index)] == scanTemplateOrModel().sequential_fit.template_file;
    dataset.outcome = scan_session_->outcome(index);
    // A fitted dataset's χ² from its results row, as a single fit's reliability shows it.
    const auto& results = scan_session_->index().rows;
    if (static_cast<std::size_t>(index) < results.size() && results[static_cast<std::size_t>(index)].offset >= 0) {
        dataset.reliability = QStringLiteral("χ² ") +
                              QString::number(results[static_cast<std::size_t>(index)].reduced_chi_square, 'f', 2);
    }
    // A single fit on the template dataset with no scan row gives it that fit's outcome.
    if (dataset.outcome.isEmpty() && dataset.is_template && scanTemplateOrModel().fit_result.held()) {
        dataset.outcome = recorded_outcome(scanTemplateOrModel().fit_result);
    }
    if (const std::vector<std::string>* values = scan_session_->extracted(index)) {
        std::size_t rule = 0;
        for (const auto& extract : project_->sequential_fit.extract) {
            QString value = rule < values->size() ? QString::fromStdString((*values)[rule]) : QString();
            const QString unit = QString::fromStdString(edi::scan_target_unit(extract->target));
            if (!value.isEmpty() && !unit.isEmpty()) {
                value += QStringLiteral(" ") + unit;
            }
            dataset.extracted.append(value);
            ++rule;
        }
    } else if (const QString error = scan_session_->metadataError(index); !error.isEmpty()) {
        // A file whose extract rules could not be read says so, rather than reading as one without values.
        dataset.extracted.append(tr("unreadable"));
    }
    return dataset;
}

void ProjectViewModel::syncDatasets() {
    syncScanAdmission();
    if (!scan_) {
        experiment_list_->setColumns({});
        experiment_list_->setExperiments(experiment_models_, *project_);
        syncPatternColours();
        return;
    }
    const int count = static_cast<int>(scan_session_->datasets().files.size());
    ExperimentViewModel* experiment = experiment_models_.value(0);
    experiment_list_->setColumns(scan_columns_);
    if (experiment_list_->showsDatasets(experiment, count)) {
        experiment_list_->datasetsChanged();
    } else {
        experiment_list_->setDatasets(experiment, count, [this](int index) { return datasetRow(index); });
    }
    if (experiment != nullptr) {
        experiment->setFitOutcome(current_dataset_ >= 0 && current_dataset_ < count ? datasetRow(current_dataset_).outcome
                                                                                    : QString());
    }
    syncPatternColours();
}

void ProjectViewModel::syncPatternColours() {
    // One colour per experiment on every page (edi::pattern_colour by place and count): a scan's template shows one
    // dataset at a time, in that dataset's colour among the scan's datasets.
    for (int i = 0; i < experiment_models_.size(); ++i) {
        if (scan_ && i == 0) {
            experiment_models_[i]->setColourPlace(static_cast<std::size_t>(std::max(current_dataset_, 0)),
                                                  scan_session_->datasets().files.size());
        } else {
            experiment_models_[i]->setColourPlace(std::nullopt, 0);
        }
    }
}

void ProjectViewModel::syncDataset(int index) {
    if (!scan_ || index < 0 || index >= static_cast<int>(scan_session_->datasets().files.size())) {
        return;
    }
    experiment_list_->datasetChanged(index);
    if (index == current_dataset_) {
        if (ExperimentViewModel* experiment = experiment_models_.value(0)) {
            experiment->setFitOutcome(datasetRow(index).outcome);
        }
    }
}

std::vector<edi::Edit::ScanValue> ProjectViewModel::datasetValues(const std::vector<std::string>& row) const {
    // Every parameter at the template's state, then the results row's value and uncertainty over it. The row was
    // checked as it was read: a cell that does not convert now refuses, never falling back to the template's value.
    std::vector<edi::Edit::ScanValue> values;
    edi::Project& from = const_cast<edi::Project&>(scanTemplateOrModel());
    for (const edi::NamedSlot& slot : edi::named_slots(from)) {
        values.push_back({slot.unique_name, slot.parameter->value.get(), slot.parameter->uncertainty.get()});
    }
    if (row.empty()) {
        return values;
    }
    std::map<std::string, const edi::ScanParameterColumns*> columns;
    for (const edi::ScanParameterColumns& parameter : scan_session_->index().parameters) {
        columns.emplace(parameter.name, &parameter);
    }
    for (edi::Edit::ScanValue& value : values) {
        const auto found = columns.find(edi::scan_results_column(value.unique_name));
        if (found == columns.end()) {
            // A parameter the results do not record keeps the template's value; its s.u. belonged to an
            // earlier fit, not to the one this row records.
            value.uncertainty.reset();
            continue;
        }
        double number = 0.0, uncertainty = 0.0;
        const std::string& uncertainty_cell = row[found->second->uncertainty];
        if (!edi::parse_scan_number(row[found->second->value], number) ||
            (uncertainty_cell != "nan" && !edi::parse_scan_number(uncertainty_cell, uncertainty))) {
            throw std::invalid_argument("analysis/results.csv: the row's '" + found->second->name +
                                        "' cells are not numbers");
        }
        value.value = number;
        // "nan": the fit gave this parameter no s.u. (it was not free in it).
        value.uncertainty = uncertainty_cell == "nan" ? std::nullopt : std::optional<double>(uncertainty);
    }
    return values;
}

void ProjectViewModel::viewDataset(int index, bool refresh) {
    // A view of another dataset replaces what a followed file waits to have drawn: its receipt is released
    // uncounted. The same dataset shown again (its row changed, the run settled) leaves it waiting.
    if (!follow_issuing_ && index != follow_index_) {
        followRendered(false);
    }
    // A scan writes nothing to the model, so its datasets can be shown while it runs; a single or joint fit's
    // model is not touched.
    if (!scan_ || index < 0 || index >= static_cast<int>(scan_session_->datasets().files.size()) ||
        (index == current_dataset_ && !refresh && projected_dataset_ == index) || experiment_models_.isEmpty() ||
        (fit_ != nullptr && fit_->running() && !fit_->scanning())) {
        return;
    }
    if (!scan_template_) {
        scan_template_ = *project_;
    }
    // The dataset already shown, with nothing pending: only its results row changed (a new row, Reset, Undo, a
    // run's end), so it is shown again at once from its row, with no file to read.
    if (index == current_dataset_ && view_applied_ == view_request_ && projected_dataset_ == index) {
        viewDatasetNow(index, false);
        return;
    }
    // One read at a time, and only the newest selection waits behind it: holding the selector or a fast Follow
    // leaves no queue of reads nobody will see.
    ++view_request_;
    view_wanted_ = index;
    publishCalculating();
    // The selection moves at once; the model follows when the read arrives. Until then an edit and a single or joint
    // fit are refused (pendingRefusal), so none acts on the dataset shown before. Reset fits, Undo of a scan's
    // results, a scan's start and a save act on the results and the template, not on the shown model: they go
    // ahead, and the dataset is read again after them (an older read in flight is dropped), so no projection
    // captured before them is applied over what they changed.
    if (index != current_dataset_) {
        current_dataset_ = index;
        syncDataset(index);
        emit currentExperimentIndexChanged();
    }
    if (!view_reading_) {
        startViewRead();
    }
}

QString ProjectViewModel::pendingRefusal() const { return editReadinessRefusal(false); }

QString ProjectViewModel::criticalEditRefusal(bool restoring) const {
    if (retired_) return tr("This project owner has been replaced or closed");
    if (editing_) return tr("The current project edit is still being published");
    if (fit_undo_invoking_ && (!fit_undo_input_ || fit_undo_input_->started))
        return tr("The current ordinary fit Undo is still being completed");
    if ((widget_input_ || widget_relation_input_ || widget_background_input_ || widget_file_input_ || widget_creation_input_) && !widget_input_executing_)
        return tr("The current visible native input is still being completed");
    if (edit_publication_failed_ && !restoring)
        return tr("An edit was applied but its presentation failed: Undo or reopen the project before further changes");
    return {};
}

QString ProjectViewModel::editReadinessRefusal(bool restoring) const {
    if (const QString critical = criticalEditRefusal(restoring); !critical.isEmpty()) return critical;
    // The model must hold the chosen dataset: not while its read is in flight, nor after a read that failed (the
    // model still holds the one before, whatever the selection says).
    if (view_applied_ != view_request_) {
        return tr("The chosen dataset is still being read");
    }
    if (scan_ && current_dataset_ >= 0 && projected_dataset_ != current_dataset_) {
        return tr("The chosen dataset could not be shown: choose it again, or another");
    }
    return {};
}

void ProjectViewModel::viewDatasetNow(int index, bool reread) {
    if (!follow_issuing_ && index != follow_index_) {
        followRendered(false);
    }
    // Read here, on the GUI thread, one dataset: the one a project opens on (`reread`), or the one already shown
    // when only its results row changed (its data are in the model, so no file is read). Nothing is left pending.
    const std::uint64_t request = ++view_request_;
    view_wanted_ = index;
    DatasetView view;
    try {
        view.values = datasetValues(scan_session_->row(*project_, index));
        if (reread || !project_->experiment().data) {
            view.data = edi::read_scan_dataset(scan_session_->datasets().directory,
                                               scan_session_->datasets().files[static_cast<std::size_t>(index)],
                                               project_->experiment().effective_beam_mode());
        } else {
            view.data = *project_->experiment().data;
        }
    } catch (const std::exception& refusal) {
        view_applied_ = request;
        const QString error = QString::fromUtf8(refusal.what());
        setLastError(error);
        emit refused(error);
        publishCalculating();
        return;
    }
    if (index != current_dataset_) {
        current_dataset_ = index;
        emit currentExperimentIndexChanged();
    }
    applyDatasetView(request, index, std::move(view));
}

void ProjectViewModel::startViewRead() {
    const std::uint64_t request = view_request_;
    const int index = view_wanted_;
    // The dataset's row is one line at its offset, checked again as it is read; its file is read off the GUI
    // thread.
    std::vector<edi::Edit::ScanValue> values;
    try {
        values = datasetValues(scan_session_->row(*project_, index));
    } catch (const std::exception& refusal) {
        view_applied_ = request;
        const QString error = QString::fromUtf8(refusal.what());
        setLastError(error);
        emit refused(error);
        publishCalculating();
        return;
    }
    // While a scan runs the worker is its own: a dataset shown gets its pattern calculated beside it, on a copy of
    // the template with the same values and data as the shown model, unless the scan's fit sent the followed file's
    // pattern with it (edi ADR-0029).
    std::optional<edi::Project> shown;
    if (fit_ != nullptr && fit_->scanning() && !(follow_frame_ && follow_frame_->first == index)) {
        shown = *scan_template_;
    }
    const std::string directory = scan_session_->datasets().directory;
    const std::string file = scan_session_->datasets().files[static_cast<std::size_t>(index)];
    const edi::BeamModeEnum mode = project_->experiment().effective_beam_mode();
    // A chart on d draws the shown dataset's d-spacing capture too.
    const bool d_spacing = !experiment_models_.isEmpty() && experiment_models_.front()->dSpacingWanted();
    view_reading_ = true;
    const QPointer<ProjectViewModel> self(this);
    run_in_background([self, request, index, directory, file, mode, d_spacing, values = std::move(values),
                       shown = std::move(shown)]() mutable {
        DatasetView view;
        view.values = std::move(values);
        try {
            view.data = edi::read_scan_dataset(directory, file, mode);
            if (shown) {
                edi::Edit::scan_view(*shown, shown->experiment(), view.values, *view.data)();
                edi::apply_relations(*shown);
                shown->calculate();
                view.frame = edi::FitFrame{edi::capture_pattern(*shown, 0)};
                if (d_spacing) {
                    view.d_frame = edi::capture_pattern(*shown, 0, edi::PatternAxis::DSpacing);
                }
            }
        } catch (const std::exception& refusal) {
            view.error = QString::fromUtf8(refusal.what());
        }
        QMetaObject::invokeMethod(
            QCoreApplication::instance(),
            [self, request, index, view = std::move(view)]() mutable {
                if (self.isNull()) {
                    return;
                }
                self->view_reading_ = false;
                if (self->view_applied_ == request) {
                    return;  // applied already
                }
                if (request != self->view_request_) {
                    // A newer selection came while this one was read: it is read now, this one dropped.
                    if (self->scan_ && self->view_applied_ != self->view_request_) {
                        self->startViewRead();
                    }
                    return;
                }
                self->applyDatasetView(request, index, std::move(view));
            },
            Qt::QueuedConnection);
    });
}

void ProjectViewModel::applyDatasetView(std::uint64_t request, int index, DatasetView view) {
    if (request != view_request_) {
        return;
    }
    view_applied_ = request;
    // The fit's pattern of a followed file goes with that file's view, and only while the scan runs.
    if (follow_frame_ && follow_frame_->first == index && fit_ != nullptr && fit_->scanning() && !view.frame) {
        view.frame = std::move(follow_frame_->second);
    }
    follow_frame_.reset();
    // A followed file is counted and the next one asked for once the chart is drawn with it, or released undrawn
    // when this read ends without it; any other view lets a followed scan move to its newest finished file.
    const bool followed = index == follow_index_ && !follow_file_.empty();
    if (followed && fit_ != nullptr && fit_->running() && fit_->scanning() && !patternShown()) {
        // No pattern chart is shown: the file is not applied, and the next one is asked for when a chart is.
        followRendered(false);
        return;
    }
    bool applied = false;
    const auto shown = qScopeGuard([this, followed, &applied] {
        if (followed) {
            if (applied) {
                awaitRender();
            } else {
                followRendered(false);
            }
        } else if (fit_ != nullptr) {
            fit_->followShown();
        }
    });
    if (!scan_ || (fit_ != nullptr && fit_->running() && !fit_->scanning())) {
        publishCalculating();
        return;
    }
    if (!view.data) {
        setLastError(view.error);
        emit refused(view.error);
        publishCalculating();
        return;
    }
    edi::Project& project = *project_;
    // Showing a dataset is not an edit: the project's modified state stays as it was.
    const bool modified = modified_;
    applying_view_ = true;
    const QString error = apply(
        edi::Edit::scan_view(project, project.experiment(), std::move(view.values), std::move(*view.data)), false);
    applying_view_ = false;
    setModified(modified);
    if (!error.isEmpty()) {
        emit refused(error);
        publishCalculating();
        return;
    }
    // A followed scan may have marked newer files while this one was read: the current dataset stays the newest
    // finished one, and only the pattern shown is this file's (edi ADR-0029).
    if (fit_ == nullptr || !fit_->following()) {
        current_dataset_ = index;
    }
    projected_dataset_ = index;
    syncDataset(index);
    publishCurrent();
    if (view.frame) {
        showFitFrame(*view.frame, std::move(view.d_frame));
    } else if (!view.error.isEmpty()) {
        setLastError(view.error);
    }
    applied = true;
}

void ProjectViewModel::syncOutOfDate() {
    // Results are out of date when the provenance the run wrote names another template than the one held now.
    // Results from a provenance file that does not read, or from more than one template, are out of date too.
    bool stale = false;
    const ScanSession::Run& run = scan_ ? scan_session_->run() : ScanSession::Run{};
    if (scan_ && scanProcessed()) {
        stale = run.invalid || run.mixed ||
                (!run.identity.empty() && run.identity != ScanSession::templateIdentity(scanTemplateOrModel()));
    }
    fit_->setOutOfDate(stale);
    evolution_->setOutOfDate(stale);
}

void ProjectViewModel::markTemplateChanged() {
    if (!scan_) {
        return;
    }
    syncOutOfDate();
}

QString ProjectViewModel::prepareScan(bool fresh) {
    const PublicationScope publication(*this);
    if (const QString critical = criticalEditRefusal(); !critical.isEmpty()) return critical;
    if (fit_ != nullptr && fit_->running()) return tr("A fit is running");
    if (const QString refusal = scanRefusal(); !refusal.isEmpty()) return refusal;
    if (project_->path.empty()) return tr("The project has no directory yet: save it first");
    const QString warning = tr("The scan preparation changed the project, but its presentation failed. Undo or reopen before further changes.");
    editing_ = true;
    const auto release = qScopeGuard([this] { editing_ = false; });
    run_identity_ = ScanSession::templateIdentity(scanTemplateOrModel());
    previous_run_.reset();
    if (!fresh) { previous_run_ = scan_session_->run(); return {}; }
    undo_history_.reserve(undo_history_.size() + 1);
    undo_history_.emplace_back(ScanRun{});
    auto& record = std::get<ScanRun>(undo_history_.back());
    QString refusal;
    try { refusal = scan_session_->takeFiles(*project_, record.files); }
    catch (...) { undo_history_.pop_back(); throw; } // takeFiles is the existing all-or-none file door.
    if (!refusal.isEmpty()) { undo_history_.pop_back(); return refusal; }
    try {
        syncUndo();
        if (retired_) return tr("The scan preparation owner was replaced");
        setModified(true);
        if (retired_) return tr("The scan preparation owner was replaced");
        reloadScanResults();
        if (retired_) return tr("The scan preparation owner was replaced");
    } catch (...) { holdPublicationFailure(warning); return warning; }
    return {};
}

QString ProjectViewModel::resetScan() {
    const PublicationScope publication(*this);
    if (const QString critical = criticalEditRefusal(); !critical.isEmpty()) return critical;
    if (fit_ != nullptr && fit_->running()) return tr("A fit is running");
    if (scan_session_ == nullptr) return scanRefusal();
    const QString warning = tr("The scan reset changed the project, but its presentation failed. Undo or reopen before further changes.");
    ScanRun run;
    run.fit_records = FitRecords{project_->fit_result, scan_template_ ? std::optional(scan_template_->fit_result) : std::nullopt};
    run.shown_dataset = projected_dataset_;
    for (const edi::NamedSlot& slot : edi::named_slots(*project_))
        run.shown_values.push_back({slot.unique_name, slot.parameter->value.get(), slot.parameter->uncertainty.get()});
    undo_history_.reserve(undo_history_.size() + 1);
    editing_ = true;
    const auto release = qScopeGuard([this] { editing_ = false; });
    undo_history_.emplace_back(std::move(run));
    auto& record = std::get<ScanRun>(undo_history_.back());
    QString refusal;
    try { refusal = scan_session_->takeFiles(*project_, record.files); }
    catch (...) { undo_history_.pop_back(); throw; }
    if (!refusal.isEmpty()) { undo_history_.pop_back(); setLastError(refusal); return refusal; }
    try {
        project_->fit_result = {};
        if (scan_template_) scan_template_->fit_result = {};
        syncCorrelations();
        if (retired_) return tr("The scan reset owner was replaced");
        syncUndo();
        if (retired_) return tr("The scan reset owner was replaced");
        setModified(true);
        if (retired_) return tr("The scan reset owner was replaced");
        reloadScanResults();
        if (retired_) return tr("The scan reset owner was replaced");
        if (current_dataset_ >= 0) {
            const QPointer<ProjectViewModel> self(this);
            const int index = current_dataset_;
            QMetaObject::invokeMethod(this, [self, index] {
                if (self && !self->retired_ && self->current_dataset_ == index) self->viewDataset(index, true);
            }, Qt::QueuedConnection);
        }
    } catch (...) { holdPublicationFailure(warning); return warning; }
    return {};
}

bool ProjectViewModel::restoreScanRun(const ScanRun& run, bool restoring) {
    const PublicationScope publication(*this);
    if (const QString critical = criticalEditRefusal(restoring); !critical.isEmpty()) { setLastError(critical); return false; }
    if (fit_ != nullptr && fit_->running()) return false;
    const QString warning = tr("The scan Undo restored files and model, but its presentation failed. Reopen before further changes.");
    const QString prepare_warning = tr("The previous scan results could not be prepared for Undo; nothing was restored.");
    editing_ = true;
    const auto release = qScopeGuard([this] { editing_ = false; });
    std::optional<FitRecords> records;
    std::optional<edi::detail::PreparedScanView> projection;
    bool files_committed = false;
    QString file_error;
    try {
        // Every owning copy, name resolution and projection allocation precedes
        // file reversal. No callbacks or model changes intervene before commit.
        records = run.fit_records;
        if (run.shown_dataset >= 0 && run.shown_dataset == projected_dataset_ &&
            view_applied_ == view_request_ && project_->experiment().data)
            projection.emplace(edi::detail::prepare_scan_view(*project_, project_->experiment(),
                run.shown_values, *project_->experiment().data));
        file_error = scan_session_->putFiles(*project_, run.files, &files_committed);
    } catch (...) {
        if (!files_committed) { setLastError(prepare_warning); return false; }
        file_error = warning; // Genuine file commit still obliges model restoration below.
    }
    if (!files_committed) {
        const QString message = tr("The previous scan results could not be put back: %1").arg(file_error);
        setLastError(message);
        if (!retired_) emit refused(message);
        return false; // The sole Undo remains; a kept-aside OS diagnostic is retained.
    }
    // Real model restoration, with prepared ownership and nonthrowing writes,
    // completes BEFORE observers. Only now may the caller consume this Undo.
    static_assert(std::is_nothrow_move_assignable_v<edi::FitResultRecord>);
    if (records) {
        project_->fit_result = std::move(records->model);
        if (scan_template_ && records->stash) scan_template_->fit_result = std::move(*records->stash);
    }
    if (projection) { projection->commit(); project_->note_edit(); }
    if ((records || projection) && fit_) fit_->invalidateFitUndo();
    try {
        if (records) { syncCorrelations(); if (retired_) return true; }
        setModified(true);
        if (retired_) return true;
        scan_refusal_ = scan_session_->load(*project_);
        reloadScanResults();
        if (retired_) return true;
        if (projection) {
            // shown_values captured every original named slot, including its
            // completed dependents. Publish that exact restored state; no new
            // normalization or owning data copy is part of the file commit.
            pending_structural_ = false;
            publish(false);
            if (retired_) return true;
            for (ExperimentViewModel* experiment : experiment_models_) {
                experiment->markPatternStale();
                if (retired_) return true;
            }
            for (StructureViewModel* structure : structure_models_) {
                if (!structure->structure()->geometry_current()) structure->markSceneStale();
                if (retired_) return true;
            }
            preview_->recalculate();
            if (retired_) return true;
            publishCalculating();
            if (retired_) return true;
            publishCurrent();
        } else if (current_dataset_ >= 0) {
            const QPointer<ProjectViewModel> self(this);
            const int index = current_dataset_;
            QMetaObject::invokeMethod(this, [self, index] {
                if (self && !self->retired_ && self->current_dataset_ == index) self->viewDataset(index, true);
            }, Qt::QueuedConnection);
        }
        if (!retired_) {
            if (file_error.isEmpty()) { edit_publication_failed_ = false; setLastError({}); }
            else holdPublicationFailure(file_error);
        }
    } catch (...) { holdPublicationFailure(warning); }
    return true;
}

void ProjectViewModel::reloadScanResults() {
    const PublicationScope publication(*this);
    if (retired_) return;
    if (scan_session_ == nullptr) {
        return;
    }
    if (const QString refusal = scan_session_->reindex(*project_); !refusal.isEmpty()) {
        setLastError(refusal);
        emit refused(refusal);
        if (retired_) return;
    }
    showScanResults();
}

void ProjectViewModel::showScanResults() {
    const PublicationScope publication(*this);
    if (retired_) return;
    syncDatasets();
    if (retired_) return;
    evolution_->setScan(scan_session_, project_.get(), scan_columns_.value(0));
    if (retired_) return;
    const ScanSession::Run& provenance = scan_session_->run();
    if (!scan_session_->index().error.empty()) {
        // A refused read has no rows to summarise: no summary is built from it, the refusal is shown instead.
        fit_->showScanRefused(QString::fromStdString(scan_session_->index().error), provenance.outcome,
                              provenance.seconds);
        syncOutOfDate();
        if (retired_) return;
        return;
    }
    fit_->showScan(scanSummary(provenance.outcome, provenance.seconds), !provenance.last_single);
    if (retired_) return;
    syncOutOfDate();
    if (retired_) return;
}

ScanSummary ProjectViewModel::scanSummary(const QString& run_outcome, double seconds) const {
    ScanSummary summary;
    summary.files = static_cast<int>(scan_session_->datasets().files.size());
    summary.seconds = seconds;
    // The worst file's outcome: Max iterations, then No step, then Not converged (no reason recorded), else Success.
    static const QStringList severity{QStringLiteral("refused"), QStringLiteral("maxIterations"),
                                      QStringLiteral("noStep"), QStringLiteral("notConverged")};
    QString worst;
    const auto& rows = scan_session_->index().rows;
    bool first = true;
    for (std::size_t index = 0; index < rows.size(); ++index) {
        summary.negative_points += static_cast<long long>(rows[index].negative_points);
        if (rows[index].skipped) {
            ++summary.skipped;
        }
        if (rows[index].offset < 0) {
            continue;
        }
        ++summary.fitted;
        ++(rows[index].converged ? summary.ok : summary.failed);
        const double chi2 = rows[index].reduced_chi_square;
        if (!std::isnan(chi2)) {  // a refused file has none
            summary.chi_min = first ? chi2 : std::min(summary.chi_min, chi2);
            summary.chi_max = first ? chi2 : std::max(summary.chi_max, chi2);
            first = false;
        }
        const QString outcome = scan_session_->outcome(static_cast<int>(index));
        const qsizetype rank = severity.indexOf(outcome);
        if (rank >= 0 && (worst.isEmpty() || rank < severity.indexOf(worst))) {
            worst = outcome;
        }
    }
    if (summary.fitted == 0) {
        // A run that failed or was stopped before its first file still says so; one that skipped every file it
        // reached is complete when it reached them all.
        if (run_outcome == QLatin1String("failed") || run_outcome == QLatin1String("stopped")) {
            summary.outcome = run_outcome;
        } else if (summary.skipped > 0) {
            summary.outcome = summary.skipped >= summary.files ? QStringLiteral("skipped") : QStringLiteral("stopped");
        }
        return summary;
    }
    // The run's own outcome when this app ran it (Failed, Stopped); otherwise the worst file's, a run that left
    // files unfitted reading as stopped part way.
    if (run_outcome == QLatin1String("failed") || run_outcome == QLatin1String("stopped")) {
        summary.outcome = run_outcome;
    } else if (summary.fitted + summary.skipped < summary.files) {
        summary.outcome = QStringLiteral("stopped");
    } else {
        summary.outcome = worst.isEmpty() ? QStringLiteral("success") : worst;
    }
    return summary;
}

int ProjectViewModel::scanFileFitted(const edi::ScanFileRecord& record) {
    if (scan_session_ == nullptr) {
        return -1;
    }
    // The event's own row: checked and indexed where the driver appended it, never read from the moving tail.
    QString error;
    const int index = scan_session_->addRow(*project_, record.cells, record.termination, error);
    if (index < 0) {
        setLastError(error);
        return -1;
    }
    syncDataset(index);
    evolution_->addRow(index, record.cells);
    adoptScanFileResult(scan_session_->datasets().files[static_cast<std::size_t>(index)], record.result);
    if (index == current_dataset_) {
        syncCorrelations();
    }
    // The shown dataset got its result: it is shown again with it.
    if (index == current_dataset_ && !(fit_ != nullptr && fit_->following())) {
        viewDataset(index, true);
    }
    return index;
}

void ProjectViewModel::markScanFile(const std::string& file) {
    const int index = scan_ && scan_session_ != nullptr ? scan_session_->place(file) : -1;
    if (index < 0 || index == current_dataset_) {
        return;
    }
    current_dataset_ = index;
    syncDataset(index);
    emit currentExperimentIndexChanged();
}

void ProjectViewModel::followScanFile(const std::string& file, std::uint64_t token) {
    // Each file as it is fitted: a lookup by name and one read, off the GUI thread.
    if (const int index = scan_session_ != nullptr ? scan_session_->place(file) : -1; index >= 0) {
        handFollowed(index, file, token);
        follow_issuing_ = true;
        viewDataset(index, true);
        follow_issuing_ = false;
    } else if (fit_ != nullptr) {
        fit_->followRendered(token, file, false);
    }
}

void ProjectViewModel::followScanFrame(const std::string& file, const edi::FitFrame& frame, std::uint64_t token) {
    // The file's data are still read off the GUI thread for the model; its pattern is the one given.
    if (const int index = scan_session_ != nullptr ? scan_session_->place(file) : -1; index >= 0) {
        handFollowed(index, file, token);
        follow_frame_.emplace(index, frame);
        follow_issuing_ = true;
        viewDataset(index, true);
        follow_issuing_ = false;
    } else if (fit_ != nullptr) {
        fit_->followRendered(token, file, false);
    }
}

namespace {

constexpr int kRenderWaitMs = 2000;

// The window the chart is drawn in: the app's application window, or a test's only Qt Quick window.
QQuickWindow* chart_window() {
    QQuickWindow* shown = nullptr;
    for (QWindow* window : QGuiApplication::topLevelWindows()) {
        auto* quick = qobject_cast<QQuickWindow*>(window);
        if (quick == nullptr) {
            continue;
        }
        if (quick->inherits("QQuickApplicationWindow")) {
            return quick;
        }
        if (shown == nullptr && quick->isVisible()) {
            shown = quick;
        }
    }
    return shown;
}

}  // namespace

void ProjectViewModel::handFollowed(int index, const std::string& file, std::uint64_t token) {
    followRendered(false);  // an earlier file still waiting is not counted
    follow_index_ = index;
    follow_file_ = file;
    follow_token_ = token;
    follow_generation_ = 0;
    const ExperimentViewModel* experiment = currentExperiment();
    follow_before_ = experiment != nullptr ? experiment->patternGeneration() : 0;
    render_swaps_ = -1;
    render_wait_.start(kRenderWaitMs);
}

bool ProjectViewModel::presentedFollowed() const {
    // The model still holds the followed dataset, and a shown chart has drawn its pattern (the one its application
    // set, or a later calculation of the same dataset).
    const ExperimentViewModel* experiment = currentExperiment();
    return experiment != nullptr && experiment->patternShown() && follow_generation_ != 0 &&
           projected_dataset_ == follow_index_ && experiment->presentedGeneration() >= follow_generation_;
}

bool ProjectViewModel::patternShown() const {
    const ExperimentViewModel* experiment = currentExperiment();
    return experiment != nullptr && experiment->patternShown();
}

void ProjectViewModel::awaitRender() {
    // The application must have set a new pattern: one that failed leaves the previous file's on the chart.
    const ExperimentViewModel* experiment = currentExperiment();
    const std::uint64_t generation = experiment != nullptr ? experiment->patternGeneration() : 0;
    follow_generation_ = generation != follow_before_ ? generation : 0;
    QQuickWindow* window = chart_window();
    if (window == nullptr || !presentedFollowed()) {
        followRendered(false);
        return;
    }
    if (!render_connection_) {
        // Swaps can be reported on the render thread; the count is kept on this one. The first swap may be a frame
        // already under way when the dataset was applied, so one more is asked for and the second one counts.
        render_connection_ = connect(
            window, &QQuickWindow::frameSwapped, this,
            [this, window] {
                if (render_swaps_ <= 0) {
                    return;
                }
                if (!presentedFollowed()) {
                    followRendered(false);  // hidden, or another pattern replaced it, before it was drawn
                } else if (--render_swaps_ == 0) {
                    followRendered(true);
                } else {
                    window->update();
                }
            },
            Qt::QueuedConnection);
    }
    render_swaps_ = 2;
    render_wait_.start(kRenderWaitMs);
    window->update();
}

void ProjectViewModel::followRendered(bool drawn) {
    if (follow_file_.empty()) {
        return;
    }
    const std::string file = std::move(follow_file_);
    const std::uint64_t token = follow_token_;
    follow_file_.clear();
    follow_index_ = -1;
    follow_token_ = 0;
    follow_generation_ = 0;
    render_swaps_ = -1;
    render_wait_.stop();
    if (fit_ != nullptr) {
        fit_->followRendered(token, file, drawn);
    }
}

bool ProjectViewModel::scanProcessed() const {
    // A scan ran when a file has a row or was skipped: an all-skipped scan has results to describe too.
    return scan_session_ != nullptr && scan_session_->index().fitted + scan_session_->index().skipped > 0;
}

void ProjectViewModel::settleScan() {
    if (scan_session_ != nullptr) {
        scan_session_->reindex(*project_);
    }
}

void ProjectViewModel::scanEnded(edi::FitStatus status, double seconds) {
    if (scan_session_ == nullptr) {
        return;
    }
    // The run's provenance: the template it fitted from, its time and outcome, kept beside the results.
    const QString final_outcome = status == edi::FitStatus::ERROR       ? QStringLiteral("failed")
                                  : status == edi::FitStatus::CANCELLED ? QStringLiteral("stopped")
                                                                        : QString();
    // A Continue: the total time adds this run's to the earlier ones' (unknown if theirs is), and rows from another
    // template than this run's leave the scan mixed (out of date) until Reset fits and a complete run replace them.
    ScanSession::Run provenance{run_identity_, seconds, final_outcome, false};
    if (previous_run_) {
        provenance.seconds = previous_run_->seconds >= 0.0 ? previous_run_->seconds + seconds : -1.0;
        provenance.mixed = previous_run_->mixed || previous_run_->invalid || previous_run_->identity != run_identity_;
    }
    previous_run_.reset();
    if (const QString refusal = scan_session_->writeRun(*project_, provenance); !refusal.isEmpty()) {
        setLastError(refusal);
    }
    setModified(true);
    if (!scan_session_->index().error.empty()) {
        // The results did not read whole: the datasets, the evolution and the counts stay as last accepted, and the
        // refusal is the state shown until a full read succeeds.
        fit_->showScanRefused(QString::fromStdString(scan_session_->index().error), final_outcome, provenance.seconds);
        return;
    }
    showScanResults();
    // The shown dataset as the rows on disk now give it.
    viewDataset(std::max(0, current_dataset_), true);
}

void ProjectViewModel::noteAddedExperiments(std::size_t before) {
    AddedExperiments added;
    for (std::size_t i = before; i < project_->experiments.size(); ++i) {
        added.experiments.push_back(project_->experiments[i].get());
    }
    if (!added.experiments.empty()) {
        undo_history_.emplace_back(std::move(added));
        syncUndo();
    }
}

void ProjectViewModel::removeStructure(int index) {
    if (index < 0 || index >= structure_models_.size()) {
        return;
    }
    edi::Project& project = *project_;
    // The experiments that link the structure lose the link (and any texture row for it) in the same step.
    const std::string name = project.structures[static_cast<std::size_t>(index)]->name.value();
    const std::string spelled = name.empty() ? std::string("structure") : name;
    QStringList linking;
    for (const auto& experiment : project.experiments) {
        for (const auto& link : experiment->linked_structures) {
            const std::string id = link->structure_id.value();
            if ((id.empty() ? std::string("structure") : id) == spelled) {
                linking.append(QString::fromStdString(experiment->name));
            }
        }
    }
    edi::StructuresUndo before = edi::capture_structures(project);
    const QString error = apply(edi::Edit::remove_structure(project, static_cast<std::size_t>(index)), true);
    if (!error.isEmpty()) {
        emit refused(error);
        return;
    }
    undo_history_.emplace_back(std::move(before));
    syncUndo();
    if (!linking.isEmpty()) {
        emit message(tr("Structure '%1' removed, with its link from %n experiment(s): %2", nullptr,
                        static_cast<int>(linking.size()))
                         .arg(QString::fromStdString(name), linking.join(QStringLiteral(", "))));
    }
}

int ProjectViewModel::structureIndex(const QString& name) const {
    const std::string wanted = name.toStdString();
    for (std::size_t i = 0; i < project_->structures.size(); ++i) {
        if (project_->structures[i]->name == wanted) {
            return static_cast<int>(i);
        }
    }
    return -1;
}

void ProjectViewModel::removeExperiment(int index) {
    if (index < 0 || index >= experiment_models_.size()) {
        return;
    }
    edi::Project& project = *project_;
    apply(edi::Edit::erase_experiment(project, static_cast<std::size_t>(index)), true);
}

void ProjectViewModel::pinTimestamps(const QString& timestamp) {
    // A demo seam, not an edit: the modified state stays as it was.
    const bool modified = modified_;
    edi::Project& project = *project_;
    apply(edi::Edit::timestamps(project, timestamp.toStdString()), false);
    setModified(modified);
}

std::shared_ptr<ProjectViewModel::WidgetRelationInput> ProjectViewModel::prepareWidgetRelations(const ProjectEditor::RelationAction& action) {
    if (const QString refusal = editReadinessRefusal(false); !refusal.isEmpty()) throw std::runtime_error(refusal.toStdString());
    auto input = std::make_shared<WidgetRelationInput>();
    input->expected = action;
    input->outcome.message = tr("The original relation control did not commit");
    widget_relation_input_ = input;
    return input;
}
void ProjectViewModel::finishWidgetRelations(const std::shared_ptr<WidgetRelationInput>& input) noexcept {
    if (widget_relation_input_ == input) widget_relation_input_.reset();
}
QString ProjectViewModel::apply_relation_control(const edi::Edit& change, const ProjectEditor::RelationAction& action) {
    const PublicationScope publication(*this);
    const auto input = widget_relation_input_;
    if (!input) return apply_relation_edit(change);
    if (input->consumed || input->expected.kind != action.kind || input->expected.row != action.row ||
        input->expected.text != action.text || input->expected.enabled != action.enabled)
        return tr("A different relation control cannot enter the original native event");
    input->consumed = true;
    const QPointer<ProjectViewModel> self(this);
    const bool previous = widget_input_executing_;
    widget_input_executing_ = true;
    const auto release = qScopeGuard([self, previous] { if (self) self->widget_input_executing_ = previous; });
    input->outcome = applyRecordedEdit(change, true);
    return input->outcome.applied ? QString{} : input->outcome.message;
}

std::shared_ptr<ProjectViewModel::WidgetParameterInput> ProjectViewModel::prepareWidgetValue(const edi::Parameter& parameter, double value) {
    if (const QString pending = editReadinessRefusal(false); !pending.isEmpty()) throw std::runtime_error(pending.toStdString());
    auto input = std::make_shared<WidgetParameterInput>();
    input->field = WidgetParameterInput::Field::Value; input->parameter = &parameter; input->value = value;
    input->outcome.message = tr("The visible parameter input was not committed");
    widget_input_ = input;
    return input;
}
std::shared_ptr<ProjectViewModel::WidgetParameterInput> ProjectViewModel::prepareWidgetFree(const edi::Parameter& parameter, bool free) {
    if (const QString pending = editReadinessRefusal(false); !pending.isEmpty()) throw std::runtime_error(pending.toStdString());
    auto input = std::make_shared<WidgetParameterInput>();
    input->field = WidgetParameterInput::Field::Free; input->parameter = &parameter; input->free = free;
    input->outcome.message = tr("The visible free-flag input was not committed");
    widget_input_ = input;
    return input;
}
std::shared_ptr<ProjectViewModel::WidgetParameterInput> ProjectViewModel::prepareWidgetFreeGroup(std::vector<const edi::Parameter*> members, bool free) {
    if (const QString pending=editReadinessRefusal(false);!pending.isEmpty())throw std::runtime_error(pending.toStdString());
    if(members.empty())throw std::invalid_argument("The original free-header set is empty");
    for(const auto* member:members) {
        const auto* item=registry_->find(member);
        if(!item || !item->isFittable() || !item->isRefinable() || std::count(members.begin(),members.end(),member)!=1)
            throw std::invalid_argument("The original free-header member changed");
    }
    auto input=std::make_shared<WidgetParameterInput>();input->field=WidgetParameterInput::Field::FreeGroup;
    input->members=std::move(members);input->free=free;input->outcome.message=tr("The original free-header action did not commit");
    widget_input_=input;return input;
}
void ProjectViewModel::finishWidgetInput(const std::shared_ptr<WidgetParameterInput>& input) noexcept {
    if (widget_input_ == input) widget_input_.reset(); // Never detach a replacement input.
}
QString ProjectViewModel::assign_parameter_value(edi::Parameter& parameter, double value) {
    const PublicationScope publication(*this);
    const auto input = widget_input_;
    if (!input) return ProjectEditor::assign_parameter_value(parameter, value);
    if (input->consumed || input->parameter != &parameter || input->field != WidgetParameterInput::Field::Value || input->value != value)
        return tr("A different parameter input cannot enter the current native event");
    input->consumed = true;
    widget_input_executing_ = true;
    const QPointer<ProjectViewModel> self(this);
    const auto release = qScopeGuard([self] { if (self) self->widget_input_executing_ = false; });
    input->outcome = applyRecordedEdit(edi::Edit::value(parameter, value), false);
    return input->outcome.applied ? QString{} : input->outcome.message;
}
QString ProjectViewModel::assign_parameter_free(edi::Parameter& parameter, bool free) {
    const PublicationScope publication(*this);
    const auto input = widget_input_;
    if (!input) return ProjectEditor::assign_parameter_free(parameter, free);
    if (input->consumed || input->parameter != &parameter || input->field != WidgetParameterInput::Field::Free || input->free != free)
        return tr("A different free-flag input cannot enter the current native event");
    input->consumed = true;
    widget_input_executing_ = true;
    const QPointer<ProjectViewModel> self(this);
    const auto release = qScopeGuard([self] { if (self) self->widget_input_executing_ = false; });
    input->outcome = applyRecordedEdit(edi::Edit::assign(parameter.free, free), false);
    return input->outcome.applied ? QString{} : input->outcome.message;
}

QString ProjectViewModel::apply(const edi::Edit& change, bool structural) {
    const PublicationScope publication(*this);
    const EditOutcome result = applyEdit(change, structural);
    if (!retired_ && !result.applied) setLastError(result.message);
    return result.applied ? QString{} : result.message;
}

ProjectViewModel::EditOutcome ProjectViewModel::applyEdit(const edi::Edit& change, bool structural, bool restoring) {
    const PublicationScope publication(*this);
    EditOutcome result;
    // Own the post-write warning before the write, including if exception formatting fails.
    const QString applied_warning = tr("The edit was applied, but its presentation could not be completed. Undo or reopen the project before further changes.");
    result.message = tr("The project edit was refused before changing the model");
    const auto refuse = [&result](const QString& message) {
        result.message = message;
        return result;
    };
    if (fit_ != nullptr && fit_->running() && !(applying_view_ && fit_->scanning()))
        return refuse(tr("The project cannot be edited while a fit is running"));
    // Reentrancy and an uncertain prior publication are unconditional fences,
    // including while a scan projection is being applied. Only a real Undo may
    // recover the publication fence; dataset readiness remains authoritative.
    if (const QString critical = criticalEditRefusal(restoring); !critical.isEmpty())
        return refuse(critical);
    if (const QString pending = editReadinessRefusal(restoring); !applying_view_ && !pending.isEmpty())
        return refuse(pending);
    const QPointer<ProjectViewModel> self(this);
    editing_ = true;
    const auto release = qScopeGuard([self] { if (self) self->editing_ = false; });
    pending_structural_ = structural;
    const auto relation_input = widget_input_executing_ ? widget_relation_input_ : nullptr;
    const auto background_input = widget_input_executing_ ? widget_background_input_ : nullptr;
    const auto parameter_input = widget_input_executing_ ? widget_input_ : nullptr;
    const auto file_input = widget_input_executing_ ? widget_file_input_ : nullptr;
    const auto creation_input = widget_input_executing_ ? widget_creation_input_ : nullptr;
    auto* applied_result = creation_input && creation_input->consumed ? &creation_input->applied_result
        : file_input && file_input->consumed ? &file_input->applied_result : nullptr;
    const auto fit_undo_input = fit_undo_invoking_ && fit_undo_input_ && fit_undo_input_->consumed && !fit_undo_input_->started ? fit_undo_input_ : nullptr;
    if (fit_undo_input) fit_undo_input->started = true;
    bool* applied = fit_undo_input ? &fit_undo_input->outcome.applied : creation_input && creation_input->consumed ? &creation_input->outcome.applied
        : file_input && file_input->consumed ? &file_input->outcome.applied
        : relation_input && relation_input->consumed ? &relation_input->outcome.applied
        : background_input && background_input->consumed ? &background_input->outcome.applied
        : parameter_input && parameter_input->consumed ? &parameter_input->outcome.applied : &result.applied;
    try {
        preview_->apply(change, applied, applied_result);
        result.applied = *applied;
        if (result.applied && fit_) fit_->invalidateFitUndo();
        if (!self || retired_) { result.message = applied_warning; return result; }
        // An admitted edit while a scan dataset is shown (edi ADR-0017 §19): a project-wide setting goes to the
        // template too; an edit of the experiment or the structures makes the shown values the template's, over the
        // template's own data file. A refused edit never gets here. A stopped scan is then started afresh.
        if (!applying_view_) {
            if (scan_template_ && applying_setting_) {
                scan_template_->metadata = project_->metadata;
                scan_template_->fitting_mode = project_->fitting_mode;
                scan_template_->descent = project_->descent;
                scan_template_->minimizer_max_iterations = project_->minimizer_max_iterations;
                scan_template_->minimizer_chi_square_tolerance = project_->minimizer_chi_square_tolerance;
                scan_template_->su_rule = project_->su_rule;
                scan_template_->report_html = project_->report_html;
                scan_template_->report_pdf = project_->report_pdf;
                scan_template_->report_cif = project_->report_cif;
                scan_template_->report_html_offline = project_->report_html_offline;
                scan_template_->report_excluded = project_->report_excluded;
                scan_template_->correlation_threshold = project_->correlation_threshold;
                scan_template_->pattern_x_axis = project_->pattern_x_axis;
            } else if (scan_template_) {
                edi::Project promoted = *project_;
                promoted.experiment().data = scan_template_->experiment().data;
                promoted.experiment().calculation_only = scan_template_->experiment().calculation_only;
                scan_template_ = std::move(promoted);
            }
            // The results' outdated state follows any change of the template's identity, the minimizer's settings included.
            markTemplateChanged();
            if (!self || retired_) { result.message = applied_warning; return result; }
        }
        setLastError({});
        if (!self || retired_) { result.message = applied_warning; return result; }
        setModified(true);
        if (!self || retired_) { result.message = applied_warning; return result; }
        publishCalculating();
        if (!self || retired_) { result.message = applied_warning; return result; }
        edit_publication_failed_ = false;
        notifyProjectEdited();
        if (!self || retired_) { result.message = applied_warning; return result; }
        result.published = true;
        result.message.clear();
    } catch (...) {
        result.applied = *applied;
        if (result.applied && fit_) fit_->invalidateFitUndo();
        if (!self || retired_) {
            result.message = result.applied ? applied_warning : result.message;
            return result;
        }
        if (result.applied) {
            // Completion/request/Qt observers may fail AFTER the actual closed edit.
            // Its exact Undo footprint already belongs to the history, never a rollback.
            finishRecordedEdit();
            edit_publication_failed_ = true;
            result.message = applied_warning;
            try { setModified(true); } catch (...) { /* actual edit/Undo stay owned */ }
            if (self && !retired_) try { notifyProjectEdited(); } catch (...) { /* fence remains authoritative */ }
        } else {
            try { throw; }
            catch (const std::exception& error) {
                try { result.message = (creation_input || file_input) ? original_input_error(error.what()) : QString::fromUtf8(error.what()); } catch (...) { /* prepared refusal */ }
            } catch (...) { /* prepared refusal */ }
        }
        if (self && !retired_) try { setLastError(result.message); } catch (...) { /* prepared result still returns to its owner */ }
    }
    return result;
}

QString ProjectViewModel::applyUndo(const edi::Edit& change, bool structural) {
    const auto input = fit_undo_input_;
    if (input) {
        if (!fit_undo_invoking_ || !input->consumed || input->started || !fitUndoAvailable() ||
            input->attempt != fit_->undo_attempt_) return tr("The latest adopted fit is no longer undoable");
    }
    const EditOutcome result = applyEdit(change, structural, true);
    if (input) {
        input->outcome.applied = result.applied;
        input->outcome.published = result.published;
    }
    return result.applied ? QString{} : result.message;
}

QString ProjectViewModel::apply_setting(const edi::Edit& change) {
    const PublicationScope publication(*this);
    applying_setting_ = true;
    const QString refusal = apply(change, false);
    applying_setting_ = false;
    return refusal;
}

QString ProjectViewModel::apply_report_setting(const edi::Edit& change) {
    const PublicationScope publication(*this);
    if (const QString critical = criticalEditRefusal(); !critical.isEmpty()) return critical;
    const QString warning = tr("The report setting was applied and Undo retained, but its presentation failed");
    edi::ReportSettingsState before = edi::report_settings_state(*project_);
    undo_history_.reserve(undo_history_.size() + 1);
    undo_history_.emplace_back(std::move(before)); // own normal Undo before the report setting writes
    QString refusal;
    try { refusal = write_report_settings(change); }
    catch (...) { undo_history_.pop_back(); throw; } // Only pre-write setup can escape.
    if (retired_) return refusal;
    if (!refusal.isEmpty()) { undo_history_.pop_back(); return refusal; }
    try { syncUndo(); }
    catch (...) { holdPublicationFailure(warning); }
    return refusal;
}

QString ProjectViewModel::write_report_settings(const edi::Edit& change, bool restoring) {
    const PublicationScope publication(*this);
    if (const QString critical = criticalEditRefusal(restoring); !critical.isEmpty()) return critical;
    if (fit_ != nullptr && fit_->running()) return tr("The project cannot be edited while a fit is running");
    const QString warning = tr("The report setting was applied, but its presentation failed. Undo or reopen before further changes.");
    bool applied = false;
    editing_ = true;
    const auto release = qScopeGuard([this] { editing_ = false; });
    try {
        preview_->apply_setting(change);
        applied = true;
        if (fit_) fit_->invalidateFitUndo();
        notifyProjectEdited();
        if (retired_) return {};
        if (scan_template_) edi::Edit::report_settings(*scan_template_, edi::report_settings_state(*project_))();
        setLastError({});
        if (retired_) return {};
        setModified(true);
        if (retired_) return {};
        publishMetadata();
        if (retired_) return {};
        syncCorrelations();
        if (retired_) return {};
        saved_files_.reset();
        invalidateTexts();
        if (retired_) return {};
        report_->refresh();
        if (!retired_) edit_publication_failed_ = false;
        return {};
    } catch (const std::exception& error) {
        if (applied) { holdPublicationFailure(warning); return {}; }
        const QString refusal = QString::fromUtf8(error.what());
        setLastError(refusal);
        return refusal;
    } catch (...) {
        if (applied) { holdPublicationFailure(warning); return {}; }
        throw;
    }
}

void ProjectViewModel::finishRecordedEdit() noexcept {
    RecordedEdit* record = recording_;
    if (record == nullptr) return;
    recording_ = nullptr; // no UI observer can reuse this stack receipt
    auto& states = std::get<edi::RelationsUndo>(undo_history_[record->index]).parameters;
    std::size_t kept = 0;
    for (std::size_t i = 0; i < states.size(); ++i) {
        const edi::Parameter& now = *record->targets[i];
        const auto& before = states[i];
        if (now.value.get() != before.value || now.uncertainty.get() != before.uncertainty || now.free.get() != before.free) {
            if (kept != i) states[kept] = std::move(states[i]);
            ++kept;
        }
    }
    states.resize(kept); // shrink only; strings move, no map/traversal/allocation after write
}

ProjectViewModel::EditOutcome ProjectViewModel::applyRecordedEdit(const edi::Edit& change, bool structural) {
    const PublicationScope publication(*this);
    if (const QString pending = editReadinessRefusal(false); !pending.isEmpty())
        return {false, false, pending};
    const QPointer<ProjectViewModel> self(this);
    const QString warning = tr("The edit was applied and Undo retained, but its presentation could not be completed");
    edi::RelationsUndo before = edi::capture_relations(*project_);
    // These closed relation/value/free operations preserve parameter membership/names.
    // Resolve the exact before-state pointers BEFORE writing, not after publication.
    std::map<std::string, const edi::Parameter*> named;
    for (const edi::NamedSlot& slot : edi::named_slots(*project_)) named.emplace(slot.unique_name, slot.parameter);
    RecordedEdit record;
    record.index = undo_history_.size();
    record.targets.reserve(before.parameters.size());
    for (const auto& state : before.parameters) record.targets.push_back(named.at(state.unique_name));
    undo_history_.reserve(record.index + 1);
    const auto detach = qScopeGuard([self, &record] {
        if (self && self->recording_ == &record) self->recording_ = nullptr;
    });
    undo_history_.emplace_back(std::move(before)); // complete owner exists before the first live write
    recording_ = &record;
    EditOutcome result;
    try { result = applyEdit(change, structural); }
    catch (...) {
        // applyEdit contains every post-write failure; only its pre-write setup
        // can escape. The prepared but unadmitted Undo must not become a step.
        if (self) {
            recording_ = nullptr;
            undo_history_.pop_back();
        }
        throw;
    }
    if (!self || retired_) return result;
    if (!result.applied) {
        recording_ = nullptr;
        undo_history_.pop_back();
    } else finishRecordedEdit();
    try { syncUndo(); }
    catch (...) {
        if (result.applied) {
            edit_publication_failed_ = true;
            result.published = false;
            result.message = warning;
            holdPublicationFailure(warning);
        } else throw;
    }
    return result;
}

ProjectViewModel::EditOutcome ProjectViewModel::populateEmptyProject(const std::shared_ptr<edi::EmptyProjectPopulation>& prepared) {
    const PublicationScope publication(*this);
    if (const QString pending = editReadinessRefusal(false); !pending.isEmpty()) return {false, false, pending};
    if (!edi::empty_for_population(*project_)) return {false, false, tr("The current project is no longer empty")};
    const auto edit = edi::Edit::populate_empty_project(*project_, prepared);
    const QPointer<ProjectViewModel> self(this);
    const QString warning = tr("The scientific graph was added and Undo retained, but its presentation was incomplete");
    undo_history_.reserve(undo_history_.size() + 1);
    undo_history_.emplace_back(EmptyPopulationUndo{prepared}); // before the first live write
    EditOutcome result;
    try { result = applyEdit(edit, true); }
    catch (...) { if (self && !prepared->committed()) undo_history_.pop_back(); throw; }
    if (!self || retired_) return result;
    if (!prepared->committed()) undo_history_.pop_back();
    try {
        if (prepared->committed()) {
            // Same explicit selection as the ordinary separate block imports.
            setCurrentStructureIndex(0);
            if (retired_) return result;
            setCurrentExperimentIndex(0);
            if (retired_) return result;
        }
        syncUndo();
    }
    catch (...) {
        if (!prepared->committed()) throw;
        result.applied = true; result.published = false; result.message = warning;
        edit_publication_failed_ = true; holdPublicationFailure(warning);
    }
    return result;
}

std::shared_ptr<ProjectViewModel::WidgetBackgroundInput> ProjectViewModel::prepareWidgetBackground(
    edi::ExperimentBase& experiment, const edi::BackgroundPointInput& expected) {
    if (const QString refusal = editReadinessRefusal(false); !refusal.isEmpty()) throw std::runtime_error(refusal.toStdString());
    auto input = std::make_shared<WidgetBackgroundInput>(); input->experiment = &experiment; input->expected = expected;
    if (expected.action != edi::BackgroundPointInput::Action::Add) {
        const auto row = std::find_if(experiment.background.begin(), experiment.background.end(),
            [&](const auto& point) { return point->id.value() == expected.id; });
        if (row == experiment.background.end()) throw std::invalid_argument("The original background member is unavailable");
        input->row = row->get();
    }
    input->outcome.message = tr("The original background control did not commit");
    widget_background_input_ = input; return input;
}
std::shared_ptr<ProjectViewModel::WidgetBackgroundInput> ProjectViewModel::prepareWidgetBackgroundRename(
    edi::ExperimentBase& experiment, edi::LineSegment& point, const std::string& id) {
    if (const QString refusal = editReadinessRefusal(false); !refusal.isEmpty()) throw std::runtime_error(refusal.toStdString());
    auto input = std::make_shared<WidgetBackgroundInput>();
    input->experiment = &experiment; input->row = &point; input->rename = true; input->expected.id = id;
    input->outcome.message = tr("The original background ID control did not commit");
    widget_background_input_ = input; return input;
}
std::shared_ptr<ProjectViewModel::WidgetBackgroundInput> ProjectViewModel::prepareWidgetBackgroundNames(edi::ExperimentBase& experiment) {
    if(const QString pending=editReadinessRefusal(false);!pending.isEmpty())throw std::runtime_error(pending.toStdString());
    if(!currentExperiment() || currentExperiment()->experiment()!=&experiment)throw std::invalid_argument("The original background experiment changed");
    auto input=std::make_shared<WidgetBackgroundInput>();input->names=true;input->experiment=&experiment;
    input->members.reserve(experiment.background.size());
    for(const auto& point:experiment.background)input->members.push_back(point.get());
    input->outcome.message=tr("The original position-derived IDs action did not commit");widget_background_input_=input;return input;
}
void ProjectViewModel::finishWidgetBackground(const std::shared_ptr<WidgetBackgroundInput>& input) noexcept {
    if (widget_background_input_ == input) widget_background_input_.reset();
}
ProjectViewModel::EditOutcome ProjectViewModel::changeBackgroundPoint(
    edi::ExperimentBase& experiment, const edi::BackgroundPointInput& request, bool native_bounded) {
    const PublicationScope publication(*this);
    const QPointer<ProjectViewModel> self(this);
    const auto input = widget_background_input_;
    EditOutcome result;
    result.message = tr("The background point operation was refused");
    const bool previous = widget_input_executing_;
    std::shared_ptr<edi::BackgroundPointChange> prepared;
    try {
        using Limits = edi::assistant::Limits;
        if (input) {
            const auto& expected = input->expected;
            if (input->rename || input->consumed || input->experiment != &experiment || request.action != expected.action || request.id != expected.id ||
                (request.action != edi::BackgroundPointInput::Action::Remove && (request.position != expected.position ||
                 request.intensity != expected.intensity || request.free != expected.free)))
                throw std::invalid_argument("The actual background control differs from its original request");
            if (request.action != edi::BackgroundPointInput::Action::Add &&
                std::none_of(experiment.background.begin(), experiment.background.end(), [&](const auto& point) {
                    return point.get() == input->row && point->id.value() == request.id;
                })) throw std::invalid_argument("The original background member was replaced");
            input->consumed = true; widget_input_executing_ = true;
        }
        const auto release = qScopeGuard([self, previous] { if (self) self->widget_input_executing_ = previous; });
        if (const QString refusal = editReadinessRefusal(false); !refusal.isEmpty()) { result.message = refusal; if (input) input->outcome = result; return result; }
        if (!currentExperiment() || currentExperiment()->experiment() != &experiment)
            throw std::invalid_argument("The requested background bank is not the selected experiment");
        // Native packet/source/domain policy is caller-owned. Ordinary manual
        // simulation/extrapolation and stored keys use this same Edit/Undo path.
        const auto unbounded = std::numeric_limits<std::size_t>::max();
        prepared = edi::prepare_background_point(*project_, experiment, request,
            native_bounded ? Limits::stream_items : unbounded, native_bounded ? Limits::id_bytes : unbounded,
            native_bounded ? edi::assistant::SelectedFileLimits::collection_bytes / sizeof(double) : unbounded,
            native_bounded ? Limits::stream_items : unbounded, native_bounded);
        if (input && request.action != edi::BackgroundPointInput::Action::Remove) {
            const auto row = std::find_if(prepared->after.begin(), prepared->after.end(),
                [&](const auto& point) { return point->id.value() == request.id; });
            if (row == prepared->after.end()) throw std::invalid_argument("The prepared background row is unavailable");
            input->result_row = row->get(); // Exact preowned replacement, before any model callback.
        }
        const auto edit = edi::Edit::background_point(*project_, prepared);
        const auto index = undo_history_.size(); undo_history_.reserve(index + 1);
        undo_history_.emplace_back(BackgroundPointUndo{prepared});
        try { result = applyEdit(edit, true); }
        catch (...) { if (self && !prepared->committed) undo_history_.pop_back(); throw; }
        if (input) input->outcome = result; // Actual committed/applied latch before presentation/readback.
        if (!self || retired_) return result;
        if (!prepared->committed) undo_history_.pop_back();
        try { syncUndo(); }
        catch (...) {
            if (!result.applied) throw;
            result.published = false; result.message = tr("The background edit and Undo are retained; final presentation was incomplete");
            holdPublicationFailure(result.message);
        }
    } catch (...) {
        if (input && input->outcome.applied) result = input->outcome;
        if (prepared && prepared->committed) result.applied = true;
        if (!result.applied) result.message = tr("The background edit was refused; check its current bank, ID, measured domain and relation ownership");
        else { result.published = false; result.message = tr("The background edit was applied; final presentation was not confirmed"); }
    }
    if (input) input->outcome = result;
    return result;
}
ProjectEditor::BackgroundOutcome ProjectViewModel::edit_background_point(edi::ExperimentBase& experiment, const edi::BackgroundPointInput& request) {
    const QPointer<ProjectViewModel> self(this);
    const auto result = changeBackgroundPoint(experiment, request);
    if (self && !retired_ && !result.applied) setLastError(result.message);
    return {result.applied, result.published, result.message};
}
QString ProjectViewModel::rename_background_point(edi::ExperimentBase& experiment, edi::LineSegment& point, const std::string& id) {
    const PublicationScope publication(*this);
    const auto input = widget_background_input_;
    const QPointer<ProjectViewModel> original(this);
    const bool previous = widget_input_executing_;
    if (input) {
        if (!input->rename || input->consumed || input->experiment != &experiment || input->row != &point || input->expected.id != id)
            return tr("A different background ID cannot enter the original control");
        input->consumed = true; widget_input_executing_ = true;
    }
    const auto release = qScopeGuard([original, previous] { if (original) original->widget_input_executing_ = previous; });
    if (const QString refusal = editReadinessRefusal(false); !refusal.isEmpty()) return refusal;
    if (!currentExperiment() || currentExperiment()->experiment() != &experiment ||
        std::none_of(project_->experiments.begin(), project_->experiments.end(), [&](const auto& bank) { return bank.get() == &experiment; }))
        return tr("The background experiment was replaced or is not selected");
    PointIds before{&experiment, {}}; before.before.reserve(experiment.background.size());
    bool found = false;
    for (const auto& row : experiment.background) {
        before.before.push_back(row->id.value()); found = found || row.get() == &point;
    }
    if (!found) return tr("The exact background row was replaced");
    undo_history_.reserve(undo_history_.size() + 1); undo_history_.emplace_back(std::move(before));
    const QPointer<ProjectViewModel> self(this);
    EditOutcome result;
    try { result = applyEdit(edi::Edit::background_id(point, id), true); }
    catch (...) { if (self) undo_history_.pop_back(); throw; }
    if (input) input->outcome = result;
    if (!self || retired_) return result.applied ? QString{} : result.message;
    if (!result.applied) undo_history_.pop_back();
    try { syncUndo(); } catch (...) { if (!result.applied) throw; holdPublicationFailure(tr("The background rename and Undo are retained")); }
    return result.applied ? QString{} : result.message;
}

QString ProjectViewModel::apply_relation_edit(const edi::Edit& change) {
    const PublicationScope publication(*this);
    if (widget_relation_input_) return tr("A different relation action cannot enter the original native control");
    const EditOutcome result = applyRecordedEdit(change, true);
    if (!retired_ && !result.applied) setLastError(result.message);
    return result.applied ? QString{} : result.message;
}

QString ProjectViewModel::rename_structure(edi::Structure& structure, const std::string& name) {
    const PublicationScope publication(*this);
    const QPointer<ProjectViewModel> self(this);
    BlockName record{true, {}, structure.name.value(), project_->fit_result.scan_results, {}};
    const QString refusal = apply_creation_control(edi::Edit::structure_name(structure, name), true,
        {CreationAction::Kind::StructureName,&structure,{},QString::fromStdString(name)});
    if (!self || retired_) return refusal;
    if (refusal.isEmpty() && structure.name.value() != record.before) {
        record.name = structure.name.value();
        record.results_after = project_->fit_result.scan_results;
        undo_history_.emplace_back(std::move(record));
        syncUndo();
    }
    return refusal;
}

QString ProjectViewModel::rename_experiment(edi::Project& project, edi::ExperimentBase& experiment,
                                            const std::string& name) {
    const PublicationScope publication(*this);
    const QPointer<ProjectViewModel> self(this);
    BlockName record{false, {}, experiment.name.value(), project_->fit_result.scan_results, {}};
    const QString refusal = apply_creation_control(edi::Edit::rename_experiment(project, experiment, name), true,
        {CreationAction::Kind::ExperimentName, &experiment, {}, QString::fromStdString(name)});
    if (!self || retired_) return refusal;
    if (refusal.isEmpty() && experiment.name.value() != record.before) {
        record.name = experiment.name.value();
        record.results_after = project_->fit_result.scan_results;
        undo_history_.emplace_back(std::move(record));
        syncUndo();
    }
    return refusal;
}

bool ProjectViewModel::fitUndoAvailable() const {
    return !retired_ && !editing_ && !calculating() && fit_ && !fit_->running() && !fit_->nativeRunning() &&
        !fit_->presenting_ && fit_->undo_attempt_ && fit_->undo_attempt_ == fit_->latest_attempt_ &&
        !edi::is_scan_fitting_mode(edi::effective_fitting_mode(*project_)) && can_undo_ && fit_->canUndo() &&
        !undo_history_.empty() && std::holds_alternative<std::monostate>(undo_history_.back()) &&
        criticalEditRefusal(true).isEmpty() && editReadinessRefusal(true).isEmpty();
}
std::shared_ptr<ProjectViewModel::FitUndoInput> ProjectViewModel::prepareFitUndo() {
    if (fit_undo_input_ || !fitUndoAvailable()) throw std::runtime_error("The latest adopted fit is not undoable");
    auto input = std::make_shared<FitUndoInput>();
    input->attempt = fit_->undo_attempt_;
    fit_undo_input_ = input;
    return input;
}
void ProjectViewModel::finishFitUndo(const std::shared_ptr<FitUndoInput>& input) noexcept {
    if (fit_undo_input_ == input) fit_undo_input_.reset();
}
void ProjectViewModel::undo() {
    const PublicationScope publication(*this);
    if (fit_undo_invoking_) return; // A completed/retired prearm never becomes a nested manual Undo.
    const auto input = fit_undo_input_;
    if (input) {
        if (input->consumed || fit_undo_invoking_ || !fitUndoAvailable() || input->attempt != fit_->undo_attempt_) return;
        input->consumed = true;
    }
    const QPointer<ProjectViewModel> self(this);
    const auto release_input = qScopeGuard([self, input] {
        if (self && (!self->fit_undo_input_ || self->fit_undo_input_ == input)) self->fit_undo_invoking_ = false;
    });
    if (const QString critical = criticalEditRefusal(true); !critical.isEmpty()) { setLastError(critical); return; }
    syncUndo();
    if (retired_) return;
    if (!can_undo_) {
        return;
    }
    if (input && (fit_undo_input_ != input || !fitUndoAvailable() || input->attempt != fit_->undo_attempt_)) return;
    // The newest record is kept until its reversal succeeds: a refused restore (a parameter it names was
    // removed or renamed since) leaves it in place, with the refusal as the message. A fit's undo can drop
    // its own entry on the way (its start state is gone once restored), so only a record still there goes.
    const std::size_t depth = undo_history_.size();
    bool undone = false;
    const auto restore = [this](const edi::Edit& edit, bool structural) {
        return applyEdit(edit, structural, true).applied;
    };
    if (const auto* relations = std::get_if<edi::RelationsUndo>(&undo_history_.back())) {
        undone = restore(edi::Edit::restore_relations(*project_, *relations), true);
    } else if (const auto* population = std::get_if<EmptyPopulationUndo>(&undo_history_.back())) {
        undone = restore(edi::Edit::undo_empty_population(*project_, population->prepared), true);
    } else if (const auto* added = std::get_if<AddedExperiments>(&undo_history_.back())) {
        undone = restore(edi::Edit::erase_experiments(*project_, added->experiments), true);
    } else if (const auto* run = std::get_if<ScanRun>(&undo_history_.back())) {
        undone = restoreScanRun(*run, true);
    } else if (const auto* loaded = std::get_if<LoadedData>(&undo_history_.back())) {
        // The experiment as it was before the load: its simulation with its range and type, or the earlier data.
        const auto found = std::find_if(project_->experiments.begin(), project_->experiments.end(),
                                        [loaded](const auto& held) { return held.get() == loaded->experiment; });
        if (found == project_->experiments.end()) {
            setLastError(tr("undo: the loaded experiment is no longer in the project"));
        } else {
            const LoadedData record = *loaded;
            const QString error = replaceData(static_cast<int>(found - project_->experiments.begin()),
                                              edi::BraggPdExperiment(*record.before), true);
            undone = error.isEmpty();
        }
    } else if (const auto* controls = std::get_if<edi::ExperimentControlsUndo>(&undo_history_.back())) {
        undone=restore(edi::Edit::restore_experiment_controls(*project_,*controls),true);
    } else if (const auto* structures = std::get_if<edi::StructuresUndo>(&undo_history_.back())) {
        undone = restore(edi::Edit::restore_structures(*project_, *structures), true);
    } else if (const auto* report = std::get_if<edi::ReportSettingsState>(&undo_history_.back())) {
        undone = write_report_settings(edi::Edit::report_settings(*project_, *report), true).isEmpty();
    } else if (const auto* flags = std::get_if<FreeFlags>(&undo_history_.back())) {
        undone = restore(edi::Edit::set_free(*project_, flags->before), false);
    } else if (const auto* block = std::get_if<BlockName>(&undo_history_.back())) {
        // The block by the name the rename gave it, named back through the same edit, so its references follow.
        const BlockName record = *block;
        const bool results_unchanged = project_->fit_result.scan_results == record.results_after;
        const auto named = [&record](const auto& held) { return held->name.value() == record.name; };
        if (record.structure) {
            const auto found = std::find_if(project_->structures.begin(), project_->structures.end(), named);
            if (found == project_->structures.end()) {
                setLastError(tr("undo: the structure is no longer in the project"));
            } else {
                undone = restore(edi::Edit::structure_name(**found, record.before), true);
            }
        } else {
            const auto found = std::find_if(project_->experiments.begin(), project_->experiments.end(), named);
            if (found == project_->experiments.end()) {
                setLastError(tr("undo: the experiment is no longer in the project"));
            } else {
                undone = restore(edi::Edit::rename_experiment(*project_, **found, record.before), true);
            }
        }
        // The results the rename replaced come back as they were, unless something changed them since.
        if (undone && results_unchanged) {
            project_->fit_result.scan_results = record.results_before;
            if (scan_template_) {
                scan_template_->fit_result.scan_results = record.results_before;
            }
            syncCorrelations();
        }
    } else if (const auto* point = std::get_if<BackgroundPointUndo>(&undo_history_.back())) {
        undone = restore(edi::Edit::background_point(*project_, point->prepared, true), true);
    } else if (const auto* ids = std::get_if<PointIds>(&undo_history_.back())) {
        const auto found = std::find_if(project_->experiments.begin(), project_->experiments.end(),
                                        [ids](const auto& held) { return held.get() == ids->experiment; });
        if (found == project_->experiments.end()) {
            setLastError(tr("undo: the experiment is no longer in the project"));
        } else {
            undone = restore(edi::Edit::background_point_ids(**found, ids->before), true);
        }
    } else {
        // A single fit on a scan dataset made it the template and the last fit. Its Undo is refused, with nothing
        // changed, while the model's dataset is still being read, and when the run record is there but cannot be
        // read. Otherwise the record as it was first replaces the current one, which is kept aside until the fit is
        // undone: if that fails, the current one goes back (or stays aside, named in the refusal). A failure leaves
        // the step, to be tried again. A record that could not be read when the fit started is left as it is.
        const auto refuse = [this](const QString& refusal) {
            setLastError(refusal);
            emit refused(refusal);
            syncUndo();
        };
        if (const QString pending = editReadinessRefusal(true); !pending.isEmpty()) {
            refuse(pending);
            return;
        }
        std::string kept;
        bool swapped = false;
        if (fit_template_undo_ && fit_template_undo_->run_file_known) {
            std::optional<std::string> now;
            if (!scan_session_->runFile(*project_, now)) {
                refuse(tr("The scan's run record (analysis/scan-run.json) cannot be read, so the fit is not undone"));
                return;
            }
            if (const QString refusal = scan_session_->swapRunFile(*project_, fit_template_undo_->run_file, kept);
                !refusal.isEmpty()) {
                refuse(refusal);
                return;
            }
            swapped = true;
        }
        if (input && (fit_undo_input_ != input || !fitUndoAvailable() || input->attempt != fit_->undo_attempt_)) return;
        fit_undo_invoking_ = bool(input);
        undone = fit_->undo();
        if (retired_) return;
        if (swapped && undone) {
            ScanSession::dropRunFile(kept);
        } else if (swapped) {
            // The fit stays: so does the record saying it came last.
            if (const QString refusal = scan_session_->restoreRunFile(*project_, kept); !refusal.isEmpty()) {
                setLastError(refusal);
                emit refused(refusal);
            }
        }
        if (undone && fit_template_undo_) {
            project_->sequential_fit.template_file = fit_template_undo_->template_file;
            // The scan's results and rows as they were before the fit (shared pointers and the rows as recorded).
            project_->fit_result.scan_results = std::move(fit_template_undo_->results);
            std::vector<edi::ItemVec<edi::FitParameterCorrelation>::Ptr> rows;
            rows.reserve(fit_template_undo_->rows.size());
            for (const edi::FitParameterCorrelation& row : fit_template_undo_->rows) {
                rows.push_back(std::make_shared<edi::FitParameterCorrelation>(row));
            }
            project_->fit_result.correlations.assign(std::move(rows));
            scan_template_ = std::move(fit_template_undo_->stash);
            syncCorrelations();
            fit_template_undo_.reset();
            publishTemplate();
            showScanResults();
        }
    }
    if (retired_) return;
    if (undone && undo_history_.size() == depth) {
        undo_history_.pop_back();
    }
    syncUndo();
}

void ProjectViewModel::syncUndo() {
    if (retired_) return;
    // Nothing is undone while a fit runs, as nothing is edited then. A fit entry whose start state is gone
    // (undone, or replaced by a load) is no longer undoable; while a fit runs its start state only reads as
    // unavailable, so the entry stays, and a refused fit leaves it as it was.
    const bool running = fit_ != nullptr && fit_->running();
    while (!running && !undo_history_.empty() && std::holds_alternative<std::monostate>(undo_history_.back()) &&
           (fit_ == nullptr || !fit_->canUndo())) {
        undo_history_.pop_back();
    }
    const bool can_undo = !running && !undo_history_.empty();
    if (can_undo != can_undo_) {
        can_undo_ = can_undo;
        emit canUndoChanged();
    }
}

void ProjectViewModel::setModified(bool modified) {
    if (retired_) return;
    if (modified != modified_) {
        modified_ = modified;
        emit modifiedChanged();
    }
}

// Prepared landing of a verified native save, matching saveTo's rounding and
// saved-state contract without re-entering its writer/projectEdited boundary.
struct ProjectViewModel::NativeSavedState {
    edi::Project* owner=nullptr;
    std::unique_ptr<edi::PreparedSavedValues> values;
    bool committed=false;
    bool modified_changed=false;
};
std::shared_ptr<ProjectViewModel::NativeSavedState> ProjectViewModel::prepareNativeSaved(
    const edi::Project& reopened,const edi::WorkStamps& original,edi::CalculationResult calculation,const QString& destination) {
    return prepareNativeSaved(reopened,original,std::move(calculation),destination,std::numeric_limits<std::size_t>::max());
}
std::shared_ptr<ProjectViewModel::NativeSavedState> ProjectViewModel::prepareNativeSaved(
    const edi::Project& reopened,const edi::WorkStamps& original,edi::CalculationResult calculation,const QString& destination,
    std::size_t metadata_limit) {
    const PublicationScope publication(*this);
    if(retired_ || editing_ || edit_publication_failed_ || scan_template_ || calculating_ ||
       (fit_ && fit_->running()))throw std::invalid_argument("The project is not a settled current save owner");
    const auto fixed=sizeof(NativeSavedState)+2*sizeof(void*)+sizeof(edi::PreparedSavedValues)+sizeof(QByteArray)+
        sizeof(QString)+sizeof(QByteArray)+2*sizeof(QChar)+4;
    if(metadata_limit<fixed)throw std::length_error("Saved-state presentation metadata exceeds capacity");
    metadata_limit-=fixed;
    std::size_t encoded_bytes=0;
    // Same bounded one-code-point Qt counter as native import admission: no
    // full owning UTF-8 path exists before its complete scratch role is owned.
    for(qsizetype i=0;i<destination.size();) {
        const auto c=destination.at(i);
        const qsizetype width=c.isHighSurrogate() && i+1<destination.size() && destination.at(i+1).isLowSurrogate()?2:1;
        const auto bytes=static_cast<std::size_t>(destination.mid(i,width).toUtf8().size());
        if(bytes>metadata_limit-encoded_bytes)throw std::length_error("Saved destination metadata exceeds capacity");
        encoded_bytes+=bytes;i+=width;
    }
    // QByteArray scratch plus destination and metadata.path's future owning
    // strings coexist. Their logical byte roles are admitted before encoding.
    if(metadata_limit<3 || encoded_bytes>(metadata_limit-3)/3)
        throw std::length_error("Saved destination metadata exceeds capacity");
    metadata_limit-=encoded_bytes+1; // QByteArray scratch; core owns both final strings below.
    const auto encoded=destination.toUtf8();
    auto ready=std::make_shared<NativeSavedState>();ready->owner=project_.get();
    ready->values=std::make_unique<edi::PreparedSavedValues>(*project_,reopened,original,std::move(calculation),
        std::string(encoded.constData(),static_cast<std::size_t>(encoded.size())),metadata_limit);
    return ready;
}

bool ProjectViewModel::commitNativeSaved(NativeSavedState& ready) noexcept {
    // Caller has rechecked the prepared stamps immediately before its actual
    // no-overwrite publication/reopen. No signal/callback occurs in this landing.
    if(retired_ || ready.owner!=project_.get() || ready.committed || !ready.values ||
       editing_ || edit_publication_failed_ || scan_template_ || calculating_ || (fit_ && fit_->running()))return false;
    if(!ready.values->commit(*project_))return false;ready.committed=true;
    ready.modified_changed=modified_;modified_=false;
    saved_files_.reset();return true;
}
bool ProjectViewModel::presentNativeSaved(NativeSavedState& ready) {
    const PublicationScope publication(*this);
    if(retired_ || !ready.committed || ready.owner!=project_.get())return false;
    // Notify after the real state has landed. A reentrant user edit/replacement
    // wins: never reset modified/path or publish an obsolete owner's state later.
    const auto saved_stamps=edi::work_stamps(*project_);
    if(ready.modified_changed)emit modifiedChanged();
    if(retired_ || !edi::unchanged_since(*project_,saved_stamps))return false;
    // This is persistence presentation, not a new user edit. Its known landing
    // is refreshed explicitly by the original native call. Any nested actual
    // edit still emits the ordinary projectEdited signal without suppression.
    emit pathChanged();
    if(retired_ || !edi::unchanged_since(*project_,saved_stamps))return false;
    publish(false);
    if(retired_ || !edi::unchanged_since(*project_,saved_stamps))return false;
    for(ExperimentViewModel* experiment:experiment_models_) {
        experiment->pattern()->calculated({});
        if(retired_ || !edi::unchanged_since(*project_,saved_stamps))return false;
        experiment->capturePattern();
        if(retired_ || !edi::unchanged_since(*project_,saved_stamps))return false;
    }
    for(StructureViewModel* structure:structure_models_) {
        structure->captureScene();
        if(retired_ || !edi::unchanged_since(*project_,saved_stamps))return false;
    }
    publishMetadata();
    if(retired_ || !edi::unchanged_since(*project_,saved_stamps))return false;
    invalidateTexts();
    if(retired_ || !edi::unchanged_since(*project_,saved_stamps))return false;
    report_->refresh();
    if(retired_ || !edi::unchanged_since(*project_,saved_stamps))return false;
    setLastError({});return !retired_ && edi::unchanged_since(*project_,saved_stamps);
}

void ProjectViewModel::notifyProjectEdited(std::uint64_t origin) {
    const QPointer<ProjectViewModel> receiver(this);
    const auto previous=project_edit_origin_;project_edit_origin_=origin;
    const auto scope=qScopeGuard([receiver,previous]{if(receiver)receiver->project_edit_origin_=previous;});
    emit projectEdited();
}

QString ProjectViewModel::saveTo(const QString& directory) {
    const auto save_origin=std::exchange(assistant_save_origin_,0);
    const PublicationScope publication(*this);
    if (const QString critical = criticalEditRefusal(); !critical.isEmpty()) return critical;
    // A running fit owns the project's output (a scan appends its results there): nothing is saved under it.
    if (fit_ != nullptr && fit_->running()) {
        const QString message = tr("The project cannot be saved while a fit is running");
        setLastError(message);
        return message;
    }
    editing_ = true;
    const auto release = qScopeGuard([this] { editing_ = false; });
    // Saving may round/adopt values or partially advance files even if later readback refuses.
    // Retire manual authority as before; only this original Save's exact
    // one-shot notification may be recognized as its own assistant effect.
    notifyProjectEdited(save_origin);
    if (retired_) return tr("The save was retired before writing because the project owner changed");
    // While a scan dataset is shown, the template is what a save writes; the shown model follows it to the new
    // directory, so a scan started next reads and writes there.
    try {
        if (scan_template_) {
            edi::save_project_as(*scan_template_, directory.toStdString());
        } else {
            edi::save_project_as(*project_, directory.toStdString());
        }
    } catch (const std::exception& refusal) {
        const QString message = QString::fromUtf8(refusal.what());
        setLastError(message);
        return message;
    }
    if (scan_template_) {
        project_->path = scan_template_->path;
        project_->metadata = scan_template_->metadata;
        project_->scan_data_root = scan_template_->scan_data_root;
    }
    // The saved project then holds what its files hold, as a reopen reads them (values and correlations rounded by
    // the IUCr rule), and is calculated once from that: not an edit, so it stays unmodified with nothing to undo.
    try {
        if (edi::adopt_saved_values(scan_template_ ? *scan_template_ : *project_, directory.toStdString())) {
            if (scan_template_) {
                scan_template_->refresh_calculated_pattern();
            } else {
                preview_->recalculate();
            }
            publish(false);
            if (retired_) return tr("The project was saved, but its owner was replaced during presentation");
            publishCalculating();
        }
    } catch (const std::exception& error) {
        const QString message =
            tr("The project was saved, but reading it back failed: %1").arg(QString::fromUtf8(error.what()));
        setLastError(message);
        return message;
    }
    setLastError({});
    if (retired_) return tr("The project was saved, but its owner was replaced during presentation");
    emit pathChanged();
    if (retired_) return tr("The project was saved, but its owner was replaced during presentation");
    // The results came along with the tree; their provenance is kept with them, and the datasets are listed
    // from the saved directory.
    if (scan_session_ != nullptr) {
        const ScanSession::Run run = scan_session_->run();
        if (scanProcessed() && !run.identity.empty()) {
            if (const QString refusal = scan_session_->writeRun(*project_, run); !refusal.isEmpty()) {
                setLastError(refusal);
            }
        }
        scan_refusal_ = scan_session_->load(*project_);
        syncScanAdmission();
        if (retired_) return tr("The project was saved, but its owner was replaced during presentation");
        showScanResults();
        if (retired_) return tr("The project was saved, but its owner was replaced during presentation");
    }
    // The saved project's last-modified time advanced: its metadata and every text a save writes show it.
    publishMetadata();
    if (retired_) return tr("The project was saved, but its owner was replaced during presentation");
    saved_files_.reset();
    invalidateTexts();
    if (retired_) return tr("The project was saved, but its owner was replaced during presentation");
    report_->refresh();
    if (retired_) return tr("The project was saved, but its owner was replaced during presentation");
    setModified(false);
    if (retired_) return tr("The project was saved, but its owner was replaced during presentation");
    return {};
}

void ProjectViewModel::publishTemplate() {
    const PublicationScope publication(*this);
    if (retired_) return;
    // The template designation or the template itself changed: the texts a save writes, the dataset tags and the
    // results' outdated state follow.
    setModified(true);
    if (retired_) return;
    saved_files_.reset();
    invalidateTexts();
    if (retired_) return;
    report_->refresh();
    if (retired_) return;
    markTemplateChanged();
    if (retired_) return;
    syncDatasets();
    if (retired_) return;
    emit templateIndexChanged();
    if (retired_) return;
}

void ProjectViewModel::publish(bool structural) {
    const PublicationScope publication(*this);
    if (retired_) return;
    if (structural) {
        registry_->rebuild(*project_);
        if (retired_) return;
        syncBlocks();
        if (retired_) return;
    }
    registry_->publish(*project_);
    if (retired_) return;
    for (StructureViewModel* structure : structure_models_) {
        structure->sync();
        if (retired_) return;
    }
    for (ExperimentViewModel* experiment : experiment_models_) {
        experiment->sync();
        if (retired_) return;
    }
    structure_list_->setStructures(structure_models_);
    if (retired_) return;
    // A scan's rows change with its results and its template, not with an edit or a dataset shown: those are
    // updated one row at a time (syncDataset). A structural change listed them already (syncBlocks).
    if (!structural && !scan_) {
        syncDatasets();
        if (retired_) return;
    }
    analysis_->sync();
    if (retired_) return;
    evolution_->syncParameters();
    if (retired_) return;
    syncCorrelations();
    if (retired_) return;
    syncParameterTable(false);  // the report is refreshed below, once everything it reads is published
    if (retired_) return;
    publishMetadata();
    if (retired_) return;
    // What a save writes changed now, not at the recalculation: a Text read in this same turn sees it.
    saved_files_.reset();
    invalidateTexts();
    if (retired_) return;
    report_->refresh();
    if (retired_) return;
    if (fit_ != nullptr) {
        fit_->sync();
        if (retired_) return;
    }
}

void ProjectViewModel::adoptScanFileResult(const std::string& file,
                                           const std::shared_ptr<const edi::ScanFileResult>& result) {
    // The template dataset in effect (declared, else the first file), whose pairs the record keeps (edi ADR-0034).
    const std::string template_file =
        scan_session_ != nullptr ? edi::effective_scan_template_file(scanTemplateOrModel(), scan_session_->datasets())
                                 : scanTemplateOrModel().sequential_fit.template_file;
    edi::adopt_scan_file_result(project_->fit_result, file, result, template_file);
    if (scan_template_) {
        edi::adopt_scan_file_result(scan_template_->fit_result, file, result, template_file);
    }
}

void ProjectViewModel::syncCorrelations() {
    const PublicationScope publication(*this);
    if (retired_) return;
    if (correlations_ == nullptr) {
        return;
    }
    // The level is the project's `_correlation_chart.threshold`, so it is saved, undone and reported as one.
    correlations_->setThreshold(project_->correlation_threshold);
    if (retired_) return;
    if (scan_) {
        const std::vector<std::string>& files = scan_session_->datasets().files;
        const bool shown = current_dataset_ >= 0 && current_dataset_ < static_cast<int>(files.size());
        // ADR-0034: the shown dataset's table when its fit made one; else the rows read with it; else none.
        const edi::FitResultRecord& record = scanTemplateOrModel().fit_result;
        const std::string file = shown ? files[static_cast<std::size_t>(current_dataset_)] : std::string();
        if (const auto found = shown ? record.scan_results.find(file) : record.scan_results.end();
            found != record.scan_results.end()) {
            if (found->second && found->second->correlations) {
                correlations_->setTable(*found->second->correlations);
                if (retired_) return;
            } else if (found->second && !found->second->read_rows.empty()) {
                correlations_->setRows(file, found->second->read_rows);
                if (retired_) return;
            } else {
                correlations_->setRows(file, {});
                if (retired_) return;
            }
            return;
        }
        std::vector<std::shared_ptr<const edi::FitParameterCorrelation>> rows;
        for (const auto& row : record.correlations) {
            if (shown && row->file_path.value() == file) {
                rows.push_back(row);
            }
        }
        if (!rows.empty()) {
            correlations_->setRows(file, rows);
            if (retired_) return;
            return;
        }
        // A save keeps only the template dataset's correlations (the owner, 2026-10-12): a dataset fitted before the
        // project was opened has none here.
        QString absent;
        if (shown && files[static_cast<std::size_t>(current_dataset_)] != scanTemplateOrModel().sequential_fit.template_file) {
            const QString outcome = scan_session_->outcome(current_dataset_);
            if (!outcome.isEmpty() && outcome != QStringLiteral("skipped")) {
                absent = tr("Correlations are kept only for the template dataset");
            }
        }
        correlations_->setRows(file, {}, absent);
        if (retired_) return;
        return;
    }
    const ExperimentViewModel* experiment = currentExperiment();
    correlations_->setRecord(*project_, current_experiment_,
                             experiment != nullptr && !experiment->fitOutcome().isEmpty());
                             if (retired_) return;
}

void ProjectViewModel::publishFit() {
    const PublicationScope publication(*this);
    if (retired_) return;
    // The fitted values, uncertainties and fit start, and the pattern of the fitted state the fit's own last
    // calculation left (edi::FitJob): the parameter table, the blocks and the texts, then the patterns.
    publish(false);
    if (retired_) return;
    QString error;
    for (const auto& experiment : project_->experiments) {
        if (!experiment->computed_current()) {
            error = tr("The fitted model cannot be calculated");
        }
    }
    published(edi::PreviewResult{preview_->newest_request(), error.toStdString()});
    if (retired_) return;
    setModified(true);
    if (retired_) return;
}

void ProjectViewModel::showFitFrame(const edi::FitFrame& frame, std::optional<edi::PatternSource> d_frame) {
    const PublicationScope publication(*this);
    if (retired_) return;
    for (int i = 0; i < experiment_models_.size() && i < static_cast<int>(frame.size()); ++i) {
        experiment_models_[i]->showPattern(frame[static_cast<std::size_t>(i)],
                                           i == 0 ? std::move(d_frame) : std::nullopt);
    }
}

void ProjectViewModel::restorePatterns() {
    const PublicationScope publication(*this);
    if (retired_) return;
    for (ExperimentViewModel* experiment : experiment_models_) {
        experiment->capturePattern();
        if (retired_) return;
    }
}

void ProjectViewModel::completeSymmetry() {
    // A parameter the space group fixes or ties shows the value symmetry implies (edi ADR-0019): after a
    // load and after every edit the model's dependents are re-derived from its independent values, through
    // the completion a fit itself applies. A structure crysta cannot resolve keeps what it holds — the
    // calculation says why.
    edi::apply_relations(*project_);
}

void ProjectViewModel::syncParameterTable(bool refresh_report) {
    const PublicationScope publication(*this);
    if (retired_) return;
    // The Analysis table follows the fitting mode (owner, 2026-09-29; edi ADR-0019): a joint fit varies
    // every experiment's parameters together, so all are listed; a scan mode (sequential, independent)
    // fits one experiment at a time, so only the selected experiment's are, beside the structures'.
    const ExperimentViewModel* selected = currentExperiment();
    const bool scan = edi::is_scan_fitting_mode(edi::effective_fitting_mode(*project_));
    parameters_->setExperimentScope(scan && selected != nullptr ? selected->name() : QString());
    if (retired_) return;
    parameters_->sync();
    if (retired_) return;
    // The report keeps its composed text and counts this table's rows: a selection that changes the rows
    // changes the report in the same step. The status bar and the Analysis table bind the model itself.
    if (refresh_report && report_ != nullptr) {
        report_->refresh();
        if (retired_) return;
    }
}

void ProjectViewModel::invalidateTexts() {
    const PublicationScope publication(*this);
    if (retired_) return;
    for (ExperimentViewModel* experiment : experiment_models_) {
        experiment->text()->invalidate();
        if (retired_) return;
    }
    for (StructureViewModel* structure : structure_models_) {
        structure->text()->invalidate();
        if (retired_) return;
    }
    analysis_->text()->invalidate();
    if (retired_) return;
    metadata_text_->invalidate();
    if (retired_) return;
    report_text_->invalidate();
    if (retired_) return;
    project_text_->invalidate();
    if (retired_) return;
}

void ProjectViewModel::syncBlocks() {
    const PublicationScope publication(*this);
    if (retired_) return;
    // One view-model per core block, matched by identity: kept while the block exists, created for a
    // new one, removed (after the lists drop it) for a gone one — never a reset (I5).
    QList<QObject*> gone;
    {
        QList<StructureViewModel*> next;
        for (std::size_t i = 0; i < project_->structures.size(); ++i) {
            edi::Structure& block = *project_->structures[i];
            StructureViewModel* found = nullptr;
            for (StructureViewModel* model : structure_models_) {
                found = model->structure() == &block ? model : found;
            }
            next.append(found != nullptr ? found : new StructureViewModel(savedFileFunction(), block, *this, *registry_, this));
        }
        for (StructureViewModel* model : structure_models_) {
            if (!next.contains(model)) {
                gone.append(model);
            }
        }
        structure_models_ = next;
    }
    {
        QList<ExperimentViewModel*> next;
        for (std::size_t i = 0; i < project_->experiments.size(); ++i) {
            edi::ExperimentBase& block = *project_->experiments[i];
            ExperimentViewModel* found = nullptr;
            for (ExperimentViewModel* model : experiment_models_) {
                found = model->experiment() == &block ? model : found;
            }
            if (found == nullptr) {
                found = new ExperimentViewModel(savedFileFunction(), *project_, block, *this, *registry_, this);
                // A followed scan waits for a shown pattern chart; one shown again asks for the next pattern.
                connect(found, &ExperimentViewModel::patternShownChanged, this, [this, found] {
                    if (fit_ != nullptr && found == currentExperiment()) {
                        fit_->patternShownChanged();
                        if (retired_) return;
                    }
                });
            }
            next.append(found);
        }
        for (ExperimentViewModel* model : experiment_models_) {
            if (!next.contains(model)) {
                gone.append(model);
            }
        }
        experiment_models_ = next;
    }
    syncLoadState();
    if (retired_) return;
    structure_list_->setStructures(structure_models_);
    if (retired_) return;
    syncDatasets();
    if (retired_) return;
    const int structures = static_cast<int>(structure_models_.size());
    const int experiments = static_cast<int>(experiment_models_.size());
    if (current_structure_ >= structures) {
        current_structure_ = structures - 1;
    }
    if (current_experiment_ >= experiments) {
        current_experiment_ = experiments - 1;
    }
    if (report_ != nullptr) {  // not during construction: the constructor records the first state
        publishCurrent();
        if (retired_) return;
        if (canLoadStructure() != published_can_load_structure_) {
            published_can_load_structure_ = canLoadStructure();
            emit canLoadStructureChanged();
            if (retired_) return;
        }
        if (canCreateExperiment() != published_can_create_experiment_) {
            published_can_create_experiment_ = canCreateExperiment();
            emit canCreateExperimentChanged();
            if (retired_) return;
        }
    }
    for (QObject* model : gone) {
        model->deleteLater();
        if (retired_) return;
    }
}

void ProjectViewModel::published(const edi::PreviewResult& result) {
    const PublicationScope publication(*this);
    if (retired_) return;
    // The project holds the calculation now (or its refusal, with every computed category cleared): the
    // tables, the charts, the texts and the report follow, once.
    const QString error = QString::fromStdString(result.refusal);
    for (ExperimentViewModel* experiment : experiment_models_) {
        experiment->pattern()->calculated(error);
        if (retired_) return;
        experiment->capturePattern();
        if (retired_) return;
    }
    // ADR-0022: the transaction published every structure's geometry; each structure view re-presents from
    // its captured source, here on the owner thread.
    for (StructureViewModel* structure : structure_models_) {
        structure->captureScene();
        if (retired_) return;
    }
    saved_files_.reset();  // a save writes the calculated pattern too
    invalidateTexts();
    if (retired_) return;
    report_->refresh();
    if (retired_) return;
    publishCalculating();
    if (retired_) return;
    emit recalculated();
    if (retired_) return;
}

void ProjectViewModel::publishCalculating() {
    if (retired_) return;
    // A dataset view on its way is a calculation too: the shown state is not the newest until it arrives.
    const bool calculating = (preview_ != nullptr && preview_->busy()) || view_applied_ != view_request_;
    if (calculating != calculating_) {
        calculating_ = calculating;
        emit calculatingChanged();
    }
}

const std::vector<std::pair<std::string, std::string>>& ProjectViewModel::savedFiles() const {
    // One save of the whole project serves every Text tab until the next change (D7).
    if (!saved_files_.has_value()) {
        try {
            saved_files_ = SavedFiles{edi::project_edi_files(scanTemplateOrModel()), {}};
        } catch (const std::exception& refusal) {
            saved_files_ = SavedFiles{{}, refusal.what()};
        }
    }
    if (!saved_files_->refusal.empty()) {
        throw std::runtime_error(saved_files_->refusal);
    }
    return saved_files_->files;
}

SavedFile ProjectViewModel::savedFileFunction() const {
    return [this](const std::string& relative) { return savedFile(relative); };
}

std::string ProjectViewModel::savedFile(const std::string& relative) const {
    for (const auto& [path, body] : savedFiles()) {
        if (path == relative) {
            return body;
        }
    }
    return {};
}

void ProjectViewModel::setLastError(const QString& error) {
    if (retired_) return;
    if (error != last_error_) {
        last_error_ = error;
        emit lastErrorChanged();
    }
}

}  // namespace edi_app
