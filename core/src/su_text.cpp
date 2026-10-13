// SPDX-License-Identifier: BSD-3-Clause
#include "edi/su_text.hpp"

#include <charconv>
#include <cmath>
#include <optional>
#include <stdexcept>

// The IUCr rule is crysta's (ADR-0089). Until edi's crysta pin carries it, a build against the older SDK keeps
// today's display spelling: the s.u. to one significant digit and the value to the same place. Remove this branch
// when the pin moves.
#if __has_include("crysta/su_format.hpp")
#include "crysta/su_format.hpp"
#define EDI_CRYSTA_SU_FORMAT 1
#endif

namespace edi {

namespace {

void check_rule(const std::string& rule) {
    if (rule != "iucr_19" && rule != "iucr_99") {
        throw std::invalid_argument("_su_format.rule is '" + rule + "', expected iucr_19 or iucr_99");
    }
}

#ifdef EDI_CRYSTA_SU_FORMAT
crysta::SuRule rule_of(const std::string& rule) {
    check_rule(rule);
    return *crysta::su_rule_from_name(rule);
}
#else
std::string fixed(double value, int decimals) {
    char buffer[400];
    const auto result =
        std::to_chars(buffer, buffer + sizeof(buffer), value, std::chars_format::fixed, decimals);
    return std::string(buffer, result.ptr);
}
#endif

}  // namespace

SuText su_text(double value, double su, const std::string& rule) {
#ifdef EDI_CRYSTA_SU_FORMAT
    const crysta::RoundedSu rounded = crysta::round_value_su(value, su, rule_of(rule));
    return {rounded.value, rounded.su, rounded.bracket};
#else
    check_rule(rule);
    if (!std::isfinite(value) || !std::isfinite(su) || su == 0.0) {
        throw std::invalid_argument("a finite value and a finite, nonzero standard uncertainty are needed");
    }
    int place = static_cast<int>(std::floor(std::log10(std::abs(su))));
    double digit = std::round(std::abs(su) / std::pow(10.0, place));
    if (digit >= 10.0) {
        digit = 1.0;
        ++place;
    }
    const int decimals = place < 0 ? -place : 0;
    const double scale = std::pow(10.0, place);
    const double rounded_value = std::round(value / scale) * scale;
    const std::string digits = std::to_string(static_cast<int>(digit));
    return {fixed(rounded_value == 0.0 ? 0.0 : rounded_value, decimals), fixed(digit * scale, decimals),
            place > 0 ? digits + std::string(static_cast<std::size_t>(place), '0') : digits};
#endif
}

std::string value_su_text(double value, double su, const std::string& rule) {
    const SuText text = su_text(value, su, rule);
    return text.value + "(" + text.bracket + ")";
}

std::string correlation_text(double coefficient) {
#ifdef EDI_CRYSTA_SU_FORMAT
    return crysta::iucr_correlation(coefficient);
#else
    if (!std::isfinite(coefficient)) {
        throw std::invalid_argument("a correlation coefficient must be finite");
    }
    return fixed(coefficient, 2);
#endif
}

}  // namespace edi
