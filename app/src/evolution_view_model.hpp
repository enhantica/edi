// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_EVOLUTION_VIEW_MODEL_HPP
#define EDI_APP_EVOLUTION_VIEW_MODEL_HPP

#include <QHash>
#include <QObject>
#include <functional>
#include <QPointer>
#include <QString>
#include <QStringList>
#include <QTimer>
#include <QtQml/qqmlregistration.h>
#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "edi/scan.hpp"
#include "scan_session.hpp"
#include "measured_layer.hpp"
#include "row_table_model.hpp"

namespace edi_app {

// The parameters of the Evolution tab's selector: every free parameter, then any other one the scan's results
// record; roles `name` (the results column, a diffraction-lib unique name) and `label` (the same, as the selector
// shows it).
class EvolutionParameterListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to the evolution view")

   public:
    explicit EvolutionParameterListModel(QObject* parent);
    // Each parameter's results column (`name`) and what the selector shows for it (`label`): its name as the parameter
    // table shows it, else the column (the owner, 2026-11-16).
    void setNames(const QStringList& names, const QStringList& labels = {});
};

// The Evolution tab (edi ADR-0017 §19): one fitted parameter across a scan's datasets, read from
// `analysis/results.csv`. x is the first extract rule's value (with its unit) or the file's place in the scan; y the
// parameter's value with its uncertainty as an error bar. Above `kThinningLimit` points the chart draws a thinned
// set that keeps each bucket's lowest and highest point.
class EvolutionViewModel : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a project")
    Q_PROPERTY(edi_app::EvolutionParameterListModel* parameters READ parameters CONSTANT)
    Q_PROPERTY(int currentParameter READ currentParameter WRITE setCurrentParameter NOTIFY currentParameterChanged)
    // 0: x is the extracted value; 1: x is the file's place in the scan, from 1.
    Q_PROPERTY(int xMode READ xMode WRITE setXMode NOTIFY xModeChanged)
    // Whether the next datasetAt picks: a pointer gesture that is not a plain left click (a drag, a right click) turns
    // it off, so it selects nothing.
    Q_PROPERTY(bool picking READ picking WRITE setPicking NOTIFY pickingChanged)
    Q_PROPERTY(QStringList xModes READ xModes CONSTANT)
    Q_PROPERTY(QString xTitle READ xTitle NOTIFY xTitleChanged)
    Q_PROPERTY(QString yTitle READ yTitle NOTIFY yTitleChanged)
    // The y title as the parameter table names it (yTitle is the results column, the tooltip's full name).
    Q_PROPERTY(QString yLabel READ yLabel NOTIFY yLabelChanged)
    Q_PROPERTY(double xMin READ xMin NOTIFY xMinChanged)
    Q_PROPERTY(double xMax READ xMax NOTIFY xMaxChanged)
    Q_PROPERTY(double yMin READ yMin NOTIFY yMinChanged)
    Q_PROPERTY(double yMax READ yMax NOTIFY yMaxChanged)
    Q_PROPERTY(int count READ count NOTIFY countChanged)
    // The template changed after these results were written (FitViewModel::outOfDate).
    Q_PROPERTY(bool outOfDate READ outOfDate NOTIFY outOfDateChanged)
    // Some dataset of the scan has a row in its results: until then the chart has no axes.
    Q_PROPERTY(bool fitted READ fitted NOTIFY fittedChanged)
    // A series of joint fits (edi ADR-0089): its parameters Shared (results.csv, one row per point) or Per experiment
    // (results_experiments.csv), the latter for the experiment `currentExperiment` (a place in `experiments`), or at -1
    // for every bank, one curve each on its own layer (bankLayer; the owner, 2026-11-16).
    Q_PROPERTY(bool series READ series NOTIFY seriesChanged)
    Q_PROPERTY(bool perExperiment READ perExperiment WRITE setPerExperiment NOTIFY perExperimentChanged)
    Q_PROPERTY(QStringList experiments READ experiments NOTIFY experimentsChanged)
    Q_PROPERTY(int currentExperiment READ currentExperiment WRITE setCurrentExperiment NOTIFY currentExperimentChanged)
    // The layer the points are drawn on (the chart's).
    Q_PROPERTY(edi_app::MeasuredLayer* layer READ layer WRITE setLayer NOTIFY layerChanged)

   public:
    static constexpr int kThinningLimit = 5000;

    explicit EvolutionViewModel(QObject* parent);

    // The scan's results (the session's index and the project they belong to) and its first extract rule's title,
    // after a load or a refresh: the chart reads the selected parameter's column from the file. Neither is copied.
    void setScan(const ScanSession* session, const edi::Project* project, const QString& extracted_title);
    // A parametric fit's latest iterate (ADR-0107): the chosen parameter's every point redrawn from it, without s.u.
    // A parameter the iterate does not carry keeps its points. The fit's end or cancel rebuilds from the files.
    void showIterate(const edi::ParametricIterate& iterate);
    // A row a run just appended: its point joins the chart without reading the file again.
    void addRow(int dataset, const std::vector<std::string>& cells);
    // After an edit: a parameter freed or fixed joins or leaves the selector.
    void syncParameters();
    // The scan's template project, which holds the template's fit result and values (the shown model may be another
    // dataset's); null: the project given to setScan.
    void setTemplate(const edi::Project* project) { template_ = project; }

    EvolutionParameterListModel* parameters() const { return parameters_; }
    bool series() const { return !experiments_.isEmpty(); }
    bool perExperiment() const { return per_experiment_; }
    void setPerExperiment(bool on);
    QStringList experiments() const { return experiments_; }
    int currentExperiment() const { return current_experiment_; }
    void setCurrentExperiment(int index);
    int currentParameter() const { return current_; }
    void setCurrentParameter(int index);
    int xMode() const { return x_mode_; }
    void setXMode(int mode);
    QStringList xModes() const;
    QString xTitle() const;
    QString yTitle() const;
    QString yLabel() const;
    double xMin() const { return x_min_; }
    double xMax() const { return x_max_; }
    double yMin() const { return y_min_; }
    double yMax() const { return y_max_; }
    int count() const { return static_cast<int>(points_.size()); }
    bool outOfDate() const { return out_of_date_; }
    bool fitted() const { return fitted_; }
    void setOutOfDate(bool out_of_date);
    MeasuredLayer* layer() const { return layer_; }
    void setLayer(MeasuredLayer* layer);

    // The dataset (its place in the scan) of the drawn point nearest to (x, y) in data units, within the given
    // distances, or -1.
    Q_INVOKABLE int datasetAt(double x, double y, double x_tolerance, double y_tolerance) const;
    // The x of a dataset's drawn point, or NaN when it has none.
    Q_INVOKABLE double datasetX(int dataset) const;
    // How a results column reads in the selector, given whether it is a bank's own (the project's parameter names).
    void setLabeller(std::function<QString(const QString&, bool)> labeller) { labeller_ = std::move(labeller); }
    // The parameter a results column stands for (a bank's own with `bank`), for the selector's coloured name.
    void setFinder(std::function<QObject*(const QString&, bool)> finder) { finder_ = std::move(finder); }
    // The parameter of the selector's entry `index`; null for a column no parameter has (a derived value).
    Q_INVOKABLE QObject* parameterItem(int index) const {
        return finder_ && index >= 0 && index < names_.size() ? finder_(names_[index], per_experiment_) : nullptr;
    }
    // The layer bank `bank` is drawn on when every bank is shown; null unregisters it.
    Q_INVOKABLE void setBankLayer(int bank, edi_app::MeasuredLayer* layer);
    // The project's Evolution chart settings changed: the range and the drawing follow them.
    void viewSettingsChanged() { finish(); }
    bool picking() const { return picking_; }
    void setPicking(bool picking) {
        if (picking_ != picking) {
            picking_ = picking;
            emit pickingChanged();
        }
    }

   signals:
    // A reread of the results refused (the path is no longer a regular file): no point is drawn.
    void refused(const QString& message);
    void currentParameterChanged();
    void xModeChanged();
    void pickingChanged();
    void xTitleChanged();
    void yTitleChanged();
    void yLabelChanged();
    void xMinChanged();
    void xMaxChanged();
    void yMinChanged();
    void yMaxChanged();
    void countChanged();
    void outOfDateChanged();
    void fittedChanged();
    void seriesChanged();
    void experimentsChanged();
    void perExperimentChanged();
    void currentExperimentChanged();
    void layerChanged();

   private:
    // Lists the parameters again; whether the list changed. The shown one stays, else the first.
    bool syncNames();
    void syncFitted();
    // Thins the points above the drawing limit (per x bucket the lowest and the highest).
    void thin();
    int published_count_ = 0;
    bool picking_ = true;
    struct Point {
        double x = 0.0, y = 0.0, error = 0.0;
        int dataset = -1;
        int bank = -1;  // per bank with every bank shown: the bank's place
        friend bool operator==(const Point&, const Point&) = default;
    };
    // Before the scan has a fitted row: the fitted template's own point, its current value and s.u. at its dataset's
    // x, so a parameter can be chosen before the scan starts (the owner, 2026-11-04); none when the template has no
    // fit result or the scan has rows.
    std::optional<Point> templatePoint() const;
    bool scanRows() const;
    std::optional<Point> template_point_;
    void rebuild();
    // What a rebuild reads the points from, copied so a worker can read them (rebuild).
    struct Read {
        std::shared_ptr<const edi::Project> project;
        edi::ScanPlaces places;
        std::shared_ptr<const edi::ScanResultIndex> index;
        edi::ScanDatasets datasets;
        edi::SeriesBankRule rule;
        std::string name;
        bool by_value = false, per_experiment = false, all_banks = false;
        int experiment = -1;
        int leader = -1;  // a shared experiment parameter's leader experiment, else -1
    };
    // The points of a parameter's column, read from the results (throws when the read refuses).
    static std::vector<Point> readPoints(const Read& read);
    std::uint64_t rebuild_request_ = 0;
    bool rebuild_owed_ = false;  // a rebuild asked for while no chart showed the points (ADR-0102 rule 1)
    void draw();

    QHash<QString, int> shared_paths_;  // ADR-0089 point 1: path -> leader experiment
    EvolutionParameterListModel* parameters_;
    QPointer<MeasuredLayer> layer_;
    QList<QPointer<MeasuredLayer>> bank_layers_;
    bool allBanks() const { return per_experiment_ && current_experiment_ < 0; }
    QStringList names_;
    QStringList labels_;  // names_' labels, as the selector shows them
    std::function<QString(const QString&, bool)> labeller_;
    std::function<QObject*(const QString&, bool)> finder_;
    QStringList experiments_;  // a series of joint fits' experiments, in project order; empty otherwise
    bool per_experiment_ = false;
    int current_experiment_ = 0;
    void syncExperiments();
    QString extracted_title_;
    const ScanSession* session_ = nullptr;
    const edi::Project* project_ = nullptr;
    const edi::Project* template_ = nullptr;
    std::vector<Point> points_;
    // A running scan adds a point per fitted file, up to dozens a second with several fits at once: the chart is
    // redrawn for the first at once and then at most every kRowRedrawMs, the last always drawn (the owner, 2026-11-04).
    QTimer row_redraw_;
    bool row_redraw_due_ = false;
    void finishRow();
    // The x of a dataset: its first extracted value, or its place in the scan from 1; nullopt when not finite.
    std::optional<double> xOf(int dataset, const std::vector<std::string>* extracted) const;
    // Publishes the points; false when an observer deleted this view meanwhile (nothing may touch it then).
    bool finish();
    bool range_with_errors() const {
        return project_ != nullptr && project_->evolution_range.value_or("values") == "values_su";
    }
    int current_ = -1;
    int x_mode_ = 0;
    bool out_of_date_ = false;
    bool fitted_ = false;
    double x_min_ = 0.0, x_max_ = 1.0, y_min_ = 0.0, y_max_ = 1.0;
};

}  // namespace edi_app

#endif  // EDI_APP_EVOLUTION_VIEW_MODEL_HPP
