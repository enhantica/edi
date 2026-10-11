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
// the `maxParameters` most correlated; a pair weaker than `level` is left blank.
class CorrelationViewModel : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a project")
    // The shown parameters' unique names, rows and columns alike.
    Q_PROPERTY(QStringList labels READ labels NOTIFY labelsChanged)
    // The cells, row by row over `labels`: a coefficient below the diagonal, NaN where nothing is drawn.
    Q_PROPERTY(QList<qreal> values READ values NOTIFY valuesChanged)
    // The parameters the shown experiment's correlations name: the most `maxParameters` can show.
    Q_PROPERTY(int available READ available NOTIFY availableChanged)
    // Why nothing is drawn; empty when the matrix is.
    Q_PROPERTY(QString emptyText READ emptyText NOTIFY emptyTextChanged)
    // The smallest absolute correlation shown, 0 to 1.
    Q_PROPERTY(double level READ level WRITE setLevel NOTIFY levelChanged)
    // The most parameters shown, at least 2.
    Q_PROPERTY(int maxParameters READ maxParameters WRITE setMaxParameters NOTIFY maxParametersChanged)

   public:
    // diffraction-lib's default parameter count (DEFAULT_CORRELATION_MAX_PARAMETERS).
    static constexpr int kDefaultMaxParameters = 5;

    explicit CorrelationViewModel(QObject* parent);

    // The project's last fit and the shown experiment (its index, and whether the last fit included it), after
    // every publication and every change of the shown experiment.
    void setRecord(const edi::Project& project, int experiment, bool fitted);

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
    void rebuild();

    // The shown experiment's correlations: the parameters in the fit's order and the full matrix over them
    // (row-major, 1 on the diagonal).
    std::vector<std::string> names_;
    std::vector<double> matrix_;
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
