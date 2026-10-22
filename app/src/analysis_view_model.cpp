// SPDX-License-Identifier: BSD-3-Clause
#include "analysis_view_model.hpp"

#include <QMetaObject>
#include <QPointer>
#include <QtCore/qarraydata.h>
#include <cstddef>
#include <QScopeGuard>
#include <limits>
#include "codex_agent.hpp"

#include <algorithm>
#include <string>
#include <vector>

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
        return editor_.apply_relation_control(edi::Edit::rename_alias(*alias, text), {ProjectEditor::RelationAction::Kind::AliasId, alias, value}).isEmpty();
    }
    if (role == QLatin1String("parameter")) {
        return editor_.apply_relation_control(edi::Edit::assign(alias->parameter_unique_name, text), {ProjectEditor::RelationAction::Kind::AliasParameter, alias, value}).isEmpty();
    }
    return false;
}

void AliasListModel::append() {
    edi::Project& project = project_;
    const auto offered = edi::named_parameters(project);
    if (offered.empty()) return; // No lawful target: no Edit or Undo is admitted.
    edi::ParameterAlias alias;
    alias.id = unused_name("alias_", [&project](const std::string& id) { return holds_id(project.aliases, id); });
    // First not-yet-named parameter, otherwise the first real offered target.
    // Multiple alias names for one parameter are lawful; the shared validator
    // still owns ID/target/dependence and complete scientific validation.
    alias.parameter_unique_name = offered.front().unique_name;
    for (const edi::NamedParameter& named : offered) {
        bool aliased = false;
        for (const auto& existing : project.aliases) {
            aliased = aliased || existing->parameter_unique_name.value() == named.unique_name;
        }
        if (!aliased) {
            alias.parameter_unique_name = named.unique_name;
            break;
        }
    }
    editor_.apply_relation_control(edi::Edit::append(project.aliases, std::move(alias)), {ProjectEditor::RelationAction::Kind::AliasAppend});
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
    const auto* member=keyAt(row);
    if (member == nullptr) return;
    edi::Project& project = project_;
    editor_.apply_relation_control(edi::Edit::erase(project.aliases, static_cast<std::size_t>(row)),
        {ProjectEditor::RelationAction::Kind::AliasRemove,member});
}

// ---- ConstraintListModel ------------------------------------------------------------------------

ConstraintListModel::ConstraintListModel(edi::Project& project, ProjectEditor& editor, QObject* parent)
    : RowTableModel({"id", "expression", "enabled", "draft", "draftToken"}, parent), project_(project), editor_(editor) {
    sync();
}

void ConstraintListModel::sync() {
    // FIRST Rows::assign coalescing: do not nest Qt begin/end transactions when
    // Stop/manual takeover/unrelated publication changes the pending row.
    sync_pending_ = true;
    if (syncing_) return;
    syncing_ = true;
    const QPointer<ConstraintListModel> self(this);
    const auto release = qScopeGuard([self] { if (self) self->syncing_ = false; });
    while (sync_pending_) {
        sync_pending_ = false;
        QList<Row> rows;
        for (const auto& constraint : project_.constraints) {
            rows.append({constraint.get(), {QString::fromStdString(constraint->id.value()),
                QString::fromStdString(constraint->expression.value()), constraint->enabled.get(), false, QString{}}});
        }
        // Keep the old tag alive through the whole current row transaction.
        const auto draft = draft_;
        if (draft) rows.append({draft.get(), {draft->id, draft->expression, draft->intendedEnabled, true, draft->token}});
        setTableRows(rows);
        if (!self) return;
    }
}

std::optional<ConstraintRowRef> ConstraintListModel::rowRef(int row) const {
    const auto* key = keyAt(row);
    if (!key) return {};
    if (draft_ && key == draft_.get()) return DraftConstraintRef{draft_->key};
    for (const auto& member : project_.constraints)
        if (member.get() == key) return CoreConstraintRef{member.get()};
    return {}; // Never cast a provisional or retired table key to a core row.
}
std::optional<ConstraintDraftId> ConstraintListModel::currentDraft() const noexcept {
    return draft_ ? std::optional<ConstraintDraftId>(draft_->key) : std::nullopt;
}
int ConstraintListModel::draftRow(ConstraintDraftId id) const noexcept {
    if (!draft_ || id.serial != draft_->key.serial) return -1;
    for (int row = 0; row < count(); ++row) if (keyAt(row) == draft_.get()) return row;
    return -1;
}
void ConstraintListModel::draftError(QString message) {
    if (last_error_ == message) return;
    last_error_ = std::move(message); emit draftErrorChanged();
}
ConstraintDraftId ConstraintListModel::beginDraft(QString id, QString expression, bool enabled, DraftOrigin origin, ConstraintDraftId* created) {
    if (committing_) throw std::runtime_error("A constraint commit is in progress");
    if (draft_) throw std::runtime_error("Finish or remove the current constraint Draft first");
    if (project_.constraints.size() >= static_cast<std::size_t>(std::numeric_limits<int>::max()))
        throw std::length_error("The constraint table row index is exhausted");
    if (draft_serial_ == std::numeric_limits<quint64>::max()) throw std::length_error("Constraint Draft identity exhausted");
    auto next = std::make_shared<Draft>();
    next->key.serial = draft_serial_ + 1;
    next->id = std::move(id); next->expression = std::move(expression);
    next->token = QString::number(next->key.serial);
    next->intendedEnabled = enabled; next->origin = origin;
    ++draft_serial_; draft_ = next;
    if (created) *created = next->key; // Exact provisional owner before synchronous table callbacks.
    sync(); return next->key;
}
ConstraintDraftId ConstraintListModel::beginNativeDraft(const QString& id, const QString& expression, bool enabled, ConstraintDraftId* created) {
    return beginDraft(id, expression, enabled, DraftOrigin::Native, created);
}

