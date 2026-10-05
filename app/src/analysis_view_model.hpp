// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_ANALYSIS_VIEW_MODEL_HPP
#define EDI_APP_ANALYSIS_VIEW_MODEL_HPP

#include <QObject>
#include <QString>
#include <QStringList>
#include <QtQml/qqmlregistration.h>

#include "block_text.hpp"
#include "category_list_model.hpp"
#include "edi/model.hpp"
#include "option_list_model.hpp"
#include "project_editor.hpp"
#include "row_table_model.hpp"

namespace edi_app {

class ProjectEditor;

// The joint-fit weights, in every mode (they act in joint mode): roles `experiment`, `weight`.
class JointWeightListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to the analysis")

   public:
    JointWeightListModel(edi::Project& project, QObject* parent);
    void sync();

   private:
    edi::Project& project_;
};

// The declared `_sequential_fit` block (scan modes), read-only. The scan's extraction rules
// (`_sequential_fit_extract`, read-only like the scan declaration): `id`,
// `target`, `pattern` and `required` (a loop is a table).
class SequentialExtractListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to the analysis")

   public:
    SequentialExtractListModel(const edi::Project& project, QObject* parent);
    void sync();

   private:
    const edi::Project& project_;
};

// The declared parameter aliases (`_alias`): `id`, editable as text, and `parameter`, the unique name of
// the parameter it stands for, chosen from `parameterNames`; append, duplicate and remove as the atom sites
// do.
class AliasListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to the analysis")
    // Every refinable parameter of the project, by unique name, in the slot walk's order.
    Q_PROPERTY(QStringList parameterNames READ parameterNames NOTIFY parameterNamesChanged)

   public:
    AliasListModel(edi::Project& project, ProjectEditor& editor, QObject* parent);
    void sync();
    QStringList parameterNames() const { return parameter_names_; }
    Q_INVOKABLE bool setText(int row, const QString& role, const QString& value);
    Q_INVOKABLE void append();
    Q_INVOKABLE void duplicate(int row);
    Q_INVOKABLE void remove(int row);

   signals:
    void parameterNamesChanged();

   protected:
    bool setRole(int row, const QString& role, const QVariant& value) override { return setText(row, role, value.toString()); }

   private:
    edi::Project& project_;
    ProjectEditor& editor_;
    QStringList parameter_names_;
};

// The declared constraints (`_constraint`): `id` and `expression`, editable as text, and `enabled` (a
// disabled constraint stays in the project and is not applied); append, duplicate and remove as the
// aliases.
class ConstraintListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to the analysis")

   public:
    ConstraintListModel(edi::Project& project, ProjectEditor& editor, QObject* parent);
    void sync();
    Q_INVOKABLE bool setText(int row, const QString& role, const QString& value);
    Q_INVOKABLE bool setEnabled(int row, bool enabled);
    Q_INVOKABLE void append();
    Q_INVOKABLE void duplicate(int row);
    Q_INVOKABLE void remove(int row);

   protected:
    bool setRole(int row, const QString& role, const QVariant& value) override;

   private:
    edi::Project& project_;
    ProjectEditor& editor_;
};

// The persisted pre-fit start state (`_fit_parameter`, read-only: a fit writes it, undo restores it):
// `id`, `startValue` and `startUncertainty` (undefined when the row has none) —.
class FitStartListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to the analysis")

   public:
    FitStartListModel(const edi::Project& project, QObject* parent);
    void sync();

   private:
    const edi::Project& project_;
};

class SequentialFitViewModel : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to the analysis")
    Q_PROPERTY(bool declared READ declared NOTIFY declaredChanged)
    Q_PROPERTY(QString dataDir READ dataDir NOTIFY dataDirChanged)
    Q_PROPERTY(QString filePattern READ filePattern NOTIFY filePatternChanged)
    Q_PROPERTY(bool reverse READ reverse NOTIFY reverseChanged)
    Q_PROPERTY(int extractRules READ extractRules NOTIFY extractRulesChanged)

   public:
    SequentialFitViewModel(const edi::Project& project, QObject* parent);
    bool declared() const { return declared_; }
    QString dataDir() const { return data_dir_; }
    QString filePattern() const { return file_pattern_; }
    bool reverse() const { return reverse_; }
    int extractRules() const { return extract_rules_; }
    void sync();

   signals:
    void declaredChanged();
    void dataDirChanged();
    void filePatternChanged();
    void reverseChanged();
    void extractRulesChanged();

   private:
    const edi::Project& project_;
    bool declared_ = false, reverse_ = false;
    QString data_dir_, file_pattern_;
    int extract_rules_ = 0;
};

