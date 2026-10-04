// SPDX-License-Identifier: BSD-3-Clause
#include "analysis_view_model.hpp"

#include "edi/categories.hpp"
#include "edi/edits.hpp"
#include "edi/selectors.hpp"
#include "project_editor.hpp"

namespace edi_app {

// ---- JointWeightListModel -----------------------------------------------------------------------

JointWeightListModel::JointWeightListModel(edi::Project& project, QObject* parent)
    : RowTableModel({"experiment", "weight"}, parent), project_(project) {
    sync();
}

void JointWeightListModel::sync() {
    // Every mode: the writer writes the joint weights in each, so they are a table in each; they act in
    // joint mode.
    QList<Row> rows;
    for (const auto& experiment : project_.experiments) {
        rows.append({experiment.get(), {QString::fromStdString(experiment->name), experiment->dataset_weight}});
    }
    setTableRows(rows);
}

// ---- SequentialExtractListModel -----------------------------------------------------------------

SequentialExtractListModel::SequentialExtractListModel(const edi::Project& project, QObject* parent)
    : RowTableModel({"id", "target", "pattern", "required"}, parent), project_(project) {
    sync();
}

void SequentialExtractListModel::sync() {
    QList<Row> rows;
    // The rules are the collection's shared items, keyed by their unique id; a row is keyed by the
    // item itself, so it keeps its identity across syncs.
    for (const auto& rule : project_.sequential_fit.extract) {
        rows.append({rule.get(),
                     {QString::fromStdString(rule->id.value()), QString::fromStdString(rule->target.value()),
                      QString::fromStdString(rule->pattern.value()), rule->required.get()}});
    }
    setTableRows(rows);
}

// ---- FitStartListModel --------------------------------------------------------------------------

FitStartListModel::FitStartListModel(const edi::Project& project, QObject* parent)
    : RowTableModel({"id", "startValue", "startUncertainty"}, parent), project_(project) {
    sync();
}

void FitStartListModel::sync() {
    QList<Row> rows;
    for (const edi::FitStartRow& start : edi::fit_start_rows(project_)) {
        const edi::Parameter& parameter = *start.parameter;
        rows.append({start.parameter,
                     {QString::fromStdString(start.id), parameter.start_value.value_or(0.0),
                      parameter.start_uncertainty ? QVariant(*parameter.start_uncertainty) : QVariant()}});
    }
    setTableRows(rows);
}

// ---- SequentialFitViewModel ---------------------------------------------------------------------

SequentialFitViewModel::SequentialFitViewModel(const edi::Project& project, QObject* parent)
    : QObject(parent), project_(project) {
    sync();
}

void SequentialFitViewModel::sync() {
    const edi::SequentialFitConfig& fit = project_.sequential_fit;
    const auto update = [this](auto& member, const auto& value, void (SequentialFitViewModel::*signal)()) {
        if (member != value) {
            member = value;
            emit(this->*signal)();
        }
    };
    update(declared_, fit.declared(), &SequentialFitViewModel::declaredChanged);
    update(data_dir_, QString::fromStdString(fit.data_dir), &SequentialFitViewModel::dataDirChanged);
    update(file_pattern_, QString::fromStdString(fit.file_pattern), &SequentialFitViewModel::filePatternChanged);
    update(reverse_, fit.reverse, &SequentialFitViewModel::reverseChanged);
    update(extract_rules_, static_cast<int>(fit.extract.size()), &SequentialFitViewModel::extractRulesChanged);
}

// ---- AnalysisViewModel --------------------------------------------------------------------------

AnalysisViewModel::AnalysisViewModel(edi::Project& project, ProjectEditor& editor, SavedFile saved, QObject* parent)
    : QObject(parent),
      project_(project),
      editor_(editor),
      fitting_mode_options_(new OptionListModel(this)),
      descent_options_(new OptionListModel(this)),
      minimizer_type_options_(new OptionListModel(this)),
      joint_weights_(new JointWeightListModel(project, this)),
      sequential_fit_(new SequentialFitViewModel(project, this)),
      sequential_extract_(new SequentialExtractListModel(project, this)),
      fit_start_(new FitStartListModel(project, this)),
      categories_(new CategoryListModel(this)),
      text_(new BlockText([saved] { return saved("analysis/analysis.edi"); }, this)) {
    fitting_mode_options_->setOptions(edi::supported_fitting_modes(), "single");
    descent_options_->setOptions(edi::supported_descents(), edi::default_descent());
    minimizer_type_options_->setOptions(edi::supported_minimizer_types());
    sync();
}

QString AnalysisViewModel::minimizerType() const {
    // The engine that runs: crysta is the only one; another declared value is kept in the model and
    // warned about at load.
    return minimizer_type_options_->tokenAt(0);
}

void AnalysisViewModel::setFittingMode(const QString& mode) {
    if (mode == fitting_mode_) {
        return;
    }
    edi::Project& project = project_;
    setLastError(editor_.apply(edi::Edit::fitting_mode(project, mode.toStdString()), false));
}

void AnalysisViewModel::setDescent(const QString& id) {
    if (id == descent_) {
        return;
    }
    edi::Project& project = project_;
    setLastError(editor_.apply(edi::Edit::descent(project, id.toStdString()), false));
}

void AnalysisViewModel::setMaxIterations(int bound) {
    edi::Project& project = project_;
    setLastError(editor_.apply(edi::Edit::max_iterations(project, bound), false));
}

void AnalysisViewModel::setChiSquareTolerance(double tolerance) {
    edi::Project& project = project_;
    setLastError(editor_.apply(edi::Edit::chi_square_tolerance(project, tolerance), false));
}

void AnalysisViewModel::setLastError(const QString& error) {
    if (error != last_error_) {
        last_error_ = error;
        emit lastErrorChanged();
    }
}

void AnalysisViewModel::sync() {
    const QString mode = QString::fromStdString(edi::effective_fitting_mode(project_));
    if (mode != fitting_mode_) {
        fitting_mode_ = mode;
        emit fittingModeChanged();
    }
    const QString descent = QString::fromStdString(project_.descent.empty() ? edi::default_descent() : project_.descent);
    if (descent != descent_) {
        descent_ = descent;
        emit descentChanged();
    }
    if (project_.minimizer_max_iterations != max_iterations_) {
        const bool had = hasMaxIterations();
        max_iterations_ = project_.minimizer_max_iterations;
        emit maxIterationsChanged();
        if (had != hasMaxIterations()) {
            emit hasMaxIterationsChanged();
        }
    }
    if (project_.minimizer_chi_square_tolerance != chi_square_tolerance_) {
        const bool had = hasChiSquareTolerance();
        chi_square_tolerance_ = project_.minimizer_chi_square_tolerance;
        emit chiSquareToleranceChanged();
        if (had != hasChiSquareTolerance()) {
            emit hasChiSquareToleranceChanged();
        }
    }
    joint_weights_->sync();
    sequential_fit_->sync();
    sequential_extract_->sync();
    fit_start_->sync();
    categories_->setCategories(edi::analysis_categories(project_));
}

}  // namespace edi_app
