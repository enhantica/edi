// Observe only the native atomic publication imported by the archive object.
#include <fcntl.h>
#include <limits.h>
#include <unistd.h>

#include <cerrno>
#include <cstdarg>
#if defined(__linux__)
#include <sys/syscall.h>
#endif
namespace {
QString nativeObservationFailure;
QString nativeAt(int descriptor, const char* name) {
    if (QDir::isAbsolutePath(QString::fromLocal8Bit(name))) return QString::fromLocal8Bit(name);
    if (descriptor == AT_FDCWD) return QDir::current().filePath(QString::fromLocal8Bit(name));
    char parent[PATH_MAX];
#if defined(__linux__)
    const auto path = QByteArray("/proc/self/fd/") + QByteArray::number(descriptor);
    const auto size = ::readlink(path.constData(), parent, sizeof(parent));
    if (size < 0 || size == sizeof(parent))
        throw std::runtime_error(
            "The native publication parent must resolve from its actual descriptor");
    return QDir(QString::fromLocal8Bit(parent, size)).filePath(QString::fromLocal8Bit(name));
#elif defined(__APPLE__)
    if (::fcntl(descriptor, F_GETPATH, parent) < 0)
        throw std::runtime_error("The native publication parent descriptor must resolve");
    return QDir(QString::fromLocal8Bit(parent)).filePath(QString::fromLocal8Bit(name));
#endif
}
}  // namespace
#if defined(__linux__)
extern "C" long publication_syscall(long number, ...) {
    if (number != SYS_renameat2) {
        nativeObservationFailure = "The archive object requested an unobserved native syscall";
        errno = ENOSYS;
        return -1;
    }
    va_list arguments;
    va_start(arguments, number);
    const int from = va_arg(arguments, int);
    const char* source = va_arg(arguments, const char*);
    const int to = va_arg(arguments, int);
    const char* target = va_arg(arguments, const char*);
    const unsigned flags = va_arg(arguments, unsigned);
    va_end(arguments);
    const int before = errno;
    QString destination;
    try {
        destination = nativeAt(to, target);
        ownerCoreAttempt();
        sealBeforeRename(nativeAt(from, source), destination);
    } catch (const std::exception& error) {
        nativeObservationFailure = QString::fromUtf8(error.what());
    }
    errno = before;
    const long result = ::syscall(number, from, source, to, target, flags);
    const int after = errno;
    if (result == 0) sealCommitted(destination);
    errno = after;
    return result;
}
#elif defined(__APPLE__)
extern "C" int publication_renameatx(int from, const char* source, int to, const char* target,
                                     unsigned flags) {
    const int before = errno;
    QString destination;
    try {
        destination = nativeAt(to, target);
        ownerCoreAttempt();
        sealBeforeRename(nativeAt(from, source), destination);
    } catch (const std::exception& error) {
        nativeObservationFailure = QString::fromUtf8(error.what());
    }
    errno = before;
    const int result = ::renameatx_np(from, source, to, target, flags);
    const int after = errno;
    if (result == 0) sealCommitted(destination);
    errno = after;
    return result;
}
#endif
