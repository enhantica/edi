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
#include <limits.h>
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
/* Root-elected opt-in for the FIRST native whole-tree Save transaction.
 * Observe root -> previous, staging -> root success, then refuse one next
 * root -> previous move. Default first-file-failure behavior is unchanged. */
#ifdef __linux__
static int post_commits;
static int post_failed;
static int post_moved;
static struct stat post_committed;
static int post_mode(void) {
    const char* mode = getenv("TEMPORARY_FAILURE_AFTER_FIRST");
    return mode && strcmp(mode, "1") == 0;
}
static int post_owned_directory(const char* name, struct stat* proof) {
    return name && lstat(name, proof) == 0 && S_ISDIR(proof->st_mode) && proof->st_uid == geteuid();
}
static int post_armed(void) {
    const char* armed = getenv("TEMPORARY_FAILURE_ARMED");
    struct stat proof;
    return armed && lstat(armed, &proof) == 0 && S_ISREG(proof.st_mode) && proof.st_uid == geteuid();
}
static int post_absent(const char* name) {
    struct stat proof;
    return lstat(name, &proof) != 0 && errno == ENOENT;
}
static void post_receipt(const char* phase, const char* operation, int error, const struct stat* target) {
    const char* name = getenv("TEMPORARY_FAILURE_RECEIPT");
    if (!name) return;
    const int file = open(name, O_CREAT | O_WRONLY | O_APPEND | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (file < 0) return;
    char text[512];
    const int size = snprintf(text, sizeof text,
        "{\"phase\":\"%s\",\"operation\":\"%s\",\"successful_commits\":%d,\"pid\":%ld,\"error\":%d,\"device\":%ju,\"inode\":%ju}\n",
        phase, operation, post_commits, (long)getpid(), error, (uintmax_t)target->st_dev, (uintmax_t)target->st_ino);
    if (size > 0 && size < (int)sizeof text) (void)write(file, text, (size_t)size);
    close(file);
}
#endif

int FAULT(rename)(const char* from, const char* to) {
    int (*original)(const char*, const char*) = REAL(rename);
#ifdef __linux__
    if (post_mode()) {
        const char* root = getenv("TEMPORARY_FAILURE_TARGET");
        char previous[PATH_MAX], staging[PATH_MAX];
        const int previous_size = root ? snprintf(previous, sizeof previous, "%s.edi-save-previous", root) : -1;
        const int staging_size = root ? snprintf(staging, sizeof staging, "%s.edi-save-staging", root) : -1;
        if (!post_failed && root && root[0] == '/' && post_armed() &&
            previous_size > 0 && previous_size < (int)sizeof previous &&
            staging_size > 0 && staging_size < (int)sizeof staging) {
            struct stat proof;
            if (strcmp(from, root) == 0 && strcmp(to, previous) == 0 &&
                post_owned_directory(root, &proof) && post_absent(previous)) {
                if (post_commits == 1 && proof.st_dev == post_committed.st_dev && proof.st_ino == post_committed.st_ino) {
                    post_failed = 1;
                    post_receipt("second_transaction_refused", "root_to_previous", EACCES, &proof);
                    errno = EACCES;
                    return -1;
                }
                const int result = original(from, to);
                const int error = errno;
                if (result == 0 && post_commits == 0) {
                    post_moved = 1;
                    post_receipt("first_tree_moved_aside", "root_to_previous", 0, &proof);
                }
                errno = error;
                return result;
            }
            if (post_moved && post_commits == 0 && strcmp(from, staging) == 0 && strcmp(to, root) == 0 &&
                post_owned_directory(staging, &proof) && post_absent(root)) {
                const int result = original(from, to);
                const int error = errno;
                if (result == 0 && post_owned_directory(root, &post_committed)) {
                    post_moved = 0;
                    post_commits = 1;
                    post_receipt("first_commit_succeeded", "staging_to_root", 0, &post_committed);
                }
                errno = error;
                return result;
            }
        }
        return original(from, to); /* Unrelated operations, rollback, cleanup and all later calls. */
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
