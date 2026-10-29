#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <inttypes.h>
#include "../project_output/fault_interpose.h"
static int refuse(const char* operation, const char* to) {
    const char* target = getenv("TEMPORARY_FAILURE_TARGET");
    static int fired = 0;
    if (!fired && target && !strcmp(target, to)) {
        fired = 1;
        const char* receipt = getenv("TEMPORARY_FAILURE_RECEIPT");
        int file = receipt ? open(receipt, O_CREAT | O_WRONLY | O_APPEND, 0600) : -1;
        if (file >= 0) {
            write(file, "rename-after-write\n", 19);
            write(file, operation, strlen(operation));
            write(file, "\n", 1);
            close(file);
        }
        errno = EACCES;
        return 1;
    }
    return 0;
}
/* Root-elected opt-in: one successful replacement of ONE exact regular
 * owned fixture file, followed by one genuine EACCES at its next replacement.
 * The default first-failure witness and every unrelated path remain unchanged. */
#ifdef __linux__
static int post_commits;
static int post_failed;
static int post_mode(void) {
    const char* mode = getenv("TEMPORARY_FAILURE_AFTER_FIRST");
    return mode && strcmp(mode, "1") == 0;
}
static int post_selected(const char* to, struct stat* target) {
    const char* name = getenv("TEMPORARY_FAILURE_TARGET");
    const char* armed = getenv("TEMPORARY_FAILURE_ARMED");
    struct stat arm;
    return name && armed && strcmp(to, name) == 0 && lstat(armed, &arm) == 0 &&
           S_ISREG(arm.st_mode) && arm.st_uid == geteuid() && lstat(to, target) == 0 &&
           S_ISREG(target->st_mode) && target->st_uid == geteuid();
}
static void post_receipt(const char* phase, int error, const struct stat* target) {
    const char* name = getenv("TEMPORARY_FAILURE_RECEIPT");
    if (!name) return;
    const int file = open(name, O_CREAT | O_WRONLY | O_APPEND | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (file < 0) return;
    char text[512];
    const int size = snprintf(text, sizeof text,
        "{\"phase\":\"%s\",\"successful_commits\":%d,\"pid\":%ld,\"error\":%d,\"device\":%ju,\"inode\":%ju}\n",
        phase, post_commits, (long)getpid(), error, (uintmax_t)target->st_dev, (uintmax_t)target->st_ino);
    if (size > 0 && size < (int)sizeof text) (void)write(file, text, (size_t)size);
    close(file);
}
#endif

int FAULT(rename)(const char* from, const char* to) {
    int (*original)(const char*, const char*) = REAL(rename);
#ifdef __linux__
    if (post_mode()) {
        struct stat proof;
        if (!post_failed && post_selected(to, &proof)) {
            if (post_commits == 1) {
                post_failed = 1;
                post_receipt("second_replacement_refused", EACCES, &proof);
                errno = EACCES;
                return -1;
            }
            const int result = original(from, to);
            const int error = errno;
            if (result == 0) {
                ++post_commits;
                if (lstat(to, &proof) == 0) post_receipt("first_commit_succeeded", 0, &proof);
            }
            errno = error;
            return result;
        }
        return original(from, to); /* Including cleanup after the one failure. */
    }
#endif
    if (refuse("rename", to)) return -1;
    return original(from, to);
}

INTERPOSE(rename)

#ifdef __APPLE__
int FAULT(renameat)(int from_fd, const char* from, int to_fd, const char* to) {
    if (refuse("renameat", to)) return -1;
    return renameat(from_fd, from, to_fd, to);
}
int FAULT(renamex_np)(const char* from, const char* to, unsigned int flags) {
    if (refuse("renamex_np", to)) return -1;
    return renamex_np(from, to, flags);
}
int FAULT(renameatx_np)(int from_fd, const char* from, int to_fd, const char* to,
                       unsigned int flags) {
    if (refuse("renameatx_np", to)) return -1;
    return renameatx_np(from_fd, from, to_fd, to, flags);
}
INTERPOSE(renameat)
INTERPOSE(renamex_np)
INTERPOSE(renameatx_np)
#endif
