// SPDX-License-Identifier: BSD-3-Clause
// Linux GNU stream ABI and POSIX/stdio operation faults; no downloader code is linked.
#include <atomic>
#include <cerrno>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <fcntl.h>
#include <ios>
#include <filesystem>
#include <map>
#include <mutex>
#include <string>
#include <sys/syscall.h>
#include <sys/stat.h>
#include <unistd.h>

namespace {
std::atomic<bool> hit{false};
// Interposition may run during other libraries' static initialization or teardown.
std::mutex& writer_lock() { static auto* value = new std::mutex; return *value; }
std::map<void*, std::string>& streams() {
    static auto* value = new std::map<void*, std::string>; return *value;
}
void record(const std::string& text) {
    const char* trace = std::getenv("EDI_REFERENCE_IO_TRACE");
    if (!trace) _exit(71);
    const int output = static_cast<int>(::syscall(SYS_openat, AT_FDCWD, trace,
        O_WRONLY | O_CREAT | O_APPEND, 0600));
    if (output < 0) _exit(72);
    const std::string line = text + "\n";
    ::syscall(SYS_write, output, line.data(), line.size());
    ::syscall(SYS_close, output);
}
void created(const char* path) {
    const char* root = std::getenv("EDI_REFERENCE_IO_ROOT");
    if (!root || std::strncmp(path, root, std::strlen(root)) != 0) return;
    const char* child = path + std::strlen(root);
    if (*child != '/') return;
    struct stat facts{};
    if (::stat(path, &facts) == 0)
        record(std::string("stage|") + path + "|" + std::to_string(facts.st_mode & 0777)
            + "|" + std::to_string(facts.st_uid));
}
bool owned(const char* path) {
    const char* root = std::getenv("EDI_REFERENCE_IO_ROOT");
    const char* leaf = std::strrchr(path, '/');
    return root && std::strncmp(path, root, std::strlen(root)) == 0
        && path[std::strlen(root)] == '/' && leaf && std::strcmp(leaf, "/project.edi") == 0;
}
std::string fd_path(int descriptor) {
    char name[64], path[4096];
    std::snprintf(name, sizeof(name), "/proc/self/fd/%d", descriptor);
    const auto size = ::readlink(name, path, sizeof(path)-1);
    if (size <= 0) return {};
    path[size] = '\0';
    return path;
}
std::string path_at(int directory, const char* path) {
    if (*path == '/') return std::filesystem::path(path).lexically_normal().string();
    const auto base = directory == AT_FDCWD ? std::filesystem::current_path().string() : fd_path(directory);
    return (std::filesystem::path(base) / path).lexically_normal().string();
}
void opened(int descriptor) {
    const auto path = fd_path(descriptor);
    if (!path.empty() && owned(path.c_str())) record("opened|" + path);
}
bool fail(const std::string& path, const char* mode, const char* channel) {
    const char* requested = std::getenv("EDI_REFERENCE_IO_FAILURE");
    if (path.empty() || !owned(path.c_str()) || !requested || std::strcmp(mode, requested) != 0
        || hit.exchange(true)) return false;
    record(std::string(mode) + " " + channel + " " + path);
    errno = EIO;
    return true;
}
std::string stream_path(void* stream) {
    const std::lock_guard<std::mutex> guard(writer_lock());
    const auto found = streams().find(stream);
    return found == streams().end() ? std::string() : found->second;
}
template<class Function> Function next(const char* name) {
    auto result = reinterpret_cast<Function>(::dlsym(RTLD_NEXT, name));
    if (!result) _exit(73);
    return result;
}
}

// These public libstdc++ filebuf operations are declared by the installed C++ headers.
// Explicit this pointers express the Linux GNU member-call ABI only in this test shim.
extern "C" void* stream_open(void*, const char*, std::ios_base::openmode)
    asm("_ZNSt13basic_filebufIcSt11char_traitsIcEE4openEPKcSt13_Ios_Openmode");
extern "C" void* stream_open(void* stream, const char* path, std::ios_base::openmode mode) {
    const auto actual = next<void*(*)(void*, const char*, std::ios_base::openmode)>(
        "_ZNSt13basic_filebufIcSt11char_traitsIcEE4openEPKcSt13_Ios_Openmode");
    void* result = actual(stream, path, mode);
    if (result && (mode & std::ios_base::out) && owned(path)) {
        const std::lock_guard<std::mutex> guard(writer_lock());
        streams()[stream] = path;
        record(std::string("opened|") + path);
    }
    return result;
}
extern "C" int stream_sync(void*) asm("_ZNSt13basic_filebufIcSt11char_traitsIcEE4syncEv");
extern "C" int stream_sync(void* stream) {
    if (fail(stream_path(stream), "flush", "filebuf.sync")) return -1;
    return next<int(*)(void*)>("_ZNSt13basic_filebufIcSt11char_traitsIcEE4syncEv")(stream);
}
extern "C" void* stream_close(void*) asm("_ZNSt13basic_filebufIcSt11char_traitsIcEE5closeEv");
extern "C" void* stream_close(void* stream) {
    const bool refusal = fail(stream_path(stream), "close", "filebuf.close");
    void* result = next<void*(*)(void*)>("_ZNSt13basic_filebufIcSt11char_traitsIcEE5closeEv")(stream);
    { const std::lock_guard<std::mutex> guard(writer_lock()); streams().erase(stream); }
    return refusal ? nullptr : result;
}
extern "C" long stream_write(void*, const char*, long)
    asm("_ZNSt13basic_filebufIcSt11char_traitsIcEE6xsputnEPKcl");
