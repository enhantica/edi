#include <fcntl.h>
#include <stdlib.h>
#include <unistd.h>

__attribute__((constructor)) static void loaded(void) {
    const char* path = getenv("OUTPUT_PROBE_LOADED");
    if (!path) return;
    int fd = open(path, O_CREAT | O_WRONLY | O_TRUNC, 0600);
    if (fd >= 0) {
        write(fd, "loaded\n", 7);
        close(fd);
    }
}
