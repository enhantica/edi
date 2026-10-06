#define _GNU_SOURCE

#include <dlfcn.h>
#include <fcntl.h>
#include <spawn.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>

/* : Darwin's two-level/shared-cache bindings need dyld interpose tuples;
 * exporting libc names plus DYLD_FORCE_FLAT_NAMESPACE missed real scan reads.
 * The same wrappers serve the scan and earlier whole-fit I/O gates. Darwin calls
 * the original SDK symbol from this image (dyld excludes the interposer itself).
 * Contract: apple-oss-distributions/dyld/include/mach-o/dyld-interposing.h. */
#if defined(__APPLE__)
/* dyld's source header is not part of the public macOS SDK. */
#define DYLD_INTERPOSE(replacement_function, original_function) \
    __attribute__((used, section("__DATA,__interpose"))) \
    static const struct { const void *replacement; const void *replacee; } \
        interpose_##original_function = { \
            (const void *)&replacement_function, (const void *)&original_function \
        };
#define OBSERVER_NAME(name) observer_##name
#define ORIGINAL(name) name
/* Darwin's uint16_t mode_t is promoted to int in variadic calls. */
#define OBSERVER_MODE(arguments) ((mode_t)va_arg(arguments, int))
/* stdio.h selects one spelling according to feature macros. Observe both:
 * libc++ clients can use the unlimited-streams $DARWIN_EXTSN entry point.
 * fcntl.h supplies the variadic open/openat prototypes and their SDK aliases. */
extern FILE *observer_libc_fopen(const char *, const char *) __asm("_fopen");
extern FILE *observer_libc_fopen_extsn(const char *, const char *)
    __asm("_fopen$DARWIN_EXTSN");
#else
#define OBSERVER_NAME(name) name
#define ORIGINAL(name) dlsym(RTLD_NEXT, #name)
#define OBSERVER_MODE(arguments) va_arg(arguments, mode_t)
#endif

static int observer_fd = -1;

static int observer_active(void) {
    const char *value = getenv("EDI_C08_NATIVE_OBSERVER_ACTIVE");
    return value != NULL && strcmp(value, "1") == 0;
}

static void record_event(const char *operation, const char *path) {
    if (!observer_active() || observer_fd < 0) {
        return;
    }
    char line[4096];
    int length = snprintf(line, sizeof(line), "%s\t%s\n", operation, path != NULL ? path : "");
    if (length > 0) {
        if ((size_t)length >= sizeof(line)) {
            const char *failure = "unresolved\tpath exceeds observer record capacity\n";
            (void)write(observer_fd, failure, strlen(failure));
            return;
        }
        (void)write(observer_fd, line, (size_t)length);
    }
}

static void record_file(const char *operation, int directory_fd, const char *path) {
    if (!observer_active() || observer_fd < 0 || path == NULL) return;
    char base[4096], joined[8192], resolved[8192];
    if (path[0] == '/') {
        snprintf(joined, sizeof(joined), "%s", path);
    } else {
        if (directory_fd == AT_FDCWD) {
            if (getcwd(base, sizeof(base)) == NULL) {
                record_event("unresolved", path); return;
            }
        } else {
#if defined(__APPLE__)
            if (fcntl(directory_fd, F_GETPATH, base) < 0) {
                record_event("unresolved", path); return;
            }
#else
            char descriptor[64];
            snprintf(descriptor, sizeof(descriptor), "/proc/self/fd/%d", directory_fd);
            ssize_t size = readlink(descriptor, base, sizeof(base) - 1);
            if (size < 0) { record_event("unresolved", path); return; }
            base[size] = '\0';
#endif
        }
        snprintf(joined, sizeof(joined), "%s/%s", base, path);
    }
    record_event(operation, realpath(joined, resolved) != NULL ? resolved : joined);
}

__attribute__((constructor)) static void initialise_observer(void) {
    const char *path = getenv("EDI_C08_NATIVE_OBSERVER_LOG");
    if (path == NULL) {
        return;
    }
    int (*real_open)(const char *, int, ...) = ORIGINAL(open);
    if (real_open != NULL) {
        observer_fd = real_open(path, O_WRONLY | O_CREAT | O_APPEND, 0600);
    }
}

int OBSERVER_NAME(open)(const char *path, int flags, ...) {
    static int (*real_open)(const char *, int, ...) = NULL;
    if (real_open == NULL) {
        real_open = ORIGINAL(open);
    }
    mode_t mode = 0;
    if ((flags & O_CREAT) != 0) {
        va_list arguments;
        va_start(arguments, flags);
        mode = OBSERVER_MODE(arguments);
        va_end(arguments);
    }
    record_file("open", AT_FDCWD, path);
    return (flags & O_CREAT) != 0 ? real_open(path, flags, mode) : real_open(path, flags);
}

int OBSERVER_NAME(openat)(int directory_fd, const char *path, int flags, ...) {
    static int (*real_openat)(int, const char *, int, ...) = NULL;
    if (real_openat == NULL) {
        real_openat = ORIGINAL(openat);
    }
    mode_t mode = 0;
    if ((flags & O_CREAT) != 0) {
        va_list arguments;
        va_start(arguments, flags);
        mode = OBSERVER_MODE(arguments);
        va_end(arguments);
    }
    record_file("openat", directory_fd, path);
    return (flags & O_CREAT) != 0 ? real_openat(directory_fd, path, flags, mode)
                                  : real_openat(directory_fd, path, flags);
}

