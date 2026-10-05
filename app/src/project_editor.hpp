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
    // Empty on success; the core's refusal message otherwise, with nothing changed.
    virtual QString apply(const edi::Edit& change, bool structural) = 0;
    // An edit of the declared relations (edi ADR-0024): applied as `apply` does, and recorded, so the
    // app bar's Undo restores the rows and every parameter state it changed.
    virtual QString apply_relation_edit(const edi::Edit& change) = 0;
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
