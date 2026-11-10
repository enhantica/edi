// SPDX-License-Identifier: BSD-3-Clause
#include "edi/duration_text.hpp"

#include <cmath>
#include <cstdio>

namespace edi {

std::string duration_text(double seconds) {
    if (!(seconds > 0.0) || !std::isfinite(seconds)) {
        return "0";
    }
    char buffer[32];
    // From 9.95 up, two significant digits would drop whole seconds (127 as 1.3e2): whole seconds instead.
    if (seconds >= 9.95) {
        std::snprintf(buffer, sizeof(buffer), "%.0f", seconds);
    } else {
        std::snprintf(buffer, sizeof(buffer), "%.2g", seconds);
    }
    return buffer;
}

}  // namespace edi
