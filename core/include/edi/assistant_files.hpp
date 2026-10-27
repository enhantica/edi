// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <cstddef>
#include <cstdint>
#include <string>
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
    static constexpr std::size_t file_bytes = 16 * 1024 * 1024;
    static constexpr std::size_t collection_bytes = 64 * 1024 * 1024;
    static constexpr std::size_t name_bytes = 512;
    static constexpr std::size_t read_bytes = 64 * 1024;
};
}  // namespace edi::assistant
