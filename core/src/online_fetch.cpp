// SPDX-License-Identifier: BSD-3-Clause
#include "edi/online_fetch.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <system_error>

#include "edi/project_archive.hpp"

namespace edi::online {
namespace {
namespace fs = std::filesystem;

// FIPS 180-4 SHA-256.
class Sha256 {
   public:
    void update(std::string_view data) {
        for (const char c : data) {
            block_[used_++] = static_cast<std::uint8_t>(c);
            if (used_ == 64) {
                compress();
                used_ = 0;
            }
        }
        length_ += data.size();
    }
    std::string hex() {
        const std::uint64_t bits = length_ * 8;
        block_[used_++] = 0x80;
        if (used_ > 56) {
            while (used_ < 64) block_[used_++] = 0;
            compress();
            used_ = 0;
        }
        while (used_ < 56) block_[used_++] = 0;
        for (int i = 7; i >= 0; --i) block_[used_++] = static_cast<std::uint8_t>(bits >> (8 * i));
        compress();
        static const char* digits = "0123456789abcdef";
        std::string out;
        for (const std::uint32_t word : state_)
            for (int i = 28; i >= 0; i -= 4) out += digits[(word >> i) & 0xF];
        return out;
    }

   private:
    static std::uint32_t rotr(std::uint32_t x, int n) { return (x >> n) | (x << (32 - n)); }
    void compress() {
        static constexpr std::array<std::uint32_t, 64> k = {
            0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
            0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
            0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
            0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
            0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
            0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
            0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
            0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};
        std::array<std::uint32_t, 64> w{};
        for (int i = 0; i < 16; ++i)
            w[i] = (std::uint32_t(block_[4 * i]) << 24) | (std::uint32_t(block_[4 * i + 1]) << 16) |
                   (std::uint32_t(block_[4 * i + 2]) << 8) | std::uint32_t(block_[4 * i + 3]);
        for (int i = 16; i < 64; ++i) {
            const auto s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
            const auto s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16] + s0 + w[i - 7] + s1;
        }
        auto [a, b, c, d, e, f, g, h] = state_;
        for (int i = 0; i < 64; ++i) {
            const auto t1 = h + (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) + ((e & f) ^ (~e & g)) + k[i] + w[i];
            const auto t2 = (rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
            h = g, g = f, f = e, e = d + t1, d = c, c = b, b = a, a = t1 + t2;
        }
        const std::array<std::uint32_t, 8> add = {a, b, c, d, e, f, g, h};
        for (int i = 0; i < 8; ++i) state_[i] += add[i];
    }
    std::array<std::uint32_t, 8> state_ = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
                                           0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
    std::array<std::uint8_t, 64> block_{};
    std::size_t used_ = 0;
    std::uint64_t length_ = 0;
};

std::string lowercase(std::string text) {
    for (char& c : text)
        if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
    return text;
}

std::string read_file(const fs::path& path) {
    std::ifstream in(path, std::ios::binary);
    return {std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>()};
}

// The project folder inside an unpacked archive's folder, as unpack_project_archive answers it: the folder itself when
// it holds project.edi, else its one subfolder that does; empty when neither.
std::string project_folder(const fs::path& folder) {
    std::error_code ec;
    if (fs::is_regular_file(folder / "project.edi", ec)) return folder.string();
    std::string found;
    for (const auto& child : fs::directory_iterator(folder, ec)) {
        if (!child.is_directory(ec) || !fs::is_regular_file(child.path() / "project.edi", ec)) continue;
        if (!found.empty()) return {};
        found = child.path().string();
    }
    return found;
}

bool digits_only(const std::string& text) {
    return !text.empty() && text.size() < 10 &&
           std::all_of(text.begin(), text.end(), [](char c) { return c >= '0' && c <= '9'; });
}

}  // namespace

std::string sha256_hex(std::string_view bytes) {
    Sha256 hash;
    hash.update(bytes);
    return hash.hex();
}

Mismatch content_mismatch(std::string_view bytes, const File& file) {
    if (file.bytes >= 0 && static_cast<long long>(bytes.size()) != file.bytes) return Mismatch::size;
    if (!file.sha256.empty() && sha256_hex(bytes) != lowercase(file.sha256)) return Mismatch::digest;
    return Mismatch::none;
}

std::string content_problem(std::string_view bytes, const File& file, const std::string& name) {
    switch (content_mismatch(bytes, file)) {
        case Mismatch::size:
            return name + " has " + std::to_string(bytes.size()) + " bytes, not the " + std::to_string(file.bytes) +
                   " the index records";
        case Mismatch::digest:
            return name + " does not match the digest the index records";
        case Mismatch::none:
            break;
    }
    return {};
}

std::string location_url(const std::string& base, const std::string& path) {
    std::string root = base;
    while (!root.empty() && root.back() == '/') root.pop_back();
    return root + '/' + path;
}

FileRead::FileRead(std::vector<std::string> bases, std::string path) : bases_(std::move(bases)), path_(std::move(path)) {
    next();
}

FileRead::FileRead(std::vector<std::string> bases, const File& expected)
    : bases_(std::move(bases)), path_(expected.path), check_(true), expected_(expected) {
    next();
}

void FileRead::next() {
    if (position_ >= bases_.size()) {
        done_ = true;
        unreachable_ = true;
        if (error_.empty()) error_ = "No location to read " + path_ + " from";
        return;
    }
    url_ = location_url(bases_[position_], path_);
}

void FileRead::answered(std::string bytes) {
    if (done_) return;
    done_ = true;
    error_.clear();  // an earlier location's outage is not this read's outcome
    if (check_) {
        const auto slash = path_.find_last_of('/');
        error_ = content_problem(bytes, expected_, slash == std::string::npos ? path_ : path_.substr(slash + 1));
        if (!error_.empty()) return;
    }
    served_by_ = bases_[position_];
    bytes_ = std::move(bytes);
}

void FileRead::failed(const std::string& message, bool outage) {
    if (done_) return;
    error_ = message;
    if (!outage) {
        done_ = true;
        return;
    }
    ++position_;
    next();
}

std::vector<const Entry*> listing(const Index& index, const std::string& kind) {
    std::vector<const Entry*> out;
    for (const Entry& entry : index.entries)
        if (kind.empty() || entry.kind == kind) out.push_back(&entry);
    // Tutorials keep the index's learning order; everything else is listed by id, as diffraction-lib lists its data.
    if (kind != "tutorial")
        std::stable_sort(out.begin(), out.end(), [](const Entry* a, const Entry* b) { return a->id < b->id; });
    return out;
}

const Entry& resolve(const Index& index, const std::string& name, const std::string& kind) {
    const auto shown = listing(index, kind);
    if (digits_only(name)) {
        const auto row = std::stoul(name);
        if (row < 1 || row > shown.size())
            throw std::invalid_argument("No row " + name + " in the listing; it has rows 1 to " +
                                        std::to_string(shown.size()) + ". Use the id in saved code.");
        return *shown[row - 1];
    }
    for (const Entry* entry : shown)
        if (entry->id == name) return *entry;
    throw std::invalid_argument("No entry '" + name + "'" + (kind.empty() ? "" : " of kind " + kind) +
                                " in the collection; list it to see the ids");
}

Placement placement(const std::string& destination, const Entry& entry, const File& file) {
    const fs::path root(destination);
    const auto slash = file.path.find_last_of('/');
    const std::string name = slash == std::string::npos ? file.path : file.path.substr(slash + 1);
    Placement where{(root / name).string(), {}};
    if (entry.kind == "project" && file.format == "zip")
        where.folder = (root / (file.sha256.empty() ? entry.id : entry.id + "-" + lowercase(file.sha256).substr(0, 12))).string();
    return where;
}

std::string stored(const Placement& where, const File& file) {
    std::error_code ec;
    if (!where.folder.empty()) return fs::is_directory(where.folder, ec) ? project_folder(where.folder) : std::string();
    if (fs::is_regular_file(where.file, ec) && content_mismatch(read_file(where.file), file) == Mismatch::none)
        return where.file;
    return {};
}

std::string store(const Placement& where, const File& file, std::string_view bytes, bool overwrite) {
    if (const auto problem = content_problem(bytes, file, where.file); !problem.empty()) throw std::runtime_error(problem);
    std::error_code ec;
    if (!where.folder.empty()) {
        if (fs::is_directory(where.folder, ec)) {
            if (const auto kept = project_folder(where.folder); !overwrite && !kept.empty()) return kept;
            fs::remove_all(where.folder);
        }
        return unpack_project_archive(bytes, where.folder);
    }
    if (!overwrite && !stored(where, file).empty()) return where.file;
    fs::create_directories(fs::path(where.file).parent_path());
    const fs::path partial = where.file + ".partial";
    {
        std::ofstream out(partial, std::ios::binary | std::ios::trunc);
        out.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
        if (!out) throw std::runtime_error("Cannot write " + where.file);
    }
    fs::rename(partial, where.file);
    return where.file;
}

}  // namespace edi::online
