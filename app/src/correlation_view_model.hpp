// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_CORRELATION_VIEW_MODEL_HPP
#define EDI_APP_CORRELATION_VIEW_MODEL_HPP

#include <QList>
#include <QObject>
#include <QString>
#include <QStringList>
#include <QtQml/qqmlregistration.h>
#include <string>
#include <vector>

#include "edi/model.hpp"

namespace edi_app {

// The Correlations tab: the last fit's parameter correlations (edi::FitResultRecord::correlations) for the shown
// experiment, drawn as diffraction-lib draws its correlation heatmap (display/plotting.py plot_param_correlations):
// the lower triangle of the matrix over the parameters shown, in the fit's order, with the diagonal left blank.
// The shown experiment's parameters and the structures' are shown; another experiment's (a joint fit's other banks)
// are not. Of those, a parameter is shown when its strongest correlation with another reaches `level`, and of these
// the `maxParameters` most correlated; every pair among the shown parameters is drawn (owner, 2026-10-11). The two are one filter (owner,
// 2026-10-11): a level sets the count to the parameters reaching it, a count sets the level to the strongest
// correlation of the count-th most correlated parameter, and a new matrix keeps the count.
class CorrelationViewModel : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a project")
    // The shown parameters' unique names, rows and columns alike.
    Q_PROPERTY(QStringList labels READ labels NOTIFY labelsChanged)
    // The cells, row by row over `labels`: every finite coefficient below the diagonal, NaN where nothing is drawn.
    Q_PROPERTY(QList<qreal> values READ values NOTIFY valuesChanged)
    // The parameters the shown experiment's correlations name: the most `maxParameters` can show.
    Q_PROPERTY(int available READ available NOTIFY availableChanged)
    // Why nothing is drawn; empty when the matrix is.
    Q_PROPERTY(QString emptyText READ emptyText NOTIFY emptyTextChanged)
    // The smallest absolute correlation a shown parameter has with another, 0 to 1; setting it sets maxParameters.
    Q_PROPERTY(double level READ level WRITE setLevel NOTIFY levelChanged)
    // The most parameters shown, 2 to `available`; setting it sets level.
    Q_PROPERTY(int maxParameters READ maxParameters WRITE setMaxParameters NOTIFY maxParametersChanged)

   public:
    // diffraction-lib's default parameter count (DEFAULT_CORRELATION_MAX_PARAMETERS).
    static constexpr int kDefaultMaxParameters = 5;

    explicit CorrelationViewModel(QObject* parent);

    // The project's last fit and the shown experiment (its index, and whether the last fit included it), after
    // every publication and every change of the shown experiment.
    void setRecord(const edi::Project& project, int experiment, bool fitted);
    // A scan dataset's own correlations, from its file's fit (all its parameters are the template experiment's), and
    // why there are none when `absent` says so.
    void setPairs(const std::vector<edi::FitParameterCorrelation>& pairs, const QString& absent = {});
    // A scan dataset's correlations as its fit made them (ADR-0034): the matrix comes from the numbers.
    void setTable(const edi::CorrelationTable& table);

    QStringList labels() const { return labels_; }
    QList<qreal> values() const { return values_; }
    int available() const { return available_; }
    QString emptyText() const { return empty_text_; }
    double level() const { return level_; }
    void setLevel(double level);
    int maxParameters() const { return max_parameters_; }
    void setMaxParameters(int count);

   signals:
    void labelsChanged();
    void valuesChanged();
    void availableChanged();
    void emptyTextChanged();
    void levelChanged();
    void maxParametersChanged();

   private:
    // The level and the count, which edit each other, then the matrix they show.
    void apply(double level, int count);
    // The matrix of `pairs` without the parameters named under `hidden` prefixes; `reason` when fewer than two remain.
    void show(const std::vector<edi::FitParameterCorrelation>& pairs, const std::vector<std::string>& hidden,
              const QString& reason);
    // The strengths, the level and the count over the matrix just made; `reason` when it has fewer than two rows.
    void settle(const QString& reason);
    void rebuild();

    // The shown experiment's correlations: the parameters in the fit's order and the full matrix over them
    // (row-major, 1 on the diagonal).
    std::vector<std::string> names_;
    std::vector<double> matrix_;
    // Each parameter's strongest correlation with another, in the fit's order, and from the strongest down.
    std::vector<double> strength_;
    std::vector<double> ranked_;
    QString reason_;
    QStringList labels_;
    QList<qreal> values_;
    QString empty_text_;
    int available_ = 0;
    double level_ = 0.0;
    int max_parameters_ = kDefaultMaxParameters;
};

}  // namespace edi_app

#endif  // EDI_APP_CORRELATION_VIEW_MODEL_HPP
