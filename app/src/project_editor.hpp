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
};

// A file of the project's current save, by its path relative to the project directory (D7); throws
// the writer's refusal.
using SavedFile = std::function<std::string(const std::string& relative)>;

// The ParameterItem of a core parameter, as a model role value (null when the parameter is not
// shown). Defined in parameter_registry.cpp.
class ParameterRegistry;
QVariant parameter_role(const ParameterRegistry& registry, const void* parameter);

}  // namespace edi_app

#endif  // EDI_APP_PROJECT_EDITOR_HPP
