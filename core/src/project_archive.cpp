// SPDX-License-Identifier: BSD-3-Clause
#include "edi/project_archive.hpp"

#include <algorithm>
#include <atomic>
#include <cctype>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <memory>
#include <random>
#include <sstream>
#include <system_error>

#include "edi/io.hpp"
#include "miniz.h"

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
        const fs::path relative = fs::relative(it->path(), root);
        if (excluded(relative)) {
            if (it->is_directory()) {
                it.disable_recursion_pending();
            }
            continue;
        }
        if (it->is_regular_file()) {
            members.push_back(relative.generic_string());
        }
    }
    if (error) {
        throw IoError("cannot list " + directory + ": " + error.message());
    }
    std::sort(members.begin(), members.end());
    return members;
}

std::string project_archive_bytes(const std::string& directory) {
    const std::vector<std::string> members = project_archive_members(directory);
    Writer writer;
    if (!mz_zip_writer_init_heap(&writer.zip, 0, 0)) {
        throw IoError("cannot start an archive of " + directory);
    }
    writer.open = true;
    for (const std::string& member : members) {
        const fs::path path = fs::path(directory) / fs::path(member);
        const std::string body = read_bytes(path);
        MZ_TIME_T written = modification_time(path);
        if (!mz_zip_writer_add_mem_ex_v2(&writer.zip, member.c_str(), body.data(), body.size(),
                                         nullptr, 0, MZ_DEFAULT_LEVEL, 0, 0, &written, nullptr, 0,
                                         nullptr, 0)) {
            throw IoError("cannot add " + member + " to the archive of " + directory);
        }
    }
    void* buffer = nullptr;
    std::size_t size = 0;
    if (!mz_zip_writer_finalize_heap_archive(&writer.zip, &buffer, &size)) {
        throw IoError("cannot finish the archive of " + directory);
    }
    const std::unique_ptr<void, decltype(&mz_free)> owned(buffer, &mz_free);
    return std::string(static_cast<const char*>(buffer), size);
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

std::string fresh_archive_directory(const std::string& kind) {
    static std::atomic<unsigned> counter{0};
    std::error_code error;
    const fs::path base = fs::temp_directory_path(error) / "edi-archives";
    std::random_device seed;
    for (int attempt = 0; attempt < 100; ++attempt) {
        const fs::path path = base / (kind + "-" + std::to_string(seed()) + "-" +
                                      std::to_string(counter.fetch_add(1)));
        fs::create_directories(base, error);
        if (fs::create_directory(path, error) && !error) {
            return path.string();
        }
    }
    throw IoError("cannot create a temporary directory for an archive");
}

}  // namespace edi
