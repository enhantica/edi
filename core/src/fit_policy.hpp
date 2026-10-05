// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_FIT_POLICY_HPP
#define EDI_FIT_POLICY_HPP

// edi-side refinement policy (lifted verbatim out of adapter.cpp): what a refinement request is
// REFUSED for before any engine contact (ADR-0003 pt 5 — a structured error, never a partial or
// silent result), the site-identity rule, the bounds a fit runs under, and how a resolved result
// is written back onto the model. Everything here operates on edi value types only, so it sits on
// edi's side of the ADR-0003 line and is unit-testable without the engine. core/src-private
// (never installed): these are the adapter's own rules, not product surface. The one-call
// `Project::fit*` sourcing overloads are defined in fit_policy.cpp for the same reason — they
// read the model's embedded data and delegate; they touch no crysta type.

#include <cstddef>
#include <vector>

#include "edi/model.hpp"
#include "parameter_paths.hpp"

namespace edi::detail {

// Project::fit(grid, observed, sigma, ...) boundary checks: empty or ragged measured data, a
// structure with no atom sites.
void validate_fit_request(const std::vector<double>& grid, const std::vector<double>& observed,
                             const std::vector<double>& sigma, const Project& project);

// Project::fit_joint(patterns, ...) boundary checks: no experiments, a pattern/bank count
// mismatch, no atom sites, an unusable bank identity (empty / delimiter / duplicate / site-colliding
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
