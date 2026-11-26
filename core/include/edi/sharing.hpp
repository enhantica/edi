// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_SHARING_HPP
#define EDI_SHARING_HPP

#include <string>
#include <vector>

#include "edi/model.hpp"

namespace edi {

/// ADR-0087: the experiments a switch ties together, the leader first: the members of the experiment set the
/// experiment belongs to, its template leading, or every experiment of the project, the first leading, when it
/// belongs to none. Throws std::invalid_argument for an experiment the project does not hold.
std::vector<std::string> sharing_scope(const Project& project, const std::string& experiment);

/// "Same for all experiments": whether every other experiment of `experiment`'s scope follows the leader's
/// parameter `path` (a unique name without its datablock, `peak.broad_gauss_sigma_2`) through the alias and
/// constraint rows the switch writes, in that form.
bool shared_across_experiments(const Project& project, const std::string& experiment, const std::string& path);

/// Turns the switch on: for every other member an alias for its parameter, an alias for the leader's, and the
/// constraint `<member alias> = <leader alias>`; ids `same_<experiment>_<path>` with the path's dots as
/// underscores, a numeric suffix when taken. Refuses, writing nothing, when a member has no such parameter.
void share_across_experiments(Project& project, const std::string& experiment, const std::string& path);

/// Turns it off: removes exactly the rows the switch wrote for `path` in the scope.
void unshare_across_experiments(Project& project, const std::string& experiment, const std::string& path);

/// "Phase ratios shared": whether every other member's linked scales follow the leader's ratios, for each
/// structure `p` other than the reference `r`: `s(e,p) = s(e,r) * s(a,p) / s(a,r)`.
bool phase_ratios_shared(const Project& project, const std::string& experiment);

/// Turns the phase-ratio switch on or off. The reference is the leader's first enabled linked structure whose
/// scale is not zero. Refuses, writing nothing, when every leader scale is zero or the members link different
/// structures.
void share_phase_ratios(Project& project, const std::string& experiment, bool on);

/// ADR-0107: whether the parametric fit gives `parameter` one value for every point of the scan. False for a
/// parameter the project does not name.
bool parametric_shared(const Project& project, const Parameter& parameter);

/// ADR-0107: shares or unshares `parameter` in the parametric fit: one value for every point, fixed or free. The free
/// flag is left as it is. Refuses (std::invalid_argument) a dependent and a parameter the project does not name.
void set_parametric_shared(Project& project, Parameter& parameter, bool shared);

/// ADR-0107, at load: a name the project does not hold, or a dependent's, is dropped; a listed parameter keeps the free
/// flag its value's spelling gives. Returns a note for each dropped name.
std::vector<std::string> settle_parametric_shared(Project& project);

}  // namespace edi

#endif  // EDI_SHARING_HPP
