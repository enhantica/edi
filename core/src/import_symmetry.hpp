// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include "edi/io.hpp"

namespace edi {
struct Structure;
struct AtomSite;
namespace detail {
// The native CIF automatic-position matcher, for a genuinely omitted mapped
// declaration. Returns its letter only; the existing completion checks still
// require all supplied coordinates, occupancy and ADPs to remain exact.
std::string inferred_wyckoff_letter(const Structure& structure,const AtomSite& site);
// File import dialects may use a known alternate spelling of one exact setting.
std::optional<SpaceGroupSettingName> unambiguous_space_group_alias(const std::string& name);
std::optional<double> import_atomic_mass(const std::string& type_symbol);
}  // namespace detail
}  // namespace edi
