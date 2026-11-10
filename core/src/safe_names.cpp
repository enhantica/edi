// SPDX-License-Identifier: BSD-3-Clause
#include "edi/safe_names.hpp"

#include <array>
#include <stdexcept>
#include <string>

namespace edi {
namespace {

constexpr std::size_t kCollectionSegment = 128, kProjectSegment = 255, kNested = 1024;
// A project's folder is its id plus '-' and twelve digest characters, which must still fit one collection segment.
constexpr std::size_t kEntryId = kCollectionSegment - 13;
constexpr const char* kReserved = "/\\:*?\"<>|";  // characters Windows refuses in a file name

bool word(char c) {
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_' || c == '-';
}

char lower(char c) { return c >= 'A' && c <= 'Z' ? static_cast<char>(c - 'A' + 'a') : c; }

// A Windows device name addresses a device in every folder, with or without an extension; the digit of COM and LPT
// may also be a superscript one, two or three (UTF-8 C2 B9, C2 B2, C2 B3). Trailing spaces before the extension do
// not make it an ordinary name.
bool device(std::string_view segment) {
    std::string_view stem = segment.substr(0, segment.find('.'));
    while (!stem.empty() && stem.back() == ' ') stem.remove_suffix(1);
    std::string base;
    for (const char c : stem) base += lower(c);
    static constexpr std::array<std::string_view, 4> plain{"con", "prn", "aux", "nul"};
    for (const auto name : plain)
        if (base == name) return true;
    if (base.rfind("com", 0) != 0 && base.rfind("lpt", 0) != 0) return false;
    const std::string_view digit = std::string_view(base).substr(3);
    return (digit.size() == 1 && digit[0] >= '0' && digit[0] <= '9') || digit == "\xc2\xb9" || digit == "\xc2\xb2" ||
           digit == "\xc2\xb3";
}

// The length of the UTF-8 encoding of one Unicode scalar value starting at `text[i]`, or 0 when the bytes there are
// not one: no overlong form, no surrogate (U+D800 to U+DFFF), nothing above U+10FFFF.
std::size_t scalar_length(std::string_view text, std::size_t i) {
    const auto at = [&](std::size_t k) { return static_cast<unsigned char>(text[i + k]); };
    const auto c = at(0);
    const std::size_t length = c < 0x80                ? 1
                               : c >= 0xc2 && c <= 0xdf ? 2
                               : c >= 0xe0 && c <= 0xef ? 3
                               : c >= 0xf0 && c <= 0xf4 ? 4
                                                        : 0;
    if (length == 0 || i + length > text.size()) return 0;
    for (std::size_t k = 1; k < length; ++k)
        if ((at(k) & 0xc0) != 0x80) return 0;
    // The second byte's range rules out overlong, surrogate and above-range forms.
    if ((c == 0xe0 && at(1) < 0xa0) || (c == 0xed && at(1) > 0x9f) || (c == 0xf0 && at(1) < 0x90) ||
        (c == 0xf4 && at(1) > 0x8f))
        return 0;
    return length;
}

// Unicode scalar values in UTF-8, without control characters or the characters Windows reserves in a file name.
bool project_characters(std::string_view segment) {
    for (std::size_t i = 0; i < segment.size();) {
        const std::size_t length = scalar_length(segment, i);
        if (length == 0) return false;
        if (length == 1) {
            const auto c = static_cast<unsigned char>(segment[i]);
            if (c < 0x20 || c == 0x7f || std::string_view(kReserved).find(static_cast<char>(c)) != std::string_view::npos)
                return false;
        }
        i += length;
    }
    return true;
}

bool segment_admitted(std::string_view segment, NameRule rule) {
    if (segment.empty() || segment == "." || segment == ".." || segment.back() == '.' || segment.back() == ' ' ||
        device(segment))
        return false;
    if (rule == NameRule::project) return segment.size() <= kProjectSegment && project_characters(segment);
    const std::size_t bound = rule == NameRule::entry_id ? kEntryId : kCollectionSegment;
    if (segment.size() > bound || !word(segment.front()) || !word(segment.back())) return false;
    for (const char c : segment)
        if (!word(c) && c != '.') return false;
    return true;
}

}  // namespace

bool admitted_name(std::string_view name, bool nested, NameRule rule) {
    if (name.empty() || name.size() > (nested ? kNested : kProjectSegment)) return false;
    if (!nested) return segment_admitted(name, rule);
    std::size_t start = 0;
    for (;;) {
        const std::size_t end = name.find('/', start);
        const std::size_t length = end == std::string_view::npos ? std::string_view::npos : end - start;
        if (!segment_admitted(name.substr(start, length), rule)) return false;
        if (end == std::string_view::npos) return true;
        start = end + 1;
    }
}

std::string shown_name(std::string_view name) {
    static constexpr char hex[] = "0123456789ABCDEF";
    std::string shown;
    for (std::size_t i = 0; i < name.size();) {
        const std::size_t length = scalar_length(name, i);
        const auto c = static_cast<unsigned char>(name[i]);
        if (length > 1 || (length == 1 && c >= 0x20 && c != 0x7f)) {
            shown.append(name.substr(i, length));
            i += length;
        } else {
            shown += "\\x";
            shown += hex[c >> 4];
            shown += hex[c & 0xf];
            ++i;
        }
    }
    return shown;
}

std::filesystem::path safe_relative_path(std::string_view name, bool nested, NameRule rule) {
    if (!admitted_name(name, nested, rule)) throw std::invalid_argument("'" + shown_name(name) + "' is not a plain name");
    return std::filesystem::path(std::string(name));
}

}  // namespace edi
