#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
int rename(const char* from, const char* to) {
    int (*original)(const char*, const char*) = dlsym(RTLD_NEXT, "rename");
    const char* target = getenv("TEMPORARY_FAILURE_TARGET");
    static int fired = 0;
    if (!fired && target && !strcmp(target, to)) {
        fired = 1;
        const char* receipt = getenv("TEMPORARY_FAILURE_RECEIPT");
        int file = receipt ? open(receipt, O_CREAT | O_WRONLY | O_APPEND, 0600) : -1;
        if (file >= 0) {
            write(file, "rename-after-write\n", 19);
            close(file);
        }
        errno = EACCES;
        return -1;
    }
    return original(from, to);
}
