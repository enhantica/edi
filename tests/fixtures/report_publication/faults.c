// SPDX-License-Identifier: BSD-3-Clause
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/uio.h>
#include <unistd.h>
#include "../project_output/fault_interpose.h"

static void receipt(const char* event, const char* path) {
    const char* log = getenv("EDI_REPORT_FAULT_LOG");
    if (!log) return;
    int fd = open(log, O_WRONLY | O_CREAT | O_APPEND, 0600);
    if (fd < 0) return;
    ssize_t (*real_write)(int, const void*, size_t) = REAL(write);
    real_write(fd, event, strlen(event));
    real_write(fd, " ", 1);
    real_write(fd, path, strlen(path));
    real_write(fd, "\n", 1);
    close(fd);
}
static int target(int fd, char* path, const void* buffer, size_t size) {
    const char* directory = getenv("EDI_REPORT_FAULT_DIR");
    const char* kind = getenv("EDI_REPORT_FAULT_KIND");
    if (!directory || !kind || !strcmp(kind, "settings") || !strcmp(kind, "scan-rename")) return 0;
#ifdef __APPLE__
    if (fcntl(fd, F_GETPATH, path) != 0) return 0;
#else
    char link[64];
    snprintf(link, sizeof(link), "/proc/self/fd/%d", fd);
    ssize_t n = readlink(link, path, PATH_MAX - 1);
    if (n < 0) return 0;
    path[n] = 0;
#endif
    if (strncmp(path, directory, strlen(directory)) || path[strlen(directory)] != '/') return 0;
    const char* base = path + strlen(directory) + 1;
    if (!strcmp(kind, "settings-write")) return strstr(base, "report.edi") != NULL;
    if (!strcmp(kind, "settings-close")) {
        const char* leaf = strrchr(path, '/');
        leaf = leaf ? leaf + 1 : path;
        return size == 0 && strstr(leaf, "report.edi") && strcmp(leaf, "report.edi");
    }
    if (!strcmp(kind, "pdf")) return strstr(base, ".pdf") != NULL || (size >= 4 && !memcmp(buffer, "%PDF", 4));
    return !strstr(base, "report.edi") && !strstr(base, ".pdf") && !strstr(base, ".cif");
}
ssize_t FAULT(write)(int fd, const void* buffer, size_t size) {
    ssize_t (*real_write)(int, const void*, size_t) = REAL(write);
    char path[PATH_MAX];
    if (size && target(fd, path, buffer, size)) {
        real_write(fd, buffer, size < 64 ? size : 64);
        receipt("write-after-open", path);
        errno = ENOSPC;
        return -1;
    }
    return real_write(fd, buffer, size);
}
ssize_t FAULT(writev)(int fd, const struct iovec* vectors, int count) {
    ssize_t (*real_writev)(int, const struct iovec*, int) = REAL(writev);
    char path[PATH_MAX];
    if (count && target(fd, path, vectors[0].iov_base, vectors[0].iov_len)) {
        ssize_t (*real_write)(int, const void*, size_t) = REAL(write);
        real_write(fd, vectors[0].iov_base, vectors[0].iov_len < 64 ? vectors[0].iov_len : 64);
        receipt("write-after-open", path);
        errno = ENOSPC;
        return -1;
    }
    return real_writev(fd, vectors, count);
}
int FAULT(close)(int fd) {
    int (*real_close)(int) = REAL(close);
    const char* kind = getenv("EDI_REPORT_FAULT_KIND");
    char path[PATH_MAX];
    if (kind && !strcmp(kind, "settings-close") && target(fd, path, "", 0)) {
        int result = real_close(fd);
        if (result != 0) return result;
        receipt("close-after-write", path);
        errno = EIO;
        return -1;
    }
    return real_close(fd);
}
int FAULT(fclose)(FILE* stream) {
    int (*real_fclose)(FILE*) = REAL(fclose);
    const char* kind = getenv("EDI_REPORT_FAULT_KIND");
    char path[PATH_MAX];
    if (kind && !strcmp(kind, "settings-close") && target(fileno(stream), path, "", 0)) {
        int result = real_fclose(stream);
        if (result != 0) return result;
        receipt("close-after-write", path);
        errno = EIO;
        return EOF;
    }
    return real_fclose(stream);
}
/* Both module placements and the retained multi-file staging route reach rename. */
static int scan_temporary(const char* from, const char* to, const char* directory) {
    size_t n = strlen(directory);
    if (strncmp(to, directory, n) || to[n] != '/') return 0;
    const char* leaf = to + n + 1;
    if (!*leaf || strchr(leaf, '/')) return 0;
    char expected[PATH_MAX];
    int size = snprintf(expected, sizeof(expected), "%s.edi-staged", to);
    if (size >= 0 && size < (int)sizeof(expected) && !strcmp(from, expected)) return 1;
    size = snprintf(expected, sizeof(expected), "%s.tmp", to);
    if (size >= 0 && size < (int)sizeof(expected) && !strcmp(from, expected)) return 1;
    const char* slash = strrchr(directory, '/');
    if (!slash) return 0;
    size = snprintf(expected, sizeof(expected), "%.*s/.%s.tmp",
                    (int)(slash - directory), directory, leaf);
    return size >= 0 && size < (int)sizeof(expected) && !strcmp(from, expected);
}
int FAULT(rename)(const char* from, const char* to) {
    int (*real_rename)(const char*, const char*) = REAL(rename);
    const char* directory = getenv("EDI_REPORT_FAULT_DIR");
    const char* kind = getenv("EDI_REPORT_FAULT_KIND");
    if (directory && kind && !strcmp(kind, "settings") &&
        !strncmp(to, directory, strlen(directory)) && !strcmp(to + strlen(directory), "/report.edi")) {
        receipt("settings-rename", to);
        errno = EACCES;
        return -1;
    }
    if (directory && kind && !strcmp(kind, "scan-rename") &&
        scan_temporary(from, to, directory)) {
        receipt("scan-rename-after-write", to);
        errno = EACCES;
        return -1;
    }
    return real_rename(from, to);
}

INTERPOSE(write)
INTERPOSE(writev)
INTERPOSE(close)
INTERPOSE(fclose)
INTERPOSE(rename)
