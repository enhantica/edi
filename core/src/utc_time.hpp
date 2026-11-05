// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <ctime>
#include <optional>
#include <stdexcept>

namespace edi::detail {
inline std::tm utc_calendar(std::time_t time) {
    std::tm result{};
#ifdef _WIN32
    if (gmtime_s(&result, &time) != 0)
#else
    if (gmtime_r(&time, &result) == nullptr)
#endif
        throw std::runtime_error("Timestamp is outside the UTC calendar range");
    return result;
}

inline std::optional<std::time_t> utc_seconds(std::tm parsed) {
#ifdef _WIN32
    const auto result = _mkgmtime(&parsed);
    return result == static_cast<std::time_t>(-1) ? std::nullopt : std::optional<std::time_t>(result);
#else
    return timegm(&parsed);
#endif
}
}  // namespace edi::detail
