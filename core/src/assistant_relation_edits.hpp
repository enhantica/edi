// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include "assistant_json.hpp"
#include "edi/edit.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/selectors.hpp"
#include <map>
#include <set>
#include <limits>

namespace edi::assistant::detail {
struct NativeAliasInput { std::string id, path; };
struct NativeConstraintInput { std::string id, expression; bool enabled = false; };

// The existing manual alias/constraint editor and Undo consume the same declared
// rows. Append a whole validated declaration, never replace an existing rule or
// parse its affine expression in the app. Actual crysta completion owns semantics.
inline Edit prepare_relation_append(Project& project, const std::vector<NativeAliasInput>& aliases,
                                     const std::vector<NativeConstraintInput>& constraints) {
    if (constraints.empty())
        refuse("invalid_argument", "The native constraint declaration must be nonempty");
    std::uint64_t bytes = sizeof("{\"aliases\":[],\"constraints\":[]}") - 1;
    const auto charge = [&](std::uint64_t n) {
        if (n > std::numeric_limits<std::uint64_t>::max() - bytes) throw std::overflow_error("Native relation byte count overflow");
        bytes += n;
    };
    const auto text = [&](const std::string& value, std::optional<std::uint64_t> limit) {
        if (value.empty() || (limit && value.size() > *limit) || value.find('\0') != std::string::npos || !utf8(value))
            refuse("invalid_argument", "Native relation text is empty, invalid or exceeds capacity");
        charge(json::encoded_string_size(value));
    };
    bool first = true;
    for (const auto& row : aliases) {
        if (!first) charge(sizeof(",") - 1); first = false;
        charge(sizeof("{\"id\":,\"path\":}") - 1); text(row.id, Limits::id_bytes); text(row.path, Limits::id_bytes);
    }
    first = true;
    for (const auto& row : constraints) {
        if (!first) charge(sizeof(",") - 1); first = false;
        charge(sizeof("{\"id\":,\"expression\":,\"enabled\":}") - 1);
        charge(row.enabled ? sizeof("true") - 1 : sizeof("false") - 1);
        text(row.id, Limits::id_bytes); text(row.expression, std::nullopt);
    }
    if (project.structures.empty())
        refuse("unsupported_model", "Native affine relations require a structure that the existing relation engine can validate");
    // Resolve exactly the same exposed paths used by set_parameters/set_free.
    std::map<const Parameter*, std::string> names;
    for (const auto& slot : named_slots(project)) names.emplace(slot.parameter, slot.unique_name);
    std::map<std::string, const Parameter*> paths;
    for (const auto& entry : parameter_entries(project)) if (names.count(entry.parameter)) paths.emplace(entry.path, entry.parameter);
    RelationsUndo declaration;
    std::set<std::string> alias_ids, constraint_ids;
    for (const auto& row : project.aliases) { alias_ids.insert(row->id.value()); declaration.aliases.push_back(*row); }
    for (const auto& row : project.constraints) { constraint_ids.insert(row->id.value()); declaration.constraints.push_back(*row); }
    for (const auto& row : aliases) {
        const auto found = paths.find(row.path);
        if (found == paths.end() || !alias_ids.insert(row.id).second)
            refuse("invalid_argument", "Unknown native parameter path or duplicate alias id");
        ParameterAlias alias; alias.id = row.id; alias.parameter_unique_name = names.at(found->second);
        declaration.aliases.push_back(std::move(alias));
    }
    for (const auto& row : constraints) {
        if (!constraint_ids.insert(row.id).second) refuse("invalid_argument", "Duplicate native constraint id");
        ParameterConstraint constraint; constraint.id = row.id; constraint.expression = row.expression; constraint.enabled = row.enabled;
        declaration.constraints.push_back(std::move(constraint));
    }
    Project validated = project;
    Edit::restore_relations(validated, declaration)();
    complete_relations(validated); // Existing SDK grammar/cycles/ranges/symmetry/physical validation, not another solver.
    // Parameter-state list is intentionally empty. The actual editor's completion
    // derives dependents; the actual RelationsUndo capture records what changed.
    return Edit::restore_relations(project, std::move(declaration));
}
} // namespace edi::assistant::detail
