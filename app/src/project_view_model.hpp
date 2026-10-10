// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_PROJECT_VIEW_MODEL_HPP
#define EDI_APP_PROJECT_VIEW_MODEL_HPP

#include <QHash>
#include <QList>
#include <QStringList>
#include <QObject>
#include <QPointer>
#include <QTemporaryDir>
#include <QTimer>
#include <QString>
#include <QUrl>
#include <QtQml/qqmlregistration.h>
#include <functional>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <string>
#include <utility>
#include <variant>
#include <vector>

#include "analysis_view_model.hpp"
#include "block_text.hpp"
#include "edi/edit.hpp"
#include "edi/live_preview.hpp"
#include "edi/model.hpp"
#include "edi/scan.hpp"
#include "edi/worker.hpp"
#include "evolution_view_model.hpp"
#include "scan_session.hpp"
#include "experiment_view_model.hpp"
#include "fit_view_model.hpp"
#include "parameter_table_model.hpp"
#include "project_editor.hpp"
#include "report_view_model.hpp"
#include "row_table_model.hpp"
#include "structure_view_model.hpp"
#include "structure_view_options.hpp"

namespace edi_app {

class ParameterRegistry;

// The project's structures: roles `name`, `label` (`name · file`, the file the structure is saved as),
// `structure` (StructureViewModel), `colorIndex`.
class StructureListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a project")

   public:
    explicit StructureListModel(QObject* parent);
    void setStructures(const QList<StructureViewModel*>& structures);
};

// The project's experiments: roles `name`, `label` (`name · file`), `experiment` (ExperimentViewModel),
// `fitOutcome`, the outcome key of the project's last fit (recorded_outcome) on each experiment it fitted, else
// empty: the first experiment after a single fit, every bank of a joint fit; `file`, the file its data is in; and
// `extracted`, its scan values with their units. In a scan project the rows are the scan's datasets instead
// (setDatasets): each the template experiment over one data file, with that file's results.csv outcome.
class ExperimentListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a project")
    // A scan's extract columns, one per rule with its unit, in the order of each row's `extracted` values.
    Q_PROPERTY(QStringList columns READ columns NOTIFY columnsChanged)

   public:
    explicit ExperimentListModel(QObject* parent);
    void setExperiments(const QList<ExperimentViewModel*>& experiments, const edi::Project& project);
    struct Dataset {
        QString file;
        QString outcome;
        QStringList extracted;
        bool is_template = false;
    };
    // A scan's `count` datasets. The rows hold only their keys: a row's values are built from `row` when it is read,
    // so a scan of many files keeps no text per file (the session holds its facts).
    void setDatasets(ExperimentViewModel* experiment, int count, std::function<Dataset(int)> row);
    // A dataset's facts changed; its row is read again.
    void datasetChanged(int index) { announceRows(index, index); }
    // Every dataset's facts may have changed.
    void datasetsChanged() { announceRows(0, count() - 1); }
    // Whether the rows are `count` datasets of `experiment` already, so a change needs only announcing.
    bool showsDatasets(ExperimentViewModel* experiment, int count) const {
        return dataset_row_ && dataset_experiment_ == experiment && this->count() == count;
    }
    QStringList columns() const { return columns_; }
    void setColumns(const QStringList& columns);
    // Called with each row a view reads (a scan's datasets): the owner loads what the row still lacks, so only shown
    // rows are read.
    void setShownHook(std::function<void(int)> shown) { shown_ = std::move(shown); }
    QVariant data(const QModelIndex& index, int role) const override;

   signals:
    void columnsChanged();

   protected:
    QList<QVariant> rowValues(int row) const override;

   private:
    QStringList columns_;
    std::function<void(int)> shown_;
    std::function<Dataset(int)> dataset_row_;  // set while the rows are a scan's datasets
    QPointer<ExperimentViewModel> dataset_experiment_;
};