extern "C" long stream_write(void* stream, const char* data, long size) {
    if (fail(stream_path(stream), "write", "filebuf.xsputn")) return 0;
    return next<long(*)(void*, const char*, long)>(
        "_ZNSt13basic_filebufIcSt11char_traitsIcEE6xsputnEPKcl")(stream, data, size);
}
extern "C" ssize_t write(int fd, const void* data, size_t size) {
    if (fail(fd_path(fd), "write", "write")) return -1;
    return next<ssize_t(*)(int, const void*, size_t)>("write")(fd, data, size);
}
extern "C" size_t fwrite(const void* data, size_t size, size_t count, FILE* file) {
    if (fail(fd_path(::fileno(file)), "write", "fwrite")) return 0;
    return next<size_t(*)(const void*, size_t, size_t, FILE*)>("fwrite")(data, size, count, file);
}
extern "C" int fflush(FILE* file) {
    if (file && fail(fd_path(::fileno(file)), "flush", "fflush")) return EOF;
    return next<int(*)(FILE*)>("fflush")(file);
}
extern "C" int fsync(int fd) {
    if (fail(fd_path(fd), "flush", "fsync")) return -1;
    return next<int(*)(int)>("fsync")(fd);
}
extern "C" int close(int fd) {
    const bool refusal = fail(fd_path(fd), "close", "close");
    const int result = next<int(*)(int)>("close")(fd);
    return refusal ? -1 : result;
}
extern "C" int fclose(FILE* file) {
    const auto path = fd_path(::fileno(file));
    const bool delayed_flush = fail(path, "flush", "fclose.flush");
    const bool refusal = fail(path, "close", "fclose");
    const int result = next<int(*)(FILE*)>("fclose")(file);
    return refusal || delayed_flush ? EOF : result;
}
extern "C" int mkdir(const char* path, mode_t mode) noexcept {
    const int result = next<int(*)(const char*, mode_t)>("mkdir")(path, mode);
    if (result == 0) created(path_at(AT_FDCWD, path).c_str());
    return result;
}
extern "C" char* mkdtemp(char* pattern) noexcept {
    char* result = next<char*(*)(char*)>("mkdtemp")(pattern);
    if (result) created(path_at(AT_FDCWD, result).c_str());
    return result;
}
extern "C" int directory_at(int, const char*, mode_t) asm("mkdirat");
extern "C" int directory_at(int directory, const char* path, mode_t mode) {
    const auto absolute = path_at(directory, path);
    const int result = next<int(*)(int, const char*, mode_t)>("mkdirat")(directory, path, mode);
    if (result == 0) created(absolute.c_str());
    return result;
}
extern "C" FILE* stdio_open(const char*, const char*) asm("fopen");
extern "C" FILE* stdio_open(const char* path, const char* mode) {
    FILE* result = next<FILE*(*)(const char*, const char*)>("fopen")(path, mode);
    if (result && std::strpbrk(mode, "wa+")) opened(::fileno(result));
    return result;
}
extern "C" FILE* stdio_open64(const char*, const char*) asm("fopen64");
extern "C" FILE* stdio_open64(const char* path, const char* mode) {
    FILE* result = next<FILE*(*)(const char*, const char*)>("fopen64")(path, mode);
    if (result && std::strpbrk(mode, "wa+")) opened(::fileno(result));
    return result;
}
extern "C" int descriptor_open(const char*, int, ...) asm("open");
extern "C" int descriptor_open(const char* path, int flags, ...) {
    mode_t mode = 0;
    if ((flags & O_CREAT) || ((flags & O_TMPFILE) == O_TMPFILE)) {
        va_list args;va_start(args, flags);mode=va_arg(args, mode_t);va_end(args);
    }
    const int result = next<int(*)(const char*, int, ...)>("open")(path, flags, mode);
    if (result >= 0 && (flags & (O_WRONLY | O_RDWR))) opened(result);
    return result;
}
extern "C" int descriptor_open64(const char*, int, ...) asm("open64");
extern "C" int descriptor_open64(const char* path, int flags, ...) {
    mode_t mode = 0;
    if ((flags & O_CREAT) || ((flags & O_TMPFILE) == O_TMPFILE)) {
        va_list args;va_start(args, flags);mode=va_arg(args, mode_t);va_end(args);
    }
    const int result = next<int(*)(const char*, int, ...)>("open64")(path, flags, mode);
    if (result >= 0 && (flags & (O_WRONLY | O_RDWR))) opened(result);
    return result;
}
extern "C" int descriptor_openat(int, const char*, int, ...) asm("openat");
extern "C" int descriptor_openat(int directory, const char* path, int flags, ...) {
    mode_t mode = 0;
    if ((flags & O_CREAT) || ((flags & O_TMPFILE) == O_TMPFILE)) {
        va_list args;va_start(args, flags);mode=va_arg(args, mode_t);va_end(args);
    }
    const int result = next<int(*)(int, const char*, int, ...)>("openat")(directory, path, flags, mode);
    if (result >= 0 && (flags & (O_WRONLY | O_RDWR))) opened(result);
    return result;
}
extern "C" int descriptor_openat64(int, const char*, int, ...) asm("openat64");
extern "C" int descriptor_openat64(int directory, const char* path, int flags, ...) {
    mode_t mode = 0;
    if ((flags & O_CREAT) || ((flags & O_TMPFILE) == O_TMPFILE)) {
        va_list args;va_start(args, flags);mode=va_arg(args, mode_t);va_end(args);
    }
    const int result = next<int(*)(int, const char*, int, ...)>("openat64")(directory, path, flags, mode);
    if (result >= 0 && (flags & (O_WRONLY | O_RDWR))) opened(result);
    return result;
}
