// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include "assistant_json.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/io.hpp"
#include "edi/fittability.hpp"
#include "edi/selectors.hpp"
#include <map>
#include <set>
#include <type_traits>

namespace edi::assistant::detail {
inline bool independently_fittable(const ParameterEntry& entry) noexcept {
    return entry.refinable && entry.parameter->dependence==Dependence::Independent &&
        entry.parameter->fit_blocker==FitBlocker::None;
}
// Shared native/restricted-controller parameter preparation. Path/dependence,
// range and relation validation complete on a copy before a live editor writes.
template<class T>
Edit prepare_parameter_edit(Project& project, const std::vector<std::pair<std::string, T>>& requested,
                            const std::set<std::string>* allowed = nullptr,
                            std::vector<std::pair<std::string, bool>>* before_flags = nullptr) {
    refresh_fittability(project);
    std::map<const Parameter*, std::string> names;
    for (const auto& slot : named_slots(project)) names.emplace(slot.parameter, slot.unique_name);
    std::map<std::string, ParameterEntry> metadata;
    for (const auto& entry : parameter_entries(project)) if (names.count(entry.parameter)) metadata.emplace(entry.path, entry);
    std::set<std::string> seen;
    std::vector<std::pair<std::string, T>> edits;
    for (const auto& [path, value] : requested) {
        const auto found = metadata.find(path);
        if (!seen.insert(path).second || found == metadata.end()) refuse("invalid_argument", "Unknown or duplicate parameter: " + path);
        if (allowed && !allowed->count(path)) refuse("out_of_scope", "Parameter not approved: " + path);
        const auto& entry = found->second;
        if (entry.parameter->dependence != Dependence::Independent) refuse("out_of_scope", "Dependent parameter: " + path);
        if constexpr (std::is_same_v<T, bool>) {
            if (value && !independently_fittable(entry))
                refuse("out_of_scope", "The parameter is not independently fittable in this profile: " + path +
                    (entry.parameter->fit_reason.empty()?std::string{}:" ("+entry.parameter->fit_reason+")"));
        } else if (!std::isfinite(value)) refuse("invalid_argument", "Parameter value must be finite");
        if constexpr (std::is_same_v<T, bool>)
            if (before_flags) before_flags->emplace_back(names.at(entry.parameter), entry.parameter->free.get());
        edits.emplace_back(names.at(entry.parameter), value);
    }
    if (edits.empty()) refuse("invalid_argument", "Empty parameter batch");
    Project validated = project;
    if constexpr (std::is_same_v<T, bool>) Edit::set_free(validated, edits)();
    else Edit::parameter_values(validated, edits)();
    if (!validated.aliases.empty() || !validated.constraints.empty()) complete_relations(validated);
    else refresh_relations(validated);
    if constexpr (std::is_same_v<T, bool>) return Edit::set_free(project, std::move(edits));
    else return Edit::parameter_values(project, std::move(edits));
}
} // namespace edi::assistant::detail
