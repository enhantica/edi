// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_PROJECT_EDITOR_HPP
#define EDI_APP_PROJECT_EDITOR_HPP

#include <QObject>
#include <QString>
#include <QVariant>
#include <functional>
#include <memory>
#include <string>
#include <variant>

#include "edi/background_estimate.hpp"
#include "edi/edit.hpp"

namespace edi_app {

// Why the user may not edit the experiment's background points or terms: in auto mode the estimate owns them
// (ADR-0040), so the pages show them locked and a write that reaches the model anyway refuses before anything changes.
// Freeing or fixing one stays allowed. Empty in manual mode.
inline QString estimated_background_refusal(const edi::ExperimentBase& experiment) {
    return edi::background_estimate_mode(experiment) == "auto"
               ? QObject::tr("the background is estimated automatically; choose the manual estimation mode to edit it")
               : QString();
}

// Some experiment of the project holds measured data; without any there is nothing to fit (edi ADR-0046).
inline bool has_measured_data(const edi::Project& project) {
    for (const auto& experiment : project.experiments) {
        if (!experiment->calculation_only) {
            return true;
        }
    }
    return false;
}

// The one door every write goes through: run a core call, then publish what it changed. The call is
// an edi::Edit (edi ADR-0020 §8): one core operation that refuses before it writes, or completes. The
// door takes no callable, so a change that writes and then throws cannot be passed to it.
// `structural` says the set of shown parameters or rows may have changed (a profile switch, an added
// row), so the pages' lists are re-derived; a plain value write only publishes differences.
class ProjectEditor {
   public:
    virtual ~ProjectEditor() = default;
    // Empty after an actual edit (a later presentation failure remains a held app
    // warning); nonempty only for a refusal before the core operation writes.
    // Native callers use ProjectViewModel's explicit applied/published outcome.
    virtual QString apply(const edi::Edit& change, bool structural) = 0;
    // The same closed typed writes used by genuine parameter widgets. A native
    // recorded-input scope may own their Undo without replacing widget events.
    virtual QString assign_parameter_value(edi::Parameter& parameter, double value) {
        return apply(edi::Edit::value(parameter, value), false);
    }
    struct BackgroundOutcome { bool applied = false, published = false; QString message; };
    virtual BackgroundOutcome edit_background_point(edi::ExperimentBase&, const edi::BackgroundPointInput&) {
        return {false, false, QStringLiteral("Defined background editing is unavailable for this editor")};
    }
    virtual QString rename_background_point(edi::ExperimentBase&, edi::LineSegment& point, const std::string& id) {
        return apply(edi::Edit::background_id(point, id), true);
    }
    virtual QString assign_parameter_free(edi::Parameter& parameter, bool free) {
        return apply(edi::Edit::assign(parameter.free, free), false);
    }
    // An edit of the declared relations (edi ADR-0024): applied as `apply` does, and recorded, so the
    // app bar's Undo restores the rows and every parameter state it changed.
    struct RelationAction {
        enum class Kind { Other, AliasAppend, AliasId, AliasParameter, ConstraintAppend, ConstraintId, ConstraintExpression, ConstraintEnabled, AliasRemove, ConstraintRemove };
        Kind kind = Kind::Other;
        const void* row = nullptr;
        QString text;
        bool enabled = false;
        QString expression;
    };
    struct RelationOutcome { bool applied = false, published = false; QString message; const edi::ParameterConstraint* constraint = nullptr; };
    virtual RelationOutcome append_constraint(edi::Project&, edi::ParameterConstraint&&, const RelationAction&) {
        return {false, false, QStringLiteral("Constraint append is unavailable for this editor")};
    }
    virtual QString apply_relation_edit(const edi::Edit& change) = 0;
    virtual QString apply_relation_control(const edi::Edit& change, const RelationAction&) {
        return apply_relation_edit(change);
    }
    // Original creation-row controls expose finite semantic metadata, just as
    // the original alias/constraint controls do. No provider callable/edit exists.
    struct CreationAction {
        enum class Kind { ExperimentAppend, ExperimentType, ExperimentName, PeakProfile, AbsorptionType, ExtinctionType, MosaicDistribution, CutoffFwhm, DatasetWeight, ExclusionAppend, ExclusionStart, ExclusionEnd, ExclusionRemove, StructureAppend, StructureName, SpaceGroupName, SpaceGroupNumber, SpaceGroupSetting, AtomAppend, AtomText, AtomRemove, AtomAdpType, PhaseAppend, PhaseRetarget, PhaseEnabled, PhaseRemove };
        Kind kind;
        const void* row = nullptr;
        QString field, text;
        double number = 0;
    };
    virtual QString apply_creation_control(const edi::Edit& change, bool structural, const CreationAction&) {
        return apply(change, structural);
    }
    // An edit of a setting of the whole project (its fitting mode, its minimizer settings, its name), applied as
    // `apply` does. In a scan project it changes the template as it is: it never makes a shown dataset the template.
    virtual QString apply_setting(const edi::Edit& change) { return apply(change, false); }
    // An edit of a setting no calculation reads (a single crystal's observed threshold, which changes only the
    // observed counts and R(gt)): applied and published as `apply` does, but the published patterns stay current, so
    // nothing is recalculated and no chart is redrawn.
    virtual QString apply_unread(const edi::Edit& change) { return apply(change, false); }
    // Why a user may not set this parameter's value, before anything is written: empty when they may. An auto-mode
    // background's point intensities and term coefficients refuse (estimated_background_refusal).
    virtual QString value_refusal(const edi::Parameter& /*parameter*/) const { return {}; }
    // Why no parameter may be set free or fixed now: empty when they may. A project with no measured data in any
    // experiment has nothing to fit, so it refuses (edi ADR-0046).
    virtual QString free_refusal() const { return {}; }
    // An edit of an experiment's background rows (an id, position or order, a row added or removed, the rows named):
    // refused in auto mode (estimated_background_refusal), else applied as `apply` does.
    virtual QString apply_background_edit(const edi::ExperimentBase& experiment, const edi::Edit& change,
                                          bool structural) {
        const QString refusal = estimated_background_refusal(experiment);
        return refusal.isEmpty() ? apply(change, structural) : refusal;
    }
    // A structure's or an experiment's name, which every name of its parameters follows: applied as `apply` does, and
    // recorded, so Undo names it back the same way.
    virtual QString rename_structure(edi::Structure& structure, const std::string& name) {
        return apply(edi::Edit::structure_name(structure, name), true);
    }
    virtual QString rename_experiment(edi::Project& project, edi::ExperimentBase& experiment, const std::string& name) {
        return apply(edi::Edit::rename_experiment(project, experiment, name), true);
    }
};

// A file of the project's current save, by its path relative to the project directory (D7); throws
// the writer's refusal.
using SavedFile = std::function<std::string(const std::string& relative)>;

// A fresh name "<stem><n>" not among `taken`, for an appended or duplicated row.
template <typename Taken>
std::string unused_name(const std::string& stem, Taken taken) {
    for (int n = 1;; ++n) {
        const std::string candidate = stem + std::to_string(n);
        if (!taken(candidate)) {
            return candidate;
        }
    }
}

// The ParameterItem of a core parameter, as a model role value (null when the parameter is not
// shown). Defined in parameter_registry.cpp.
class ParameterRegistry;
QVariant parameter_role(const ParameterRegistry& registry, const void* parameter);

}  // namespace edi_app

#endif  // EDI_APP_PROJECT_EDITOR_HPP
