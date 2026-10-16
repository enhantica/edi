// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_PROJECT_EDITOR_HPP
#define EDI_APP_PROJECT_EDITOR_HPP

#include <QObject>
#include <QString>
#include <QVariant>
#include <functional>
#include <string>

#include "edi/edit.hpp"

namespace edi_app {

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
    virtual QString assign_parameter_free(edi::Parameter& parameter, bool free) {
        return apply(edi::Edit::assign(parameter.free, free), false);
    }
    // An edit of the declared relations (edi ADR-0024): applied as `apply` does, and recorded, so the
    // app bar's Undo restores the rows and every parameter state it changed.
    virtual QString apply_relation_edit(const edi::Edit& change) = 0;
    // An edit of a setting of the whole project (its fitting mode, its minimizer settings, its name), applied as
    // `apply` does. In a scan project it changes the template as it is: it never makes a shown dataset the template.
    virtual QString apply_setting(const edi::Edit& change) { return apply(change, false); }
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
