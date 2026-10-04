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

#include <optional>
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
// fract_y and fract_z, in the structure's own order. Occupancy and the ADP are not symmetry
// quantities here and have no row. A setting crysta cannot resolve, or a site it cannot place,
// reports that part independent: the calculation refuses such a structure with its own message,
// and a page that could not edit the offending field could not repair it.
std::vector<ParameterTie> structure_ties(const Structure& structure);

}  // namespace edi

#endif  // EDI_SYMMETRY_HPP
