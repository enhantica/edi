// SPDX-License-Identifier: BSD-3-Clause
#include "edi/online_fetch.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <random>
#include <stdexcept>
#include <system_error>
#include <vector>

#if !defined(_WIN32)
#include <sys/stat.h>

#include <cerrno>
#endif

#include "edi/io.hpp"
#include "edi/project_archive.hpp"
#include "edi/safe_names.hpp"

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
// it holds project.edi, else its one subfolder that does; empty when neither. Nothing reached through a link counts:
// a folder this code unpacked holds no links, so one there was put there by something else.
std::string project_folder(const fs::path& folder) {
    std::error_code ec;
    const auto plain = [&](const fs::path& path, bool directory) {
        return !fs::is_symlink(path, ec) && (directory ? fs::is_directory(path, ec) : fs::is_regular_file(path, ec));
    };
    if (!plain(folder, true)) return {};
    if (plain(folder / "project.edi", false)) return folder.string();
    std::string found;
    for (const auto& child : fs::directory_iterator(folder, ec)) {
        if (!plain(child.path(), true) || !plain(child.path() / "project.edi", false)) continue;
        if (!found.empty()) return {};
        found = child.path().string();
    }
    return found;
}

// A name beside `target` that nothing else uses, for a file or folder this operation creates and owns.
fs::path private_name(const fs::path& target, const char* suffix) {
    thread_local std::mt19937_64 random{std::random_device{}()};
    return target.parent_path() /
           ("." + target.filename().string() + "." + std::to_string(random() % 1000000000000ULL) + suffix);
}

// Write `bytes` to `target` through a staging file created for this call alone, so an existing file, link or hard
// link at any staging name is never opened or written through. The rename replaces the entry at `target` itself.
void write_through_staging(const fs::path& target, std::string_view bytes) {
    for (int attempt = 0; attempt < 100; ++attempt) {
        const fs::path staging = private_name(target, ".partial");
        // "x" fails when anything at all has the name, a dangling link included.
#if defined(_WIN32)
        std::FILE* out = _wfopen(staging.c_str(), L"wbx");
#else
        std::FILE* out = std::fopen(staging.c_str(), "wbx");
#endif
        if (out == nullptr) {
            std::error_code ec;
            if (fs::symlink_status(staging, ec).type() != fs::file_type::not_found) continue;
            throw IoError("Cannot write " + target.string());
        }
        const bool written = std::fwrite(bytes.data(), 1, bytes.size(), out) == bytes.size();
        if (std::fclose(out) != 0 || !written) {
            std::error_code ec;
            fs::remove(staging, ec);
            throw IoError("Cannot write " + target.string());
        }
        std::error_code ec;
        fs::rename(staging, target, ec);
        if (ec) {
            fs::remove(staging, ec);
            throw IoError("Cannot write " + target.string());
        }
        return;
    }
    throw IoError("Cannot write " + target.string() + ": no free staging name");
}

// The completion marker of an unpacked project folder: a hidden file beside it holding the archive's SHA-256, written
// last, after the folder is in place. Only a folder with its matching marker is a finished download.
fs::path marker_of(const fs::path& folder) { return folder.parent_path() / ("." + folder.filename().string() + ".complete"); }

bool plain_file(const fs::path& path) {
    std::error_code ec;
    return !fs::is_symlink(path, ec) && fs::is_regular_file(path, ec);
}

// Create `path` as a new folder only its owner can enter, in one step, so it is never visible with wider permissions;
// false without an error when the name is taken.
bool private_directory(const fs::path& path, std::error_code& ec) {
    ec.clear();
#if defined(_WIN32)
    return fs::create_directory(path, ec);  // a new folder is the user's own under their profile's ACLs
#else
    if (::mkdir(path.c_str(), S_IRWXU) == 0) return true;
    if (errno != EEXIST) ec = std::error_code(errno, std::generic_category());
    return false;
#endif
}

