// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

namespace edi::assistant {
/// Human-selected immutable bytes; identifiers are opaque, never file-system paths.
struct SelectedFile {
    std::string id;
    std::string relative_name;
    std::vector<std::uint8_t> bytes;
};
struct SelectedFiles {
    std::string collection_id;
    std::uint64_t generation = 0;
    std::vector<SelectedFile> files;
};
/// Inclusive local-input policy, independent of provider/token capacity.
struct SelectedFileLimits {
    static constexpr std::size_t files = 32;
    static constexpr std::size_t message_files = 6; // Pending attachments in one user message, not retained task files.
    static constexpr std::size_t file_bytes = std::size_t{16} * 1024 * 1024;
    static constexpr std::size_t collection_bytes = std::size_t{64} * 1024 * 1024;
    static constexpr std::size_t name_bytes = 512;
    static constexpr std::size_t read_bytes = std::size_t{64} * 1024;
};
/// The character of a windows-1252 byte, or 0 for a byte that has none.
constexpr char32_t windows_1252(unsigned char byte) {
    constexpr std::array<char16_t, 32> high{
        0x20ac, 0, 0x201a, 0x0192, 0x201e, 0x2026, 0x2020, 0x2021, 0x02c6, 0x2030, 0x0160, 0x2039, 0x0152, 0, 0x017d, 0,
        0, 0x2018, 0x2019, 0x201c, 0x201d, 0x2022, 0x2013, 0x2014, 0x02dc, 0x2122, 0x0161, 0x203a, 0x0153, 0, 0x017e, 0x0178};
    return byte >= 0x80 && byte < 0xa0 ? char32_t{high[byte - 0x80]} : char32_t{byte};
}
/// Older CIF and data files are windows-1252 (of which ISO-8859-1's characters are a part). Bytes are such text when
/// each is a character and none is a control character that text does not use; a NUL or a binary file is not.
constexpr bool windows_1252_text(std::string_view bytes) {
    for (const char c : bytes) {
        const auto byte = static_cast<unsigned char>(c);
        const bool control = (byte < 0x20 && !(byte >= 0x09 && byte <= 0x0d) && byte != 0x1a) || byte == 0x7f;
        if (control || windows_1252(byte) == 0) return false;
    }
    return true;
}
/// A selected file's `format`: UTF-8 text, text in windows-1252, or neither.
inline constexpr std::string_view selected_utf8_format = "unverified_text";
inline constexpr std::string_view selected_windows_1252_format = "unverified_text_windows_1252";
inline constexpr std::string_view selected_binary_format = "unsupported_binary";
}  // namespace edi::assistant
