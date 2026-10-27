// SPDX-License-Identifier: BSD-3-Clause
#pragma once

// Core-private import normalization, implemented in the one crysta adapter.
namespace edi {
struct Structure;
namespace detail {
// Fill only absent, '?' or '.' classic-CIF Wyckoff letters, using a uniquely
// proved orbit membership in the resolved setting. Never moves coordinates.
// Unsupported/ambiguous inference or engine completion that would change the
// physical site/tensor refuses before a structure is returned.
void normalize_imported_wyckoff(Structure& structure);
}  // namespace detail
}  // namespace edi