// The open project. It owns the core Project and is the editor every write goes through: the core
// call, then the differences published (I3), the block lists re-derived after a structural
// change, and one queued recalculation per event-loop turn (D8).
class ProjectViewModel : public QObject, public ProjectEditor {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Opened through Session")
    Q_PROPERTY(QString name READ name WRITE setName NOTIFY nameChanged)
    Q_PROPERTY(QString title READ title WRITE setTitle NOTIFY titleChanged)
    Q_PROPERTY(QString description READ description WRITE setDescription NOTIFY descriptionChanged)
    Q_PROPERTY(QString path READ path NOTIFY pathChanged)
    // True after any edit since the project was opened or last saved (edi ADR-0017 §13).
    Q_PROPERTY(bool modified READ modified NOTIFY modifiedChanged)
    Q_PROPERTY(QString lastModified READ lastModified NOTIFY lastModifiedChanged)
    Q_PROPERTY(edi_app::StructureListModel* structures READ structures CONSTANT)
    Q_PROPERTY(edi_app::ExperimentListModel* experiments READ experiments CONSTANT)
    Q_PROPERTY(edi_app::ParameterTableModel* parameters READ parameters CONSTANT)
    Q_PROPERTY(edi_app::AnalysisViewModel* analysis READ analysis CONSTANT)
    // Start fitting, its progress and its result.
    Q_PROPERTY(edi_app::FitViewModel* fit READ fit CONSTANT)
    Q_PROPERTY(edi_app::BlockText* metadataText READ metadataText CONSTANT)
    Q_PROPERTY(edi_app::BlockText* projectText READ projectText CONSTANT)
    Q_PROPERTY(edi_app::ReportViewModel* report READ report CONSTANT)
    Q_PROPERTY(int currentStructureIndex READ currentStructureIndex WRITE setCurrentStructureIndex NOTIFY currentStructureIndexChanged)
    Q_PROPERTY(int currentExperimentIndex READ currentExperimentIndex WRITE setCurrentExperimentIndex NOTIFY currentExperimentIndexChanged)
    Q_PROPERTY(edi_app::StructureViewModel* currentStructure READ currentStructure NOTIFY currentStructureChanged)
    Q_PROPERTY(edi_app::ExperimentViewModel* currentExperiment READ currentExperiment NOTIFY currentExperimentChanged)
    Q_PROPERTY(bool canLoadStructure READ canLoadStructure NOTIFY canLoadStructureChanged)
    // Create experiment adds an experiment without data, beside experiments with data too: a fit skips it, a
    // calculation covers it. A scan project keeps its one template experiment.
    Q_PROPERTY(bool canCreateExperiment READ canCreateExperiment NOTIFY canCreateExperimentChanged)
    // A scan project (sequential or independent mode over a declared scan): its experiment list is the scan's
    // datasets, and the current experiment index the shown dataset. `scanColumns`: one heading per extract
    // rule, with its unit ("temperature (K)").
    Q_PROPERTY(bool scan READ scan NOTIFY scanChanged)
    Q_PROPERTY(QStringList scanColumns READ scanColumns CONSTANT)
    // The template dataset's place among the datasets (`_sequential_fit.template_file`), or -1.
    Q_PROPERTY(int templateIndex READ templateIndex NOTIFY templateIndexChanged)
    // The Evolution tab: a fitted parameter across the scan's datasets (scan projects).
    Q_PROPERTY(edi_app::EvolutionViewModel* evolution READ evolution CONSTANT)
    Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)
    // The app bar's Undo (edi ADR-0024): the newest recorded change — an edit of the aliases or
    // constraints, or a fit — is undone, so they undo in the order they were made.
    Q_PROPERTY(bool canUndo READ canUndo NOTIFY canUndoChanged)
    // A calculation is in flight or owed (edi ADR-0020): the pattern, the texts and the report show the last
    // published one until `recalculated`.
    Q_PROPERTY(bool calculating READ calculating NOTIFY calculatingChanged)
    // ADR-0017 §16: the structure view's options, one object for the open project, shared by the toolbar, the
    // Appearance group and every structure's view; a new project starts at the defaults.
    Q_PROPERTY(edi_app::StructureViewOptions* structureViewOptions READ structureViewOptions CONSTANT)

   public:
    ProjectViewModel(edi::Project project, QObject* parent);
    ~ProjectViewModel() override;

    QString name() const;
    void setName(const QString& name);
    QString title() const;
    void setTitle(const QString& title);
    QString description() const;
    void setDescription(const QString& description);
    QString path() const { return QString::fromStdString(project_->path); }
    bool modified() const { return modified_; }
    // Save the project into `directory` through the core (edi::save_project_as), which then is the
    // project's directory; an empty string on success, else the core's message (also `lastError`).
    QString saveTo(const QString& directory);
    QString lastModified() const;
    StructureListModel* structures() const { return structure_list_; }
    ExperimentListModel* experiments() const { return experiment_list_; }
    ParameterTableModel* parameters() const { return parameters_; }
    AnalysisViewModel* analysis() const { return analysis_; }
    FitViewModel* fit() const { return fit_; }
    BlockText* metadataText() const { return metadata_text_; }
    BlockText* projectText() const { return project_text_; }
    ReportViewModel* report() const { return report_; }
    int currentStructureIndex() const { return current_structure_; }
    void setCurrentStructureIndex(int index);
    int currentExperimentIndex() const { return scan_ ? current_dataset_ : current_experiment_; }
    void setCurrentExperimentIndex(int index);
    StructureViewModel* currentStructure() const { return structure_models_.value(current_structure_); }
    ExperimentViewModel* currentExperiment() const { return experiment_models_.value(current_experiment_); }
    // A project holds any number of structures (phases); loading one is always possible.
    bool canLoadStructure() const { return true; }
    bool canCreateExperiment() const;
    bool scan() const { return scan_; }
    QStringList scanColumns() const { return scan_columns_; }
    EvolutionViewModel* evolution() const { return evolution_; }
    int templateIndex() const;
    QString lastError() const { return last_error_; }
    bool calculating() const { return calculating_; }
    StructureViewOptions* structureViewOptions() const { return structure_view_options_; }
    const QList<StructureViewModel*>& structureModels() const { return structure_models_; }
    const QList<ExperimentViewModel*>& experimentModels() const { return experiment_models_; }
    const edi::Project& project() const { return *project_; }
    // The demo's seam: the project's created and last-modified times, which a loaded example takes
    // from the clock, set to a fixed value so its saved Text is reproducible.
    void pinTimestamps(const QString& timestamp);
    // The files a save of the project writes (path relative to the project, text), from one save
    // per change; a writer refusal is thrown as its message.
    const std::vector<std::pair<std::string, std::string>>& savedFiles() const;
    std::string savedFile(const std::string& relative) const;
    SavedFile savedFileFunction() const;

    // D12: add blocks from `.edi` files; on a refusal nothing changes and `refused` names the reason.
    Q_INVOKABLE bool loadStructure(const QUrl& file);
    Q_INVOKABLE bool loadExperiments(const QList<QUrl>& files);
    // A structure's removal takes every experiment's link to it (and texture row for it) with it, in one undoable
    // step, with a message naming the experiments.
    Q_INVOKABLE void removeStructure(int index);
    // Create structure: a new structure named structure1, structure2, … holding easydiffractionbeta's default phase
    // (P b n m, a = 10, b = 6, c = 5 Å, one O site at the origin), selected and linked to no experiment. One
    // undoable step.
    Q_INVOKABLE bool createStructure();
    Q_INVOKABLE void removeExperiment(int index);
    // A new experiment without data (edi::simulation_experiment), selected: powder, constant wavelength,
    // neutron, Bragg, linked to every structure. One undoable step, as a load of experiments is.
    Q_INVOKABLE bool createExperiment();
    // Load data…: the plain-data file's rows (crysta's reader) become the measured data of experiment `index`, one
    // made with Create experiment; its type then locks and its range shows the data's. An experiment still named
    // experiment1, experiment2, … takes the file's name. A second load replaces the data. One undoable step, and
    // one message saying what the reader skipped or changed.
    Q_INVOKABLE bool loadData(int index, const QUrl& file);
    // Load data for the experiment a chooser was opened for, wherever its row is now: refused when that experiment
    // is no longer in the project (removed, or replaced by an Undo or a type change since).
    Q_INVOKABLE bool loadDataInto(edi_app::ExperimentViewModel* experiment, const QUrl& file);
    // One type axis ("sampleForm", "beamMode", "radiationProbe", "scatteringType") of an experiment without
    // data set to `token`: the experiment is made anew with that type, keeping its name, its link and,
    // within one beam mode, its range.
    Q_INVOKABLE bool setExperimentType(int index, const QString& axis, const QString& token);
    // The place of the structure of this name in the project, or -1: its colour (edi ADR-0017 §8).
    Q_INVOKABLE int structureIndex(const QString& name) const;

    QString apply(const edi::Edit& change, bool structural) override;
    QString apply_relation_edit(const edi::Edit& change) override;
    bool canUndo() const { return can_undo_; }
    Q_INVOKABLE void undo();

    // , the fit's three owner-thread steps (FitViewModel): the project took a fit's result — every view
    // publishes it, the pattern included, in one step; a frame of a running fit is drawn; the patterns go back
    // to what the project holds (a fit that wrote nothing).
    void publishFit();
    void showFitFrame(const edi::FitFrame& frame);
    void restorePatterns();
    // A scan run's owner-thread steps (FitViewModel): before a fresh run, the previous results set aside, which
    // Undo restores; each file it fits; the file it shows while followed; its end, after which the shown dataset is
    // viewed again from the rows on disk. The shown dataset stays in the model while the scan runs from the template.
    QString prepareScan(bool fresh);
    // Reset fits (FitViewModel::reset): every dataset's fit result cleared, one Undo step; the refusal, if any.
    QString resetScan();
    // Why an edit or a single or joint fit waits: a chosen dataset is still being read, so the model still shows the
    // one before; empty otherwise.
    QString pendingRefusal() const;
    // The template a scan runs from: the stored one while a dataset is shown, else none (the model is the template).
    const edi::Project* scanTemplate() const { return scan_template_ ? &*scan_template_ : nullptr; }
    // The place of the file's dataset in the scan, or -1 when its row could not be indexed.
    int scanFileFitted(const edi::ScanFileRecord& record);
    void showScanFrame(const std::string& file, const edi::FitFrame& frame);
    void followScanFile(const std::string& file);
    // The run's driver returned: the rows and notes on disk are indexed again, the files skipped after the last
    // row included (a skipped file sends no event). Comes before scanEnded.
    void settleScan();
    // The run ended: its status, seconds and outcome key (the worst file's, Stopped or Failed).
    void scanEnded(edi::FitStatus status, double seconds);
    // Why the scan modes cannot run here (no single template experiment, no datasets), or empty.
    QString scanRefusal() const;
    QString apply_setting(const edi::Edit& change) override;
    // The scan's results (null outside a scan project).
    const ScanSession* scanSession() const { return scan_session_; }

   signals:
    void nameChanged();
    void titleChanged();
    void descriptionChanged();
    void lastModifiedChanged();
    void currentStructureIndexChanged();
    void currentStructureChanged();
    void currentExperimentIndexChanged();
    void currentExperimentChanged();
    void canLoadStructureChanged();
    void canCreateExperimentChanged();
    void lastErrorChanged();
    void canUndoChanged();
    void refused(const QString& message);
    // A message for the status bar's Messages (Session lists it): a load's account, a removal's links.
    void message(const QString& text);
    void pathChanged();
    void modifiedChanged();
    // A calculation was published; each experiment's pattern holds its outcome (Session's message list).
    void recalculated();
    void calculatingChanged();
    // A calculation began, and ended, on the worker (edi::LivePreview's `calculating` and `calculated` hooks):
    // every one it runs, a superseded one included, in order, each before its publication or rejection. What
    // counts the calculations an input costs (the owner's one-calculation rule).
    void calculationStarted();
    void templateIndexChanged();
    void scanChanged();
    void calculationFinished();

   private:
    void publish(bool structural);
    // Each of these signals only what changed since it was last published (the owner's per-property
    // rule).
    void publishMetadata();
    void publishCurrent();
    void syncBlocks();
    void completeSymmetry();
    void syncParameterTable(bool refresh_report = true);
    void invalidateTexts();
    // A calculation the worker finished was published into the project (edi::LivePreview's hook).
    void published(const edi::PreviewResult& result);
    void publishCalculating();
    void setLastError(const QString& error);
    void setModified(bool modified);

    std::unique_ptr<edi::Project> project_;
    ParameterRegistry* registry_;
    QList<StructureViewModel*> structure_models_;
    QList<ExperimentViewModel*> experiment_models_;
    StructureListModel* structure_list_;
    ExperimentListModel* experiment_list_;
    ParameterTableModel* parameters_;
    AnalysisViewModel* analysis_;
    FitViewModel* fit_ = nullptr;
    // The undo history, oldest first: a fit (none: the fit's own start state is what undo_fit restores), an
    // edit of the relations (its RelationsUndo), or experiments added by Create or Load experiment.
    struct AddedExperiments {
        std::vector<const edi::ExperimentBase*> experiments;
    };
    // A fresh scan run: the result files it replaced, as they were (absent: there was none, also recorded).
    // The fit records Reset fits clears: the model's and, while a dataset is shown, the template's.
    struct FitRecords {
        edi::FitResultRecord model;
        std::optional<edi::FitResultRecord> stash;
    };
    struct ScanRun {
        ScanSession::Files files;
        std::optional<FitRecords> fit_records;  // Reset fits only
        int shown_dataset = -1;                 // Reset fits only: the dataset the model showed, and its values
        std::vector<edi::Edit::ScanValue> shown_values;
    };
    // Load data: the experiment as it was before (a simulation, or its earlier data, with its file name).
    struct LoadedData {
        const edi::ExperimentBase* experiment = nullptr;
        std::shared_ptr<const edi::BraggPdExperiment> before;
    };
    using UndoRecord =
        std::variant<std::monostate, edi::RelationsUndo, AddedExperiments, ScanRun, LoadedData, edi::StructuresUndo>;
    // The experiments made with Create experiment (they take Load data…), kept by identity: a replaced experiment
    // (Load data, a type change, their undo) passes its entry on.
    std::set<const edi::ExperimentBase*> created_;
    void experimentReplaced(const edi::ExperimentBase* before, const edi::ExperimentBase* after, bool created);
    // Each experiment view's Load data… state, from the set above.
    void syncLoadState();
    // Applies an experiment's replacement by Load data or its undo; the refusal, if any.
    QString replaceData(int index, edi::BraggPdExperiment replacement);
    bool restoreScanRun(const ScanRun& run);
    // The results read again from disk (after a run, an undo or a load), with every view of them.
    void reloadScanResults();
    // The indexed results in the lists, Evolution, the fit summary and the outdated state.
    void showScanResults();
    // After the template changed (a single fit's designation, its Undo): texts, tags and outdated state.
    void publishTemplate();
    // The run as a whole, from the indexed rows: `run_outcome` is the run's own end when it failed or was stopped.
    ScanSummary scanSummary(const QString& run_outcome, double seconds) const;
    // The template designation a single fit on a dataset changes, as it was before the fit, for its Undo.
    struct TemplateState {
        std::string template_file;
        std::optional<edi::Project> stash;
        std::optional<std::string> run_file;  // the scan's provenance file as it was (which fit came last)
        bool run_file_known = false;          // false: it could not be read, so its Undo leaves it alone
    };
    std::optional<TemplateState> fit_template_before_, fit_template_undo_;
    std::vector<UndoRecord> undo_history_;
    void noteAddedExperiments(std::size_t before);
    bool can_undo_ = false;
    void syncUndo();
    BlockText* metadata_text_;
    BlockText* project_text_;
    ReportViewModel* report_;
    StructureViewOptions* structure_view_options_;
    int current_structure_ = -1;
    int current_experiment_ = -1;
    // A scan project (edi ADR-0017 §19, ADR-0026): its results (the session), the dataset shown, and the template.
    // While a dataset is shown the model holds that dataset's projection (its data, the template's parameters with
    // its results row over them) and `scan_template_` holds the template, which is what a save writes and what a
    // scan runs from. An admitted edit of the experiment or the structures goes to the template, seeded from the
    // shown values; an edit of a project-wide setting goes to both; a refused edit to neither.
    bool scan_ = false;
    QString scan_refusal_;
    EvolutionViewModel* evolution_ = nullptr;
    QStringList scan_columns_;
    ScanSession* scan_session_ = nullptr;
    int current_dataset_ = -1;
    std::optional<edi::Project> scan_template_;
    bool applying_view_ = false;
    bool applying_setting_ = false;
    // The newest dataset view asked for: a projection read off the GUI thread applies only while it is the newest.
    std::uint64_t view_request_ = 0, view_applied_ = 0;
    int view_wanted_ = -1;       // the dataset of the newest request
    int projected_dataset_ = -1;  // the dataset the model holds now (a failed read leaves the one before)
    bool view_reading_ = false;  // a read is in flight
    // Reads the newest requested dataset off the GUI thread; its delivery applies it, or reads a newer one.
    void startViewRead();
    // Shows a dataset at once: the one a project opens on (`reread`: its file is read), or the shown one again from
    // its changed row.
    void viewDatasetNow(int index, bool reread);
    // The identity of the template a run is fitting from (ScanSession::templateIdentity), for its provenance.
    std::string run_identity_;
    // A Continue's earlier provenance (its rows stay), for the run's own at its end.
    std::optional<ScanSession::Run> previous_run_;
    void loadScan();
    // Re-derives whether the scan modes can run (a single template experiment and a listed scan).
    void syncScanAdmission();
    // Shows a dataset: its projection is read off the GUI thread and applied when ready. `refresh`: again, even
    // when it is the shown one (its results row changed).
    void viewDataset(int index, bool refresh = false);
    // A dataset's projection, read off the GUI thread: its data, the values it is shown with and, while a scan
    // runs, its calculated pattern; or the refusal.
    struct DatasetView {
        std::optional<edi::PdDataBase> data;
        std::vector<edi::Edit::ScanValue> values;
        std::optional<edi::FitFrame> frame;
        QString error;
    };
    // Applies a projection read for request `request`, unless a newer one was asked for since.
    void applyDatasetView(std::uint64_t request, int index, DatasetView view);
    // The values a dataset is shown with: the template's, with its results row's over them.
    std::vector<edi::Edit::ScanValue> datasetValues(const std::vector<std::string>& row) const;
    void syncDatasets();
    // One dataset's row in the lists (its outcome, extracted values, template tag).
    void syncDataset(int index);
    ExperimentListModel::Dataset datasetRow(int index) const;
    // The template, or the model when no dataset view holds one apart.
    const edi::Project& scanTemplateOrModel() const { return scan_template_ ? *scan_template_ : *project_; }
    // The results' outdated state, from their provenance against the template.
    void syncOutOfDate();
    void markTemplateChanged();
    struct SavedFiles {
        std::vector<std::pair<std::string, std::string>> files;
        std::string refusal;
    };
    mutable std::optional<SavedFiles> saved_files_;
    // ADR-0020: the calculation runs on the worker; every edit goes through the preview, which publishes a
    // result only if no newer request exists. Deliveries arrive here by a queued call, so every model write
    // and every signal of a publication happens on this object's (the GUI) thread. The preview goes first
    // when the project closes, then the worker, which waits for a calculation in flight.
    std::unique_ptr<edi::work::Worker> worker_;
    std::unique_ptr<edi::LivePreview> preview_;
    bool pending_structural_ = false;
    bool calculating_ = false;
    bool modified_ = false;
    QString last_error_;
    QString published_name_, published_title_, published_description_, published_last_modified_;
    StructureViewModel* published_structure_ = nullptr;
    ExperimentViewModel* published_experiment_ = nullptr;
    int published_structure_index_ = -1;
    int published_experiment_index_ = -1;
    bool published_can_load_structure_ = false;
    bool published_can_create_experiment_ = false;
};

}  // namespace edi_app

#endif  // EDI_APP_PROJECT_VIEW_MODEL_HPP
