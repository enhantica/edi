// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_FIT_POLICY_HPP
#define EDI_FIT_POLICY_HPP

// edi-side refinement policy (lifted verbatim out of adapter.cpp): what a refinement request is
// REFUSED for before any engine contact (ADR-0003 pt 5 — a structured error, never a partial or
// silent result), the site-identity rule, the bounds a fit runs under, and how a resolved result
// is written back onto the model. Everything here operates on edi value types, except
// require_populated_participants: which structures take part in a fit is the engine's answer, so
// that one rule reads the crysta project the fit builds. core/src-private (never installed): these
// are the adapter's own rules, not product surface. The one-call `Project::fit*` sourcing overloads
// are defined in fit_policy.cpp too; they read the model's embedded data and delegate.

#include <cstddef>
#include <vector>

#include "crysta/model.hpp"
#include "edi/model.hpp"
#include "parameter_paths.hpp"

namespace edi::detail {

// Project::fit(grid, observed, sigma, ...) boundary checks: empty or ragged measured data. The atom-site
// rule is require_populated_participants, on the project the fit builds.
void validate_fit_request(const std::vector<double>& grid, const std::vector<double>& observed,
                             const std::vector<double>& sigma, const Project& project);

// The atom-site rule on exactly a fit's participants: every structure an enabled link of the fitted
// banks names, resolved by crysta on the project the fit builds. Refused by name otherwise.
void require_populated_participants(const crysta::Project& project, const char* surface);

// Project::fit_joint(patterns, ...) boundary checks: no experiments, a pattern/bank count
// mismatch, an unusable bank identity (empty / delimiter / duplicate / site-colliding
// name), empty or ragged per-bank data. `PdDataBase::axis()` fails closed on none-or-both.
void validate_joint_request(const Project& project,
                            const ItemVec<BraggPdExperiment>& experiments,
                            const std::vector<PdDataBase>& patterns);

// dof for the per-iteration reduced chi-square — the same denominator crysta's own record uses;
// never below 1.
double reduced_chi_square_dof(std::size_t n_data, std::size_t n_free);

// The project's declared `_minimizer.max_iterations` bounds the fit; absent (0) keeps the
// historical 50-iteration cap.
int bounded_max_iterations(int declared);

// One translated result entry: the resolved edi parameter + the refined value and its e.s.d.
struct RefinedValue {
    ResolvedParameter resolved;
    double value;
    double uncertainty;
};

// Write the refined value/esd back onto the edi model Parameters (every label already resolved).
void write_back(const std::vector<RefinedValue>& refined);

}  // namespace edi::detail

#endif  // EDI_FIT_POLICY_HPP