bool ConstraintListModel::changeDraft(const QString& role, const QString& value) {
    if (!draft_ || committing_ || (role != QLatin1String("id") && role != QLatin1String("expression"))) return false;
    const auto old = draft_;
    if ((role == QLatin1String("id") ? old->id : old->expression) == value) return true;
    if (old->revision == std::numeric_limits<quint64>::max()) return false;
    // A genuine manual write takes over identity BEFORE it changes pending text;
    // old native Stop cleanup can no longer discard this row.
    if (old->origin == DraftOrigin::Native) {
        if (draft_serial_ == std::numeric_limits<quint64>::max()) return false;
        auto next = std::make_shared<Draft>(*old);
        next->key.serial = draft_serial_ + 1; next->token = QString::number(next->key.serial);
        next->origin = DraftOrigin::Manual; next->prepared.reset();
        ++draft_serial_; draft_ = next;
    }
    if (role == QLatin1String("id")) draft_->id = value; else draft_->expression = value;
    ++draft_->revision; draft_->prepared.reset();
    const auto key = draft_->key;
    const QPointer<ConstraintListModel> self(this);
    sync();
    if (self && draft_ && draft_->key.serial == key.serial && role == QLatin1String("expression"))
        commitDraft(QString::number(key.serial));
    return true;
}

bool ConstraintListModel::setRole(int row, const QString& role, const QVariant& value) {
    return role == QLatin1String("enabled") ? setEnabled(row, value.toBool()) : setText(row, role, value.toString());
}
bool ConstraintListModel::setText(int row, const QString& role, const QString& value) {
    if (committing_) return false;
    const auto reference = rowRef(row); if (!reference) return false;
    if (std::holds_alternative<DraftConstraintRef>(*reference)) return changeDraft(role, value);
    auto* member = const_cast<edi::ParameterConstraint*>(std::get<CoreConstraintRef>(*reference).member);
    if (role == QLatin1String("id")) {
        if (QString::fromStdString(member->id.value()) == value) return true;
        return editor_.apply_relation_control(edi::Edit::rename_constraint(*member, value.toStdString()),
            {ProjectEditor::RelationAction::Kind::ConstraintId, member, value}).isEmpty();
    }
    if (role == QLatin1String("expression")) {
        if (QString::fromStdString(member->expression.value()) == value) return true;
        return editor_.apply_relation_control(edi::Edit::constraint_expression(project_, *member, value.toStdString()),
            {ProjectEditor::RelationAction::Kind::ConstraintExpression, member, value}).isEmpty();
    }
    return false;
}
bool ConstraintListModel::setEnabled(int row, bool enabled) {
    if (committing_) return false;
    const auto reference = rowRef(row); if (!reference || !std::holds_alternative<CoreConstraintRef>(*reference)) return false;
    auto* member = const_cast<edi::ParameterConstraint*>(std::get<CoreConstraintRef>(*reference).member);
    if (member->enabled.get() == enabled) return true;
    return editor_.apply_relation_control(edi::Edit::constraint_enabled(project_, *member, enabled),
        {ProjectEditor::RelationAction::Kind::ConstraintEnabled, member, {}, enabled}).isEmpty();
}

