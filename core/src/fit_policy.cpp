// SPDX-License-Identifier: BSD-3-Clause
#include "fit_policy.hpp"

#include <algorithm>
#include <cstddef>
#include <map>
#include <tuple>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

#include "crysta/model.hpp"
#include "edi/model.hpp"
#include "edi/categories.hpp"
#include "edi/parameter_walk.hpp"

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
        item.resolved.target->uncertainty = item.uncertainty;
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
    return experiment.data.has_value() && !experiment.calculation_only;
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
                target->fit_n_data_points = source->fit_n_data_points;
                target->fit_prof_wr_factor = source->fit_prof_wr_factor;
                target->fit_chi_square = source->fit_chi_square;
            }
        }
    }
    project.refresh_calculated_pattern();
    return result;
}

}  // namespace

FitResultBase Project::fit(const IterationCallback& on_iteration,
                           const PreambleCallback& on_start, const CancelCallback& should_cancel) {
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
    if (mixed_experiments(*this)) {
        return fit_measured_experiments(*this, on_iteration, [&](Project& measured, const IterationCallback& forward) {
            return measured.fit(forward, on_start, should_cancel);
        });
    }
    if (experiment().linked_structures.empty()) {
        throw std::invalid_argument("edi fit: experiment '" + experiment().name +
                                    "' links no structure; link one before fitting");
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
    // Review-1 F4: the third native entry point gets the same refusal as fit(). A scan
    // project reaching fit_joint() would fit the template's banks once and write no
    // results.csv — the same wrong-answer-to-a-different-question, one function along.
    if (!fitting_mode.empty() && fitting_mode != "joint") {
        throw std::invalid_argument(
            "edi fit_joint: _fitting_mode.type is '" + fitting_mode +
            "' - this entry point serves exactly the 'joint' mode; use analysis.fit(), which "
            "routes each declared mode to its own entry");
    }
    if (experiments.empty()) {
        throw std::invalid_argument("edi fit_joint: project has no experiments");
    }
    if (mixed_experiments(*this)) {
        return fit_measured_experiments(*this, on_iteration, [&](Project& measured, const IterationCallback& forward) {
            return measured.fit_joint(forward, on_start, should_cancel);
        });
    }
    std::vector<PdDataBase> patterns;
    patterns.reserve(experiments.size());
    for (const auto& bank_item : experiments) {
        const ExperimentBase& bank = *bank_item;
        if (bank.linked_structures.empty()) {
            throw std::invalid_argument("edi fit_joint: experiment '" + bank.name +
                                        "' links no structure; link one before fitting");
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
