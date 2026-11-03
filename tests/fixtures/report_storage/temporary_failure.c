#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
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
int FAULT(rename)(const char* from, const char* to) {
    int (*original)(const char*, const char*) = REAL(rename);
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
