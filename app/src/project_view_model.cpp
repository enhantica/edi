// SPDX-License-Identifier: BSD-3-Clause
#include "project_view_model.hpp"

#include <QMetaObject>

#include "edi/edits.hpp"
#include "edi/io.hpp"
#include "edi/selectors.hpp"
#include "parameter_registry.hpp"
#include "report_view_model.hpp"

namespace edi_app {

// ---- StructureListModel / ExperimentListModel ---------------------------------------------------

namespace {
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

ExperimentListModel::ExperimentListModel(QObject* parent) : RowTableModel({"name", "label", "experiment"}, parent) {}

void ExperimentListModel::setExperiments(const QList<ExperimentViewModel*>& experiments) {
    QList<Row> rows;
    for (ExperimentViewModel* experiment : experiments) {
        rows.append({experiment,
                     {experiment->name(), block_label(experiment->name(), QStringLiteral("experiment")),
                      QVariant::fromValue<QObject*>(experiment)}});
    }
    setTableRows(rows);
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
    apply(edi::Edit::project_name(project, name.toStdString()), false);
}

void ProjectViewModel::setTitle(const QString& title) {
    edi::Project& project = *project_;
    apply(edi::Edit::assign(project.metadata.title, title.toStdString()), false);
}

void ProjectViewModel::setDescription(const QString& description) {
    edi::Project& project = *project_;
    apply(edi::Edit::assign(project.metadata.description, description.toStdString()), false);
}

void ProjectViewModel::setCurrentStructureIndex(int index) {
    if (index != current_structure_ && index >= -1 && index < structure_models_.size()) {
        current_structure_ = index;
        publishCurrent();
    }
}

void ProjectViewModel::setCurrentExperimentIndex(int index) {
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
    if (current_experiment_ != published_experiment_index_) {
        published_experiment_index_ = current_experiment_;
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
    setCurrentExperimentIndex(static_cast<int>(experiment_models_.size()) - 1);
    return true;
}

void ProjectViewModel::removeStructure(int index) {
    if (index < 0 || index >= structure_models_.size()) {
        return;
    }
    edi::Project& project = *project_;
    apply(edi::Edit::erase(project.structures, static_cast<std::size_t>(index)), true);
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
    apply(edi::Edit::erase(project.experiments, static_cast<std::size_t>(index)), true);
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
    if (fit_ != nullptr && fit_->running()) {
        const QString message = tr("The project cannot be edited while a fit is running");
        setLastError(message);
        return message;
    }
    pending_structural_ = structural;
    try {
        preview_->apply(change);
    } catch (const std::exception& refusal) {
        const QString message = QString::fromUtf8(refusal.what());
        setLastError(message);
        return message;
    }
    setLastError({});
    setModified(true);
    publishCalculating();
    return {};
}

void ProjectViewModel::setModified(bool modified) {
    if (modified != modified_) {
        modified_ = modified;
        emit modifiedChanged();
    }
}

QString ProjectViewModel::saveTo(const QString& directory) {
    try {
        edi::save_project_as(*project_, directory.toStdString());
    } catch (const std::exception& refusal) {
        const QString message = QString::fromUtf8(refusal.what());
        setLastError(message);
        return message;
    }
    setLastError({});
    emit pathChanged();
    // The saved project's last-modified time advanced: its metadata and every text a save writes show it.
    publishMetadata();
    saved_files_.reset();
    invalidateTexts();
    report_->refresh();
    setModified(false);
    return {};
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
    experiment_list_->setExperiments(experiment_models_);
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
    for (const auto& structure : project_->structures) {
        try {
            edi::complete_model_cell(*structure);
            edi::complete_model_positions(*structure);
        } catch (const std::exception&) {
            continue;
        }
    }
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
    structure_list_->setStructures(structure_models_);
    experiment_list_->setExperiments(experiment_models_);
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
    const bool calculating = preview_ != nullptr && preview_->busy();
    if (calculating != calculating_) {
        calculating_ = calculating;
        emit calculatingChanged();
    }
}

const std::vector<std::pair<std::string, std::string>>& ProjectViewModel::savedFiles() const {
    // One save of the whole project serves every Text tab until the next change (D7).
    if (!saved_files_.has_value()) {
        try {
            saved_files_ = SavedFiles{edi::project_edi_files(*project_), {}};
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
