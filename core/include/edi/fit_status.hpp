// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_FIT_STATUS_HPP
#define EDI_FIT_STATUS_HPP

#include <cstdint>

namespace edi {

// Why a refinement stopped — deliberately NOT collapsed into `converged`, so a fit that exhausted
// its iteration budget is distinguishable from one that could not take a step. Mirrors the
// engine's REACHABLE set; diverged/singular are reserved there and never emitted, because nothing
// detects them today. adds UNAVAILABLE: the fit did not converge and the CAUSE was not persisted,
// so it cannot be reported. It is reached only by reconstruction from a scan's `results.csv`,
// which records a success BIT and no cause — never by a live fit, which always knows whether it
// exhausted its budget or could not take a step. Mirrors crysta::FitStatus::Unavailable (ADR-0057
// shape). adds SUPERSEDED (ADR-0057): a model input was written while the fit ran, so the fit
// published nothing. Mirrors crysta::FitStatus::Superseded.
enum class FitStatus : std::uint8_t {
    DONE,
    MAX_ITER,
    NO_STEP,
    CANCELLED,
    ERROR,
    UNAVAILABLE,
    SUPERSEDED
};

}  // namespace edi

#endif
