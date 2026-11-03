// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_NUMBER_TOKEN_HPP
#define EDI_NUMBER_TOKEN_HPP

// How a bare number token in a project file reads, the same rule the engine's loader keeps, so both readers take
// the same values on every platform. A stream read diverged: libc++ refuses every subnormal value and reads
// hexadecimal, libstdc++ reads a nonzero value that underflows as zero.
//
//   a representable value, subnormal ones included   -> ok, rounded once by strtod
//   a genuine zero ("0", "-0.0", "0e5")               -> ok
//   a nonzero value that underflows to zero            -> underflow, refused
//   a magnitude beyond the double range                -> overflow, refused
//   anything but digits, sign, '.' and an exponent      -> malformed, refused
//
// Decided from the value strtod returns and the token's own digits, never from errno, which a subnormal sets on
// some platforms and not on others. strtod reads the C locale's radix, so the token's '.' is written as that radix
// first, and a comma-decimal locale reads the same value.

#include <clocale>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <string>

namespace edi::detail {

enum class NumberToken : std::uint8_t { ok, malformed, underflow, overflow };

inline NumberToken read_number(const std::string& token, double& out) {
    if (token.empty()) {
        return NumberToken::malformed;
    }
    for (const char character : token) {
        const bool allowed = (character >= '0' && character <= '9') || character == '+' || character == '-' ||
                             character == '.' || character == 'e' || character == 'E';
        if (!allowed) {
            return NumberToken::malformed;
        }
    }
    std::string text = token;
    const char* const radix = std::localeconv()->decimal_point;
    if (radix != nullptr && radix[0] != '\0' && (radix[0] != '.' || radix[1] != '\0')) {
        if (const std::size_t dot = text.find('.'); dot != std::string::npos) {
            text.replace(dot, 1, radix);
        }
    }
    char* end = nullptr;
    const double value = std::strtod(text.c_str(), &end);
    if (end != text.c_str() + text.size()) {
        return NumberToken::malformed;
    }
    if (!std::isfinite(value)) {
        return NumberToken::overflow;
    }
    if (value == 0.0 && token.substr(0, token.find_first_of("eE")).find_first_of("123456789") != std::string::npos) {
        return NumberToken::underflow;
    }
    out = value;
    return NumberToken::ok;
}

}  // namespace edi::detail

#endif  // EDI_NUMBER_TOKEN_HPP
