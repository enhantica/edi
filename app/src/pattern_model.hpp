// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_PATTERN_MODEL_HPP
#define EDI_APP_PATTERN_MODEL_HPP

#include <QAbstractListModel>
#include <QObject>
#include <QString>
#include <QtQml/qqmlregistration.h>

#include "edi/model.hpp"

namespace edi_app {

// The experiment's measured range: the data axis summarised, the step the nominal (max - min) / (n - 1)
// the original shows as "inc", and the smallest and largest step between neighbouring points, for "inc" to
// show a range when the steps differ (edi ADR-0017 §6).
class RangeViewModel : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to an experiment")
    Q_PROPERTY(double minimum READ minimum NOTIFY minimumChanged)
    Q_PROPERTY(double maximum READ maximum NOTIFY maximumChanged)
    Q_PROPERTY(double step READ step NOTIFY stepChanged)
    Q_PROPERTY(double stepMinimum READ stepMinimum NOTIFY stepMinimumChanged)
    Q_PROPERTY(double stepMaximum READ stepMaximum NOTIFY stepMaximumChanged)
    Q_PROPERTY(int points READ points NOTIFY pointsChanged)

   public:
    RangeViewModel(const edi::ExperimentBase& experiment, QObject* parent);
    double minimum() const { return minimum_; }
    double maximum() const { return maximum_; }
    double step() const { return step_; }
    double stepMinimum() const { return step_minimum_; }
    double stepMaximum() const { return step_maximum_; }
    int points() const { return points_; }
    void sync();

   signals:
    void minimumChanged();
    void maximumChanged();
    void stepChanged();
    void stepMinimumChanged();
    void stepMaximumChanged();
    void pointsChanged();

   private:
    const edi::ExperimentBase& experiment_;
    double minimum_ = 0.0, maximum_ = 0.0, step_ = 0.0, step_minimum_ = 0.0, step_maximum_ = 0.0;
    int points_ = 0;
};

// The experiment's pattern: the data axis and intensities exactly as the core holds them, the
// calculated one after each coalesced recalculation. Roles `x`,
// `intensityMeas`, `intensityMeasSu`, `intensityCalc`.
class PatternModel : public QAbstractListModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to an experiment")
    Q_PROPERTY(int count READ count NOTIFY countChanged)
    Q_PROPERTY(double xMin READ xMin NOTIFY xMinChanged)
    Q_PROPERTY(double xMax READ xMax NOTIFY xMaxChanged)
    Q_PROPERTY(AxisKind axisKind READ axisKind NOTIFY axisKindChanged)
    Q_PROPERTY(QString calculationError READ calculationError NOTIFY calculationErrorChanged)
    Q_PROPERTY(bool stale READ stale NOTIFY staleChanged)

   public:
    enum AxisKind { TwoTheta, TimeOfFlight };
    Q_ENUM(AxisKind)
    enum Role { XRole = Qt::UserRole + 1, IntensityMeasRole, IntensityMeasSuRole, IntensityCalcRole, DSpacingRole, IntensityBkgRole, CalcStatusRole, ResidualRole };

    PatternModel(const edi::ExperimentBase& experiment, QObject* parent);
    int count() const { return count_; }
    double xMin() const { return x_min_; }
    double xMax() const { return x_max_; }
    AxisKind axisKind() const { return axis_kind_; }
    QString calculationError() const { return calculation_error_; }
    bool stale() const { return stale_; }

    int rowCount(const QModelIndex& parent = QModelIndex()) const override;
    QVariant data(const QModelIndex& index, int role) const override;
    QHash<int, QByteArray> roleNames() const override;

    // The model changed and a recalculation is queued.
    void markStale();
    // A recalculation finished: the calculated intensities (or the refusal) are the core's now. Only
    // what changed signals: an experiment whose intensities are unchanged emits nothing.
    void calculated(const QString& error);

   signals:
    void countChanged();
    void xMinChanged();
    void xMaxChanged();
    void axisKindChanged();
    void calculationErrorChanged();
    void staleChanged();

   private:
    void readAxis();
    const edi::ExperimentBase& experiment_;
    int count_ = 0;
    double x_min_ = 0.0, x_max_ = 0.0;
    AxisKind axis_kind_ = TwoTheta;
    QString calculation_error_;
    bool stale_ = true;
    std::vector<double> published_d_, published_bkg_, published_residual_;
    std::vector<std::string> published_status_;
    std::vector<double> published_calc_;  // the intensities the views were last told about
};

}  // namespace edi_app

#endif  // EDI_APP_PATTERN_MODEL_HPP
