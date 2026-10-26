#pragma once

#include <algorithm>
#include <charconv>
#include <cmath>
#include <cstdlib>
#include <stdexcept>
#include <string>
#include <system_error>

namespace saved_reference {
// Round the shortest decimal digits half away from zero, independently of the project writer.
inline double six_digits(double value) {
    if (!std::isfinite(value))
        throw std::invalid_argument("The saved-value reference requires a finite input");
    char text[64];
    const auto written = std::to_chars(text, text + sizeof(text), value);
    if (written.ec != std::errc{})
        throw std::runtime_error("The independent decimal conversion must succeed");
    std::string digits(text, written.ptr);
    const bool negative = digits.front() == '-';
    if (negative) digits.erase(0, 1);
    int exponent = 0;
    if (const auto e = digits.find_first_of("eE"); e != std::string::npos) {
        exponent = std::stoi(digits.substr(e + 1));
        digits.resize(e);
    }
    if (const auto dot = digits.find('.'); dot != std::string::npos) {
        exponent -= static_cast<int>(digits.size() - dot - 1);
        digits.erase(dot, 1);
    }
    const auto first = digits.find_first_not_of('0');
    if (first == std::string::npos) return value;
    digits.erase(0, first);
    if (digits.size() <= 6) return value;
    exponent += static_cast<int>(digits.size() - 6);
    const bool upward = digits[6] >= '5';
    digits.resize(6);
    if (upward) {
        auto i = digits.size();
        while (i && digits[i - 1] == '9') digits[--i] = '0';
        if (i)
            ++digits[i - 1];
        else
            digits.insert(0, "1");
    }
    const std::string token = (negative ? "-" : "") + digits + "e" + std::to_string(exponent);
    // An integer significand and exponent contain no locale-dependent decimal separator.
    char* end = nullptr;
    const double result = std::strtod(token.c_str(), &end);
    if (end != token.c_str() + token.size() || !std::isfinite(result) || result == 0.0)
        throw std::runtime_error("The independent saved-value conversion must consume its token");
    return result;
}
}  // namespace saved_reference