// Give a complete unpacked tree its final folder permissions before it is published: the owner keeps full access, so
// the tree can always be traversed and removed again, and group and others get what `destination` grants them. The
// folders are listed first, while all of them are still owner-only, and every filesystem call is checked on its own;
// the first failure throws and nothing is published.
void finish_permissions(const fs::path& staging, const fs::path& destination) {
    std::error_code ec;
    const auto refuse = [&](const fs::path& at) {
        throw IoError("Cannot set the permissions of " + at.string() + ": " + ec.message());
    };
    const fs::file_status parent = fs::status(destination.empty() ? fs::path(".") : destination, ec);
    if (ec) refuse(destination);
    const fs::perms shared =
        fs::perms::owner_all | (parent.permissions() & (fs::perms::group_all | fs::perms::others_all));
    std::vector<fs::path> folders;
    fs::recursive_directory_iterator it(staging, ec);
    if (ec) refuse(staging);
    for (const fs::recursive_directory_iterator end; it != end;) {
        const fs::file_status entry = it->symlink_status(ec);
        if (ec) refuse(it->path());
        if (fs::is_directory(entry)) folders.push_back(it->path());
        it.increment(ec);
        if (ec) refuse(staging);
    }
    folders.push_back(staging);
    for (const fs::path& folder : folders) {
        fs::permissions(folder, shared, fs::perm_options::replace, ec);
        if (ec) refuse(folder);
    }
}

