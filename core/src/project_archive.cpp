// SPDX-License-Identifier: BSD-3-Clause
#include "edi/project_archive.hpp"

#include <algorithm>
#include <atomic>
#include <cctype>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <memory>
#include <mutex>
#include <random>
#include <sstream>
#include <system_error>

#include "edi/io.hpp"
#include "miniz.h"

#if defined(_WIN32)
#include <process.h>
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#else
#include <unistd.h>

#include <cerrno>
#include <csignal>
#endif

namespace fs = std::filesystem;

namespace edi {
namespace {

bool excluded(const fs::path& relative) {
    for (const fs::path& part : relative) {
        const std::string name = part.string();
        if (name.starts_with('.') || name == "__pycache__" || name == "build") {
            return true;
        }
    }
    const std::string file = relative.filename().string();
    return file.ends_with(".edi-staged") || file.ends_with(".pyc");
}

std::string read_bytes(const fs::path& path) {
    std::ifstream stream(path, std::ios::binary);
    if (!stream) {
        throw IoError("cannot read " + path.string());
    }
    std::ostringstream buffer;
    buffer << stream.rdbuf();
    return buffer.str();
}

MZ_TIME_T modification_time(const fs::path& path) {
    std::error_code error;
    const fs::file_time_type written = fs::last_write_time(path, error);
    if (error) {
        return 0;
    }
    // The file clock's epoch is unspecified: its offset from the system clock now carries the time
    // across.
    const auto system = std::chrono::time_point_cast<std::chrono::system_clock::duration>(
        written - fs::file_time_type::clock::now() + std::chrono::system_clock::now());
    return static_cast<MZ_TIME_T>(std::chrono::system_clock::to_time_t(system));
}

// The writer's archive, ended whichever way the work leaves.
struct Writer {
    mz_zip_archive zip{};
    bool open = false;
    ~Writer() {
        if (open) {
            mz_zip_writer_end(&zip);
        }
    }
};

struct Reader {
    mz_zip_archive zip{};
    bool open = false;
    ~Reader() {
        if (open) {
            mz_zip_reader_end(&zip);
        }
    }
};

// A member name that stays inside the project folder: relative, with no drive, no backslash and no
// `..` component.
bool inside(const std::string& name) {
    if (name.empty() || name.front() == '/' || name.find('\\') != std::string::npos ||
        name.find(':') != std::string::npos) {
        return false;
    }
    std::size_t start = 0;
    while (start <= name.size()) {
        const std::size_t end = std::min(name.find('/', start), name.size());
        if (name.compare(start, end - start, "..") == 0 && end - start == 2) {
            return false;
        }
        start = end + 1;
    }
    return true;
}

bool is_link(const mz_zip_archive_file_stat& stat) {
    // The Unix mode sits in the upper half of the external attributes; 0120000 is a symbolic link.
    return ((stat.m_external_attr >> 16) & 0170000U) == 0120000U;
}

}  // namespace

std::vector<std::string> project_archive_members(const std::string& directory) {
    const fs::path root(directory);
    std::error_code error;
    if (!fs::is_directory(root, error)) {
        throw IoError("not a project directory: " + directory);
    }
    std::vector<std::string> members;
    for (fs::recursive_directory_iterator it(root, error), end; !error && it != end;
         it.increment(error)) {
        // Named by where the entry is in the folder, never where a link leads.
        const fs::path relative = it->path().lexically_relative(root);
        std::error_code status;
        if (excluded(relative)) {
            if (it->is_directory(status)) {
                it.disable_recursion_pending();
            }
            continue;
        }
        const std::string name = relative.generic_string();
        // A link to a file is archived as that file under the link's own name; a link to a folder, or one that
        // leads nowhere, is refused rather than left out.
        if (it->is_symlink(status)) {
            if (fs::is_directory(it->path(), status)) {
                throw IoError("cannot archive " + name + ": it is a link to a folder");
            }
            if (!fs::is_regular_file(it->path(), status)) {
                throw IoError("cannot archive " + name + ": it is a link to no file");
            }
            members.push_back(name);
        } else if (it->is_regular_file(status)) {
            members.push_back(name);
        }
    }
    if (error) {
        throw IoError("cannot list " + directory + ": " + error.message());
    }
    std::sort(members.begin(), members.end());
    for (std::size_t index = 0; index < members.size(); ++index) {
        if (!inside(members[index]) || (index > 0 && members[index] == members[index - 1])) {
            throw IoError("cannot archive " + members[index] + ": not a single name inside the project");
        }
    }
    return members;
}

namespace {

// Each member of a finished archive stored as a Unix regular file readable by everyone and writable by its owner
// (0644), as Qt's writer stores them: miniz leaves the mode out, and an extractor that applies stored modes would
// otherwise write files nobody can read. The central directory's records are walked from its end record.
void give_members_unix_modes(std::string& archive) {
    const auto u16 = [&archive](std::size_t at) {
        return static_cast<unsigned>(static_cast<unsigned char>(archive[at])) |
               static_cast<unsigned>(static_cast<unsigned char>(archive[at + 1])) << 8U;
    };
    const auto u32 = [&u16](std::size_t at) { return u16(at) | u16(at + 2) << 16U; };
    const auto u64 = [&u32](std::size_t at) {
        return static_cast<std::uint64_t>(u32(at)) | static_cast<std::uint64_t>(u32(at + 4)) << 32U;
    };
    const auto put32 = [&archive](std::size_t at, unsigned value) {
        for (int byte = 0; byte < 4; ++byte) {
            archive[at + static_cast<std::size_t>(byte)] = static_cast<char>((value >> (8 * byte)) & 0xFFU);
        }
    };
    constexpr std::size_t kEndRecord = 22;
    if (archive.size() < kEndRecord || u32(archive.size() - kEndRecord) != 0x06054b50U) {
        throw IoError("cannot finish the archive: no end of its central directory");
    }
    const std::size_t end = archive.size() - kEndRecord;
    std::uint64_t entries = u16(end + 10);
    std::uint64_t at = u32(end + 16);
    // A ZIP64 archive (more members, or a larger directory, than the end record holds) keeps the full count and
    // offset in the ZIP64 end record, which its locator, just before the end record, names. A maximal value alone is
    // no proof: a classic archive of exactly 65,535 members holds 0xFFFF there, with no locator.
    constexpr std::size_t kLocator = 20;
    const bool locator = end >= kLocator && u32(end - kLocator) == 0x07064b50U;
    if ((entries == 0xFFFFU || at == 0xFFFFFFFFU) && locator) {
        const std::uint64_t record = u64(end - kLocator + 8);
        if (record + 56 > end || u32(record) != 0x06064b50U) {
            throw IoError("cannot finish the archive: its ZIP64 end record does not read");
        }
        entries = u64(record + 32);
        at = u64(record + 48);
    }
    for (std::uint64_t entry = 0; entry < entries; ++entry) {
        if (at + 46 > end || u32(at) != 0x02014b50U) {
            throw IoError("cannot finish the archive: its central directory does not read");
        }
        archive[at + 5] = 3;                    // made by Unix, so the mode below is read
        put32(at + 38, 0100644U << 16U);        // a regular file, rw-r--r--
        at += 46 + u16(at + 28) + u16(at + 30) + u16(at + 32);
    }
}

}  // namespace

// An archive of members whose bytes `body` reads and whose time `time` gives.
template <typename Body, typename Time>
std::string archive_of(const std::vector<std::string>& members, const Body& body,
                       const Time& time) {
    Writer writer;
    if (!mz_zip_writer_init_heap(&writer.zip, 0, 0)) {
        throw IoError("cannot start an archive");
    }
    writer.open = true;
    for (std::size_t index = 0; index < members.size(); ++index) {
        const std::string& member = members[index];
        const std::string data = body(index);
        MZ_TIME_T written = time(index);
        if (!mz_zip_writer_add_mem_ex_v2(&writer.zip, member.c_str(), data.data(), data.size(),
                                         nullptr, 0, MZ_DEFAULT_LEVEL, 0, 0, &written, nullptr, 0,
                                         nullptr, 0)) {
            throw IoError("cannot add " + member + " to the archive");
        }
    }
    void* buffer = nullptr;
    std::size_t size = 0;
    if (!mz_zip_writer_finalize_heap_archive(&writer.zip, &buffer, &size)) {
        throw IoError("cannot finish the archive");
    }
    const std::unique_ptr<void, decltype(&mz_free)> owned(buffer, &mz_free);
    std::string archive(static_cast<const char*>(buffer), size);
    give_members_unix_modes(archive);
    return archive;
}

std::string project_archive_bytes(const std::string& directory) {
    const std::vector<std::string> members = project_archive_members(directory);
    const auto path = [&](std::size_t index) {
        return fs::path(directory) / fs::path(members[index]);
    };
    return archive_of(
        members, [&](std::size_t index) { return read_bytes(path(index)); },
        [&](std::size_t index) { return modification_time(path(index)); });
}

std::string archive_bytes(const std::vector<std::pair<std::string, std::string>>& members) {
    std::vector<std::string> names;
    names.reserve(members.size());
    for (const auto& member : members) {
        names.push_back(member.first);
    }
    const MZ_TIME_T now = std::time(nullptr);
    return archive_of(
        names, [&](std::size_t index) { return members[index].second; },
        [&](std::size_t) { return now; });
}

void write_project_archive(const std::string& directory, const std::string& archive) {
    const fs::path folder = fs::weakly_canonical(fs::path(directory));
    const fs::path target = fs::weakly_canonical(fs::path(archive));
    const auto [inner, outer] =
        std::mismatch(folder.begin(), folder.end(), target.begin(), target.end());
    if (inner == folder.end()) {
        throw IoError("cannot write the archive " + archive +
                      " inside the project folder it archives");
    }
    const std::string bytes = project_archive_bytes(directory);
    const fs::path staged = target.parent_path() / (target.filename().string() + ".edi-staged");
    {
        std::ofstream stream(staged, std::ios::binary | std::ios::trunc);
        if (!stream || !stream.write(bytes.data(), static_cast<std::streamsize>(bytes.size())) ||
            !stream.flush()) {
            std::error_code ignored;
            fs::remove(staged, ignored);
            throw IoError("cannot write " + archive);
        }
    }
    std::error_code error;
    fs::rename(staged, target, error);
    if (error) {
        fs::remove(staged, error);
        throw IoError("cannot write " + archive);
    }
}

std::string unpack_project_archive(std::string_view bytes, const std::string& target) {
    Reader reader;
    if (bytes.empty() || !mz_zip_reader_init_mem(&reader.zip, bytes.data(), bytes.size(), 0)) {
        throw IoError("the file is not a .zip archive");
    }
    reader.open = true;
    const mz_uint count = mz_zip_reader_get_num_files(&reader.zip);
    if (count == 0) {
        throw IoError("the .zip archive is empty");
    }
    std::vector<mz_zip_archive_file_stat> entries(count);
    for (mz_uint index = 0; index < count; ++index) {
        if (!mz_zip_reader_file_stat(&reader.zip, index, &entries[index])) {
            throw IoError("the .zip archive is damaged");
        }
        if (!inside(entries[index].m_filename)) {
            throw IoError(std::string("the archive names a path outside its folder: ") +
                          entries[index].m_filename);
        }
        if (!entries[index].m_is_supported) {
            throw IoError(
                std::string(
                    "the archive's member cannot be read (encrypted or an unknown method): ") +
                entries[index].m_filename);
        }
    }
    const fs::path root(target);
    std::error_code error;
    fs::create_directories(root, error);
    if (error) {
        throw IoError("cannot create " + target + ": " + error.message());
    }
    for (mz_uint index = 0; index < count; ++index) {
        const mz_zip_archive_file_stat& entry = entries[index];
        const fs::path path = root / fs::path(entry.m_filename);
        if (entry.m_is_directory) {
            fs::create_directories(path, error);
            continue;
        }
        if (is_link(entry)) {
            continue;
        }
        std::size_t size = 0;
        void* data = mz_zip_reader_extract_to_heap(&reader.zip, index, &size, 0);
        if (data == nullptr) {
            throw IoError(std::string("cannot unpack ") + entry.m_filename);
        }
        const std::unique_ptr<void, decltype(&mz_free)> owned(data, &mz_free);
        fs::create_directories(path.parent_path(), error);
        std::ofstream stream(path, std::ios::binary | std::ios::trunc);
        if (!stream ||
            !stream.write(static_cast<const char*>(data), static_cast<std::streamsize>(size))) {
            throw IoError(std::string("cannot unpack ") + entry.m_filename);
        }
    }
    if (fs::is_regular_file(root / "project.edi")) {
        return root.string();
    }
    std::vector<fs::path> folders;
    for (const fs::directory_entry& child : fs::directory_iterator(root, error)) {
        if (child.is_directory()) {
            folders.push_back(child.path());
        }
    }
    if (folders.size() == 1 && fs::is_regular_file(folders.front() / "project.edi")) {
        return folders.front().string();
    }
    throw IoError("the archive holds no project: no project.edi at its top or in its one folder");
}

bool is_project_archive(const std::string& path) {
    std::string extension = fs::path(path).extension().string();
    std::transform(extension.begin(), extension.end(), extension.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    std::error_code error;
    return extension == ".zip" && fs::is_regular_file(fs::path(path), error);
}

namespace {

fs::path archive_base() {
    std::error_code error;
    return fs::temp_directory_path(error) / "edi-archives";
}

long this_process() {
#if defined(_WIN32)
    return static_cast<long>(_getpid());
#else
    return static_cast<long>(getpid());
#endif
}

bool running(long pid) {
#if defined(_WIN32)
    HANDLE process =
        OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, static_cast<DWORD>(pid));
    if (process == nullptr) {
        return false;
    }
    DWORD code = 0;
    const bool alive = GetExitCodeProcess(process, &code) && code == STILL_ACTIVE;
    CloseHandle(process);
    return alive;
#else
    return kill(static_cast<pid_t>(pid), 0) == 0 || errno == EPERM;
#endif
}

// The directories this process made, removed when it ends normally.
struct Made {
    std::mutex mutex;
    std::vector<fs::path> paths;
    Made() = default;
    Made(const Made&) = delete;
    Made& operator=(const Made&) = delete;
    Made(Made&&) = delete;
    Made& operator=(Made&&) = delete;
    ~Made() {
        for (const fs::path& path : paths) {
            std::error_code ignored;
            fs::remove_all(path, ignored);
        }
    }
};

auto recorded_root(std::vector<fs::path>& paths,const fs::path& given) {
    return std::find_if(paths.begin(),paths.end(),[&](const auto& root) {
        const auto [inner,outer]=std::mismatch(root.begin(),root.end(),given.begin(),given.end());
        return inner==root.end();
    });
}

Made& made() {
    static Made directories;
    return directories;
}

}  // namespace

std::string fresh_archive_directory(const std::string& kind) {
    static std::atomic<unsigned> counter{0};
    std::error_code error;
    const fs::path base = archive_base();
    std::random_device seed;
    for (int attempt = 0; attempt < 100; ++attempt) {
        const fs::path path =
            base / (kind + "-" + std::to_string(this_process()) + "-" + std::to_string(seed()) +
                    "-" + std::to_string(counter.fetch_add(1)));
        fs::create_directories(base, error);
        if (fs::create_directory(path, error) && !error) {
            const std::lock_guard lock(made().mutex);
            made().paths.push_back(path);
            return path.string();
        }
    }
    throw IoError("cannot create a temporary directory for an archive");
}

namespace detail {
std::string archive_directory_root(const std::string& path) {
    const fs::path given=fs::path(path).lexically_normal();
    const std::lock_guard lock(made().mutex);
    auto& paths=made().paths;
    const auto found=recorded_root(paths,given);
    return found==paths.end()?std::string{}:found->string();
}
} // namespace detail

void remove_archive_directory(const std::string& path) {
    const fs::path given=fs::path(path).lexically_normal();
    const std::lock_guard lock(made().mutex);
    auto& paths=made().paths;
    const auto found=recorded_root(paths,given);
    if(found!=paths.end()) {
        std::error_code ignored;fs::remove_all(*found,ignored);paths.erase(found);
    }
}

void remove_stale_archive_directories() {
    std::error_code error;
    for (const fs::directory_entry& entry : fs::directory_iterator(archive_base(), error)) {
        // <kind>-<pid>-<random>-<count>
        const std::string name = entry.path().filename().string();
        const std::size_t first = name.find('-');
        const std::size_t second =
            first == std::string::npos ? std::string::npos : name.find('-', first + 1);
        if (second == std::string::npos) {
            continue;
        }
        long pid = 0;
        try {
            pid = std::stol(name.substr(first + 1, second - first - 1));
        } catch (const std::exception&) {
            continue;
        }
        if (pid > 0 && pid != this_process() && !running(pid)) {
            std::error_code ignored;
            fs::remove_all(entry.path(), ignored);
        }
    }
}

}  // namespace edi
