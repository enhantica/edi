#ifdef __APPLE__
#define _DARWIN_C_SOURCE
#endif
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/uio.h>
#include <unistd.h>

int main(int argc, char** argv) {
    if (argc != 4) return 2;
    const char* operation = argv[1];
    int result = -1;
    errno = 0;
    if (!strcmp(operation, "rename")) {
        result = rename(argv[2], argv[3]);
#ifdef __APPLE__
    } else if (!strcmp(operation, "renameat")) {
        result = renameat(AT_FDCWD, argv[2], AT_FDCWD, argv[3]);
    } else if (!strcmp(operation, "renamex_np")) {
        result = renamex_np(argv[2], argv[3], 0);
    } else if (!strcmp(operation, "renameatx_np")) {
        result = renameatx_np(AT_FDCWD, argv[2], AT_FDCWD, argv[3], 0);
#endif
    } else if (!strcmp(operation, "link")) {
        result = link(argv[2], argv[3]);
    } else if (!strcmp(operation, "unlink")) {
        result = unlink(argv[2]);
    } else if (!strcmp(operation, "remove")) {
        result = remove(argv[2]);
    } else if (!strcmp(operation, "fclose")) {
        FILE* stream = fopen(argv[2], "w");
        if (!stream) return 3;
        fputs("buffered prefix\n", stream);
        result = fclose(stream);
    } else {
        int reading = !strcmp(operation, "read") || !strcmp(operation, "fread");
        int fd = open(argv[2], reading ? O_RDONLY : O_WRONLY | O_CREAT | O_TRUNC, 0600);
        if (fd < 0) return 3;
        if (!strcmp(operation, "read")) {
            char buffer[64];
            setenv("SCAN_FAULT_ARMED", "1", 1);
            result = (int)read(fd, buffer, sizeof buffer);
        } else if (!strcmp(operation, "fread")) {
            FILE* stream = fdopen(fd, "r");
            char buffer[64];
            if (!stream) return 3;
            setenv("SCAN_FAULT_ARMED", "1", 1);
            size_t count = fread(buffer, 1, sizeof buffer, stream);
            int error = ferror(stream), saved = errno;
            fclose(stream);
            printf("result=%zu errno=%d ferror=%d\n", count, saved, error);
            return 0;
        } else if (!strcmp(operation, "writev")) {
            struct iovec vector = {(void*)"native prefix\n", 14};
            result = (int)writev(fd, &vector, 1);
        } else if (!strcmp(operation, "write")) {
            result = (int)write(fd, "native prefix\n", 14);
        } else if (!strcmp(operation, "close")) {
            if (write(fd, "native prefix\n", 14) < 0) return 3;
            result = close(fd);
            printf("result=%d errno=%d\n", result, errno);
            return 0;
        } else {
            close(fd);
            return 2;
        }
        int saved = errno;
        close(fd);
        errno = saved;
    }
    printf("result=%d errno=%d\n", result, errno);
    return 0;
}