namespace {
std::string constraint_unused_name(const edi::Project& project, const std::string& stem) {
    if (project.constraints.size() == std::numeric_limits<std::size_t>::max()) throw std::length_error("Constraint names exhausted");
    for (std::size_t n = 1; n <= project.constraints.size() + 1; ++n) {
        const auto candidate = stem + std::to_string(n);
        if (!holds_id(project.constraints, candidate)) return candidate;
    }
    throw std::length_error("Constraint names exhausted");
}
}
void ConstraintListModel::append() {
    if (committing_) return;
    if (draft_) { emit focusDraftRequested(draft_->token); return; }
    const auto id = QString::fromStdString(constraint_unused_name(project_, "constraint_"));
    const QPointer<ConstraintListModel> self(this);
    const auto key = beginDraft(id, {}, true, DraftOrigin::Manual);
    if (self && draft_ && draft_->key.serial == key.serial) emit focusDraftRequested(draft_->token);
}
void ConstraintListModel::duplicate(int row) {
    if (committing_) return;
    if (draft_) { emit focusDraftRequested(draft_->token); return; }
    const auto reference = rowRef(row); if (!reference || !std::holds_alternative<CoreConstraintRef>(*reference)) return;
    const auto* source = std::get<CoreConstraintRef>(*reference).member;
    auto copy = *source;
    copy.id = constraint_unused_name(project_, source->id.value() + "_");
    if (!copy.enabled.get()) {
        editor_.commit_constraint(project_, std::move(copy), {}); return;
    }
    // An active copied equality usually conflicts with its original target.
    // It remains visibly provisional until an explicit valid confirmation.
    const QPointer<ConstraintListModel> self(this);
    const auto key = beginDraft(QString::fromStdString(copy.id.value()), QString::fromStdString(copy.expression.value()), true, DraftOrigin::Duplicate);
    if (self && draft_ && draft_->key.serial == key.serial) emit focusDraftRequested(draft_->token);
}
void ConstraintListModel::remove(int row) {
    if (committing_) return;
    const auto reference = rowRef(row); if (!reference) return;
    if (std::holds_alternative<DraftConstraintRef>(*reference)) { discardDraft(std::get<DraftConstraintRef>(*reference).draft); return; }
    const auto* member = std::get<CoreConstraintRef>(*reference).member;
    std::size_t at = 0; while (at < project_.constraints.size() && project_.constraints[at].get() != member) ++at;
    if (at == project_.constraints.size()) return;
    editor_.apply_relation_control(edi::Edit::erase(project_.constraints, at), {ProjectEditor::RelationAction::Kind::ConstraintRemove, member});
}
bool ConstraintListModel::discardDraft(ConstraintDraftId id) {
    if (committing_ || !draft_ || draft_->key.serial != id.serial) return false;
    const auto old = std::move(draft_); sync(); return true;
}
bool ConstraintListModel::discardNativeDraft(ConstraintDraftId id) {
    return draft_ && draft_->origin == DraftOrigin::Native && discardDraft(id);
}
bool ConstraintListModel::takeOverNativeDraft(ConstraintDraftId id) {
    if (committing_ || !draft_ || draft_->key.serial != id.serial || draft_->origin != DraftOrigin::Native) return false;
    if (draft_serial_ == std::numeric_limits<quint64>::max() || draft_->revision == std::numeric_limits<quint64>::max()) return false;
    const auto token = QString::number(draft_serial_ + 1); // Allocate before changing ownership.
    ++draft_serial_; draft_->key.serial = draft_serial_; draft_->token = token;
    ++draft_->revision; draft_->origin = DraftOrigin::Manual; draft_->prepared.reset();
    sync(); return true;
}
void ConstraintListModel::focusDraft(const QString& token) {
    if (draft_ && draft_->token == token) emit focusDraftRequested(token);
}
std::shared_ptr<const ConstraintDraftCommit> ConstraintListModel::prepareDraftCommit(ConstraintDraftId id) {
    if (committing_ || !draft_ || draft_->key.serial != id.serial) throw std::runtime_error("The constraint Draft changed");
    auto prepared = std::make_shared<ConstraintDraftCommit>();
    prepared->draft = id; prepared->revision = draft_->revision;
    prepared->id = draft_->id; prepared->expression = draft_->expression; prepared->enabled = draft_->intendedEnabled;
    draft_->prepared = prepared; return prepared;
}
bool ConstraintListModel::draftCommitCurrent(const std::shared_ptr<const ConstraintDraftCommit>& prepared) const noexcept {
    return draft_ && prepared && prepared == draft_->prepared.lock() &&
        prepared->draft.serial == draft_->key.serial && prepared->revision == draft_->revision;
}
ProjectEditor::RelationOutcome ConstraintListModel::commitDraft(const std::shared_ptr<const ConstraintDraftCommit>& prepared) {
    const auto original = draft_;
    if (committing_ || !original || !prepared || prepared != original->prepared.lock() ||
        prepared->draft.serial != original->key.serial || prepared->revision != original->revision)
        return {false, false, tr("The constraint Draft changed")};
    committing_ = true;
    const QPointer<ConstraintListModel> self(this);
    const auto release = qScopeGuard([self] { if (self) self->committing_ = false; });
    const QString warning = tr("The constraint was applied but its Draft presentation could not be completed");
    edi::ParameterConstraint complete;
    try {
        complete.id = prepared->id.toStdString(); complete.expression = prepared->expression.toStdString();
        complete.enabled = prepared->enabled;
    } catch (const std::exception&) {
        return {false, false, tr("The constraint Draft declaration is invalid")};
    }
    ProjectEditor::RelationAction action; action.kind = ProjectEditor::RelationAction::Kind::ConstraintCommit; action.commit = prepared;
    auto outcome = editor_.commit_constraint(project_, std::move(complete), action);
    if (!self) return outcome;
    if (outcome.applied && draft_ == original) {
        draft_.reset();
        try { sync(); } catch (...) { outcome.published = false; outcome.message = warning; }
    }
    return outcome;
}
void ConstraintListModel::commitDraft(const QString& token) {
    if (!draft_ || draft_->token != token || draft_->origin == DraftOrigin::Native) return;
    const auto original = draft_; const QPointer<ConstraintListModel> self(this);
    try {
        const auto result = commitDraft(prepareDraftCommit(original->key));
        if (self) draftError(result.applied && result.published ? QString{} : result.message);
    } catch (const std::exception&) {
        if (self) draftError(tr("The constraint Draft could not be confirmed"));
    }
}

