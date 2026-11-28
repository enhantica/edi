// SPDX-License-Identifier: BSD-3-Clause
#include "analysis_view_model.hpp"

#include <set>
#include <charconv>
#include <array>
#include <map>
#include "run_log.hpp"

#include <QMetaObject>

#include <algorithm>
#include <stdexcept>
#include <string>
#include <vector>

#include "edi/categories.hpp"
#include "edi/display.hpp"
#include "parameter_item.hpp"
#include "parameter_registry.hpp"
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

SequentialExtractListModel::SequentialExtractListModel(edi::Project& project, ProjectEditor& editor, QObject* parent)
    : RowTableModel({"id", "target", "pattern", "required"}, parent), project_(project), editor_(editor) {
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

edi::SequentialExtractRule* SequentialExtractListModel::ruleAt(int row) const {
    return const_cast<edi::SequentialExtractRule*>(static_cast<const edi::SequentialExtractRule*>(keyAt(row)));
}

std::string SequentialExtractListModel::unusedName(const std::string& stem) const {
    return unused_name(stem, [this](const std::string& name) {
        const auto& rules = project_.sequential_fit.extract;
        return holds_id(rules, name) ||
               std::any_of(rules.begin(), rules.end(), [&name](const auto& rule) { return rule->target.value() == name; });
    });
}

bool SequentialExtractListModel::setRole(int row, const QString& role, const QVariant& value) {
    return role == QLatin1String("required") ? setRequired(row, value.toBool()) : setText(row, role, value.toString());
}

bool SequentialExtractListModel::setText(int row, const QString& role, const QString& value) {
    edi::SequentialExtractRule* rule = ruleAt(row);
    if (rule == nullptr) {
        return false;
    }
    const std::string text = value.toStdString();
    if (role == QLatin1String("id")) {
        return editor_.apply_extract_rules(edi::Edit::rename_extract_rule(*rule, text)).isEmpty();
    }
    if (role == QLatin1String("target")) {
        return editor_.apply_extract_rules(edi::Edit::extract_rule_target(project_, *rule, text)).isEmpty();
    }
    if (role == QLatin1String("pattern")) {
        return editor_.apply_extract_rules(edi::Edit::extract_rule_pattern(*rule, text)).isEmpty();
    }
    return false;
}

bool SequentialExtractListModel::setRequired(int row, bool required) {
    edi::SequentialExtractRule* rule = ruleAt(row);
    return rule != nullptr && editor_.apply_extract_rules(edi::Edit::assign(rule->required, required)).isEmpty();
}

void SequentialExtractListModel::append() {
    // A starting rule for the user to edit: the sample temperature, the value most scans follow, while no rule reads
    // it. Not required, so a file without a match is still read and fitted.
    edi::SequentialExtractRule rule;
    rule.id = unusedName("rule_");
    const auto& rules = project_.sequential_fit.extract;
    const std::string temperature = "diffrn.ambient_temperature";
    const bool read = std::any_of(rules.begin(), rules.end(),
                                  [&temperature](const auto& held) { return held->target.value() == temperature; });
    rule.target = read ? rule.id.value() : temperature;
    rule.pattern = "^TEMP\\s+([0-9.]+)";
    rule.required = false;
    editor_.apply_extract_rules(edi::Edit::append_extract_rule(project_, rule));
}

void SequentialExtractListModel::duplicate(int row) {
    const edi::SequentialExtractRule* source = ruleAt(row);
    if (source == nullptr) {
        return;
    }
    // Two rules cannot write one results column: the copy's target is the source's with a number, kept to the two parts
    // a target may have, whatever the rule's id is.
    edi::SequentialExtractRule copy = *source;
    copy.id = unusedName(source->id.value() + "_");
    std::string base = source->target.value();
    if (const auto last = base.rfind('.'); last != std::string::npos) {
        const auto before = base.rfind('.', last - 1);
        if (before != std::string::npos) base = base.substr(before + 1);
    }
    // A target loaded from a file may hold what the editor refuses (a reserved fit_result. prefix, a comma, a quote, a
    // space); the copy drops it, and falls back to a plain name when what is left still cannot be a target.
    std::erase_if(base, [](char c) { return c == ',' || c == '"' || c == ' ' || c == '\t'; });
    if (base.starts_with("fit_result.")) base = base.substr(std::string("fit_result.").size());
    copy.target = unusedName((base.empty() ? std::string("value") : base) + "_");
    try {
        edi::check_extract_target(project_, nullptr, copy.target.value());
    } catch (const std::invalid_argument&) {
        copy.target = unusedName("value_");
    }
    editor_.apply_extract_rules(edi::Edit::append_extract_rule(project_, copy));
}

void SequentialExtractListModel::remove(int row) {
    if (keyAt(row) == nullptr) {
        return;
    }
    editor_.apply_extract_rules(edi::Edit::erase_extract_rule(project_, static_cast<std::size_t>(row)));
}

// ---- AliasListModel -----------------------------------------------------------------------------

AliasListModel::AliasListModel(edi::Project& project, ProjectEditor& editor, QObject* parent)
    : RowTableModel({"id", "parameter"}, parent), project_(project), editor_(editor) {
    sync();
}

void AliasListModel::sync() {
    QList<Row> rows;
    const edi::ActiveView view(project_);  // the one view of what a disabled link hides (reviews 31 and 32)
    for (const edi::ParameterAlias* alias : view.aliases()) {
        rows.append({alias,
                     {QString::fromStdString(alias->id.value()),
                      QString::fromStdString(alias->parameter_unique_name.value())}});
    }
    setTableRows(rows);
    QStringList names;
    for (const edi::NamedParameter& named : edi::named_parameters(project_)) {
        if (view.shown(named.parameter)) names.append(QString::fromStdString(named.unique_name));
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
        return editor_.apply_relation_control(edi::Edit::rename_alias(*alias, text), {ProjectEditor::RelationAction::Kind::AliasId,alias,value}).isEmpty();
    }
    if (role == QLatin1String("parameter")) {
        return editor_.apply_relation_control(edi::Edit::assign(alias->parameter_unique_name, text), {ProjectEditor::RelationAction::Kind::AliasParameter,alias,value}).isEmpty();
    }
    return false;
}

void AliasListModel::append() {
    edi::Project& project = project_;
    edi::ParameterAlias alias;
    alias.id = unused_name("alias_", [&project](const std::string& id) { return holds_id(project.aliases, id); });
    // The first shown parameter no alias names yet (a disabled phase's are not offered; review 32).
    const edi::ActiveView view(project);
    for (const edi::NamedParameter& named : edi::named_parameters(project)) {
        if (!view.shown(named.parameter)) continue;
        bool aliased = false;
        for (const auto& existing : project.aliases) {
            aliased = aliased || existing->parameter_unique_name.value() == named.unique_name;
        }
        if (!aliased) {
            alias.parameter_unique_name = named.unique_name;
            break;
        }
    }
    editor_.apply_relation_control(edi::Edit::append(project.aliases, alias), {ProjectEditor::RelationAction::Kind::AliasAppend});
}

void AliasListModel::duplicate(int row) {
    const auto* source = static_cast<const edi::ParameterAlias*>(keyAt(row));
    if (source == nullptr) {
        return;
    }
    edi::Project& project = project_;
    edi::ParameterAlias copy = *source;
    copy.id = unused_name(source->id.value() + "_", [&project](const std::string& id) { return holds_id(project.aliases, id); });
    editor_.apply_relation_edit(edi::Edit::append(project.aliases, copy));
}

void AliasListModel::remove(int row) {
    if (keyAt(row) == nullptr) {
        return;
    }
    edi::Project& project = project_;
    // The row's own alias: the table leaves a disabled phase's out (review 31), so a row is not a project index.
    const auto at = std::find_if(project.aliases.begin(), project.aliases.end(),
                                 [this, row](const auto& alias) { return alias.get() == keyAt(row); });
    if (at == project.aliases.end()) return;
    const auto index = static_cast<std::size_t>(std::distance(project.aliases.begin(), at));
    editor_.apply_relation_control(edi::Edit::erase(project.aliases, index), {ProjectEditor::RelationAction::Kind::AliasRemove,keyAt(row)});
}

// ---- ConstraintListModel ------------------------------------------------------------------------

ConstraintListModel::ConstraintListModel(edi::Project& project, ProjectEditor& editor, QObject* parent)
    : RowTableModel({"id", "expression", "enabled"}, parent), project_(project), editor_(editor) {
    sync();
}

void ConstraintListModel::sync() {
    QList<Row> rows;
    for (const edi::ParameterConstraint* constraint : edi::ActiveView(project_).constraints()) {
        rows.append({constraint,
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
        return editor_.apply_relation_control(edi::Edit::rename_constraint(*constraint, text), {ProjectEditor::RelationAction::Kind::ConstraintId,constraint,value}).isEmpty();
    }
    if (role == QLatin1String("expression")) {
        return editor_.apply_relation_control(edi::Edit::constraint_expression(project_, *constraint, text), {ProjectEditor::RelationAction::Kind::ConstraintExpression,constraint,value}).isEmpty();
    }
    return false;
}

bool ConstraintListModel::setEnabled(int row, bool enabled) {
    auto* constraint =
        const_cast<edi::ParameterConstraint*>(static_cast<const edi::ParameterConstraint*>(keyAt(row)));
    if (constraint == nullptr) {
        return false;
    }
    return editor_.apply_relation_control(edi::Edit::constraint_enabled(project_, *constraint, enabled), {ProjectEditor::RelationAction::Kind::ConstraintEnabled,constraint,{},enabled}).isEmpty();
}

void ConstraintListModel::append() {
    edi::Project& project = project_;
    edi::ParameterConstraint constraint;
    constraint.id =
        unused_name("constraint_", [&project](const std::string& id) { return holds_id(project.constraints, id); });
    // A starting expression for the user to edit, from the first two aliases whose dependent no constraint
    // sets yet: one already set would be refused, and Append would then add nothing. With none free it starts
    // empty, as it does with fewer than two aliases. Appending applies it at once, so it must change no value:
    // the dependent equal to the first alias when they already agree, else equal to its own value, which the
    // user then edits.
    std::set<std::string> dependents;
    for (const auto& existing : project.constraints) {
        const std::string& text = existing->expression.value();
        const auto equals = text.find('=');
        if (equals == std::string::npos) continue;
        std::string left = text.substr(0, equals);
        left.erase(0, left.find_first_not_of(" \t"));
        left.erase(left.find_last_not_of(" \t") + 1);
        dependents.insert(left);
    }
    std::map<std::string, double> values;
    for (const edi::NamedParameter& named : edi::named_parameters(project)) values[named.unique_name] = named.parameter->value.get();
    // Only the aliases the table shows: a disabled phase's stay out of a new expression too (review 31).
    const std::vector<const edi::ParameterAlias*> shown = edi::ActiveView(project).aliases();
    for (std::size_t dependent = 1; dependent < shown.size() && constraint.expression.value().empty(); ++dependent) {
        const std::string& name = shown[dependent]->id.value();
        if (dependents.contains(name)) continue;
        const auto own = values.find(shown[dependent]->parameter_unique_name.value());
        const auto first = values.find(shown[0]->parameter_unique_name.value());
        if (own == values.end() || first == values.end() || own->second == first->second) {
            constraint.expression = name + " = " + shown[0]->id.value();
        } else {
            std::array<char, 32> text{};
            const auto written = std::to_chars(text.data(), text.data() + text.size(), own->second);
            constraint.expression = name + " = " + std::string(text.data(), written.ptr);
        }
    }
    (void)appendComplete(QString::fromStdString(constraint.id.value()),
                         QString::fromStdString(constraint.expression.value()), constraint.enabled.get());
}

ProjectEditor::RelationOutcome ConstraintListModel::appendComplete(const QString& id, const QString& expression, bool enabled) {
    edi::ParameterConstraint row; row.id=id.toStdString(); row.expression=expression.toStdString(); row.enabled=enabled;
    ProjectEditor::RelationAction action; action.kind=ProjectEditor::RelationAction::Kind::ConstraintAppend;
    action.text=id; action.expression=expression; action.enabled=enabled;
    return editor_.append_constraint(project_, std::move(row), action);
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
    editor_.apply_relation_edit(edi::Edit::append(project.constraints, copy));
}

void ConstraintListModel::remove(int row) {
    if (keyAt(row) == nullptr) {
        return;
    }
    edi::Project& project = project_;
    // The row's own constraint: the table leaves a disabled phase's out (review 31), so a row is not a project index.
    const auto at = std::find_if(project.constraints.begin(), project.constraints.end(),
                                 [this, row](const auto& constraint) { return constraint.get() == keyAt(row); });
    if (at == project.constraints.end()) return;
    const auto index = static_cast<std::size_t>(std::distance(project.constraints.begin(), at));
    editor_.apply_relation_control(edi::Edit::erase(project.constraints, index), {ProjectEditor::RelationAction::Kind::ConstraintRemove,keyAt(row)});
}

// ---- FitStartListModel --------------------------------------------------------------------------

FitStartListModel::FitStartListModel(const edi::Project& project, QObject* parent)
    : RowTableModel({"id", "startValue", "startUncertainty", "parameter"}, parent), project_(project) {
    sync();
}

void FitStartListModel::setRegistry(const ParameterRegistry* registry) {
    registry_ = registry;
    sync();
}

void FitStartListModel::sync() {
    QList<Row> rows;
    const std::vector<const edi::Parameter*> hidden = const_cast<edi::Project&>(project_).hidden_parameters();
    for (const edi::FitStartRow& start : edi::fit_start_rows(project_)) {
        // A disabled linked structure's or link's parameter is in no view (owner decision 2026-11-27).
        if (std::find(hidden.begin(), hidden.end(), start.parameter) != hidden.end()) continue;
        const edi::Parameter& parameter = *start.parameter;
        rows.append({start.parameter,
                     {QString::fromStdString(start.id), parameter.start_value.value_or(0.0),
                      parameter.start_uncertainty ? QVariant(*parameter.start_uncertainty) : QVariant(),
                      QVariant::fromValue<QObject*>(registry_ != nullptr ? registry_->find(start.parameter) : nullptr)}});
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

AnalysisViewModel::AnalysisViewModel(edi::Project& project, ProjectEditor& editor, const SavedFile& saved, QObject* parent)
    : QObject(parent),
      project_(project),
      editor_(editor),
      fitting_mode_options_(new OptionListModel(this)),
      descent_options_(new OptionListModel(this)),
      stop_rule_options_(new OptionListModel(this)),
      moments_near_zero_options_(new OptionListModel(this)),
      minimizer_type_options_(new OptionListModel(this)),
      joint_weights_(new JointWeightListModel(project, this)),
      sequential_fit_(new SequentialFitViewModel(project, this)),
      sequential_extract_(new SequentialExtractListModel(project, editor, this)),
      fit_start_(new FitStartListModel(project, this)),
      aliases_(new AliasListModel(project, editor, this)),
      constraints_(new ConstraintListModel(project, editor, this)),
      categories_(new CategoryListModel(this)),
      text_(new BlockText([saved] { return saved("analysis/analysis.edi"); }, this,
                          [] { return std::string("analysis/analysis.edi"); }, {},
                          [saved] { return saved.discovered("analysis/analysis.edi"); })) {
    descent_options_->setItemOptions("minimizer.descent", edi::supported_descents(), edi::default_descent());
    // The non-empty sets of crysta's two stop rules, in its fixed order; a project that declares none takes both.
    stop_rule_options_->setOptions({"chi_square_change", "shift_su", "chi_square_change shift_su"},
                                   "chi_square_change shift_su",
                                   {"χ² change", "Shift/s.u.", "χ² change or Shift/s.u."});
    moments_near_zero_options_->setItemOptions("minimizer.moments_near_zero", {"try_exact_zero", "keep_free"},
                                               "keep_free");
    minimizer_type_options_->setItemOptions("minimizer.type", edi::supported_minimizer_types());
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
    qCInfo(lcApp, "fitting mode: %s", qPrintable(mode));
    setLastError(editor_.apply_setting(edi::Edit::fitting_mode(project, mode.toStdString())));
}

void AnalysisViewModel::setDescent(const QString& id) {
    if (id == descent_) {
        return;
    }
    edi::Project& project = project_;
    setLastError(editor_.apply_setting(edi::Edit::descent(project, id.toStdString())));
}

void AnalysisViewModel::setMaxIterations(int bound) {
    edi::Project& project = project_;
    setLastError(editor_.apply_setting(edi::Edit::max_iterations(project, bound)));
}

void AnalysisViewModel::setChiSquareTolerance(double tolerance) {
    edi::Project& project = project_;
    setLastError(editor_.apply_setting(edi::Edit::chi_square_tolerance(project, tolerance)));
}

void AnalysisViewModel::setStopRule(const QString& rule) {
    if (rule == stop_rule_) {
        return;
    }
    edi::Project& project = project_;
    setLastError(editor_.apply_setting(edi::Edit::stop_rules(project, rule.toStdString())));
}

void AnalysisViewModel::setShiftTolerance(double tolerance) {
    edi::Project& project = project_;
    setLastError(editor_.apply_setting(edi::Edit::shift_tolerance(project, tolerance)));
}

void AnalysisViewModel::setMomentsNearZero(const QString& option) {
    if (option == moments_near_zero_) {
        return;
    }
    edi::Project& project = project_;
    setLastError(editor_.apply_setting(edi::Edit::moments_near_zero(project, option.toStdString())));
}

void AnalysisViewModel::setRefineLsThresholdSigma(double sigma) {
    const std::optional<double> value = qIsNaN(sigma) ? std::nullopt : std::optional<double>(sigma);
    if (value == project_.refine_ls_threshold_sigma) {
        return;
    }
    edi::Project& project = project_;
    setLastError(editor_.apply_setting(edi::Edit::refine_ls_threshold_sigma(project, value)));
}

void AnalysisViewModel::setLastError(const QString& error) {
    if (error != last_error_) {
        last_error_ = error;
        emit lastErrorChanged();
    }
}

void AnalysisViewModel::sync() {
    // Only the modes that apply are offered, by their descriptive names (the owner, 2026-10-11): a scan's two and
    // single (a fit of the shown dataset), joint for several experiments, single for one. A mode that no longer applies (an experiment added or removed) gives way
    // to the one that does, after this sync.
    const std::vector<std::string> modes = edi::applicable_fitting_modes(project_);
    if (modes != fitting_modes_) {
        fitting_modes_ = modes;
        // Single is the default wherever it applies: a scan stays a single fit until the user switches (the owner,
        // 2026-11-04).
        const bool single = std::find(modes.begin(), modes.end(), "single") != modes.end();
        fitting_mode_options_->setItemOptions("fitting_mode.type", modes, single ? std::string("single") : modes.front());
    }
    if (std::find(modes.begin(), modes.end(), edi::effective_fitting_mode(project_)) == modes.end()) {
        QMetaObject::invokeMethod(
            this,
            [this] {
                const std::vector<std::string> now = edi::applicable_fitting_modes(project_);
                if (std::find(now.begin(), now.end(), edi::effective_fitting_mode(project_)) == now.end()) {
                    // Single when it applies: a scan stays a single fit until the user switches (the owner,
                    // 2026-11-04); otherwise the one mode that does.
                    const bool single = std::find(now.begin(), now.end(), "single") != now.end();
                    editor_.apply_follow_up([this, mode = QString::fromStdString(single ? std::string("single") : now.front())] { setFittingMode(mode); });
                }
            },
            Qt::QueuedConnection);
    }
    const QString mode = QString::fromStdString(edi::effective_fitting_mode(project_));
    if (mode != fitting_mode_) {
        fitting_mode_ = mode;
        emit fittingModeChanged();
    }
    const QString descent = QString::fromStdString(project_.descent.empty() ? edi::default_descent() : edi::current_descent_id(project_.descent));
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
    const QString rule = QString::fromStdString(project_.minimizer_stop_rules.empty() ? std::string("chi_square_change shift_su")
                                                                                      : project_.minimizer_stop_rules);
    if (rule != stop_rule_) {
        stop_rule_ = rule;
        emit stopRuleChanged();
    }
    if (project_.minimizer_shift_tolerance != shift_tolerance_) {
        const bool had = hasShiftTolerance();
        shift_tolerance_ = project_.minimizer_shift_tolerance;
        emit shiftToleranceChanged();
        if (hasShiftTolerance() != had) {
            emit hasShiftToleranceChanged();
        }
    }
    const QString zero = QString::fromStdString(
        project_.minimizer_moments_near_zero.empty() ? std::string("keep_free") : project_.minimizer_moments_near_zero);
    if (zero != moments_near_zero_) {
        moments_near_zero_ = zero;
        emit momentsNearZeroChanged();
    }
    const bool magnetic = std::any_of(project_.structures.begin(), project_.structures.end(),
                                      [](const auto& structure) { return !structure->atom_site_moment.empty(); });
    if (magnetic != magnetic_) {
        magnetic_ = magnetic;
        emit magneticChanged();
    }
    const double cutoff = project_.refine_ls_threshold_sigma.value_or(qQNaN());
    if (qIsNaN(cutoff) != qIsNaN(refine_ls_threshold_sigma_) ||
        (!qIsNaN(cutoff) && cutoff != refine_ls_threshold_sigma_)) {
        refine_ls_threshold_sigma_ = cutoff;
        emit refineLsThresholdSigmaChanged();
    }
    joint_weights_->sync();
    sequential_fit_->sync();
    sequential_extract_->sync();
    fit_start_->sync();
    aliases_->sync();
    constraints_->sync();
    categories_->setCategories(edi::analysis_categories(project_), [this] { return text_->discoveryText().toStdString(); });
}

}  // namespace edi_app
