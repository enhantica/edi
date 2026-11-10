// Compile this consumer without access-control test macros.
#include <exception>
#include <optional>

#include "project_view_model.hpp"

template <class Project>
bool invoke_public_unowned_save(Project* project, const QString& target, bool include,
                                bool wholeTree, QString* error) {
    if constexpr (requires {
                      project->saveTo(target, include, std::optional<quint64>{}, nullptr, nullptr,
                                      wholeTree);
                  }) {
        try {
            *error = project->saveTo(target, include, std::optional<quint64>{}, nullptr, nullptr,
                                     wholeTree);
        } catch (const std::exception& refused) {
            *error = QString::fromUtf8(refused.what());
        }
        return true;
    }
    return false;
}
extern "C" bool transaction_public_save_to(edi_app::ProjectViewModel* project,
                                           const QString& target, bool include, bool wholeTree,
                                           QString* error) {
    return invoke_public_unowned_save(project, target, include, wholeTree, error);
}