quint64 ConstraintListModel::nativeDraftPreparationBytes(quint64 idUnits, quint64 expressionUnits, quint64 idBackingBytes, quint64 expressionBackingBytes) {
    // Pinned libstdc++ inplace control: vptr + two Atomic_word counters,
    // fitting two pointers on this original LP64 producer. No dynamic trace.
    quint64 bytes = sizeof(Draft) + sizeof(ConstraintDraftCommit) + 2 * (2 * sizeof(void*)) +
        3 * sizeof(edi::ParameterConstraint) + sizeof(edi::Edit) +
        sizeof(std::shared_ptr<edi::ParameterConstraint>) + sizeof(edi::Project*) + 4 * sizeof(void*);
    const auto add = [&bytes](quint64 n) {
        if (n > std::numeric_limits<quint64>::max() - bytes) throw std::length_error("Constraint Draft size overflow");
        bytes += n;
    };
    for (const auto backing : {idBackingBytes, expressionBackingBytes}) {
        // Decoded current input, local Draft, and immutable prepared commit.
        add(backing); add(backing); add(backing);
    }
    for (const auto units : {idUnits, expressionUnits}) {
        if (units > (std::numeric_limits<quint64>::max() - 1) / 3) throw std::length_error("Constraint Draft UTF-8 overflow");
        // UTF-8 has <=3 bytes per UTF-16 unit (a supplementary pair needs4).
        // Qt conversion scratch plus the three simultaneous complete/captured/
        // about-to-insert std::string owners; ItemKey move is a COPY by design.
        add(codex_json_capacity(3 * units + 1));
        add(3 * units + 1); add(3 * units + 1); add(3 * units + 1);
    }
    add(codex_json_capacity((std::numeric_limits<quint64>::digits10 + 2) * sizeof(QChar)));
    return bytes;
}
quint64 ConstraintListModel::nativeDraftPreparationBytes(const QString& id, const QString& expression) {
    const auto actual = [](const QString& text) {
        const auto capacity = static_cast<quint64>(text.capacity());
        constexpr quint64 header = sizeof(QArrayData) + alignof(std::max_align_t) + sizeof(QChar);
        if (capacity > (std::numeric_limits<quint64>::max() - header) / sizeof(QChar)) throw std::length_error("Constraint Draft backing overflow");
        return capacity * sizeof(QChar) + header;
    };
    return nativeDraftPreparationBytes(static_cast<quint64>(id.size()), static_cast<quint64>(expression.size()), actual(id), actual(expression));
}
quint64 ConstraintListModel::draftPreparationBytes(ConstraintDraftId id) const {
    if (!draft_ || draft_->key.serial != id.serial) throw std::runtime_error("The constraint Draft changed");
    return nativeDraftPreparationBytes(draft_->id, draft_->expression);
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
        std::vector<std::string> labels;
        for (const std::string& token : modes) {
            labels.push_back(edi::fitting_mode_label(token));
        }
        fitting_mode_options_->setOptions(modes, modes.front(), labels);
    }
    if (std::find(modes.begin(), modes.end(), edi::effective_fitting_mode(project_)) == modes.end()) {
        QMetaObject::invokeMethod(
            this,
            [this] {
                const std::vector<std::string> now = edi::applicable_fitting_modes(project_);
                if (std::find(now.begin(), now.end(), edi::effective_fitting_mode(project_)) == now.end()) {
                    setFittingMode(QString::fromStdString(now.front()));
                }
            },
            Qt::QueuedConnection);
    }
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