// Unpack into a folder this call creates and owns beside `target`, then publish the complete tree by one rename and
// write its marker. Every filesystem step is checked; on any failure the staging folder goes and nothing is left at
// `target` or its marker for a later download to take.
std::string unpack_staged(std::string_view bytes, const fs::path& target, const std::string& digest) {
    std::error_code ec;
    fs::remove(marker_of(target), ec);
    if (fs::symlink_status(target, ec).type() != fs::file_type::not_found) {
        fs::remove_all(target, ec);  // an old tree, a link or a file: replaced, never written into or followed
        if (ec) throw IoError("Cannot replace " + target.string() + ": " + ec.message());
    }
    fs::path staging;
    for (int attempt = 0; attempt < 100 && staging.empty(); ++attempt) {
        const fs::path name = private_name(target, ".unpacking");
        if (private_directory(name, ec)) staging = name;
        else if (ec) throw IoError("Cannot create a folder beside " + target.string() + ": " + ec.message());
    }
    if (staging.empty()) throw IoError("Cannot unpack " + target.string() + ": no free staging name");
    std::string inside;
    try {
        inside = fs::path(unpack_project_archive(bytes, staging.string(), NameRule::collection))
                     .lexically_relative(staging)
                     .string();
        finish_permissions(staging, target.parent_path());
        fs::rename(staging, target, ec);
        if (ec) throw IoError("Cannot put " + target.string() + " in place: " + ec.message());
    } catch (...) {
        fs::remove_all(staging, ec);
        throw;
    }
    write_through_staging(marker_of(target), digest);
    return inside.empty() || inside == "." ? target.string() : (target / inside).string();
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
    // As diffraction-lib lists them: entries with a learning order first, in that order, then the rest by id.
    std::stable_sort(out.begin(), out.end(), [](const Entry* a, const Entry* b) {
        const bool ordered_a = a->order >= 0, ordered_b = b->order >= 0;
        if (ordered_a != ordered_b) return ordered_a;
        if (ordered_a && a->order != b->order) return a->order < b->order;
        return a->id < b->id;
    });
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

std::string file_name(const File& file) {
    return safe_relative_path(file.path.substr(file.path.find_last_of('/') + 1)).string();
}

Placement placement(const std::string& destination, const Entry& entry, const File& file) {
    // Every name is admitted by safe_relative_path, one plain segment each, so each place is a direct child of the
    // destination by construction.
    const fs::path root(destination);
    Placement where{(root / file_name(file)).string(), {}, entry.kind == "tutorial"};
    if (entry.kind == "project" && file.format == "zip") {
        const std::string name = file.sha256.empty() ? entry.id : entry.id + "-" + lowercase(file.sha256).substr(0, 12);
        where.folder = (root / safe_relative_path(name)).string();
    }
    return where;
}

std::string stored(const Placement& where, const File& file) {
    if (!where.folder.empty()) {
        // A project counts as downloaded only when its marker is there and names this archive's digest.
        const fs::path marker = marker_of(where.folder);
        if (file.sha256.empty() || !plain_file(marker) || read_file(marker) != lowercase(file.sha256)) return {};
        return project_folder(where.folder);
    }
    if (plain_file(where.file) && (where.keep_edited || content_mismatch(read_file(where.file), file) == Mismatch::none))
        return where.file;
    return {};
}

std::string store(const Placement& where, const File& file, std::string_view bytes, bool overwrite) {
    if (const auto problem = content_problem(bytes, file, where.file); !problem.empty()) throw std::runtime_error(problem);
    if (!overwrite) {
        if (const auto kept = stored(where, file); !kept.empty()) return kept;
    }
    std::error_code ec;
    const fs::path parent = fs::path(where.folder.empty() ? where.file : where.folder).parent_path();
    if (!parent.empty()) {
        fs::create_directories(parent, ec);
        if (ec) throw IoError("Cannot create " + parent.string() + ": " + ec.message());
    }
    if (!where.folder.empty()) return unpack_staged(bytes, where.folder, lowercase(file.sha256));
    write_through_staging(where.file, bytes);
    return where.file;
}


const std::vector<std::string>& default_collection_sources() {
    static const std::vector<std::string> sources = {"https://raw.githubusercontent.com/enhantica/edi-data/main",
                                                     "https://data.easydiffraction.org"};
    return sources;
}

const std::string& default_tutorials_source() {
    static const std::string source = "https://enhantica.github.io/edi/tutorials";
    return source;
}

std::vector<std::string> sources_for(const std::string& source, const char* variable,
                                     const std::vector<std::string>& defaults) {
    if (!source.empty()) return {source};
    if (const char* given = std::getenv(variable); given != nullptr && *given != '\0') return {given};
    return defaults;
}

Reply read_local(const std::string& url) {
    const std::string path = url.rfind("file://", 0) == 0 ? url.substr(7) : url;
    std::error_code ec;
    if (!fs::is_regular_file(path, ec)) return {false, {}, path + " does not exist", true};
    std::ifstream in(path, std::ios::binary);
    if (!in) return {false, {}, path + " cannot be read", false};
    return {true, {std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>()}, {}, false};
}

std::string read_through(FileRead read, const Transport& transport, std::string* served) {
    while (!read.done()) {
        Reply reply = transport(read.url());
        if (reply.ok) read.answered(std::move(reply.bytes));
        else read.failed(reply.error, reply.outage);
    }
    if (!read.ok()) {
        if (read.unreachable()) throw Unreachable(read.error());
        throw std::invalid_argument(read.error());
    }
    if (served != nullptr) *served = read.served_by();
    return read.bytes();
}

std::string read_index(std::vector<std::string>& sources, const Transport& transport) {
    std::string served;
    std::string text = read_through(FileRead(sources, "index.json"), transport, &served);
    const auto first = std::find(sources.begin(), sources.end(), served);
    if (first != sources.end()) std::rotate(sources.begin(), first, first + 1);
    return text;
}

std::string fetch(const std::vector<std::string>& sources, const std::string& index_text, const std::string& id,
                  const std::string& into, const Transport& transport) {
    const Index index = parse_index(index_text);
    const Entry* entry = find(index, id);
    if (entry == nullptr) throw std::invalid_argument("No entry '" + id + "' in the collection");
    const File& file = entry->files.front();
    Placement where = placement(into, *entry, file);
    where.folder.clear();  // the file itself, never unpacked
    return store(where, file, read_through(FileRead(sources, file), transport), true);
}

std::string download(const std::vector<std::string>& sources, const std::string& index_text, const std::string& name,
                     const std::string& kind, const std::string& format, const std::string& destination,
                     bool overwrite, const Transport& transport) {
    const Index index = parse_index(index_text);
    const Entry& entry = resolve(index, name, kind);
    const File* chosen = nullptr;
    for (const File& file : entry.files)
        if (format.empty() || file.format == format) {
            chosen = &file;
            break;
        }
    if (chosen == nullptr) throw std::invalid_argument("Entry '" + entry.id + "' has no " + format + " file");
    const Placement where = placement(destination, entry, *chosen);
    if (!overwrite) {
        if (std::string kept = stored(where, *chosen); !kept.empty()) return kept;
    }
    const std::string bytes = read_through(FileRead(sources, *chosen), transport);
    return store(where, *chosen, bytes, overwrite);
}

}  // namespace edi::online
