// SPDX-License-Identifier: BSD-3-Clause
#include "project_view_model.hpp"

#include <QHash>
#include <QMetaObject>
#include <algorithm>
#include <fstream>
#include <filesystem>

#include "edi/edits.hpp"
#include "edi/io.hpp"
#include "edi/scan.hpp"
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

ExperimentListModel::ExperimentListModel(QObject* parent)
    : RowTableModel({"name", "label", "experiment", "fitOutcome", "file", "extracted", "isTemplate"}, parent) {}

void ExperimentListModel::setExperiments(const QList<ExperimentViewModel*>& experiments, const edi::Project& project) {
    // A joint fit records each bank's share (`_fit_result_bank`); a single fit records none and fitted the first.
    const QString outcome = recorded_outcome(project.fit_result);
    const bool joint = std::any_of(project.experiments.begin(), project.experiments.end(),
                                   [](const auto& experiment) { return experiment->fit_prof_wr_factor.has_value(); });
    QList<Row> rows;
    for (int i = 0; i < experiments.size(); ++i) {
        ExperimentViewModel* experiment = experiments[i];
        const bool fitted = joint ? experiment->experiment()->fit_prof_wr_factor.has_value() : i == 0;
        experiment->setFitOutcome(fitted ? outcome : QString());
        rows.append({experiment,
                     {experiment->name(), block_label(experiment->name(), QStringLiteral("experiment")),
                      QVariant::fromValue<QObject*>(experiment), experiment->fitOutcome(),
                      experiment->name() + QStringLiteral(".edi"), QStringList(), false}});
    }
    setTableRows(rows);
}

void ExperimentListModel::setColumns(const QStringList& columns) {
    if (columns != columns_) {
        columns_ = columns;
        emit columnsChanged();
    }
}

