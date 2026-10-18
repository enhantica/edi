#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int matches(const char* path, const char* key) {
    const char* target = getenv(key);
    return target && path && !strcmp(path, target);
}
static void receipt(const char* text) {
    const char* path = getenv("SCAN_FAULT_RECEIPT");
    int fd = path ? open(path, O_CREAT | O_WRONLY | O_APPEND, 0600) : -1;
    if (fd >= 0) { write(fd, text, strlen(text)); close(fd); }
}
static int read_source(int fd) {
    if (!getenv("SCAN_FAULT_ARMED")) return 0;
    char path[4096];
#ifdef __APPLE__
    if (fcntl(fd, F_GETPATH, path) != 0) return 0;
#else
    char link[64];
    snprintf(link, sizeof link, "/proc/self/fd/%d", fd);
    ssize_t n = readlink(link, path, sizeof(path) - 1);
    if (n < 0) return 0;
    path[n] = 0;
#endif
    return matches(path, "SCAN_FAULT_READ_PATH");
}
ssize_t read(int fd, void* buffer, size_t count) {
    ssize_t (*original)(int, void*, size_t) = dlsym(RTLD_NEXT, "read");
    static int prefix = 0;
    if (read_source(fd)) {
        const char* after = getenv("SCAN_FAULT_PREFIX");
        if (after && !prefix) {
            prefix = 1;
            receipt("source-prefix\n");
            return original(fd, buffer, count > 17 ? 17 : count);
        }
        receipt("source-read-failed\n");
        errno = EIO;
        return -1;
    }
    return original(fd, buffer, count);
}
size_t fread(void* buffer, size_t size, size_t count, FILE* stream) {
    size_t (*original)(void*, size_t, size_t, FILE*) = dlsym(RTLD_NEXT, "fread");
    static int prefix = 0;
    if (!size || !count) return original(buffer, size, count, stream);
    if (read_source(fileno(stream))) {
        if (getenv("SCAN_FAULT_PREFIX") && !prefix) {
            prefix = 1;
            receipt("source-prefix\n");
            return original(buffer, size, count > 17 / size ? 17 / size : count, stream);
        }
        /* libc++ uses fread; glibc's stream error flag is set by a failed underlying read. */
        receipt("source-fread-failed\n");
        int saved = dup(fileno(stream));
        close(fileno(stream));
        size_t result = original(buffer, size, count, stream);
        dup2(saved, fileno(stream)); close(saved);
        return result;
    }
    return original(buffer, size, count, stream);
}
int unlink(const char* path) {
    int (*original)(const char*) = dlsym(RTLD_NEXT, "unlink");
    if (matches(path, "SCAN_FAULT_REMOVE_PATH")) { receipt("remove-refused\n"); errno = EACCES; return -1; }
    return original(path);
}
int remove(const char* path) {
    int (*original)(const char*) = dlsym(RTLD_NEXT, "remove");
    if (matches(path, "SCAN_FAULT_REMOVE_PATH")) { receipt("remove-refused\n"); errno = EACCES; return -1; }
    return original(path);
}
int rename(const char* from, const char* to) {
    int (*original)(const char*, const char*) = dlsym(RTLD_NEXT, "rename");
    if (matches(to, "SCAN_FAULT_RENAME_PATH")) { receipt("rename-after-write-refused\n"); errno = EACCES; return -1; }
    return original(from, to);
}
