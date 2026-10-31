// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_FITTABILITY_HPP
#define EDI_FITTABILITY_HPP

// Which parameters a fit can vary, and why not (edi ADR-0053): crysta's one rule, read for the fits
// the project's mode runs and marked on every parameter. The pages, the Analysis table, Python, the loader and the
// fit entries read those marks; none keeps a list of its own.

#include <cstddef>
#include <string>
#include <vector>

#include "edi/model.hpp"

namespace edi {

// The experiments a fit of the project uses, by index: in the single and joint modes the ones with measured data
// when the project mixes measured and data-free experiments, else all; in a scan mode the scan's one experiment
// (a scan with more refuses at the fit).
std::vector<std::size_t> fit_context(const Project& project);

// Marks every parameter of the project with what keeps a fit of its context from varying it (Parameter::fit_blocker
// and fit_reason), by crysta's rule. A parameter crysta's model does not hold (an inert slot of the other beam mode)
// is one no fitted experiment uses. A project crysta cannot convert, or whose relations do not hold, keeps the marks
// a descriptor gives and is otherwise left fittable: its calculation or fit says why. Implemented in the adapter
// (the one crysta-touching translation unit, ADR-0003).
void refresh_fittability(Project& project);

// Whether the dictionary entry `uid` (`category.name`) is a descriptor, a value no fit ever varies.
bool is_descriptor(const std::string& uid);

// crysta's text for `blocker` ("a descriptor, never fitted", "set by symmetry", ...), the one every surface shows;
// empty for None.
std::string fit_reason(FitBlocker blocker);

// The fit entries' check: refreshes the marks, then refuses (std::invalid_argument) the first free parameter a fit
// cannot vary, as `<unique name> cannot be fitted: <reason>`. A dependent's flag is cleared by the relations instead,
// and an idle parameter's (Parameter::fit_idle) is kept.
void require_fittable_free(Project& project);

// The loader's pass: refreshes the marks, clears the free flag of every parameter a fit cannot vary, keeping its
// value and uncertainty, and returns one note each, `<unique name> cannot be fitted: <reason>; loaded fixed`. An idle
// parameter's flag is kept.
std::vector<std::string> clear_unfittable_free(Project& project);

}  // namespace edi

#endif  // EDI_FITTABILITY_HPP
