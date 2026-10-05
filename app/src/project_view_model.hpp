// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_PROJECT_VIEW_MODEL_HPP
#define EDI_APP_PROJECT_VIEW_MODEL_HPP

#include <QHash>
#include <QList>
#include <QStringList>
#include <QObject>
#include <QString>
#include <QUrl>
#include <QtQml/qqmlregistration.h>
#include <memory>
#include <optional>
#include <string>
#include <utility>
#include <variant>
#include <vector>

#include "analysis_view_model.hpp"
#include "block_text.hpp"
#include "edi/live_preview.hpp"
#include "edi/model.hpp"
#include "edi/scan.hpp"
#include "edi/worker.hpp"
#include "evolution_view_model.hpp"
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

   public:
    explicit ExperimentListModel(QObject* parent);
    void setExperiments(const QList<ExperimentViewModel*>& experiments, const edi::Project& project);
    struct Dataset {
        QString file;
        QString outcome;
        QStringList extracted;
    };
    void setDatasets(ExperimentViewModel* experiment, const QList<Dataset>& datasets);
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
    // Create experiment adds an experiment without data: refused while the project's experiments carry
    // measured data (a project calculates or fits as a whole).
    Q_PROPERTY(bool canCreateExperiment READ canCreateExperiment NOTIFY canCreateExperimentChanged)
    // A scan project (sequential or independent mode over a declared scan): its experiment list is the scan's
    // datasets, and the current experiment index the shown dataset. `scanColumns`: one heading per extract
    // rule, with its unit ("temperature (K)").
    Q_PROPERTY(bool scan READ scan CONSTANT)
    Q_PROPERTY(QStringList scanColumns READ scanColumns CONSTANT)
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
    Q_INVOKABLE void removeStructure(int index);
    Q_INVOKABLE void removeExperiment(int index);
    // A new experiment without data (edi::simulation_experiment), selected: powder, constant wavelength,
    // neutron, Bragg, linked to the first structure. One undoable step, as a load of experiments is.
    Q_INVOKABLE bool createExperiment();
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
    void pathChanged();
    void modifiedChanged();
    // A calculation was published; each experiment's pattern holds its outcome (Session's message list).
    void recalculated();
    void calculatingChanged();
    // A calculation began, and ended, on the worker (edi::LivePreview's `calculating` and `calculated` hooks):
    // every one it runs, a superseded one included, in order, each before its publication or rejection. What
    // counts the calculations an input costs (the owner's one-calculation rule).
    void calculationStarted();
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
    using UndoRecord = std::variant<std::monostate, edi::RelationsUndo, AddedExperiments>;
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
    // A scan project's datasets: the listing, the results the driver wrote, the values read from each file once
    // shown, the dataset shown, and the template the dataset views are made from, kept until an edit makes the
    // shown state the template (edi ADR-0017 §19).
    bool scan_ = false;
    EvolutionViewModel* evolution_ = nullptr;
    QStringList scan_columns_;
    edi::ScanDatasets scan_datasets_;
    edi::ScanResults scan_results_;
    QHash<QString, QStringList> scan_extracted_;
    int current_dataset_ = -1;
    std::optional<edi::Project> scan_template_;
    bool applying_view_ = false;
    void loadScan();
    void viewDataset(int index);
    void syncDatasets();
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
