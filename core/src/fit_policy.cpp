// SPDX-License-Identifier: BSD-3-Clause
#include "fit_policy.hpp"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <cstddef>
#include <deque>
#include <map>
#include <optional>
#include <tuple>
#include <utility>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

#include "crysta/expression.hpp"
#include "crysta/model.hpp"
#include "edi/background_estimate.hpp"
#include "edi/model.hpp"
#include "edi/categories.hpp"
#include "edi/fittability.hpp"
#include "edi/io.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/selectors.hpp"

// Lifted verbatim out of adapter.cpp; see the header for what this file is.

namespace edi {

namespace detail {

// The structures taking part in a fit are those its enabled links name, resolved by crysta on the very
// project the fit builds (crysta::fit_participants), so this check and the provider see the same set.
void require_populated_participants(const crysta::Project& project, const char* surface) {
    for (const crysta::Structure* structure : crysta::fit_participants(project)) {
        if (structure->atom_sites.empty()) {
            throw std::invalid_argument(std::string(surface) + ": structure has no atom sites ('" +
                                        detail::printable_id(structure->name.value()) + "')");
        }
    }
}

// --- V3: identity rejection --------------------------------------------------------------------
void validate_fit_request(const std::vector<double>& grid, const std::vector<double>& observed,
                             const std::vector<double>& sigma, const Project& project) {
    if (grid.empty() || observed.empty() || sigma.empty()) {
        throw std::invalid_argument("edi fit: empty measured data (grid/observed/sigma)");
    }
    if (grid.size() != observed.size() || grid.size() != sigma.size()) {
        throw std::invalid_argument(
            "edi fit: measured data columns (grid, observed, sigma) must have equal length");
    }
}

void validate_joint_request(const Project& project,
                            const ItemVec<BraggPdExperiment>& experiments,
                            const std::vector<PdDataBase>& patterns) {
    if (experiments.empty()) {
        throw std::invalid_argument("edi fit_joint: project has no experiments (load a project "
                                    "directory, or use fit() for a single bank)");
    }
    if (patterns.size() != experiments.size()) {
        throw std::invalid_argument(
            "edi fit_joint: expected one measured pattern per experiment (" +
            std::to_string(experiments.size()) + " banks, got " + std::to_string(patterns.size()) +
            " patterns)");
    }
    // Bank identity: the name is the engine's joint label prefix AND edi's own result key, so an
    // empty, duplicated, delimiter-carrying, or site-colliding name would make a refined parameter's
    // identity ambiguous. Rejected up front, which is what keeps the result mapping total.
    std::map<std::string, std::size_t> seen;
    for (std::size_t bank = 0; bank < experiments.size(); ++bank) {
        const std::string& name = experiments[bank]->name;
        if (name.empty()) {
            throw std::invalid_argument("edi fit_joint: experiment " + std::to_string(bank) +
                                        " has an empty name (a bank name identifies its refined "
                                        "parameters)");
        }
        if (name.find_first_of(".[]") != std::string::npos) {
            throw std::invalid_argument("edi fit_joint: experiment name '" +
                                        detail::printable_id(name) +
                                        "' contains a reserved delimiter ('.', '[' or ']')");
        }
        if (const auto [it, inserted] = seen.emplace(name, bank); !inserted) {
            throw std::invalid_argument("edi fit_joint: duplicate experiment name '" +
                                        detail::printable_id(name) + "' (banks " +
                                        std::to_string(it->second) + " and " +
                                        std::to_string(bank) + ")");
        }
        for (const auto& structure : project.structures) {
            for (const auto& atom_item : structure->atom_sites) {
                if (atom_item->id == name) {
                    throw std::invalid_argument("edi fit_joint: experiment name '" +
                                                detail::printable_id(name) +
                                                "' collides with an atom site label");
                }
            }
            // With several structures, labels start with the structure's name as well.
            if (project.structures.size() > 1 && structure->name.value() == name) {
                throw std::invalid_argument("edi fit_joint: experiment name '" + detail::printable_id(name) +
                                            "' collides with a structure name");
            }
        }
        const PdDataBase& pattern = patterns[bank];
        const std::vector<double>& axis_values = pattern.axis();  // fails closed on none-or-both
        if (axis_values.empty() || pattern.intensity_meas.empty() ||
            pattern.intensity_meas_su.empty()) {
            throw std::invalid_argument("edi fit_joint: empty measured data for bank '" + name +
                                        "' (axis/intensity_meas/intensity_meas_su)");
        }
        if (axis_values.size() != pattern.intensity_meas.size() ||
            axis_values.size() != pattern.intensity_meas_su.size()) {
            throw std::invalid_argument(
                "edi fit_joint: measured data columns (axis, intensity_meas, "
                "intensity_meas_su) must have equal length for bank '" + name + "'");
        }
    }
}

double reduced_chi_square_dof(std::size_t n_data, std::size_t n_free) {
    return static_cast<double>(n_data > n_free ? n_data - n_free : std::size_t{1});
}

int bounded_max_iterations(int declared) { return declared > 0 ? declared : 50; }

void write_back(const std::vector<RefinedValue>& refined) {
    for (const RefinedValue& item : refined) {
        // Capture the pre-fit snapshot (upstream `_capture_fit_parameter_state`) before the
        // refined write — the edi model is untouched while the engine fits its throwaway crysta
        // project, so the target still holds its fit-start state here. Single-level: a new fit
        // overwrites the previous snapshot, as upstream's fit-undo does.
        item.resolved.target->start_value = item.resolved.target->value;
        // Review-1 F2: carry the optional through — an absent pre-fit uncertainty must undo
        // back to absent, not to a measured-looking 0.0. The writer already emits '.' for a
        // disengaged optional and the reader maps '.' back, so absence round-trips as-is.
        item.resolved.target->start_uncertainty = item.resolved.target->uncertainty;
        item.resolved.target->value = item.value;
        // An undefined s.u. (crysta's NaN for a singular covariance) leaves it without one.
        item.resolved.target->uncertainty =
            std::isfinite(item.uncertainty) ? std::optional<double>(item.uncertainty) : std::nullopt;
    }
}

}  // namespace detail

int default_max_iterations() { return detail::bounded_max_iterations(0); }

// The one-call forms. These are pure sourcing wrappers: they pull each bank's pattern from the
// model's own embedded data and delegate to the provider-building overloads (adapter.cpp), so there
// is exactly one fit path and a one-call refinement is result-identical to the explicit-pattern one
// by construction.
//
// The missing-data guard is the residual case for a hand-assembled experiment; a loaded fit-ready
// project cannot reach it, because the one loader already proved every bank carries measured data.
// A calculation-only bank (a `_data_range`-generated grid) refuses here too: the project's own
// contents selected calculate, so a fit on it is a caller error, never a data accident.
namespace {

bool has_measured_data(const ExperimentBase& experiment) {
    return (experiment.data.has_value() || experiment.reflections.has_value()) && !experiment.calculation_only;
}

// Experiments with measured data beside experiments without (a simulation made with Create experiment).
bool mixed_experiments(const Project& project) {
    return std::any_of(project.experiments.begin(), project.experiments.end(),
                       [](const auto& e) { return has_measured_data(*e); }) &&
           std::any_of(project.experiments.begin(), project.experiments.end(),
                       [](const auto& e) { return !has_measured_data(*e); });
}

// A parameter's place in the model, the same in a project and in a copy holding fewer experiments: its identity
// path is not, since one experiment is `experiment.*` and several are `experiments[name].*`.
using ParameterKey = std::tuple<std::string, std::string, std::string, std::string, std::string>;
ParameterKey key_of(const ParameterEntry& entry) {
    return {entry.block_kind, entry.block_name, entry.category, entry.row_label, entry.name};
}

std::map<std::string, double> translated(const std::map<std::string, double>& values,
                                         const std::map<std::string, std::string>& paths) {
    std::map<std::string, double> out;
    for (const auto& [path, value] : values) {
        const auto found = paths.find(path);
        out.emplace(found != paths.end() ? found->second : path, value);
    }
    return out;
}

// A fit of a mixed project leaves the simulations out. It runs on a copy holding only the measured
// experiments; every parameter it wrote (value, uncertainty, fit start) is copied back by its place in the model,
// the paths it reports are translated to the project's own, its fit records are copied by experiment name, and the
// project's calculated patterns are then refreshed at the fitted values, as every fit completes. A relation naming a
// simulation's parameter refuses the fit, since the fit cannot see it. Any other project fits itself.
template <typename Fit>
FitResultBase fit_measured_experiments(Project& project, const IterationCallback& on_iteration, Fit fit) {
    Project measured = project;
    std::vector<ItemVec<BraggPdExperiment>::Ptr> kept;
    for (const auto& experiment : measured.experiments) {
        if (has_measured_data(*experiment)) {
            kept.push_back(experiment);
        }
    }
    measured.experiments.assign(std::move(kept));
    std::set<std::string> visible;
    for (const NamedSlot& slot : named_slots(measured)) {
        visible.insert(slot.unique_name);
    }
    for (const auto& alias : project.aliases) {
        if (!visible.contains(alias->parameter_unique_name.value())) {
            throw std::invalid_argument("edi fit: the alias '" + alias->id.value() + "' names '" +
                                        alias->parameter_unique_name.value() +
                                        "', a parameter of an experiment without measured data, which a fit leaves out");
        }
    }
    std::map<ParameterKey, const ParameterEntry*> by_key;
    const std::vector<ParameterEntry> targets = parameter_entries(project);
    for (const ParameterEntry& entry : targets) {
        by_key.emplace(key_of(entry), &entry);
    }
    const std::vector<ParameterEntry> sources = parameter_entries(measured);
    std::map<std::string, std::string> paths;  // the copy's path -> the project's
    for (const ParameterEntry& entry : sources) {
        if (const auto found = by_key.find(key_of(entry)); found != by_key.end()) {
            paths.emplace(entry.path, found->second->path);
        }
    }
    IterationCallback forward;
    if (on_iteration) {
        forward = [&on_iteration, &paths](const IterationRecord& record) {
            IterationRecord own = record;
            own.values = translated(record.values, paths);
            on_iteration(own);
        };
    }
    FitResultBase result = fit(measured, forward);
    for (const ParameterEntry& entry : sources) {
        const auto found = by_key.find(key_of(entry));
        if (found == by_key.end() || found->second->parameter == nullptr || entry.parameter == nullptr) {
            continue;
        }
        Parameter& target = *found->second->parameter;
        const Parameter& source = *entry.parameter;
        if (target.value.get() != source.value.get()) {
            target.value = source.value.get();
            target.epoch = detail::Epoch();
        }
        target.uncertainty = source.uncertainty.get();
        target.start_value = source.start_value.get();
        target.start_uncertainty = source.start_uncertainty.get();
    }
    result.values = translated(result.values, paths);
    result.uncertainty = translated(result.uncertainty, paths);
    result.start = translated(result.start, paths);
    project.fit_result = measured.fit_result;
    for (const auto& target : project.experiments) {
        for (const auto& source : measured.experiments) {
            if (source->name.value() == target->name.value()) {
                copy_fit_share(*target, *source);
                record_fitted_background(*target);  // the fitted values are its background now (ADR-0040)
            }
        }
    }
    project.refresh_calculated_pattern();
    return result;
}

}  // namespace

std::vector<std::size_t> fit_context(const Project& project) {
    const bool scan = fits_a_scan(project);
    const bool mixed = !scan && mixed_experiments(project);
    std::vector<std::size_t> fitted;
    for (std::size_t index = 0; index < project.experiments.size(); ++index) {
        if (!mixed || has_measured_data(*project.experiments[index])) {
            fitted.push_back(index);
        }
    }
    return fitted;
}

namespace {
// The name a refusal or a note gives a parameter: its unique name, or for one no fit names, its path.
// In the walks' order, so a load's notes come in the file's order.
std::vector<std::pair<Parameter*, std::string>> parameter_names(Project& project) {
    std::vector<std::pair<Parameter*, std::string>> names;
    std::set<const Parameter*> seen;
    for (const NamedSlot& slot : named_slots(project)) {
        if (seen.insert(slot.parameter).second) {
            names.emplace_back(slot.parameter, slot.unique_name);
        }
    }
    for (const ParameterEntry& entry : parameter_entries(project)) {
        if (seen.insert(entry.parameter).second) {
            names.emplace_back(entry.parameter, entry.path);
        }
    }
    return names;
}
}  // namespace

namespace detail {

namespace {
// A reduced chi-square in a message, to four significant digits.
std::string four_digits(double value) {
    char buffer[32];
    const auto result = std::to_chars(buffer, buffer + sizeof(buffer), value, std::chars_format::general, 4);
    return std::string(buffer, result.ptr);
}
}  // namespace

// edi ADR-0081: the independent mode without a scan. Each experiment fits alone, as a single fit of a copy holding it
// and the structures it links, every copy taken before the first fit so all start from the same values. Only when every
// fit has succeeded is each written back, as fit_measured_experiments writes its copy back, so a refused or cancelled
// run leaves the project as it was. A structure two experiments link cannot hold two results and is refused by name;
// joint mode fits such a project.
FitResultBase fit_experiments_independently(Project& project, const IterationCallback& on_iteration,
                                            const PreambleCallback& on_start, const CancelCallback& should_cancel) {
    if (project.experiments.empty()) {
        throw std::invalid_argument("edi fit_independent: the project has no experiment");
    }
    std::map<std::string, std::string> owner;  // structure name -> the experiment linking it
    for (const auto& experiment : project.experiments) {
        bool any = false;
        for (const auto& link : experiment->linked_structures) {
            if (!link->enabled.get()) {
                continue;
            }
            any = true;
            const auto [at, added] = owner.try_emplace(link->structure_id.value(), experiment->name.value());
            if (!added) {
                throw std::invalid_argument("edi fit_independent: structure '" + link->structure_id.value() +
                                            "' is linked by experiments '" + at->second + "' and '" +
                                            experiment->name.value() +
                                            "'; each experiment fits alone, so a shared structure fits in joint mode");
            }
        }
        if (!any) {
            throw std::invalid_argument("edi fit_independent: experiment '" + experiment->name.value() +
                                        "' links no structure; link one before fitting");
        }
    }
    // Each experiment's own relations: an alias belongs to the experiment whose structures or data its parameter is in,
    // an enabled constraint to the experiment of the aliases the constraint parser finds in it. One naming aliases of
    // two experiments ties their fits, so it is refused before any fit. A disabled constraint adds no relation and is
    // left out; one that does not parse, or names no known alias, goes to every fit, whose own checks report it.
    std::map<std::string, std::size_t> datablock;
    for (std::size_t e = 0; e < project.experiments.size(); ++e) {
        datablock[project.experiments[e]->name.value()] = e;
        for (const auto& link : project.experiments[e]->linked_structures) {
            if (link->enabled.get()) {
                datablock[link->structure_id.value()] = e;
            }
        }
    }
    std::map<std::string, std::optional<std::size_t>> alias_owner;
    std::map<std::string, std::string> alias_target;
    for (const auto& alias : project.aliases) {
        const std::string& name = alias->parameter_unique_name.value();
        const auto found = datablock.find(name.substr(0, name.find('.')));
        alias_owner[alias->id.value()] = found == datablock.end() ? std::nullopt : std::optional(found->second);
        alias_target[alias->id.value()] = name;
    }
    constexpr std::size_t every = static_cast<std::size_t>(-1);
    std::map<std::string, std::size_t> constraint_owner;
    for (const auto& constraint : project.constraints) {
        if (!constraint->enabled.get()) {
            continue;
        }
        const std::string& expression = constraint->expression.value();
        std::vector<std::string> names;
        try {
            const crysta::ConstraintStatement statement = crysta::parse_constraint(expression);
            names.push_back(statement.lhs);
            names.insert(names.end(), statement.rhs.references().begin(), statement.rhs.references().end());
        } catch (const crysta::ExpressionError&) {
            constraint_owner[constraint->id.value()] = every;
            continue;
        }
        std::set<std::size_t> owners;
        for (const std::string& name : names) {
            const auto found = alias_owner.find(name);
            if (found == alias_owner.end()) {
                continue;
            }
            if (!found->second) {
                throw std::invalid_argument("edi fit_independent: alias '" + name + "' names '" +
                                            alias_target.at(name) +
                                            "', a parameter of no experiment's structures or data");
            }
            owners.insert(*found->second);
        }
        if (owners.size() > 1) {
            throw std::invalid_argument("edi fit_independent: constraint '" + constraint->id.value() + "' (" +
                                        expression + ") ties parameters of experiments '" +
                                        project.experiments[*owners.begin()]->name.value() + "' and '" +
                                        project.experiments[*std::next(owners.begin())]->name.value() +
                                        "'; each experiment fits alone, so it fits in joint mode");
        }
        constraint_owner[constraint->id.value()] = owners.empty() ? every : *owners.begin();
    }
    std::map<ParameterKey, const ParameterEntry*> by_key;
    const std::vector<ParameterEntry> targets = parameter_entries(project);
    for (const ParameterEntry& entry : targets) {
        by_key.emplace(key_of(entry), &entry);
    }
    struct One {
        explicit One(const Project& project) : copy(project) {}
        Project copy;
        std::map<std::string, std::string> paths;  // the copy's path -> the project's
        FitResultBase result;
        bool fitted = false;  // an experiment with nothing free is left as it is
    };
    std::deque<One> fits;  // each copy built in place, never moved
    for (std::size_t e = 0; e < project.experiments.size(); ++e) {
        One& one = fits.emplace_back(project);
        Project& copy = one.copy;
        std::vector<ItemVec<BraggPdExperiment>::Ptr> experiment{copy.experiments[e]};
        std::vector<ItemVec<Structure>::Ptr> structures;
        for (const auto& structure : copy.structures) {
            for (const auto& link : copy.experiments[e]->linked_structures) {
                if (link->enabled.get() && link->structure_id.value() == structure->name.value()) {
                    structures.push_back(structure);
                    break;
                }
            }
        }
        copy.experiments.assign(std::move(experiment));
        copy.structures.assign(std::move(structures));
        copy.fitting_mode = "single";
        std::vector<ItemVec<ParameterAlias>::Ptr> own_aliases;
        for (const auto& alias : copy.aliases) {
            if (alias_owner.at(alias->id.value()) == e) {
                own_aliases.push_back(alias);
            }
        }
        copy.aliases.assign(std::move(own_aliases));
        std::vector<ItemVec<ParameterConstraint>::Ptr> own_constraints;
        for (const auto& constraint : copy.constraints) {
            const auto owner = constraint_owner.find(constraint->id.value());
            if (owner != constraint_owner.end() && (owner->second == e || owner->second == every)) {
                own_constraints.push_back(constraint);
            }
        }
        copy.constraints.assign(std::move(own_constraints));
        for (const ParameterEntry& entry : parameter_entries(copy)) {
            if (const auto found = by_key.find(key_of(entry)); found != by_key.end()) {
                one.paths.emplace(entry.path, found->second->path);
            }
        }
    }
    for (One& one : fits) {
        const std::vector<ParameterEntry> entries = parameter_entries(one.copy);
        one.fitted = std::any_of(entries.begin(), entries.end(), [](const ParameterEntry& entry) {
            return entry.parameter != nullptr && entry.parameter->free.get();
        });
    }
    if (std::none_of(fits.begin(), fits.end(), [](const One& one) { return one.fitted; })) {
        throw std::invalid_argument("edi fit_independent: no free parameters (mark parameters refinable via their free flags)");
    }
    for (One& one : fits) {
        if (!one.fitted) {
            continue;
        }
        IterationCallback forward;
        if (on_iteration) {
            forward = [&on_iteration, &one](const IterationRecord& record) {
                IterationRecord own = record;
                own.values = translated(record.values, one.paths);
                on_iteration(own);
            };
        }
        const std::string name = one.copy.experiment().name.value();
        try {
            one.result = one.copy.fit(forward, on_start, should_cancel);
        } catch (const std::invalid_argument& error) {
            throw std::invalid_argument("edi fit_independent, experiment '" + name + "': " + error.what());
        }
        if (one.result.status == FitStatus::CANCELLED || one.result.status == FitStatus::SUPERSEDED) {
            return one.result;  // nothing is written back
        }
    }
    FitResultBase combined;
    combined.status = FitStatus::DONE;
    FitResultRecord record;
    double chi_square = 0.0;
    double weight = 0.0;
    bool pooled_rwp = true;
    bool first = true;
    int dof = 0;
    std::string message;
    for (One& one : fits) {
        if (!one.fitted) {
            continue;
        }
        for (const ParameterEntry& entry : parameter_entries(one.copy)) {
            const auto found = by_key.find(key_of(entry));
            if (found == by_key.end() || found->second->parameter == nullptr || entry.parameter == nullptr) {
                continue;
            }
            Parameter& target = *found->second->parameter;
            const Parameter& source = *entry.parameter;
            if (target.value.get() != source.value.get()) {
                target.value = source.value.get();
                target.epoch = detail::Epoch();
            }
            target.uncertainty = source.uncertainty.get();
            target.start_value = source.start_value.get();
            target.start_uncertainty = source.start_uncertainty.get();
        }
        const BraggPdExperiment& fitted = one.copy.experiment();
        for (const auto& target : project.experiments) {
            if (target->name.value() == fitted.name.value()) {
                copy_fit_share(*target, fitted);
                record_fitted_background(*target);
            }
        }
        const FitResultBase& result = one.result;
        for (const auto& [path, value] : translated(result.values, one.paths)) {
            combined.values[path] = value;
        }
        for (const auto& [path, value] : translated(result.uncertainty, one.paths)) {
            combined.uncertainty[path] = value;
        }
        for (const auto& [path, value] : translated(result.start, one.paths)) {
            combined.start[path] = value;
        }
        // The engine labels repeat across the experiments, so each carries its experiment's name.
        for (const auto& [label, value] : result.engine_values) {
            combined.engine_values[fitted.name.value() + "." + label] = value;
        }
        for (const auto& [label, value] : result.engine_uncertainty) {
            combined.engine_uncertainty[fitted.name.value() + "." + label] = value;
        }
        const FitResultRecord& own = one.copy.fit_result;
        const int own_dof = std::max(0, own.degrees_of_freedom);
        const double own_chi = own.reduced_chi_square.value_or(0.0) * static_cast<double>(own_dof);
        combined.banks.push_back({fitted.name.value(), result.n_points_fitted, result.rwp, own_chi});
        if (result.rwp > 0.0 && own_chi > 0.0) {
            weight += own_chi / (result.rwp * result.rwp);  // sum of w F2obs^2, from chi2 / wR^2
        } else {
            pooled_rwp = false;
        }
        if (combined.status == FitStatus::DONE && result.status != FitStatus::DONE) {
            combined.status = result.status;
        }
        // Each experiment's iterations, numbered on from the previous experiment's, in project order.
        if (combined.iterations_history.empty()) {
            combined.pre_fit = result.pre_fit;
        }
        for (IterationRecord record : result.iterations_history) {
            record.iteration = static_cast<int>(combined.iterations_history.size()) + 1;
            record.elapsed_ms += combined.elapsed_ms;
            combined.iterations_history.push_back(std::move(record));
        }
        combined.iterations += result.iterations;
        combined.n_points_loaded += result.n_points_loaded;
        combined.n_points_fitted += result.n_points_fitted;
        combined.elapsed_ms += result.elapsed_ms;
        combined.unevaluable_trials += result.unevaluable_trials;
        combined.terminal_unevaluable_trials += result.terminal_unevaluable_trials;
        combined.descent = result.descent;
        // The gain-ratio damping finished every experiment, or the combined record does not claim it:
        // when the default descent continued with fast descent in one experiment and the ladder in
        // another, the flag says false, the same as for a ladder fit.
        combined.fast_descent = (first || combined.fast_descent) && result.fast_descent;
        chi_square += own_chi;
        dof += own_dof;
        record.n_data_points += own.n_data_points;
        record.n_parameters += own.n_parameters;
        record.n_free_parameters += own.n_free_parameters;
        record.fitting_time += own.fitting_time;
        record.covariance_available = (first || record.covariance_available) && own.covariance_available;
        first = false;
        for (const auto& row : own.correlations) {
            FitParameterCorrelation copy = *row;
            copy.id = std::to_string(record.correlations.size() + 1);
            record.correlations.push_back(std::move(copy));
        }
        message += (message.empty() ? "" : "; ") + fitted.name.value() + ": " + own.exit_reason +
                   ", reduced chi-square " +
                   (own.reduced_chi_square ? four_digits(*own.reduced_chi_square) : std::string("undefined"));
        record.descent = own.descent;
    }
    combined.converged = combined.status == FitStatus::DONE;
    combined.mode = "independent";
    combined.rwp = pooled_rwp && weight > 0.0 ? std::sqrt(chi_square / weight) : 0.0;
    combined.reduced_chi_square = dof > 0 ? chi_square / dof : 0.0;
    record.result_kind = "deterministic";
    record.success = combined.status == FitStatus::DONE;
    record.exit_reason = "done";
    for (const One& one : fits) {
        if (one.fitted && !one.copy.fit_result.success) {
            record.exit_reason = one.copy.fit_result.exit_reason;
            break;
        }
    }
    record.message = message;
    record.iterations = combined.iterations;
    record.reduced_chi_square = dof > 0 ? std::optional<double>(chi_square / dof) : std::nullopt;
    record.objective_name = "chi_square";
    record.objective_value = chi_square;
    record.degrees_of_freedom = dof;
    if (combined.rwp > 0.0) {
        record.prof_wr_factor = combined.rwp;
    }
    project.fit_result = std::move(record);
    project.refresh_calculated_pattern();
    return combined;
}

}  // namespace detail


void require_fittable_free(Project& project) {
    refresh_fittability(project);
    for (const auto& [parameter, name] : parameter_names(project)) {
        if (parameter->free.get() && !parameter->fit_idle && !free_refusal(*parameter).empty()) {
            throw std::invalid_argument(name + " " + free_refusal(*parameter));
        }
    }
}

std::vector<std::string> clear_unfittable_free(Project& project) {
    refresh_fittability(project);
    std::vector<std::string> notes;
    for (const auto& [parameter, name] : parameter_names(project)) {
        if (parameter->free.get() && !parameter->fit_idle && !free_refusal(*parameter).empty()) {
            notes.push_back(name + " " + free_refusal(*parameter) + "; loaded fixed");
            parameter->free = false;
        }
    }
    return notes;
}

FitResultBase Project::fit(const IterationCallback& on_iteration,
                           const PreambleCallback& on_start, const CancelCallback& should_cancel) {
    refresh_background_estimates(*this);  // ADR-0040: auto background mode re-estimates first
    // A sequential project reaching the single-bank one-call form would silently fit the
    // TEMPLATE's embedded data once and write no results.csv — a plausible-looking answer to a
    // different question. Refuse by name; the sequential mode has exactly one entry point.
    // Review-2 F2: every native entry serves EXACTLY its own declared mode. Refusing only the
    // scan family left `joint` succeeding here as a single-bank refine of one bank — a plausible
    // answer to a different question, which is the same defect the scan refusal exists to stop.
    // An UNDECLARED mode (empty) stays permitted: that is the historical default this entry has
    // always served, and it is not one of the four declared values.
    if (!fitting_mode.empty() && fitting_mode != "single") {
        throw std::invalid_argument(
            "edi fit: _fitting_mode.type is '" + fitting_mode +
            "' - this entry point serves exactly the 'single' mode; use analysis.fit(), which "
            "routes each declared mode to its own entry");
    }
    require_fittable_free(*this);  // ADR-0053: a free flag the fit cannot honour is refused by name
    if (mixed_experiments(*this)) {
        return fit_measured_experiments(*this, on_iteration, [&](Project& measured, const IterationCallback& forward) {
            return measured.fit(forward, on_start, should_cancel);
        });
    }
    if (experiment().linked_structures.empty()) {
        throw std::invalid_argument("edi fit: experiment '" + experiment().name +
                                    "' links no structure; link one before fitting");
    }
    if (experiment().reflections.has_value()) {  // a single crystal fits its own reflections
        return fit({}, {}, {}, on_iteration, on_start, should_cancel);
    }
    if (!experiment().data.has_value() || experiment().calculation_only) {
        throw std::invalid_argument("edi fit: experiment() '" + experiment().name +
                                    "' carries no measured data (a calculation-only or "
                                    "hand-assembled experiment cannot fit; pass the pattern "
                                    "explicitly to refine with one)");
    }
    const PdDataBase& data = *experiment().data;
    return fit(data.axis(), data.intensity_meas, data.intensity_meas_su, on_iteration, on_start,
               should_cancel);
}

FitResultBase Project::fit() { return fit(IterationCallback{}); }

FitResultBase Project::fit_joint(const IterationCallback& on_iteration,
                                 const PreambleCallback& on_start,
                                 const CancelCallback& should_cancel) {
    refresh_background_estimates(*this);  // ADR-0040: auto background mode re-estimates first
    // Review-1 F4: the third native entry point gets the same refusal as fit(). A scan
    // project reaching fit_joint() would fit the template's banks once and write no
    // results.csv — the same wrong-answer-to-a-different-question, one function along.
    if (!fitting_mode.empty() && fitting_mode != "joint") {
        throw std::invalid_argument(
            "edi fit_joint: _fitting_mode.type is '" + fitting_mode +
            "' - this entry point serves exactly the 'joint' mode; use analysis.fit(), which "
            "routes each declared mode to its own entry");
    }
    require_fittable_free(*this);  // ADR-0053
    if (experiments.empty()) {
        throw std::invalid_argument("edi fit_joint: project has no experiments");
    }
    if (mixed_experiments(*this)) {
        return fit_measured_experiments(*this, on_iteration, [&](Project& measured, const IterationCallback& forward) {
            return measured.fit_joint(forward, on_start, should_cancel);
        });
    }
    // Single crystals fit together over their one structure from their own reflections: no pattern crosses.
    const bool single_crystals = std::all_of(experiments.begin(), experiments.end(),
                                             [](const auto& bank) { return bank->reflections.has_value(); });
    std::vector<PdDataBase> patterns;
    patterns.reserve(experiments.size());
    for (const auto& bank_item : experiments) {
        const ExperimentBase& bank = *bank_item;
        if (bank.linked_structures.empty()) {
            throw std::invalid_argument("edi fit_joint: experiment '" + bank.name +
                                        "' links no structure; link one before fitting");
        }
        if (single_crystals) {
            continue;
        }
        if (bank.reflections.has_value()) {
            throw std::invalid_argument("edi fit_joint: experiment '" + bank.name +
                                        "' is a single crystal, which fits only with single crystals; fit the "
                                        "powder experiments in a project of their own");
        }
        if (!bank.data.has_value() || bank.calculation_only) {
            throw std::invalid_argument("edi fit_joint: experiment '" + bank.name +
                                        "' carries no measured data (a calculation-only or "
                                        "hand-assembled experiment cannot fit; pass the patterns "
                                        "explicitly to refine with them)");
        }
        patterns.push_back(*bank.data);
    }
    return fit_joint(patterns, on_iteration, on_start, should_cancel);
}

FitResultBase Project::fit_joint() { return fit_joint(IterationCallback{}); }

}  // namespace edi
