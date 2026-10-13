// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <string>

namespace edi {

/// A fit's or a scan's time in seconds as the app and the report write it (the owner, 2026-10-13): two significant
/// digits, never fewer than the whole seconds, no unit: "0.023", "0.41", "3.2", "45", "127"; "0" for none.
std::string duration_text(double seconds);

}  // namespace edi