#if defined(__linux__)
int open64(const char *path, int flags, ...) {
    static int (*real_open64)(const char *, int, ...) = NULL;
    if (real_open64 == NULL) {
        real_open64 = dlsym(RTLD_NEXT, "open64");
    }
    mode_t mode = 0;
    if ((flags & O_CREAT) != 0) {
        va_list arguments;
        va_start(arguments, flags);
        mode = va_arg(arguments, mode_t);
        va_end(arguments);
    }
    record_file("open64", AT_FDCWD, path);
    return (flags & O_CREAT) != 0 ? real_open64(path, flags, mode) : real_open64(path, flags);
}

int openat64(int directory_fd, const char *path, int flags, ...) {
    static int (*real_openat64)(int, const char *, int, ...) = NULL;
    if (real_openat64 == NULL) {
        real_openat64 = dlsym(RTLD_NEXT, "openat64");
    }
    mode_t mode = 0;
    if ((flags & O_CREAT) != 0) {
        va_list arguments;
        va_start(arguments, flags);
        mode = va_arg(arguments, mode_t);
        va_end(arguments);
    }
    record_file("openat64", directory_fd, path);
    return (flags & O_CREAT) != 0 ? real_openat64(directory_fd, path, flags, mode)
                                  : real_openat64(directory_fd, path, flags);
}
#endif

FILE *OBSERVER_NAME(fopen)(const char *path, const char *mode) {
    static FILE *(*real_fopen)(const char *, const char *) = NULL;
    if (real_fopen == NULL) {
#if defined(__APPLE__)
        real_fopen = observer_libc_fopen;
#else
        real_fopen = ORIGINAL(fopen);
#endif
    }
    record_file("fopen", AT_FDCWD, path);
    return real_fopen(path, mode);
}

#if defined(__APPLE__)
static FILE *observer_fopen_extsn(const char *path, const char *mode) {
    record_file("fopen", AT_FDCWD, path);
    return observer_libc_fopen_extsn(path, mode);
}
#endif

FILE *OBSERVER_NAME(freopen)(const char *path, const char *mode, FILE *stream) {
    static FILE *(*real_freopen)(const char *, const char *, FILE *) = NULL;
    if (real_freopen == NULL) {
        real_freopen = ORIGINAL(freopen);
    }
    record_file("freopen", AT_FDCWD, path);
    return real_freopen(path, mode, stream);
}

int OBSERVER_NAME(execve)(const char *path, char *const argv[], char *const envp[]) {
    static int (*real_execve)(const char *, char *const[], char *const[]) = NULL;
    if (real_execve == NULL) {
        real_execve = ORIGINAL(execve);
    }
    record_event("execve", path);
    return real_execve(path, argv, envp);
}

int OBSERVER_NAME(posix_spawn)(pid_t *pid, const char *path, const posix_spawn_file_actions_t *actions,
                const posix_spawnattr_t *attributes, char *const argv[], char *const envp[]) {
    static int (*real_posix_spawn)(pid_t *, const char *, const posix_spawn_file_actions_t *,
                                   const posix_spawnattr_t *, char *const[], char *const[]) = NULL;
    if (real_posix_spawn == NULL) {
        real_posix_spawn = ORIGINAL(posix_spawn);
    }
    record_event("posix_spawn", path);
    return real_posix_spawn(pid, path, actions, attributes, argv, envp);
}

int OBSERVER_NAME(posix_spawnp)(pid_t *pid, const char *path, const posix_spawn_file_actions_t *actions,
                 const posix_spawnattr_t *attributes, char *const argv[], char *const envp[]) {
    static int (*real_posix_spawnp)(pid_t *, const char *, const posix_spawn_file_actions_t *,
                                    const posix_spawnattr_t *, char *const[], char *const[]) = NULL;
    if (real_posix_spawnp == NULL) {
        real_posix_spawnp = ORIGINAL(posix_spawnp);
    }
    record_event("posix_spawnp", path);
    return real_posix_spawnp(pid, path, actions, attributes, argv, envp);
}

int OBSERVER_NAME(system)(const char *command) {
    static int (*real_system)(const char *) = NULL;
    if (real_system == NULL) {
        real_system = ORIGINAL(system);
    }
    record_event("system", command);
    return real_system(command);
}

FILE *OBSERVER_NAME(popen)(const char *command, const char *type) {
    static FILE *(*real_popen)(const char *, const char *) = NULL;
    if (real_popen == NULL) {
        real_popen = ORIGINAL(popen);
    }
    record_event("popen", command);
    return real_popen(command, type);
}

#if defined(__APPLE__)
DYLD_INTERPOSE(observer_open, open)
DYLD_INTERPOSE(observer_openat, openat)
DYLD_INTERPOSE(observer_fopen, observer_libc_fopen)
DYLD_INTERPOSE(observer_fopen_extsn, observer_libc_fopen_extsn)
DYLD_INTERPOSE(observer_freopen, freopen)
DYLD_INTERPOSE(observer_execve, execve)
DYLD_INTERPOSE(observer_posix_spawn, posix_spawn)
DYLD_INTERPOSE(observer_posix_spawnp, posix_spawnp)
DYLD_INTERPOSE(observer_system, system)
DYLD_INTERPOSE(observer_popen, popen)
#endif
