// SPDX-License-Identifier: BSD-3-Clause
#include "project_view_model.hpp"

#include <QCoreApplication>
#include <QHash>
#include <QMetaObject>
#include <QPointer>
#include <QScopeGuard>
#include <QTemporaryDir>
#include <QFile>
#include <algorithm>
#include <cctype>
#include <map>
#include <fstream>
#include <filesystem>

#include "background.hpp"
#include "edi/edits.hpp"
#include "edi/io.hpp"
#include "edi/presentation.hpp"
#include "edi/scan.hpp"
#include "edi/selectors.hpp"
#include "parameter_registry.hpp"
#include "report_view_model.hpp"

namespace edi_app {

// ---- StructureListModel / ExperimentListModel ---------------------------------------------------

namespace {

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
    // A joint fit records each bank's share (`_fit_result_bank`); a single fit records none and fitted the first.
    const QString outcome = recorded_outcome(project.fit_result);
    const bool joint = std::any_of(project.experiments.begin(), project.experiments.end(),
                                   [](const auto& experiment) { return experiment->fit_prof_wr_factor.has_value(); });
    dataset_row_ = nullptr;
    dataset_experiment_ = nullptr;
    QList<Row> rows;
    for (int i = 0; i < experiments.size(); ++i) {
        ExperimentViewModel* experiment = experiments[i];
        const bool fitted = joint ? experiment->experiment()->fit_prof_wr_factor.has_value() : i == 0;
        experiment->setFitOutcome(fitted ? outcome : QString());
        rows.append({experiment,
                     {experiment->name(), block_label(experiment->name(), QStringLiteral("experiment")),
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
    project_text_ = new BlockText(
        [this] {
            std::string text;
            for (const auto& [path, body] : savedFiles()) {
                text += (text.empty() ? "" : "\n") + std::string("# ") + path + "\n" + body;
            }
            return text;
        },
        this);
    loadScan();
    syncBlocks();
    report_ = new ReportViewModel(*this, this);
    current_structure_ = structure_models_.isEmpty() ? -1 : 0;
    current_experiment_ = experiment_models_.isEmpty() ? -1 : 0;
    syncParameterTable();
    published_name_ = name();
    published_title_ = title();
    published_description_ = description();
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
        completeSymmetry();
        publish(pending_structural_);
        // An admitted edit, whatever it wrote: every pattern shows a calculation of the state before it, and
        // says so until the newest request publishes. A refused edit never gets here.
        for (ExperimentViewModel* experiment : experiment_models_) {
            experiment->markPatternStale();
        }
        // A structure whose geometry the edit changed shows its last published frame, reported as not current,
        // until the newest request publishes.
        for (StructureViewModel* structure : structure_models_) {
            if (!structure->structure()->geometry_current()) {
                structure->markSceneStale();
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
    connect(fit_, &FitViewModel::finished, this, note_fit);
    connect(fit_, &FitViewModel::outOfDateChanged, this, [this] { evolution_->setOutOfDate(fit_->outOfDate()); });
    // A single fit on a scan dataset makes its result the template, and that dataset the template dataset
    // (`_sequential_fit.template_file`; edi ADR-0017 §19): the shown state is the template from now on. The
    // designation before it is kept for the fit's Undo.
    connect(fit_, &FitViewModel::runningChanged, this, [this] {
        if (scan_ && fit_->running() && !fit_->scanning()) {
            fit_template_before_ = TemplateState{scanTemplateOrModel().sequential_fit.template_file, scan_template_};
            fit_template_before_->run_file_known = scan_session_->runFile(*project_, fit_template_before_->run_file);
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
    // A scan project opens on its template dataset, else on its first, read before the project is shown.
    if (scan_) {
        scan_template_ = *project_;
        viewDatasetNow(std::max(0, templateIndex()), true);
    }
    preview_->recalculate();
    publishCalculating();
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

void ProjectViewModel::publishCurrent() {
    if (current_structure_ != published_structure_index_) {
        published_structure_index_ = current_structure_;
        emit currentStructureIndexChanged();
    }
    if (currentStructure() != published_structure_) {
        published_structure_ = currentStructure();
        emit currentStructureChanged();
    }
    if (currentExperiment() != published_experiment_) {
        syncParameterTable();  // a scan mode lists the selected experiment's parameters; before the signals
    }
    if (currentExperimentIndex() != published_experiment_index_) {
        published_experiment_index_ = currentExperimentIndex();
        emit currentExperimentIndexChanged();
    }
    if (currentExperiment() != published_experiment_) {
        published_experiment_ = currentExperiment();
        emit currentExperimentChanged();
    }
}

void ProjectViewModel::publishMetadata() {
    const auto update = [this](QString& published, const QString& current, void (ProjectViewModel::*signal)()) {
        if (current != published) {
            published = current;
            emit(this->*signal)();
        }
    };
    update(published_name_, name(), &ProjectViewModel::nameChanged);
    update(published_title_, title(), &ProjectViewModel::titleChanged);
    update(published_description_, description(), &ProjectViewModel::descriptionChanged);
    update(published_last_modified_, lastModified(), &ProjectViewModel::lastModifiedChanged);
}

bool ProjectViewModel::loadStructure(const QUrl& file) {
    if (!file.isLocalFile()) {
        const QString message = QStringLiteral("not a local file: %1").arg(file.toString());
        emit refused(message);
        return false;
    }
    edi::Project& project = *project_;
    // The file is read first: a file that is refused adds nothing, and what is added is one edit.
    QString error;
    try {
        error = apply(edi::Edit::add_structure(project, edi::load_structure_edi_file(file.toLocalFile().toStdString())),
                      true);
    } catch (const std::exception& refusal) {
        error = QString::fromUtf8(refusal.what());
        setLastError(error);
    }
    if (!error.isEmpty()) {
        emit refused(error);
        return false;
    }
    setCurrentStructureIndex(static_cast<int>(structure_models_.size()) - 1);
    return true;
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
    QString error;
    try {
        error = apply(edi::Edit::create_experiment(project, edi::simulation_experiment(name, {}, structures)), true);
    } catch (const std::exception& refusal) {
        error = QString::fromUtf8(refusal.what());
        setLastError(error);
    }
    if (!error.isEmpty()) {
        emit refused(error);
        return false;
    }
    created_.insert(project.experiments.back().get());
    syncLoadState();
    noteAddedExperiments(project.experiments.size() - 1);
    setCurrentExperimentIndex(static_cast<int>(experiment_models_.size()) - 1);
    return true;
}

bool ProjectViewModel::setExperimentType(int index, const QString& axis, const QString& token) {
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
        const edi::ExperimentBase* before = &experiment;
        const bool created = created_.contains(before);
        error = apply(edi::Edit::replace_experiment(project, experiment, std::move(replacement)), true);
        if (error.isEmpty()) {
            // Undo of the experiment's creation removes it in its new type.
            experimentReplaced(before, project.experiments[static_cast<std::size_t>(index)].get(), created);
            syncDatasets();
        }
    } catch (const std::exception& refusal) {
        error = QString::fromUtf8(refusal.what());
        setLastError(error);
    }
    if (!error.isEmpty()) {
        emit refused(error);
        return false;
    }
    return true;
}

void ProjectViewModel::experimentReplaced(const edi::ExperimentBase* before, const edi::ExperimentBase* after,
                                          bool created) {
    for (UndoRecord& record : undo_history_) {
        if (auto* added = std::get_if<AddedExperiments>(&record)) {
            std::replace(added->experiments.begin(), added->experiments.end(), before, after);
        } else if (auto* loaded = std::get_if<LoadedData>(&record)) {
            loaded->experiment = loaded->experiment == before ? after : loaded->experiment;
        } else if (auto* structures = std::get_if<edi::StructuresUndo>(&record)) {
            for (auto& rows : structures->experiments) {
                rows.experiment = rows.experiment == before ? after : rows.experiment;
            }
        }
    }
    // The edit's own publication has already dropped `before`'s entry (syncLoadState): it comes from the caller.
    created_.erase(before);
    if (created) {
        created_.insert(after);
    }
    syncLoadState();
}

void ProjectViewModel::syncLoadState() {
    // Entries of experiments no longer in the project go: a new experiment could take a gone one's address.
    std::set<const edi::ExperimentBase*> held;
    for (const auto& experiment : project_->experiments) {
        held.insert(experiment.get());
    }
    std::erase_if(created_, [&held](const edi::ExperimentBase* experiment) { return !held.contains(experiment); });
    for (ExperimentViewModel* model : experiment_models_) {
        model->setCanLoadData(created_.contains(model->experiment()));
    }
}

QString ProjectViewModel::replaceData(int index, edi::BraggPdExperiment replacement) {
    edi::Project& project = *project_;
    const edi::ExperimentBase* before = project.experiments[static_cast<std::size_t>(index)].get();
    const bool created = created_.contains(before);
    QString error;
    try {
        error = apply(edi::Edit::load_data(project, *before, std::move(replacement)), true);
    } catch (const std::exception& refusal) {
        error = QString::fromUtf8(refusal.what());
        setLastError(error);
    }
    if (!error.isEmpty()) {
        return error;
    }
    experimentReplaced(before, project.experiments[static_cast<std::size_t>(index)].get(), created);
    syncDatasets();
    return {};
}

bool ProjectViewModel::loadData(int index, const QUrl& file) {
    const auto refuse = [this](const QString& refusal) {
        setLastError(refusal);
        emit refused(refusal);
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
    if (!created_.contains(&experiment)) {
        return refuse(tr("Load data works on an experiment made with Create experiment; '%1' has its data from its "
                         "file")
                          .arg(QString::fromStdString(experiment.name)));
    }
    // A name the user has not changed (experiment1, experiment2, …) gives way to the file's.
    const std::string& name = experiment.name.value();
    const bool default_name = name.size() > 10 && name.starts_with("experiment") &&
                              std::all_of(name.begin() + 10, name.end(), [](char c) { return c >= '0' && c <= '9'; });
    std::optional<edi::PlainDataLoad> read;
    try {
        read.emplace(edi::experiment_with_plain_data(experiment, file.toLocalFile().toStdString(), default_name));
    } catch (const std::exception& refusal) {
        return refuse(QString::fromUtf8(refusal.what()));
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
    const QString file_name = QString::fromStdString(load.file_name);
    LoadedData record{nullptr, std::make_shared<const edi::BraggPdExperiment>(experiment)};
    const QString loaded_name = QString::fromStdString(load.experiment.name);
    if (const QString error = replaceData(index, std::move(load.experiment)); !error.isEmpty()) {
        return refuse(error);
    }
    record.experiment = project.experiments[static_cast<std::size_t>(index)].get();
    undo_history_.emplace_back(std::move(record));
    syncUndo();
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
    edi::StructuresUndo before = edi::capture_structures(project);
    QString error;
    try {
        error = apply(edi::Edit::add_structure(project, edi::structure_from_edi_text(text)), true);
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
            continue;  // a parameter the results do not record keeps the template's value
        }
        double number = 0.0, uncertainty = 0.0;
        const std::string& uncertainty_cell = row[found->second->uncertainty];
        if (!edi::parse_scan_number(row[found->second->value], number) ||
            (uncertainty_cell != "nan" && !edi::parse_scan_number(uncertainty_cell, uncertainty))) {
            throw std::invalid_argument("analysis/results.csv: the row's '" + found->second->name +
                                        "' cells are not numbers");
        }
        value.value = number;
        value.uncertainty = uncertainty;
    }
    return values;
}

void ProjectViewModel::viewDataset(int index, bool refresh) {
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

QString ProjectViewModel::pendingRefusal() const {
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
    view_reading_ = true;
    const QPointer<ProjectViewModel> self(this);
    run_in_background([self, request, index, directory, file, mode, values = std::move(values),
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
    // However this read ends, a followed scan may move to its newest finished file afterwards.
    const auto shown = qScopeGuard([this] {
        if (fit_ != nullptr) {
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
        showFitFrame(*view.frame);
    } else if (!view.error.isEmpty()) {
        setLastError(view.error);
    }
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
    if (fit_ != nullptr && fit_->running()) {
        return tr("A fit is running");
    }
    // Admission first, before anything on disk changes: one template experiment, a listed scan, a directory.
    if (const QString refusal = scanRefusal(); !refusal.isEmpty()) {
        return refusal;
    }
    if (project_->path.empty()) {
        return tr("The project has no directory yet: save it first");
    }
    run_identity_ = ScanSession::templateIdentity(scanTemplateOrModel());
    // A Continue keeps the rows already there, which came from the run (or runs) before: their provenance stays
    // with the scan's (scanEnded).
    previous_run_.reset();
    if (!fresh) {
        previous_run_ = scan_session_->run();
        return {};
    }
    // The previous results, kept for Undo (their absence included), then removed, all or none: crysta's driver
    // starts a scan without them.
    ScanRun run;
    if (const QString refusal = scan_session_->takeFiles(*project_, run.files); !refusal.isEmpty()) {
        return refusal;
    }
    undo_history_.emplace_back(std::move(run));
    syncUndo();
    setModified(true);
    reloadScanResults();
    return {};
}

QString ProjectViewModel::resetScan() {
    if (fit_ != nullptr && fit_->running()) {
        return tr("A fit is running");
    }
    if (scan_session_ == nullptr) {
        return scanRefusal();
    }
    // Every dataset's fit result goes, as one Undo step: the result files are set aside, absent ones included, the
    // run's provenance with them, and the record a single fit left on the template (its values stay: they are the
    // template). The datasets read as unfitted.
    ScanRun run;
    if (const QString refusal = scan_session_->takeFiles(*project_, run.files); !refusal.isEmpty()) {
        setLastError(refusal);
        return refusal;
    }
    run.fit_records = FitRecords{project_->fit_result, scan_template_ ? std::optional(scan_template_->fit_result) : std::nullopt};
    // The values the model shows now (a dataset's projection, or a single fit's result on it), which its Undo
    // restores as they are rather than as the older results would project them.
    run.shown_dataset = projected_dataset_;
    for (const edi::NamedSlot& slot : edi::named_slots(*project_)) {
        run.shown_values.push_back({slot.unique_name, slot.parameter->value.get(), slot.parameter->uncertainty.get()});
    }
    project_->fit_result = {};
    if (scan_template_) {
        scan_template_->fit_result = {};
    }
    undo_history_.emplace_back(std::move(run));
    syncUndo();
    setModified(true);
    reloadScanResults();
    if (current_dataset_ >= 0) {
        viewDataset(current_dataset_, true);
    }
    return {};
}

bool ProjectViewModel::restoreScanRun(const ScanRun& run) {
    if (fit_ != nullptr && fit_->running()) {
        return false;
    }
    if (const QString refusal = scan_session_->putFiles(*project_, run.files); !refusal.isEmpty()) {
        const QString message = tr("The previous scan results could not be put back: %1").arg(refusal);
        setLastError(message);
        emit refused(message);
        return false;
    }
    if (run.fit_records) {
        project_->fit_result = run.fit_records->model;
        if (scan_template_ && run.fit_records->stash) {
            scan_template_->fit_result = *run.fit_records->stash;
        }
    }
    setModified(true);
    scan_refusal_ = scan_session_->load(*project_);
    reloadScanResults();
    // Reset fits' Undo: the values shown before it, on the same dataset, as they were. Otherwise the shown dataset as
    // its row on disk now gives it.
    if (run.shown_dataset >= 0 && run.shown_dataset == projected_dataset_ && view_applied_ == view_request_ &&
        project_->experiment().data) {
        const bool modified = modified_;
        applying_view_ = true;
        const QString error = apply(edi::Edit::scan_view(*project_, project_->experiment(), run.shown_values,
                                                         *project_->experiment().data),
                                    false);
        applying_view_ = false;
        setModified(modified || error.isEmpty());
        publishCurrent();
    } else if (current_dataset_ >= 0) {
        viewDataset(current_dataset_, true);
    }
    return true;
}

void ProjectViewModel::reloadScanResults() {
    if (scan_session_ == nullptr) {
        return;
    }
    if (const QString refusal = scan_session_->reindex(*project_); !refusal.isEmpty()) {
        setLastError(refusal);
        emit refused(refusal);
    }
    showScanResults();
}

void ProjectViewModel::showScanResults() {
    syncDatasets();
    evolution_->setScan(scan_session_, project_.get(), scan_columns_.value(0));
    const ScanSession::Run& provenance = scan_session_->run();
    if (!scan_session_->index().error.empty()) {
        // A refused read has no rows to summarise: no summary is built from it, the refusal is shown instead.
        fit_->showScanRefused(QString::fromStdString(scan_session_->index().error), provenance.outcome,
                              provenance.seconds);
        syncOutOfDate();
        return;
    }
    fit_->showScan(scanSummary(provenance.outcome, provenance.seconds), !provenance.last_single);
    syncOutOfDate();
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

void ProjectViewModel::followScanFile(const std::string& file) {
    // Each file as it is fitted: a lookup by name and one read, off the GUI thread.
    if (const int index = scan_session_ != nullptr ? scan_session_->place(file) : -1; index >= 0) {
        viewDataset(index, true);
    }
}

void ProjectViewModel::followScanFrame(const std::string& file, const edi::FitFrame& frame) {
    // The file's data are still read off the GUI thread for the model; its pattern is the one given.
    if (const int index = scan_session_ != nullptr ? scan_session_->place(file) : -1; index >= 0) {
        follow_frame_.emplace(index, frame);
        viewDataset(index, true);
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

QString ProjectViewModel::apply(const edi::Edit& change, bool structural) {
    // ADR-0020 §2, §8: every write the app admits comes through this door and through the preview, as an
    // edi::Edit: one core operation that refuses before it writes, or completes. The change runs at once; the
    // preview notes the edit, so the computed categories are stale whatever field it wrote and whatever value
    // it left; this object publishes what changed (the preview's `edited` hook); and the edit is a request,
    // calculated on the worker and published only if no newer one exists by then. While a fit runs, the model
    // it fits is not edited. A write that reached the model anyway would make the fit publish nothing
    // (Superseded).
    if (fit_ != nullptr && fit_->running() && !(applying_view_ && fit_->scanning())) {
        const QString message = tr("The project cannot be edited while a fit is running");
        setLastError(message);
        return message;
    }
    if (const QString pending = pendingRefusal(); !applying_view_ && !pending.isEmpty()) {
        setLastError(pending);
        return pending;
    }
    pending_structural_ = structural;
    try {
        preview_->apply(change);
    } catch (const std::exception& refusal) {
        const QString message = QString::fromUtf8(refusal.what());
        setLastError(message);
        return message;
    }
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
        } else if (scan_template_) {
            edi::Project promoted = *project_;
            promoted.experiment().data = scan_template_->experiment().data;
            promoted.experiment().calculation_only = scan_template_->experiment().calculation_only;
            scan_template_ = std::move(promoted);
        }
        // The results' outdated state follows any change of the template's identity, the minimizer's settings included.
        markTemplateChanged();
    }
    setLastError({});
    setModified(true);
    publishCalculating();
    return {};
}

QString ProjectViewModel::apply_setting(const edi::Edit& change) {
    applying_setting_ = true;
    const QString refusal = apply(change, false);
    applying_setting_ = false;
    return refusal;
}

QString ProjectViewModel::apply_relation_edit(const edi::Edit& change) {
    edi::RelationsUndo before = edi::capture_relations(*project_);
    const QString refusal = apply(change, true);
    if (refusal.isEmpty()) {
        // The door's completion has run: what the edit changed is now known.
        edi::keep_changed(before, *project_);
        undo_history_.emplace_back(std::move(before));
        syncUndo();
    }
    return refusal;
}

void ProjectViewModel::undo() {
    syncUndo();
    if (!can_undo_) {
        return;
    }
    // The newest record is kept until its reversal succeeds: a refused restore (a parameter it names was
    // removed or renamed since) leaves it in place, with the refusal as the message. A fit's undo can drop
    // its own entry on the way (its start state is gone once restored), so only a record still there goes.
    const std::size_t depth = undo_history_.size();
    bool undone = false;
    if (const auto* relations = std::get_if<edi::RelationsUndo>(&undo_history_.back())) {
        undone = apply(edi::Edit::restore_relations(*project_, *relations), true).isEmpty();
    } else if (const auto* added = std::get_if<AddedExperiments>(&undo_history_.back())) {
        undone = apply(edi::Edit::erase_experiments(*project_, added->experiments), true).isEmpty();
    } else if (const auto* run = std::get_if<ScanRun>(&undo_history_.back())) {
        undone = restoreScanRun(*run);
    } else if (const auto* loaded = std::get_if<LoadedData>(&undo_history_.back())) {
        // The experiment as it was before the load: its simulation with its range and type, or the earlier data.
        const auto found = std::find_if(project_->experiments.begin(), project_->experiments.end(),
                                        [loaded](const auto& held) { return held.get() == loaded->experiment; });
        if (found == project_->experiments.end()) {
            setLastError(tr("undo: the loaded experiment is no longer in the project"));
        } else {
            const LoadedData record = *loaded;
            const QString error = replaceData(static_cast<int>(found - project_->experiments.begin()),
                                              edi::BraggPdExperiment(*record.before));
            undone = error.isEmpty();
        }
    } else if (const auto* structures = std::get_if<edi::StructuresUndo>(&undo_history_.back())) {
        undone = apply(edi::Edit::restore_structures(*project_, *structures), true).isEmpty();
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
        if (const QString pending = pendingRefusal(); !pending.isEmpty()) {
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
        undone = fit_->undo();
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
            scan_template_ = std::move(fit_template_undo_->stash);
            fit_template_undo_.reset();
            publishTemplate();
            showScanResults();
        }
    }
    if (undone && undo_history_.size() == depth) {
        undo_history_.pop_back();
    }
    syncUndo();
}

void ProjectViewModel::syncUndo() {
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
    if (modified != modified_) {
        modified_ = modified;
        emit modifiedChanged();
    }
}

QString ProjectViewModel::saveTo(const QString& directory) {
    // A running fit owns the project's output (a scan appends its results there): nothing is saved under it.
    if (fit_ != nullptr && fit_->running()) {
        const QString message = tr("The project cannot be saved while a fit is running");
        setLastError(message);
        return message;
    }
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
    setLastError({});
    emit pathChanged();
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
        showScanResults();
    }
    // The saved project's last-modified time advanced: its metadata and every text a save writes show it.
    publishMetadata();
    saved_files_.reset();
    invalidateTexts();
    report_->refresh();
    setModified(false);
    return {};
}

void ProjectViewModel::publishTemplate() {
    // The template designation or the template itself changed: the texts a save writes, the dataset tags and the
    // results' outdated state follow.
    setModified(true);
    saved_files_.reset();
    invalidateTexts();
    report_->refresh();
    markTemplateChanged();
    syncDatasets();
    emit templateIndexChanged();
}

void ProjectViewModel::publish(bool structural) {
    if (structural) {
        registry_->rebuild(*project_);
        syncBlocks();
    }
    registry_->publish(*project_);
    for (StructureViewModel* structure : structure_models_) {
        structure->sync();
    }
    for (ExperimentViewModel* experiment : experiment_models_) {
        experiment->sync();
    }
    structure_list_->setStructures(structure_models_);
    // A scan's rows change with its results and its template, not with an edit or a dataset shown: those are
    // updated one row at a time (syncDataset). A structural change listed them already (syncBlocks).
    if (!structural && !scan_) {
        syncDatasets();
    }
    analysis_->sync();
    syncParameterTable(false);  // the report is refreshed below, once everything it reads is published
    publishMetadata();
    // What a save writes changed now, not at the recalculation: a Text read in this same turn sees it.
    saved_files_.reset();
    invalidateTexts();
    report_->refresh();
    if (fit_ != nullptr) {
        fit_->sync();
    }
}

void ProjectViewModel::publishFit() {
    // The fitted values, uncertainties and fit start, and the pattern of the fitted state the fit's own last
    // calculation left (edi::FitJob): the parameter table, the blocks and the texts, then the patterns.
    publish(false);
    QString error;
    for (const auto& experiment : project_->experiments) {
        if (!experiment->computed_current()) {
            error = tr("The fitted model cannot be calculated");
        }
    }
    published(edi::PreviewResult{preview_->newest_request(), error.toStdString()});
    setModified(true);
}

void ProjectViewModel::showFitFrame(const edi::FitFrame& frame) {
    for (int i = 0; i < experiment_models_.size() && i < static_cast<int>(frame.size()); ++i) {
        experiment_models_[i]->showPattern(frame[static_cast<std::size_t>(i)]);
    }
}

void ProjectViewModel::restorePatterns() {
    for (ExperimentViewModel* experiment : experiment_models_) {
        experiment->capturePattern();
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
    // The Analysis table follows the fitting mode (owner, 2026-09-29; edi ADR-0019): a joint fit varies
    // every experiment's parameters together, so all are listed; a scan mode (sequential, independent)
    // fits one experiment at a time, so only the selected experiment's are, beside the structures'.
    const ExperimentViewModel* selected = currentExperiment();
    const bool scan = edi::is_scan_fitting_mode(edi::effective_fitting_mode(*project_));
    parameters_->setExperimentScope(scan && selected != nullptr ? selected->name() : QString());
    parameters_->sync();
    // The report keeps its composed text and counts this table's rows: a selection that changes the rows
    // changes the report in the same step. The status bar and the Analysis table bind the model itself.
    if (refresh_report && report_ != nullptr) {
        report_->refresh();
    }
}

void ProjectViewModel::invalidateTexts() {
    for (ExperimentViewModel* experiment : experiment_models_) {
        experiment->text()->invalidate();
    }
    for (StructureViewModel* structure : structure_models_) {
        structure->text()->invalidate();
    }
    analysis_->text()->invalidate();
    metadata_text_->invalidate();
    project_text_->invalidate();
}

void ProjectViewModel::syncBlocks() {
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
            next.append(found != nullptr ? found
                                         : new ExperimentViewModel(savedFileFunction(), *project_, block, *this, *registry_, this));
        }
        for (ExperimentViewModel* model : experiment_models_) {
            if (!next.contains(model)) {
                gone.append(model);
            }
        }
        experiment_models_ = next;
    }
    syncLoadState();
    structure_list_->setStructures(structure_models_);
    syncDatasets();
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
        if (canLoadStructure() != published_can_load_structure_) {
            published_can_load_structure_ = canLoadStructure();
            emit canLoadStructureChanged();
        }
        if (canCreateExperiment() != published_can_create_experiment_) {
            published_can_create_experiment_ = canCreateExperiment();
            emit canCreateExperimentChanged();
        }
    }
    for (QObject* model : gone) {
        model->deleteLater();
    }
}

void ProjectViewModel::published(const edi::PreviewResult& result) {
    // The project holds the calculation now (or its refusal, with every computed category cleared): the
    // tables, the charts, the texts and the report follow, once.
    const QString error = QString::fromStdString(result.refusal);
    for (ExperimentViewModel* experiment : experiment_models_) {
        experiment->pattern()->calculated(error);
        experiment->capturePattern();
    }
    // ADR-0022: the transaction published every structure's geometry; each structure view re-presents from
    // its captured source, here on the owner thread.
    for (StructureViewModel* structure : structure_models_) {
        structure->captureScene();
    }
    saved_files_.reset();  // a save writes the calculated pattern too
    invalidateTexts();
    report_->refresh();
    publishCalculating();
    emit recalculated();
}

void ProjectViewModel::publishCalculating() {
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
    if (error != last_error_) {
        last_error_ = error;
        emit lastErrorChanged();
    }
}

}  // namespace edi_app
