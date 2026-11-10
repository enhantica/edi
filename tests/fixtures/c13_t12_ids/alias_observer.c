/*  create-new witness: supply a real hard-link alias at the entity write boundary.
 * The alias is made by the filesystem, not by a product name classifier.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static void inject(const char* path, int writing) {
    static int entered;
    const char* marker = getenv("C13_T12_ALIAS_MARKER");
    const char suffix[] = "/experiments/second.edi";
    if (!writing || entered || !marker || !path) return;
    const size_t size = strlen(path), tail = strlen(suffix);
    if (size < tail || strcmp(path + size - tail, suffix)) return;
    char source[4096];
    if (size + 16 >= sizeof(source)) return;
    entered = 1;
    memcpy(source, path, size - tail);
    strcpy(source + size - tail, "/experiments/experiment.edi");
    if (link(source, path) == 0) {
        struct stat first, second;
        if (stat(source, &first) == 0 && stat(path, &second) == 0 &&
            first.st_dev == second.st_dev && first.st_ino == second.st_ino) {
            FILE* (*real_fopen)(const char*, const char*) = dlsym(RTLD_NEXT, "fopen");
            FILE* out = real_fopen(marker, "w");
            if (out) {
                fputs("platform-equivalent hard-link obtained\n", out);
                fclose(out);
            }
        }
    }
    entered = 0;
}

int open(const char* path, int flags, ...) {
    int (*real_open)(const char*, int, ...) = dlsym(RTLD_NEXT, "open");
    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list args;
        va_start(args, flags);
        mode = va_arg(args, int);
        va_end(args);
    }
    inject(path, flags & (O_WRONLY | O_RDWR));
    return real_open(path, flags, mode);
}
int open64(const char* path, int flags, ...) {
    int (*real_open)(const char*, int, ...) = dlsym(RTLD_NEXT, "open64");
    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list args;
        va_start(args, flags);
        mode = va_arg(args, int);
        va_end(args);
    }
    inject(path, flags & (O_WRONLY | O_RDWR));
    return real_open(path, flags, mode);
}
FILE* fopen(const char* path, const char* mode) {
    FILE* (*real_fopen)(const char*, const char*) = dlsym(RTLD_NEXT, "fopen");
    inject(path, strchr(mode, 'w') != NULL || strchr(mode, 'a') != NULL);
    return real_fopen(path, mode);
}
FILE* fopen64(const char* path, const char* mode) {
    FILE* (*real_fopen)(const char*, const char*) = dlsym(RTLD_NEXT, "fopen64");
    inject(path, strchr(mode, 'w') != NULL || strchr(mode, 'a') != NULL);
    return real_fopen(path, mode);
}
