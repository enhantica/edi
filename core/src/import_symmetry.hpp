// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <string>

namespace edi {
struct Structure;
struct AtomSite;
namespace detail {
// The native CIF automatic-position matcher, for a genuinely omitted mapped
// declaration. Returns its letter only; the existing completion checks still
// require all supplied coordinates, occupancy and ADPs to remain exact.
std::string inferred_wyckoff_letter(const Structure& structure,const AtomSite& site);
}  // namespace detail
}  // namespace edi
