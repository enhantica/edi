// SPDX-License-Identifier: BSD-3-Clause
// Process-local loader substitution and a separate network refusal backstop.
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <netdb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>

int recorded_guard_ready(void) { return 6193; }
static void record(const char *name, const char *environment) {
    const char *path = getenv(environment);
    FILE *stream = path ? fopen(path, "a") : NULL;
    if (stream) { fprintf(stream, "%s\n", name); fclose(stream); }
}
void *dlopen(const char *name, int flags) {
    void *(*actual)(const char *, int) = dlsym(RTLD_NEXT, "dlopen");
    if (name && strstr(name, "libcurl")) {
        record(name, "EDI_REFERENCE_LOADER_TRACE");
        if (getenv("EDI_REFERENCE_MISSING_CURL")) return NULL;
        const char *replacement = getenv("EDI_REFERENCE_CURL_LIBRARY");
        return replacement ? actual(replacement, flags) : NULL;
    }
    return actual(name, flags);
}
int socket(int domain, int type, int protocol) {
    if (domain == AF_INET || domain == AF_INET6) {
        record("socket", "EDI_REFERENCE_NETWORK_TRACE");
        errno = EPERM;
        return -1;
    }
    int (*actual)(int, int, int) = dlsym(RTLD_NEXT, "socket");
    return actual(domain, type, protocol);
}
int connect(int descriptor, const struct sockaddr *address, socklen_t length) {
    if (address && (address->sa_family == AF_INET || address->sa_family == AF_INET6)) {
        record("connect", "EDI_REFERENCE_NETWORK_TRACE");
        errno = EPERM;
        return -1;
    }
    int (*actual)(int, const struct sockaddr *, socklen_t) = dlsym(RTLD_NEXT, "connect");
    return actual(descriptor, address, length);
}
int getaddrinfo(const char *name, const char *service, const struct addrinfo *hints,
                struct addrinfo **result) {
    (void)name; (void)service; (void)hints; (void)result;
    record("getaddrinfo", "EDI_REFERENCE_NETWORK_TRACE");
    return EAI_FAIL;
}
