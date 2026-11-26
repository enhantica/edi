// SPDX-License-Identifier: BSD-3-Clause
// ADR-0087: the "Same for all experiments" and "Phase ratios shared" switches. They write ordinary alias and
// constraint rows and read the switch's state back from those rows' exact text; crysta parses the expressions and
// decides what follows what (ADR-0024).
#include "edi/sharing.hpp"

#include <algorithm>
#include <cstddef>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

#include "edi/categories.hpp"
#include "edi/io.hpp"

namespace edi {

namespace {

std::string block_of(const std::string& name) { return datablock_key(name, "experiment"); }

const BraggPdExperiment* experiment_named(const Project& project, const std::string& name) {
    for (const auto& experiment : project.experiments) {
        if (block_of(experiment->name) == block_of(name)) {
            return experiment.get();
        }
    }
    return nullptr;
}

// The alias id the switch gives a unique name: `same_<name>` with its dots as underscores.
std::string base_alias(const std::string& unique_name) {
    std::string id = "same_" + unique_name;
    std::replace(id.begin(), id.end(), '.', '_');
    return id;
}

// The alias naming `unique_name`, or empty.
std::string alias_naming(const Project& project, const std::string& unique_name) {
    for (const auto& alias : project.aliases) {
        if (alias->parameter_unique_name.value() == unique_name) {
            return alias->id.value();
        }
    }
    return {};
}

bool alias_taken(const Project& project, const std::string& id) {
    return std::any_of(project.aliases.begin(), project.aliases.end(),
                       [&id](const auto& alias) { return alias->id.value() == id; });
}

// The rows one switch added, so a refusal can take them back.
struct Added {
    std::vector<std::string> aliases;
    std::vector<std::string> constraints;
};

// An alias for `unique_name`: the one that already names it, else a new one with the switch's id.
std::string ensure_alias(Project& project, const std::string& unique_name, Added& added) {
    if (std::string held = alias_naming(project, unique_name); !held.empty()) {
        return held;
    }
    const std::string base = base_alias(unique_name);
    std::string id = base;
    for (int n = 2; alias_taken(project, id); ++n) {
        id = base + "_" + std::to_string(n);
    }
    ParameterAlias alias;
    alias.id = id;
    alias.parameter_unique_name = unique_name;
    project.aliases.push_back(alias);
    added.aliases.push_back(id);
    return id;
}

const ParameterConstraint* constraint_with(const Project& project, const std::string& expression) {
    for (const auto& constraint : project.constraints) {
        if (constraint->expression.value() == expression && constraint->enabled.get()) {
            return constraint.get();
        }
    }
    return nullptr;
}

void add_constraint(Project& project, const std::string& lhs, const std::string& expression, Added& added) {
    if (constraint_with(project, expression) != nullptr) {
        return;
    }
    std::string id = lhs;
    for (int n = 2; std::any_of(project.constraints.begin(), project.constraints.end(),
                                [&id](const auto& c) { return c->id.value() == id; });
         ++n) {
        id = lhs + "_" + std::to_string(n);
    }
    ParameterConstraint constraint;
    constraint.id = id;
    constraint.expression = expression;
    project.constraints.push_back(constraint);
    added.constraints.push_back(id);
}

// crysta checks the rows and marks every parameter; the dependents take their values. A refusal takes back
// exactly the rows this switch added and propagates.
void settle(Project& project, const Added& added) {
    try {
        refresh_relations(project);
    } catch (...) {
        for (const std::string& id : added.constraints) {
            for (std::size_t i = 0; i < project.constraints.size(); ++i) {
                if (project.constraints[i]->id.value() == id) {
                    project.constraints.erase_at(i);
                    break;
                }
            }
        }
        for (const std::string& id : added.aliases) {
            for (std::size_t i = 0; i < project.aliases.size(); ++i) {
                if (project.aliases[i]->id.value() == id) {
                    project.aliases.erase_at(i);
                    break;
                }
            }
        }
        refresh_relations(project);
        throw;
    }
    apply_relations(project);
}

void remove_constraint(Project& project, const std::string& expression) {
    for (std::size_t i = 0; i < project.constraints.size(); ++i) {
        if (project.constraints[i]->expression.value() == expression) {
            project.constraints.erase_at(i);
            return;
        }
    }
}

// A switch's alias no constraint uses any more goes with it.
void remove_unused_alias(Project& project, const std::string& id) {
    if (id.rfind("same_", 0) != 0) {
        return;  // an alias the user made stays
    }
    for (const auto& constraint : project.constraints) {
        const std::string& text = constraint->expression.value();
        if (text.find(id) != std::string::npos) {
            return;
        }
    }
    for (std::size_t i = 0; i < project.aliases.size(); ++i) {
        if (project.aliases[i]->id.value() == id) {
            project.aliases.erase_at(i);
            return;
        }
    }
}

bool has_parameter(const Project& project, const std::string& unique_name) {
    for (const NamedParameter& parameter : named_parameters(project)) {
        if (parameter.unique_name == unique_name) {
            return true;
        }
    }
    return !alias_naming(project, unique_name).empty();
}

// The structures every member links, in the leader's order, enabled ones only.
std::vector<std::string> linked_ids(const BraggPdExperiment& experiment) {
    std::vector<std::string> ids;
    for (const auto& link : experiment.linked_structures) {
        if (link->enabled.get()) {
            ids.push_back(link->structure_id.value());
        }
    }
    return ids;
}

std::string scale_name(const std::string& experiment, const std::string& structure) {
    return block_of(experiment) + ".linked_structure." + structure + ".scale";
}

// The leader's reference structure: its first enabled link with a scale other than zero.
std::optional<std::string> reference_structure(const BraggPdExperiment& leader) {
    for (const auto& link : leader.linked_structures) {
        if (link->enabled.get() && link->scale.value != 0.0) {
            return link->structure_id.value();
        }
    }
    return std::nullopt;
}

// The expression the phase-ratio switch writes for member `e`, structure `p`, leader `a`, reference `r`.
std::string ratio_expression(const std::string& lhs, const std::string& er, const std::string& ap,
                             const std::string& ar) {
    return lhs + " = " + er + " * " + ap + " / " + ar;
}

// The constraint that makes `member` the same as `leader`.
std::string same_as(const std::string& member, const std::string& leader) {
    std::string equation = member;
    equation.append(" = ").append(leader);
    return equation;
}

}  // namespace

std::vector<std::string> sharing_scope(const Project& project, const std::string& experiment) {
    if (experiment_named(project, experiment) == nullptr) {
        throw std::invalid_argument("no experiment '" + experiment + "' in the project");
    }
    for (const auto& member : project.experiment_set_members) {
        if (block_of(member->experiment_id.value()) != block_of(experiment)) {
            continue;
        }
        std::string leader;
        for (const auto& set : project.experiment_sets) {
            if (set->id.value() == member->set_id.value()) {
                leader = set->template_experiment_id.value();
            }
        }
        std::vector<std::string> scope{leader};
        for (const auto& other : project.experiment_set_members) {
            if (other->set_id.value() == member->set_id.value() &&
                block_of(other->experiment_id.value()) != block_of(leader)) {
                scope.push_back(other->experiment_id.value());
            }
        }
        return scope;
    }
    std::vector<std::string> scope;
    for (const auto& held : project.experiments) {
        scope.push_back(held->name);
    }
    return scope;
}

bool shared_across_experiments(const Project& project, const std::string& experiment, const std::string& path) {
    const std::vector<std::string> scope = sharing_scope(project, experiment);
    if (scope.size() < 2) {
        return false;
    }
    const std::string leader = alias_naming(project, block_of(scope.front()) + "." + path);
    if (leader.empty()) {
        return false;
    }
    for (std::size_t i = 1; i < scope.size(); ++i) {
        const std::string member = alias_naming(project, block_of(scope[i]) + "." + path);
        if (member.empty() || constraint_with(project, same_as(member, leader)) == nullptr) {
            return false;
        }
    }
    return true;
}

void share_across_experiments(Project& project, const std::string& experiment, const std::string& path) {
    const std::vector<std::string> scope = sharing_scope(project, experiment);
    for (const std::string& member : scope) {
        if (!has_parameter(project, block_of(member) + "." + path)) {
            std::string message = "experiment '" + member;
            message.append("' has no parameter '").append(path).append("', so it cannot be the same for all experiments");
            throw std::invalid_argument(message);
        }
    }
    Added added;
    const std::string leader = ensure_alias(project, block_of(scope.front()) + "." + path, added);
    for (std::size_t i = 1; i < scope.size(); ++i) {
        const std::string member = ensure_alias(project, block_of(scope[i]) + "." + path, added);
        add_constraint(project, member, same_as(member, leader), added);
    }
    settle(project, added);
}

void unshare_across_experiments(Project& project, const std::string& experiment, const std::string& path) {
    const std::vector<std::string> scope = sharing_scope(project, experiment);
    const std::string leader = alias_naming(project, block_of(scope.front()) + "." + path);
    if (leader.empty()) {
        return;
    }
    for (std::size_t i = 1; i < scope.size(); ++i) {
        const std::string member = alias_naming(project, block_of(scope[i]) + "." + path);
        if (!member.empty()) {
            remove_constraint(project, same_as(member, leader));
            remove_unused_alias(project, member);
        }
    }
    remove_unused_alias(project, leader);
    refresh_relations(project);
}

bool phase_ratios_shared(const Project& project, const std::string& experiment) {
    const std::vector<std::string> scope = sharing_scope(project, experiment);
    const BraggPdExperiment* leader = experiment_named(project, scope.front());
    if (scope.size() < 2 || leader == nullptr) {
        return false;
    }
    const std::vector<std::string> phases = linked_ids(*leader);
    if (phases.size() < 2) {
        return false;
    }
    // The reference is the structure whose leader scale every ratio divides by.
    for (const std::string& reference : phases) {
        const std::string ar = alias_naming(project, scale_name(scope.front(), reference));
        bool all = !ar.empty();
        for (std::size_t i = 1; i < scope.size() && all; ++i) {
            const std::string er = alias_naming(project, scale_name(scope[i], reference));
            for (const std::string& phase : phases) {
                if (phase == reference) {
                    continue;
                }
                const std::string ep = alias_naming(project, scale_name(scope[i], phase));
                const std::string ap = alias_naming(project, scale_name(scope.front(), phase));
                all = all && !er.empty() && !ep.empty() && !ap.empty() &&
                      constraint_with(project, ratio_expression(ep, er, ap, ar)) != nullptr;
            }
        }
        if (all) {
            return true;
        }
    }
    return false;
}

void share_phase_ratios(Project& project, const std::string& experiment, bool on) {
    const std::vector<std::string> scope = sharing_scope(project, experiment);
    const BraggPdExperiment* leader = experiment_named(project, scope.front());
    const std::vector<std::string> phases = linked_ids(*leader);
    if (!on) {
        // Every ratio constraint the switch wrote in the scope, whatever reference it was turned on with.
        for (const std::string& reference : phases) {
            const std::string ar = alias_naming(project, scale_name(scope.front(), reference));
            for (std::size_t i = 1; i < scope.size() && !ar.empty(); ++i) {
                const std::string er = alias_naming(project, scale_name(scope[i], reference));
                for (const std::string& phase : phases) {
                    const std::string ep = alias_naming(project, scale_name(scope[i], phase));
                    const std::string ap = alias_naming(project, scale_name(scope.front(), phase));
                    if (phase != reference && !er.empty() && !ep.empty() && !ap.empty()) {
                        remove_constraint(project, ratio_expression(ep, er, ap, ar));
                    }
                }
            }
        }
        for (const std::string& member : scope) {
            for (const std::string& phase : phases) {
                const std::string id = alias_naming(project, scale_name(member, phase));
                if (!id.empty()) {
                    remove_unused_alias(project, id);
                }
            }
        }
        refresh_relations(project);
        return;
    }
    if (phases.size() < 2) {
        throw std::invalid_argument("experiment '" + scope.front() +
                                    "' links one structure, so there are no phase ratios to share");
    }
    for (std::size_t i = 1; i < scope.size(); ++i) {
        const BraggPdExperiment* member = experiment_named(project, scope[i]);
        if (member == nullptr || linked_ids(*member) != phases) {
            throw std::invalid_argument("the experiments link different structures, so their phase ratios "
                                        "cannot be shared");
        }
    }
    const std::optional<std::string> reference = reference_structure(*leader);
    if (!reference) {
        throw std::invalid_argument("Give a phase of the template a starting scale first");
    }
    Added added;
    const std::string ar = ensure_alias(project, scale_name(scope.front(), *reference), added);
    for (std::size_t i = 1; i < scope.size(); ++i) {
        const std::string er = ensure_alias(project, scale_name(scope[i], *reference), added);
        for (const std::string& phase : phases) {
            if (phase == *reference) {
                continue;
            }
            const std::string ep = ensure_alias(project, scale_name(scope[i], phase), added);
            const std::string ap = ensure_alias(project, scale_name(scope.front(), phase), added);
            add_constraint(project, ep, ratio_expression(ep, er, ap, ar), added);
        }
    }
    settle(project, added);
}

namespace {

std::optional<std::string> unique_name_of(const Project& project, const Parameter& parameter) {
    for (const NamedParameter& named : named_parameters(project)) {
        if (named.parameter == &parameter) {
            return named.unique_name;
        }
    }
    return std::nullopt;
}

}  // namespace

namespace {

std::optional<std::size_t> shared_row(const Project& project, const std::string& name) {
    for (std::size_t i = 0; i < project.sequential_fit.shared.size(); ++i) {
        if (project.sequential_fit.shared[i]->parameter_unique_name.value() == name) {
            return i;
        }
    }
    return std::nullopt;
}

// The experiment a unique name belongs to, and the rest of the name after its datablock; none for a name outside every
// experiment (a structure's).
std::optional<std::pair<std::string, std::string>> experiment_part(const Project& project, const std::string& name) {
    for (const auto& experiment : project.experiments) {
        const std::string prefix = experiment->name + ".";
        if (name.rfind(prefix, 0) == 0) {
            return std::make_pair(experiment->name, name.substr(prefix.size()));
        }
    }
    return std::nullopt;
}

// ADR-0107: the shared names take effect in the parametric fit of a scan and in a joint fit; in every other mode they
// are kept and do nothing.
bool active(const Project& project) {
    return project.sequential_fit.declared() ? project.fitting_mode == "parametric" : project.fitting_mode == "joint";
}

// ADR-0107: in a scan a name is its own group (the points repeat it); in a joint fit the group is the same path in every
// experiment, kept under the first experiment in project order holding it as an independent parameter.
std::string group_key(const Project& project, const std::vector<NamedParameter>& named, const std::string& name) {
    if (project.sequential_fit.declared()) {
        return name;
    }
    const auto part = experiment_part(project, name);
    if (!part) {
        return name;
    }
    // Where sharing takes no effect, a group keeps the name it is listed under while that copy can lead it, so an
    // inactive declaration is saved as written whatever order the experiments come back in.
    if (!active(project)) {
        for (const auto& row : project.sequential_fit.shared) {
            const std::string& listed = row->parameter_unique_name.value();
            const auto other = experiment_part(project, listed);
            if (!other || other->second != part->second) continue;
            for (const NamedParameter& each : named) {
                if (each.unique_name == listed) return listed;
            }
        }
    }
    for (const auto& experiment : project.experiments) {
        const std::string candidate = experiment->name + "." + part->second;
        for (const NamedParameter& each : named) {
            if (each.unique_name == candidate) {
                return candidate;
            }
        }
    }
    return name;
}

std::vector<Parameter*> group_members(Project& project, const std::string& key) {
    std::vector<Parameter*> members;
    const auto part = project.sequential_fit.declared() ? std::nullopt : experiment_part(project, key);
    for (const NamedSlot& slot : named_slots(project)) {
        if (slot.parameter->dependence != Dependence::Independent) {
            continue;
        }
        if (part ? experiment_part(project, slot.unique_name) &&
                       experiment_part(project, slot.unique_name)->second == part->second
                 : slot.unique_name == key) {
            members.push_back(slot.parameter);
        }
    }
    return members;
}

}  // namespace

namespace {

// A parameter's unique name, a dependent's included.
std::optional<std::string> any_name_of(const Project& project, const Parameter& parameter) {
    for (const NamedParameter& named : named_parameters(project)) {
        if (named.parameter == &parameter) return named.unique_name;
    }
    for (const NamedParameter& named : named_dependents(project)) {
        if (named.parameter == &parameter) return named.unique_name;
    }
    return std::nullopt;
}

// How many experiments hold `path` (a unique name without its datablock), as a parameter or a dependent.
std::size_t holders_of(const Project& project, const std::string& path) {
    std::set<std::string> experiments;
    const auto count = [&](const std::vector<NamedParameter>& list) {
        for (const NamedParameter& named : list) {
            const auto part = experiment_part(project, named.unique_name);
            if (part && part->second == path) experiments.insert(part->first);
        }
    };
    count(named_parameters(project));
    count(named_dependents(project));
    return experiments.size();
}

// The id of the user constraint that sets `name` (its left-hand alias names it), or empty.
std::string constraint_setting(const Project& project, const std::string& name) {
    const auto trimmed = [](std::string text) {
        const auto first = text.find_first_not_of(" \t");
        const auto last = text.find_last_not_of(" \t");
        return first == std::string::npos ? std::string() : text.substr(first, last - first + 1);
    };
    for (const auto& constraint : project.constraints) {
        if (!constraint->enabled.get()) continue;
        const std::string& text = constraint->expression.value();
        const auto equals = text.find('=');
        if (equals == std::string::npos) continue;
        const std::string lhs = trimmed(text.substr(0, equals));
        for (const auto& alias : project.aliases) {
            if (alias->id.value() == lhs && alias->parameter_unique_name.value() == name) return constraint->id.value();
        }
    }
    return {};
}

// Why a dependent cannot be shared: the constraint that sets it, or symmetry.
std::string dependent_reason(const Project& project, const std::string& name) {
    const std::string id = constraint_setting(project, name);
    return id.empty() ? "set by symmetry" : "set by the constraint '" + id + "'";
}

}  // namespace

std::string share_refusal(const Project& project, const Parameter& parameter) {
    const std::optional<std::string> name = any_name_of(project, parameter);
    if (!name) return "only a parameter a fit can vary can be shared";
    if (project.sequential_fit.declared()) {
        return parameter.dependence == Dependence::Independent ? std::string() : dependent_reason(project, *name);
    }
    const auto part = experiment_part(project, *name);
    if (!part || holders_of(project, part->second) < 2) return "already one value for all experiments";
    // Shared never changes a user constraint (owner, 2026-11-26): a copy any of them sets keeps the whole group out.
    for (const NamedParameter& dependent : named_dependents(project)) {
        const auto other = experiment_part(project, dependent.unique_name);
        if (other && other->second == part->second) return dependent_reason(project, dependent.unique_name);
    }
    return {};
}

bool parametric_shared(const Project& project, const Parameter& parameter) {
    if (project.sequential_fit.shared.empty()) {
        return false;
    }
    const std::vector<NamedParameter> named = named_parameters(project);
    for (const NamedParameter& each : named) {
        if (each.parameter == &parameter) {
            return shared_row(project, group_key(project, named, each.unique_name)).has_value();
        }
    }
    return false;
}

std::vector<Parameter*> shared_group(Project& project, Parameter& parameter) {
    const std::vector<NamedParameter> named = named_parameters(project);
    for (const NamedParameter& each : named) {
        if (each.parameter == &parameter) {
            const std::string key = group_key(project, named, each.unique_name);
            if (active(project) && shared_row(project, key)) {
                return group_members(project, key);
            }
        }
    }
    return {&parameter};
}

void set_parametric_shared(Project& project, Parameter& parameter, bool shared) {
    if (shared) {
        if (const std::string refusal = share_refusal(project, parameter); !refusal.empty()) {
            const std::optional<std::string> any = any_name_of(project, parameter);
            throw std::invalid_argument((any ? *any : std::string("parameter")) + " cannot be shared: " + refusal);
        }
    }
    const std::optional<std::string> name = unique_name_of(project, parameter);
    if (!name) {
        if (shared) {
            throw std::invalid_argument("only a parameter of the project that a fit can vary can be shared");
        }
        return;
    }
    const std::string key = group_key(project, named_parameters(project), *name);
    if (!shared) {
        if (const std::optional<std::size_t> row = shared_row(project, key)) {
            project.sequential_fit.shared.erase_at(*row);
        }
        return;
    }
    if (!shared_row(project, key)) {
        ParametricSharedParameter row;
        row.parameter_unique_name = key;
        project.sequential_fit.shared.push_back(std::move(row));
    }
    // One value and one free flag for the group: the shown row's (only where sharing takes effect).
    if (!active(project)) {
        return;
    }
    const std::vector<Parameter*> members = group_members(project, key);
    const Parameter& source = parameter;
    const double value = source.value.get();
    const bool free = source.free.get();
    for (Parameter* member : members) {
        if (member != &source) {
            assign_value(*member, value);
            member->free = free;
        }
    }
}

bool set_group_free(Project& project, Parameter& parameter, bool free) {
    bool done = true;
    for (Parameter* member : shared_group(project, parameter)) {
        done = set_free(*member, free) && done;
    }
    return done;
}

void set_group_value(Project& project, Parameter& parameter, double value) {
    for (Parameter* member : shared_group(project, parameter)) {
        assign_value(*member, value);
    }
}

std::vector<std::string> settle_parametric_shared(Project& project) {
    std::vector<std::string> notes;
    const std::vector<NamedParameter> named = named_parameters(project);
    std::vector<std::string> keys;
    for (std::size_t i = 0; i < project.sequential_fit.shared.size(); ++i) {
        const std::string name = project.sequential_fit.shared[i]->parameter_unique_name.value();
        bool held = false;
        for (const NamedParameter& each : named) {
            held = held || each.unique_name == name;
        }
        if (!held) {
            notes.push_back("shared parameter '" + name + "' is not in the project or is set by a relation; dropped");
            continue;
        }
        const std::string key = group_key(project, named, name);
        if (key != name) {
            notes.push_back("shared parameter '" + name + "' is kept under its group's first experiment, '" + key + "'");
        }
        if (std::find(keys.begin(), keys.end(), key) == keys.end()) {
            keys.push_back(key);
        }
    }
    while (!project.sequential_fit.shared.empty()) {
        project.sequential_fit.shared.erase_at(project.sequential_fit.shared.size() - 1);
    }
    for (const std::string& key : keys) {
        ParametricSharedParameter row;
        row.parameter_unique_name = key;
        project.sequential_fit.shared.push_back(std::move(row));
        // The group has the leader's free flag (one flag per group), where sharing takes effect.
        const std::vector<Parameter*> members = group_members(project, key);
        if (active(project) && members.size() > 1) {
            const bool free = members.front()->free.get();
            for (Parameter* member : members) {
                if (member->free.get() != free) {
                    notes.push_back("shared parameter '" + key + "': every experiment takes its free flag");
                    break;
                }
            }
            for (Parameter* member : members) {
                member->free = free;
            }
        }
    }
    // ADR-0107: a start for a name the project does not hold, a dependent's or a shared parameter's is dropped (a shared
    // parameter's one value is the template's).
    for (std::size_t i = project.sequential_fit.starts.size(); i-- > 0;) {
        const std::string name = project.sequential_fit.starts[i]->parameter_unique_name.value();
        bool held = false;
        for (const NamedParameter& each : named) held = held || each.unique_name == name;
        const char* why = !held ? "is not in the project or is set by a relation"
                          : shared_row(project, group_key(project, named, name)) ? "is shared, so its one value is the "
                                                                                    "template's"
                                                                                  : nullptr;
        if (why != nullptr) {
            notes.push_back("start for '" + name + "' at point '" + project.sequential_fit.starts[i]->point.value() +
                            "' dropped: it " + why);
            project.sequential_fit.starts.erase_at(i);
        }
    }
    return notes;
}

std::vector<std::pair<std::string, std::size_t>> experiment_shared_paths(const Project& project) {
    std::vector<std::pair<std::string, std::size_t>> found;
    const auto trimmed = [](std::string text) {
        const auto first = text.find_first_not_of(" \t");
        const auto last = text.find_last_not_of(" \t");
        return first == std::string::npos ? std::string() : text.substr(first, last - first + 1);
    };
    const auto aliased = [&project](const std::string& id) -> std::optional<std::string> {
        for (const auto& alias : project.aliases) {
            if (alias->id.value() == id) return alias->parameter_unique_name.value();
        }
        return std::nullopt;
    };
    for (const auto& constraint : project.constraints) {
        if (!constraint->enabled.get()) continue;
        const std::string& text = constraint->expression.value();
        const auto equals = text.find('=');
        if (equals == std::string::npos) continue;
        const auto lhs = aliased(trimmed(text.substr(0, equals)));
        const auto rhs = aliased(trimmed(text.substr(equals + 1)));
        if (!lhs || !rhs) continue;
        const auto member = experiment_part(project, *lhs);
        const auto leader = experiment_part(project, *rhs);
        if (!member || !leader || member->first == leader->first || member->second != leader->second) continue;
        bool listed = false;
        for (const auto& [path, place] : found) listed = listed || path == leader->second;
        if (listed) continue;
        for (std::size_t i = 0; i < project.experiments.size(); ++i) {
            if (project.experiments[i]->name == leader->first) found.emplace_back(leader->second, i);
        }
    }
    return found;
}

}  // namespace edi
