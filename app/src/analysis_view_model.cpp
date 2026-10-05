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

// ---- AliasListModel -----------------------------------------------------------------------------

namespace {
template <typename Row>
bool holds_id(const edi::ItemVec<Row>& rows, const std::string& id) {
    for (const auto& row : rows) {
        if (row->id.value() == id) {
            return true;
        }
    }
    return false;
}
}  // namespace

AliasListModel::AliasListModel(edi::Project& project, ProjectEditor& editor, QObject* parent)
    : RowTableModel({"id", "parameter"}, parent), project_(project), editor_(editor) {
    sync();
}

void AliasListModel::sync() {
    QList<Row> rows;
    for (const auto& alias : project_.aliases) {
        rows.append({alias.get(),
                     {QString::fromStdString(alias->id.value()),
                      QString::fromStdString(alias->parameter_unique_name.value())}});
    }
    setTableRows(rows);
    QStringList names;
    for (const edi::NamedParameter& named : edi::named_parameters(project_)) {
        names.append(QString::fromStdString(named.unique_name));
    }
    if (names != parameter_names_) {
        parameter_names_ = names;
        emit parameterNamesChanged();
    }
}

bool AliasListModel::setText(int row, const QString& role, const QString& value) {
    auto* alias = const_cast<edi::ParameterAlias*>(static_cast<const edi::ParameterAlias*>(keyAt(row)));
    if (alias == nullptr) {
        return false;
    }
    const std::string text = value.toStdString();
    if (role == QLatin1String("id")) {
        return editor_.apply_relation_edit(edi::Edit::rename_alias(*alias, text)).isEmpty();
    }
    if (role == QLatin1String("parameter")) {
        return editor_.apply_relation_edit(edi::Edit::assign(alias->parameter_unique_name, text)).isEmpty();
    }
    return false;
}

void AliasListModel::append() {
    edi::Project& project = project_;
    edi::ParameterAlias alias;
    alias.id = unused_name("alias_", [&project](const std::string& id) { return holds_id(project.aliases, id); });
    // The first parameter no alias names yet, else the first parameter.
    for (const edi::NamedParameter& named : edi::named_parameters(project)) {
        bool aliased = false;
        for (const auto& existing : project.aliases) {
            aliased = aliased || existing->parameter_unique_name.value() == named.unique_name;
        }
        if (!aliased) {
            alias.parameter_unique_name = named.unique_name;
            break;
        }
    }
    editor_.apply_relation_edit(edi::Edit::append(project.aliases, std::move(alias)));
}

void AliasListModel::duplicate(int row) {
    const auto* source = static_cast<const edi::ParameterAlias*>(keyAt(row));
    if (source == nullptr) {
        return;
    }
    edi::Project& project = project_;
    edi::ParameterAlias copy = *source;
    copy.id = unused_name(source->id.value() + "_", [&project](const std::string& id) { return holds_id(project.aliases, id); });
    editor_.apply_relation_edit(edi::Edit::append(project.aliases, std::move(copy)));
}

void AliasListModel::remove(int row) {
    if (keyAt(row) == nullptr) {
        return;
    }
    edi::Project& project = project_;
    editor_.apply_relation_edit(edi::Edit::erase(project.aliases, static_cast<std::size_t>(row)));
}

// ---- ConstraintListModel ------------------------------------------------------------------------

ConstraintListModel::ConstraintListModel(edi::Project& project, ProjectEditor& editor, QObject* parent)
    : RowTableModel({"id", "expression", "enabled"}, parent), project_(project), editor_(editor) {
    sync();
}

void ConstraintListModel::sync() {
    QList<Row> rows;
    for (const auto& constraint : project_.constraints) {
        rows.append({constraint.get(),
                     {QString::fromStdString(constraint->id.value()),
                      QString::fromStdString(constraint->expression.value()), constraint->enabled.get()}});
    }
    setTableRows(rows);
}

bool ConstraintListModel::setRole(int row, const QString& role, const QVariant& value) {
    return role == QLatin1String("enabled") ? setEnabled(row, value.toBool()) : setText(row, role, value.toString());
}

bool ConstraintListModel::setText(int row, const QString& role, const QString& value) {
    auto* constraint =
        const_cast<edi::ParameterConstraint*>(static_cast<const edi::ParameterConstraint*>(keyAt(row)));
    if (constraint == nullptr) {
        return false;
    }
    const std::string text = value.toStdString();
    if (role == QLatin1String("id")) {
        return editor_.apply_relation_edit(edi::Edit::rename_constraint(*constraint, text)).isEmpty();
    }
    if (role == QLatin1String("expression")) {
        return editor_.apply_relation_edit(edi::Edit::assign(constraint->expression, text)).isEmpty();
    }
    return false;
}

bool ConstraintListModel::setEnabled(int row, bool enabled) {
    auto* constraint =
        const_cast<edi::ParameterConstraint*>(static_cast<const edi::ParameterConstraint*>(keyAt(row)));
    if (constraint == nullptr) {
        return false;
    }
    return editor_.apply_relation_edit(edi::Edit::assign(constraint->enabled, enabled)).isEmpty();
}

void ConstraintListModel::append() {
    edi::Project& project = project_;
    edi::ParameterConstraint constraint;
    constraint.id =
        unused_name("constraint_", [&project](const std::string& id) { return holds_id(project.constraints, id); });
    // A starting expression from the first two aliases, for the user to edit.
    if (project.aliases.size() >= 2) {
        constraint.expression = project.aliases[1]->id.value() + " = " + project.aliases[0]->id.value();
    }
    editor_.apply_relation_edit(edi::Edit::append(project.constraints, std::move(constraint)));
}

void ConstraintListModel::duplicate(int row) {
    const auto* source = static_cast<const edi::ParameterConstraint*>(keyAt(row));
    if (source == nullptr) {
        return;
    }
    edi::Project& project = project_;
    edi::ParameterConstraint copy = *source;
    copy.id = unused_name(source->id.value() + "_",
                          [&project](const std::string& id) { return holds_id(project.constraints, id); });
    editor_.apply_relation_edit(edi::Edit::append(project.constraints, std::move(copy)));
}

void ConstraintListModel::remove(int row) {
    if (keyAt(row) == nullptr) {
        return;
    }
    edi::Project& project = project_;
    editor_.apply_relation_edit(edi::Edit::erase(project.constraints, static_cast<std::size_t>(row)));
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
      aliases_(new AliasListModel(project, editor, this)),
      constraints_(new ConstraintListModel(project, editor, this)),
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
    aliases_->sync();
    constraints_->sync();
    categories_->setCategories(edi::analysis_categories(project_));
}

}  // namespace edi_app
