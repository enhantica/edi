// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_SYMMETRY_HPP
#define EDI_SYMMETRY_HPP

// ADR-0019: what the space group leaves of a structure's cell and coordinates. A parameter is
// INDEPENDENT (a fit can vary it), FOLLOWS another (a cubic `b` follows `a`; the `y` of a site on
// `x,x,x` follows its `x`) or is FIXED to a constant (a cubic angle is 90, a coordinate on a mirror
// plane is 0). The rule is crysta's own — `crysta::cell_freedom` for the cell and
// `crysta::Structure::positional_constraints` for the coordinates, the two calls the symmetric
// completion (io.hpp) already reads — so what a page offers to vary is what a fit accepts.
// Implemented in the adapter (the one crysta-touching TU; edi-only signature, ADR-0003).

#include <array>
#include <optional>
#include <string>
#include <vector>

#include "edi/model.hpp"

namespace edi {

enum class TieKind { Independent, Follows, Fixed };

struct ParameterTie {
    const Parameter* parameter = nullptr;
    TieKind kind = TieKind::Independent;
    const Parameter* leader = nullptr;  // Follows: the independent parameter it tracks
    std::optional<double> fixed_value;  // Fixed: the constant symmetry gives it
};

// One row per cell parameter (a, b, c, alpha, beta, gamma), then one per atom site's fract_x,
// fract_y and fract_z, in the structure's own order, then, for each anisotropic site, one per
// tensor component and one for its adp_iso. A tensor component the site symmetry ties to others
// FOLLOWS the first of them (its value is a sum over them, crysta::adp_ties), and an anisotropic
// site's adp_iso FOLLOWS its tensor's adp_11 (it is the tensor's equivalent value). Occupancy and an
// isotropic ADP are not symmetry quantities and have no row. A setting crysta cannot resolve, or a
// site it cannot place, reports that part independent: the calculation refuses such a structure
// with its own message, and a page that could not edit the offending field could not repair it.
std::vector<ParameterTie> structure_ties(const Structure& structure);

// Sets a site's ADP type and converts its values, through crysta's conversion (ADR-0027):
// to an isotropic type the site keeps its equivalent isotropic value; to an anisotropic one it
// gets a tensor row holding the tensor of its current values, and a row it no longer needs is
// removed. Throws std::invalid_argument for a type that is not Biso, Uiso, Bani, Uani or beta.
void change_adp_type(Structure& structure, AtomSite& site, const std::string& adp_type);

// One tensor row for each anisotropic site and none for any other (diffraction-lib's
// _sync_atom_site_aniso): a missing row holds the tensor of the site's isotropic value, through
// crysta's conversion; a row no anisotropic site names is removed. Each anisotropic site's adp_iso
// is then set to its tensor's equivalent value.
void sync_atom_site_aniso(Structure& structure);

// An anisotropic site's tensor as U* (the CIF U scaled by the reciprocal lengths)
// at the structure's symmetry-completed cell, or nullopt for an isotropic site, a site with no
// tensor row or a cell crysta refuses.
std::optional<std::array<double, 6>> site_u_star(const Structure& structure, const AtomSite& site);

}  // namespace edi

#endif  // EDI_SYMMETRY_HPP