// The analysis block: the fitting mode and descent selectors, the one-entry minimizer, the
// declared minimizer conditions.
class AnalysisViewModel : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a project")
    Q_PROPERTY(QString fittingMode READ fittingMode WRITE setFittingMode NOTIFY fittingModeChanged)
    Q_PROPERTY(edi_app::OptionListModel* fittingModeOptions READ fittingModeOptions CONSTANT)
    Q_PROPERTY(QString descent READ descent WRITE setDescent NOTIFY descentChanged)
    Q_PROPERTY(edi_app::OptionListModel* descentOptions READ descentOptions CONSTANT)
    Q_PROPERTY(QString minimizerType READ minimizerType CONSTANT)
    Q_PROPERTY(edi_app::OptionListModel* minimizerTypeOptions READ minimizerTypeOptions CONSTANT)
    Q_PROPERTY(int maxIterations READ maxIterations WRITE setMaxIterations NOTIFY maxIterationsChanged)
    Q_PROPERTY(bool hasMaxIterations READ hasMaxIterations NOTIFY hasMaxIterationsChanged)
    Q_PROPERTY(double chiSquareTolerance READ chiSquareTolerance WRITE setChiSquareTolerance NOTIFY chiSquareToleranceChanged)
    Q_PROPERTY(bool hasChiSquareTolerance READ hasChiSquareTolerance NOTIFY hasChiSquareToleranceChanged)
    // The tolerance a fit uses when none is declared: crysta's default.
    Q_PROPERTY(double defaultChiSquareTolerance READ defaultChiSquareTolerance CONSTANT)
    // The iteration bound a fit uses when none is declared, shown as the tolerance's.
    Q_PROPERTY(int defaultMaxIterations READ defaultMaxIterations CONSTANT)
    Q_PROPERTY(edi_app::JointWeightListModel* jointWeights READ jointWeights CONSTANT)
    Q_PROPERTY(edi_app::SequentialFitViewModel* sequentialFit READ sequentialFit CONSTANT)
    Q_PROPERTY(edi_app::SequentialExtractListModel* sequentialExtract READ sequentialExtract CONSTANT)
    Q_PROPERTY(edi_app::FitStartListModel* fitStart READ fitStart CONSTANT)
    Q_PROPERTY(edi_app::AliasListModel* aliases READ aliases CONSTANT)
    Q_PROPERTY(edi_app::ConstraintListModel* constraints READ constraints CONSTANT)
    Q_PROPERTY(edi_app::CategoryListModel* categories READ categories CONSTANT)
    Q_PROPERTY(edi_app::BlockText* text READ text CONSTANT)
    Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)

   public:
    AnalysisViewModel(edi::Project& project, ProjectEditor& editor, SavedFile saved, QObject* parent);

    QString fittingMode() const { return fitting_mode_; }
    void setFittingMode(const QString& mode);
    OptionListModel* fittingModeOptions() const { return fitting_mode_options_; }
    QString descent() const { return descent_; }
    void setDescent(const QString& id);
    OptionListModel* descentOptions() const { return descent_options_; }
    QString minimizerType() const;
    OptionListModel* minimizerTypeOptions() const { return minimizer_type_options_; }
    int maxIterations() const { return max_iterations_; }
    void setMaxIterations(int bound);
    bool hasMaxIterations() const { return max_iterations_ > 0; }
    double chiSquareTolerance() const { return chi_square_tolerance_; }
    void setChiSquareTolerance(double tolerance);
    bool hasChiSquareTolerance() const { return chi_square_tolerance_ > 0.0; }
    double defaultChiSquareTolerance() const { return edi::default_chi_square_tolerance(); }
    int defaultMaxIterations() const { return edi::default_max_iterations(); }
    JointWeightListModel* jointWeights() const { return joint_weights_; }
    SequentialFitViewModel* sequentialFit() const { return sequential_fit_; }
    SequentialExtractListModel* sequentialExtract() const { return sequential_extract_; }
    FitStartListModel* fitStart() const { return fit_start_; }
    AliasListModel* aliases() const { return aliases_; }
    ConstraintListModel* constraints() const { return constraints_; }
    CategoryListModel* categories() const { return categories_; }
    BlockText* text() const { return text_; }
    QString lastError() const { return last_error_; }
    void sync();

   signals:
    void fittingModeChanged();
    void descentChanged();
    void maxIterationsChanged();
    void hasMaxIterationsChanged();
    void chiSquareToleranceChanged();
    void hasChiSquareToleranceChanged();
    void lastErrorChanged();

   private:
    void syncFittingModeOptions();
    bool scan_declared_ = false;
    void setLastError(const QString& error);

    edi::Project& project_;
    ProjectEditor& editor_;
    QString fitting_mode_, descent_, last_error_;
    int max_iterations_ = 0;
    double chi_square_tolerance_ = 0.0;
    OptionListModel* fitting_mode_options_;
    OptionListModel* descent_options_;
    OptionListModel* minimizer_type_options_;
    JointWeightListModel* joint_weights_;
    SequentialFitViewModel* sequential_fit_;
    SequentialExtractListModel* sequential_extract_;
    FitStartListModel* fit_start_;
    AliasListModel* aliases_;
    ConstraintListModel* constraints_;
    CategoryListModel* categories_;
    BlockText* text_;
};

}  // namespace edi_app

#endif  // EDI_APP_ANALYSIS_VIEW_MODEL_HPP