void ExperimentListModel::setDatasets(ExperimentViewModel* experiment, const QList<Dataset>& datasets) {
    QList<Row> rows;
    const QString name = experiment != nullptr ? experiment->name() : QString();
    for (int i = 0; i < datasets.size(); ++i) {
        const Dataset& dataset = datasets[i];
        QString label = name + QStringLiteral(" · ") + dataset.file;
        for (const QString& value : dataset.extracted) {
            if (!value.isEmpty()) {
                label += QStringLiteral(" · ") + value;
            }
        }
        // A dataset row is keyed by its place in the scan: one template experiment shows them all.
        rows.append({reinterpret_cast<const void*>(static_cast<std::uintptr_t>(i + 1)),
                     {name, label, QVariant::fromValue<QObject*>(experiment), dataset.outcome, dataset.file,
                      dataset.extracted, dataset.is_template}});
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
    // (`_sequential_fit.template_file`; edi ADR-0017 §19): the shown state is the template from now on.
    connect(fit_, &FitViewModel::finished, this, [this] {
        if (!scan_ || current_dataset_ < 0 || current_dataset_ >= static_cast<int>(scan_datasets_.files.size())) {
            return;
        }
        scan_template_.reset();
        project_->sequential_fit.template_file = scan_datasets_.files[static_cast<std::size_t>(current_dataset_)];
        setModified(true);
        fit_->noteTemplateEdit();
        syncDatasets();
        emit templateIndexChanged();
    });
    connect(fit_, &FitViewModel::canUndoChanged, this, [this] { syncUndo(); });
    connect(fit_, &FitViewModel::runningChanged, this, [this] { syncUndo(); });
    note_fit();
    scan_sync_timer_.setSingleShot(true);
    scan_sync_timer_.setInterval(250);
    connect(&scan_sync_timer_, &QTimer::timeout, this, [this] {
        syncDatasets();
        evolution_->setScan(scan_datasets_, scan_results_, project_->sequential_fit.extract.size(),
                            scan_columns_.value(0));
    });
    if (scan_) {
        fit_->showScan(scan_datasets_, scan_results_);
    }
    // A scan project opens on its template dataset, else on its first.
    if (scan_ && !scan_datasets_.files.empty()) {
        viewDataset(std::max(0, templateIndex()));
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
    if (scan_) {
        // A choice while a scan runs stops following it; the dataset is shown once the run ends.
        if (fit_ != nullptr && fit_->scanning()) {
            fit_->setFollowing(false);
            if (index >= 0 && index < static_cast<int>(scan_datasets_.files.size()) && index != current_dataset_) {
                // The model is the scan's while it runs: the chart shows the chosen file's measured points on a copy
                // of the template, and the dataset is viewed in full when the run ends.
                try {
                    edi::Project shown = scan_template_ ? *scan_template_ : *project_;
                    shown.experiment().data = edi::read_scan_dataset(
                        scan_datasets_.directory, scan_datasets_.files[static_cast<std::size_t>(index)],
                        shown.experiment().effective_beam_mode());
                    showFitFrame(edi::FitFrame{edi::capture_pattern(shown, 0)});
                } catch (const std::exception& refusal) {
                    setLastError(QString::fromUtf8(refusal.what()));
                }
                current_dataset_ = index;
                syncDatasets();
                emit currentExperimentIndexChanged();
            }
            return;
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
    return std::all_of(project_->experiments.begin(), project_->experiments.end(),
                       [](const auto& experiment) { return experiment->calculation_only; });
}

bool ProjectViewModel::createExperiment() {
    edi::Project& project = *project_;
    // The first free name of the form experiment1, experiment2, …
    std::string name;
    for (int n = 1; name.empty(); ++n) {
        const std::string candidate = "experiment" + std::to_string(n);
        const bool held = std::any_of(project.experiments.begin(), project.experiments.end(), [&candidate](const auto& item) {
            return edi::KeyTraits<edi::BraggPdExperiment>::canonical(item->name) ==
                   edi::KeyTraits<edi::BraggPdExperiment>::canonical(candidate);
        });
        name = held ? std::string() : candidate;
    }
    const std::string structure = project.structures.empty() ? std::string() : std::string(project.structures.front()->name);
    QString error;
    try {
        error = apply(edi::Edit::create_experiment(project, edi::simulation_experiment(name, {}, structure)), true);
    } catch (const std::exception& refusal) {
        error = QString::fromUtf8(refusal.what());
        setLastError(error);
    }
    if (!error.isEmpty()) {
        emit refused(error);
        return false;
    }
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
    const std::string structure = experiment.linked_structures.empty()
                                      ? std::string()
                                      : std::string((*experiment.linked_structures.begin())->structure_id);
    QString error;
    try {
        edi::BraggPdExperiment replacement = edi::simulation_experiment(experiment.name, type, structure);
        // Within one beam mode the grid stays as it was set.
        if (replacement.effective_beam_mode() == experiment.effective_beam_mode() && experiment.data.has_value()) {
            replacement.data = experiment.data;
        }
        const edi::ExperimentBase* before = &experiment;
        error = apply(edi::Edit::replace_experiment(project, experiment, std::move(replacement)), true);
        if (error.isEmpty()) {
            // Undo of the experiment's creation removes it in its new type.
            const edi::ExperimentBase* after = project.experiments[static_cast<std::size_t>(index)].get();
            for (UndoRecord& record : undo_history_) {
                if (auto* added = std::get_if<AddedExperiments>(&record)) {
                    std::replace(added->experiments.begin(), added->experiments.end(), before, after);
                }
            }
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

void ProjectViewModel::loadScan() {
    const edi::Project& project = *project_;
    // A project that declares a scan lists its datasets in every fitting mode: a single fit works on the shown one.
    scan_ = project.sequential_fit.declared() && project.experiments.size() == 1;
    evolution_ = new EvolutionViewModel(this);
    if (!scan_) {
        return;
    }
    for (const auto& rule : project.sequential_fit.extract) {
        const QString id = QString::fromStdString(rule->id.value());
        const QString unit = QString::fromStdString(edi::scan_target_unit(rule->target));
        scan_columns_.append(unit.isEmpty() ? id : QStringLiteral("%1 (%2)").arg(id, unit));
    }
    try {
        scan_datasets_ = edi::scan_datasets(project);
    } catch (const std::exception& refusal) {
        setLastError(QString::fromUtf8(refusal.what()));
    }
    scan_results_ = edi::read_scan_results(project);
    evolution_->setScan(scan_datasets_, scan_results_, project.sequential_fit.extract.size(),
                        scan_columns_.value(0));
}

int ProjectViewModel::templateIndex() const {
    const std::string& file = project_->sequential_fit.template_file;
    if (!scan_ || file.empty()) {
        return -1;
    }
    const auto found = std::find(scan_datasets_.files.begin(), scan_datasets_.files.end(), file);
    return found == scan_datasets_.files.end() ? -1 : static_cast<int>(found - scan_datasets_.files.begin());
}

void ProjectViewModel::syncDatasets() {
    if (!scan_) {
        experiment_list_->setExperiments(experiment_models_, *project_);
        return;
    }
    // A results row: file_path, reduced χ², success, iterations, then one cell per extract rule.
    constexpr std::size_t kSuccessColumn = 2, kFirstExtractColumn = 4;
    const std::size_t rules = project_->sequential_fit.extract.size();
    QStringList units;
    for (const auto& rule : project_->sequential_fit.extract) {
        units.append(QString::fromStdString(edi::scan_target_unit(rule->target)));
    }
    QList<ExperimentListModel::Dataset> rows;
    rows.reserve(static_cast<qsizetype>(scan_datasets_.files.size()));
    for (const std::string& file : scan_datasets_.files) {
        ExperimentListModel::Dataset dataset;
        dataset.file = QString::fromStdString(file);
        dataset.is_template = file == project_->sequential_fit.template_file;
        QStringList values = scan_extracted_.value(dataset.file);
        if (const auto row = scan_results_.rows.find(file); row != scan_results_.rows.end()) {
            dataset.outcome = row->second[kSuccessColumn] == "True" ? QStringLiteral("success") : QStringLiteral("failed");
            values.clear();
            for (std::size_t rule = 0; rule < rules && kFirstExtractColumn + rule < row->second.size(); ++rule) {
                values.append(QString::fromStdString(row->second[kFirstExtractColumn + rule]));
            }
        }
        for (qsizetype i = 0; i < values.size(); ++i) {
            if (!values[i].isEmpty() && i < units.size() && !units[i].isEmpty()) {
                values[i] += QStringLiteral(" ") + units[i];
            }
        }
        dataset.extracted = values;
        rows.append(dataset);
    }
    // The shown dataset's outcome is the experiment's own in the selector box.
    if (ExperimentViewModel* experiment = experiment_models_.value(0)) {
        experiment->setFitOutcome(current_dataset_ >= 0 && current_dataset_ < rows.size() ? rows[current_dataset_].outcome
                                                                                          : QString());
    }
    experiment_list_->setColumns(scan_columns_);
    experiment_list_->setDatasets(experiment_models_.value(0), rows);
}

void ProjectViewModel::viewDataset(int index) {
    if (index < 0 || index >= static_cast<int>(scan_datasets_.files.size()) || index == current_dataset_ ||
        experiment_models_.isEmpty() || (fit_ != nullptr && fit_->running())) {
        return;
    }
    const std::string& file = scan_datasets_.files[static_cast<std::size_t>(index)];
    const QString name = QString::fromStdString(file);
    if (!scan_template_) {
        scan_template_ = *project_;
    }
    // Every parameter at the template's state, then a fitted dataset's results-row values over it.
    std::vector<edi::Edit::ScanValue> values;
    for (const edi::NamedSlot& slot : edi::named_slots(*scan_template_)) {
        values.push_back({slot.unique_name, slot.parameter->value.get(), slot.parameter->uncertainty.get()});
    }
    const auto row = scan_results_.rows.find(file);
    if (row != scan_results_.rows.end()) {
        std::map<std::string, std::size_t> column;
        for (std::size_t i = 0; i < scan_results_.header.size(); ++i) {
            column.emplace(scan_results_.header[i], i);
        }
        for (edi::Edit::ScanValue& value : values) {
            bool ok = false;
            const std::string name = edi::scan_results_column(value.unique_name);
            if (const auto found = column.find(name); found != column.end()) {
                const double read = QString::fromStdString(row->second[found->second]).toDouble(&ok);
                if (ok) {
                    value.value = read;
                }
            }
            if (const auto found = column.find(name + ".uncertainty"); found != column.end()) {
                const double read = QString::fromStdString(row->second[found->second]).toDouble(&ok);
                value.uncertainty = ok ? std::optional<double>(read) : std::nullopt;
            }
        }
    }
    edi::Project& project = *project_;
    edi::PdDataBase data;
    try {
        data = edi::read_scan_dataset(scan_datasets_.directory, file, project.experiment().effective_beam_mode());
        if (row == scan_results_.rows.end() && !scan_extracted_.contains(name)) {
            QStringList extracted;
            for (const std::string& value : edi::scan_extract_values(project, scan_datasets_.directory, file)) {
                extracted.append(QString::fromStdString(value));
            }
            scan_extracted_.insert(name, extracted);
        }
    } catch (const std::exception& refusal) {
        const QString error = QString::fromUtf8(refusal.what());
        setLastError(error);
        emit refused(error);
        return;
    }
    // Showing a dataset is not an edit: the project's modified state stays as it was.
    const bool modified = modified_;
    applying_view_ = true;
    const QString error =
        apply(edi::Edit::scan_view(project, project.experiment(), std::move(values), std::move(data)), false);
    applying_view_ = false;
    setModified(modified);
    if (!error.isEmpty()) {
        emit refused(error);
        return;
    }
    current_dataset_ = index;
    syncDatasets();
    publishCurrent();
}

QString ProjectViewModel::prepareScan(bool fresh) {
    if (fit_ != nullptr && fit_->running()) {
        return tr("A fit is running");
    }
    // The template back in the model, with its own data, while a dataset is shown.
    if (scan_template_) {
        std::vector<edi::Edit::ScanValue> values;
        for (const edi::NamedSlot& slot : edi::named_slots(*scan_template_)) {
            values.push_back({slot.unique_name, slot.parameter->value.get(), slot.parameter->uncertainty.get()});
        }
        const bool modified = modified_;
        applying_view_ = true;
        const QString error = apply(
            edi::Edit::scan_view(*project_, project_->experiment(), std::move(values),
                                 scan_template_->experiment().data.value_or(edi::PdDataBase{})),
            false);
        applying_view_ = false;
        setModified(modified);
        if (!error.isEmpty()) {
            return error;
        }
        scan_template_.reset();
    }
    if (!fresh) {
        return {};
    }
    // The previous results, kept for Undo, then removed: crysta's driver starts a scan without them.
    const std::filesystem::path analysis = std::filesystem::path(project_->path) / "analysis";
    const auto take = [](const std::filesystem::path& file) -> std::optional<std::string> {
        std::ifstream input(file, std::ios::binary);
        if (!input) {
            return std::nullopt;
        }
        return std::string(std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>());
    };
    ScanRun run{take(analysis / "results.csv"), take(analysis / "results-provenance.csv")};
    if (!run.results && !run.provenance) {
        return {};
    }
    std::error_code ignored;
    std::filesystem::remove(analysis / "results.csv", ignored);
    std::filesystem::remove(analysis / "results-provenance.csv", ignored);
    undo_history_.emplace_back(std::move(run));
    syncUndo();
    reloadScanResults();
    return {};
}

bool ProjectViewModel::restoreScanRun(const ScanRun& run) {
    if (fit_ != nullptr && fit_->running()) {
        return false;
    }
    const std::filesystem::path analysis = std::filesystem::path(project_->path) / "analysis";
    const auto put = [](const std::filesystem::path& file, const std::optional<std::string>& text) {
        std::error_code ignored;
        if (!text) {
            std::filesystem::remove(file, ignored);
            return true;
        }
        std::ofstream output(file, std::ios::binary | std::ios::trunc);
        output << *text;
        return static_cast<bool>(output);
    };
    std::error_code ignored;
    std::filesystem::create_directories(analysis, ignored);
    if (!put(analysis / "results.csv", run.results) || !put(analysis / "results-provenance.csv", run.provenance)) {
        const QString message = tr("The previous scan results could not be written back to %1")
                                    .arg(QString::fromStdString(analysis.string()));
        setLastError(message);
        emit refused(message);
        return false;
    }
    fit_->noteTemplateEdit();
    reloadScanResults();
    return true;
}

void ProjectViewModel::reloadScanResults() {
    scan_results_ = edi::read_scan_results(*project_);
    syncDatasets();
    evolution_->setScan(scan_datasets_, scan_results_, project_->sequential_fit.extract.size(), scan_columns_.value(0));
    fit_->showScan(scan_datasets_, scan_results_);
}

void ProjectViewModel::scanFileFitted() {
    // The new row only: the file is read from its end.
    edi::ScanResults last = edi::read_last_scan_result(*project_);
    if (last.rows.empty()) {
        return;
    }
    if (scan_results_.header.empty()) {
        scan_results_.header = std::move(last.header);
    }
    for (auto& [file, cells] : last.rows) {
        scan_results_.rows.insert_or_assign(file, std::move(cells));
    }
    if (!scan_sync_timer_.isActive()) {
        scan_sync_timer_.start();
    }
}

void ProjectViewModel::showScanFrame(const std::string& file, const edi::FitFrame& frame) {
    const auto found = std::find(scan_datasets_.files.begin(), scan_datasets_.files.end(), file);
    if (found == scan_datasets_.files.end()) {
        return;
    }
    // The chart shows the file just fitted; the model is viewed again when the run ends.
    current_dataset_ = static_cast<int>(found - scan_datasets_.files.begin());
    showFitFrame(frame);
    emit currentExperimentIndexChanged();
    if (!scan_sync_timer_.isActive()) {
        scan_sync_timer_.start();
    }
}

void ProjectViewModel::scanEnded() {
    scan_sync_timer_.stop();
    reloadScanResults();
    // The shown dataset as the rows on disk now give it.
    const int shown = current_dataset_;
    current_dataset_ = -1;
    viewDataset(std::max(0, shown));
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
    // A structure an experiment links stays: removing it would leave the link naming nothing. The
    // link is removed first, on the Experiment page.
    const std::string& name = project.structures[static_cast<std::size_t>(index)]->name.value();
    for (const auto& experiment : project.experiments) {
        for (const auto& link : experiment->linked_structures) {
            if (link->structure_id.value() == name) {
                const QString error = tr("Structure '%1' is linked by experiment '%2'; remove that link first.")
                                          .arg(QString::fromStdString(name), QString::fromStdString(experiment->name));
                setLastError(error);
                emit refused(error);
                return;
            }
        }
    }
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
    // An edit while a scan dataset is shown makes the shown state the template, seeded from that dataset
    // (edi ADR-0017 §19): the next dataset view starts from it. A stopped scan is then started afresh.
    if (!applying_view_) {
        scan_template_.reset();
        if (scan_ && fit_ != nullptr) {
            fit_->noteTemplateEdit();
        }
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
    } else {
        undone = fit_->undo();
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
    syncDatasets();
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
