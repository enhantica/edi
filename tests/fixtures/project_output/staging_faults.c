#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include "fault_interpose.h"

int FAULT(link)(const char* from, const char* to) {
    static int injected;
    int (*real_link)(const char*, const char*) = REAL(link);
    int (*real_unlink)(const char*) = REAL(unlink);
    const char* selected = getenv("STAGING_LINK_SOURCE");
    if (!injected && selected && strcmp(from, selected) == 0) {
        injected = 1;
        const char* sentinel = getenv("STAGING_LINK_SENTINEL");
        const char* alias = getenv("STAGING_LINK_ALIAS");
        int planted = alias && strcmp(alias, "symbolic") == 0 ? symlink(sentinel, to)
                                                              : real_link(sentinel, to);
        char* parent = strdup(to);
        char* slash = strrchr(parent, '/');
        int locked = -1;
        if (slash) {
            *slash = 0;
            locked = chmod(parent, 0555);
        }
        free(parent);
        int denied = planted == 0 && locked == 0 && real_unlink(to) < 0 &&
                     (errno == EACCES || errno == EPERM);
        int receipt = open(getenv("STAGING_LINK_RECEIPT"), O_WRONLY | O_CREAT | O_APPEND, 0600);
        if (receipt >= 0) {
            write(receipt, "link-fallback\n", 14);
            if (denied) write(receipt, "removal-denied\n", 15);
            close(receipt);
        }
        errno = EXDEV;
        return -1;
    }
    return real_link(from, to);
}

INTERPOSE(link)
