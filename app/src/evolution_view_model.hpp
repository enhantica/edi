// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_EVOLUTION_VIEW_MODEL_HPP
#define EDI_APP_EVOLUTION_VIEW_MODEL_HPP

#include <QObject>
#include <QPointer>
#include <QString>
#include <QStringList>
#include <QtQml/qqmlregistration.h>
#include <optional>
#include <string>
#include <vector>

#include "edi/scan.hpp"
#include "scan_session.hpp"
#include "measured_layer.hpp"
#include "row_table_model.hpp"

namespace edi_app {

// The parameters a scan's results record, for the Evolution tab's selector: roles `name` (the results column,
// a diffraction-lib unique name) and `label` (the same, as the selector shows it).
class EvolutionParameterListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to the evolution view")

   public:
    explicit EvolutionParameterListModel(QObject* parent);
    void setNames(const QStringList& names);
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
    Q_PROPERTY(QStringList xModes READ xModes CONSTANT)
    Q_PROPERTY(QString xTitle READ xTitle NOTIFY xTitleChanged)
    Q_PROPERTY(QString yTitle READ yTitle NOTIFY yTitleChanged)
    Q_PROPERTY(double xMin READ xMin NOTIFY xMinChanged)
    Q_PROPERTY(double xMax READ xMax NOTIFY xMaxChanged)
    Q_PROPERTY(double yMin READ yMin NOTIFY yMinChanged)
    Q_PROPERTY(double yMax READ yMax NOTIFY yMaxChanged)
    Q_PROPERTY(int count READ count NOTIFY countChanged)
    // The template changed after these results were written (FitViewModel::outOfDate).
    Q_PROPERTY(bool outOfDate READ outOfDate NOTIFY outOfDateChanged)
    // The layer the points are drawn on (the chart's).
    Q_PROPERTY(edi_app::MeasuredLayer* layer READ layer WRITE setLayer NOTIFY layerChanged)

   public:
    static constexpr int kThinningLimit = 5000;

    explicit EvolutionViewModel(QObject* parent);

    // The scan's results (the session's index and the project they belong to) and its first extract rule's title,
    // after a load or a refresh: the chart reads the selected parameter's column from the file. Neither is copied.
    void setScan(const ScanSession* session, const edi::Project* project, const QString& extracted_title);
    // A row a run just appended: its point joins the chart without reading the file again.
    void addRow(int dataset, const std::vector<std::string>& cells);

    EvolutionParameterListModel* parameters() const { return parameters_; }
    int currentParameter() const { return current_; }
    void setCurrentParameter(int index);
    int xMode() const { return x_mode_; }
    void setXMode(int mode);
    QStringList xModes() const;
    QString xTitle() const;
    QString yTitle() const;
    double xMin() const { return x_min_; }
    double xMax() const { return x_max_; }
    double yMin() const { return y_min_; }
    double yMax() const { return y_max_; }
    int count() const { return static_cast<int>(points_.size()); }
    bool outOfDate() const { return out_of_date_; }
    void setOutOfDate(bool out_of_date);
    MeasuredLayer* layer() const { return layer_; }
    void setLayer(MeasuredLayer* layer);

    // The dataset (its place in the scan) of the drawn point nearest to (x, y) in data units, within the given
    // distances, or -1.
    Q_INVOKABLE int datasetAt(double x, double y, double x_tolerance, double y_tolerance) const;
    // The x of a dataset's drawn point, or NaN when it has none.
    Q_INVOKABLE double datasetX(int dataset) const;
    // Whether the next datasetAt picks: a pointer gesture that is not a plain left click (a drag, a right click) turns
    // it off, so it selects nothing.
    Q_INVOKABLE void setPicking(bool picking) { picking_ = picking; }

   signals:
    void currentParameterChanged();
    void xModeChanged();
    void xTitleChanged();
    void yTitleChanged();
    void xMinChanged();
    void xMaxChanged();
    void yMinChanged();
    void yMaxChanged();
    void countChanged();
    void outOfDateChanged();
    void layerChanged();

   private:
    // Lists the recorded parameters again; whether the list changed. The shown one stays, else the first.
    bool syncNames();
    // Thins the points above the drawing limit (per x bucket the lowest and the highest).
    void thin();
    int published_count_ = 0;
    bool picking_ = true;
    struct Point {
        double x = 0.0, y = 0.0, error = 0.0;
        int dataset = -1;
    };
    void rebuild();
    void draw();

    EvolutionParameterListModel* parameters_;
    QPointer<MeasuredLayer> layer_;
    QStringList names_;
    QString extracted_title_;
    const ScanSession* session_ = nullptr;
    const edi::Project* project_ = nullptr;
    std::vector<Point> points_;
    // The x of a dataset: its first extracted value, or its place in the scan from 1; nullopt when not finite.
    std::optional<double> xOf(int dataset, const std::vector<std::string>* extracted) const;
    void finish();
    int current_ = -1;
    int x_mode_ = 0;
    bool out_of_date_ = false;
    double x_min_ = 0.0, x_max_ = 1.0, y_min_ = 0.0, y_max_ = 1.0;
};

}  // namespace edi_app

#endif  // EDI_APP_EVOLUTION_VIEW_MODEL_HPP
