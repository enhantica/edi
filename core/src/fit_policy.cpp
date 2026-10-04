// SPDX-License-Identifier: BSD-3-Clause
#include "fit_policy.hpp"

#include <cstddef>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

#include "edi/model.hpp"

// Lifted verbatim out of adapter.cpp; see the header for what this file is.

namespace edi {

namespace detail {

// --- V3: identity rejection --------------------------------------------------------------------
void validate_fit_request(const std::vector<double>& grid, const std::vector<double>& observed,
                             const std::vector<double>& sigma, const Structure& structure) {
    if (grid.empty() || observed.empty() || sigma.empty()) {
        throw std::invalid_argument("edi fit: empty measured data (grid/observed/sigma)");
    }
    if (grid.size() != observed.size() || grid.size() != sigma.size()) {
        throw std::invalid_argument(
            "edi fit: measured data columns (grid, observed, sigma) must have equal length");
    }
    if (structure.atom_sites.empty()) {
        throw std::invalid_argument("edi fit: structure has no atom sites");
    }
}

void validate_joint_request(const Structure& structure,
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
    if (structure.atom_sites.empty()) {
        throw std::invalid_argument("edi fit_joint: structure has no atom sites");
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
        for (const auto& atom_item : structure.atom_sites) {
            const AtomSite& atom = *atom_item;
            if (atom.id == name) {
                throw std::invalid_argument("edi fit_joint: experiment name '" +
                                            detail::printable_id(name) +
                                            "' collides with an atom site label");
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
    std::vector<PdDataBase> patterns;
    patterns.reserve(experiments.size());
    for (const auto& bank_item : experiments) {
        const ExperimentBase& bank = *bank_item;
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
