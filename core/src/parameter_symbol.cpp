// SPDX-License-Identifier: BSD-3-Clause
#include <regex>
#include <string>
#include <utility>

#include "edi/parameter_spec.hpp"

namespace edi {

std::string parameter_symbol(const ParameterSpec* parameter_spec) {
    if (parameter_spec == nullptr) {
        return {};
    }
    // The FCJ asymmetry under FullProf's names (owner, 2026-10-06); its spec keeps diffraction-lib's.
    if (parameter_spec == &spec::peak_asym_fcj_1) {
        return "S/L";
    }
    if (parameter_spec == &spec::peak_asym_fcj_2) {
        return "D/L";
    }
    const std::string fallback = parameter_spec->display_name != nullptr ? parameter_spec->display_name : "";
    if (parameter_spec->latex_name == nullptr) {
        return fallback;
    }
    std::string text = parameter_spec->latex_name;
    std::erase(text, '$');
    static const std::regex roman(R"(\\mathrm\{([^{}]*)\})");
    text = std::regex_replace(text, roman, "$1");
    const std::pair<const char*, const char*> symbols[] = {
        {"\\alpha", "α"}, {"\\beta", "β"}, {"\\gamma", "γ"}, {"\\sigma", "σ"},
        {"\\theta", "θ"}, {"\\mu", "μ"},   {"\\AA", "Å"},    {"\\,", " "}};
    for (const auto& [from, to] : symbols) {
        const std::string pattern(from);
        for (std::size_t at = text.find(pattern); at != std::string::npos; at = text.find(pattern, at)) {
            text.replace(at, pattern.size(), to);
        }
    }
    // A subscript: digits become subscript digits, anything else follows after a space.
    static const std::regex subscript(R"(_\{?([0-9A-Za-z]+)\}?)");
    std::smatch match;
    while (std::regex_search(text, match, subscript)) {
        const std::string tail = match[1].str();
        std::string spelled;
        if (tail.find_first_not_of("0123456789") == std::string::npos) {
            for (const char digit : tail) {
                spelled += "\xE2\x82";
                spelled += static_cast<char>(0x80 + (digit - '0'));
            }
        } else {
            spelled = " " + tail;
        }
        text.replace(static_cast<std::size_t>(match.position(0)), static_cast<std::size_t>(match.length(0)), spelled);
    }
    if (text.empty() || text.find_first_of("\\{^") != std::string::npos) {
        return fallback;
    }
    return text;
}

}  // namespace edi
