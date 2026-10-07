#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <unistd.h>

#ifdef __APPLE__
#include <mach-o/dyld-interposing.h>
#define SCAN_FAULT_NAME(name) scan_contract_fault_##name
#else
#define SCAN_FAULT_NAME(name) name
#endif

#include <atomic>
#include <cstdio>
#include <string>

namespace {
std::string fault_root;
int fault_file = 0;
std::atomic<bool> armed{false}, failed{false};
std::atomic<int> failures{0};
bool refuse(const char* path) {
    if (!armed || !path || std::string(path).find(fault_root) != 0) return false;
    const std::string text(path);
    int file = -1;
    for (int i = 0; i < 3; ++i)
        if (text.find(i == 0   ? "results.csv"
                      : i == 1 ? "results-provenance.csv"
                               : "scan-run.json") != std::string::npos)
            file = i;
    if (file < 0 || (!failed && file != fault_file)) return false;
    failed = true;
    ++failures;
    errno = ENOSPC;
    return true;
}
}  // namespace
void scan_contract_arm_io(const std::string& root, int file) {
    fault_root = root + "/analysis/";
    fault_file = file;
    failures = 0;
    failed = false;
    armed = true;
}
int scan_contract_disarm_io() {
    armed = false;
    return failures;
}
extern "C" int SCAN_FAULT_NAME(open)(const char* path, int flags, ...) {
    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list args;
        va_start(args, flags);
        mode = va_arg(args, int);
        va_end(args);
    }
    if ((flags & (O_WRONLY | O_RDWR)) && refuse(path)) return -1;
#ifdef __APPLE__
    auto real = &::open;
#else
    static auto real = reinterpret_cast<int (*)(const char*, int, ...)>(dlsym(RTLD_NEXT, "open"));
#endif
    return real(path, flags, mode);
}
#ifdef __linux__
extern "C" int open64(const char* path, int flags, ...) {
    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list args;
        va_start(args, flags);
        mode = va_arg(args, int);
        va_end(args);
    }
    if ((flags & (O_WRONLY | O_RDWR)) && refuse(path)) return -1;
    static auto real =
        reinterpret_cast<int (*)(const char*, int, ...)>(dlsym(RTLD_NEXT, "open64"));
    return real(path, flags, mode);
}
#endif
extern "C" int SCAN_FAULT_NAME(unlink)(const char* path) {
    if (refuse(path)) return -1;
#ifdef __APPLE__
    auto real = &::unlink;
#else
    static auto real = reinterpret_cast<int (*)(const char*)>(dlsym(RTLD_NEXT, "unlink"));
#endif
    return real(path);
}
extern "C" int SCAN_FAULT_NAME(unlinkat)(int fd, const char* path, int flags) {
    if (refuse(path)) return -1;
#ifdef __APPLE__
    auto real = &::unlinkat;
#else
    static auto real =
        reinterpret_cast<int (*)(int, const char*, int)>(dlsym(RTLD_NEXT, "unlinkat"));
#endif
    return real(fd, path, flags);
}
extern "C" int SCAN_FAULT_NAME(rename)(const char* from, const char* to) {
    if (refuse(from) || refuse(to)) return -1;
#ifdef __APPLE__
    auto real = &::rename;
#else
    static auto real =
        reinterpret_cast<int (*)(const char*, const char*)>(dlsym(RTLD_NEXT, "rename"));
#endif
    return real(from, to);
}

extern "C" int SCAN_FAULT_NAME(remove)(const char* path) {
    if (refuse(path)) return -1;
#ifdef __APPLE__
    auto real = &::remove;
#else
    static auto real = reinterpret_cast<int (*)(const char*)>(dlsym(RTLD_NEXT, "remove"));
#endif
    return real(path);
}
extern "C" FILE* SCAN_FAULT_NAME(fopen)(const char* path, const char* mode) {
    if ((mode[0] == 'w' || mode[0] == 'a' || std::string(mode).find('+') != std::string::npos) &&
        refuse(path))
        return nullptr;
#ifdef __APPLE__
    auto real = &::fopen;
#else
    static auto real =
        reinterpret_cast<FILE* (*)(const char*, const char*)>(dlsym(RTLD_NEXT, "fopen"));
#endif
    return real(path, mode);
}
#ifdef __linux__
extern "C" FILE* fopen64(const char* path, const char* mode) {
    if ((mode[0] == 'w' || mode[0] == 'a' || std::string(mode).find('+') != std::string::npos) &&
        refuse(path))
        return nullptr;
    static auto real =
        reinterpret_cast<FILE* (*)(const char*, const char*)>(dlsym(RTLD_NEXT, "fopen64"));
    return real(path, mode);
}
#endif

#ifdef __APPLE__
// Darwin's two-level bindings in libc++/libSystem do not resolve to executable
// definitions by name. Interpose their actual imports; retain the Linux actor.
DYLD_INTERPOSE(scan_contract_fault_open, open)
DYLD_INTERPOSE(scan_contract_fault_unlink, unlink)
DYLD_INTERPOSE(scan_contract_fault_unlinkat, unlinkat)
DYLD_INTERPOSE(scan_contract_fault_rename, rename)
DYLD_INTERPOSE(scan_contract_fault_remove, remove)
DYLD_INTERPOSE(scan_contract_fault_fopen, fopen)
#endif
