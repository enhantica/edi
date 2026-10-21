// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_file_primitives.hpp"
#include "assistant_result.hpp"
#include <QDir>
#include <QFileInfo>
#include <QStringView>
#include <stdexcept>
#include <utility>
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
#include <fcntl.h>
#include <unistd.h>
#if defined(__linux__)
#include <sys/syscall.h>
#include <linux/fs.h>
#elif defined(__APPLE__)
#include <stdio.h>
#endif
namespace edi_app::assistant_files {
namespace { [[noreturn]] void refuse() { throw std::runtime_error("Saved assistant result is unavailable, changed, or outside the supported self-contained project limits"); } }
Fd::Fd(int fd) : n(fd) { if (n < 0) refuse(); }
Fd::~Fd() { if (n >= 0) ::close(n); }
Fd::Fd(Fd&& other) noexcept : n(std::exchange(other.n, -1)) {}
Fd& Fd::operator=(Fd&& other) noexcept { if (n >= 0) ::close(n); n = std::exchange(other.n, -1); return *this; }
Identity::Identity(int fd) { if (::fstat(fd, &value)) refuse(); }
bool Identity::object(int fd) const { struct stat now{}; return !::fstat(fd, &now) && value.st_dev == now.st_dev && value.st_ino == now.st_ino && value.st_mode == now.st_mode; }
bool Identity::unchanged(int fd) const {
        struct stat now{};
        if (::fstat(fd, &now)) return false;
#if defined(__APPLE__)
        const bool times = value.st_mtimespec.tv_sec == now.st_mtimespec.tv_sec && value.st_mtimespec.tv_nsec == now.st_mtimespec.tv_nsec &&
            value.st_ctimespec.tv_sec == now.st_ctimespec.tv_sec && value.st_ctimespec.tv_nsec == now.st_ctimespec.tv_nsec;
#else
        const bool times = value.st_mtim.tv_sec == now.st_mtim.tv_sec && value.st_mtim.tv_nsec == now.st_mtim.tv_nsec &&
            value.st_ctim.tv_sec == now.st_ctim.tv_sec && value.st_ctim.tv_nsec == now.st_ctim.tv_nsec;
#endif
        return object(fd) && value.st_size == now.st_size && times;
    }
Fd physical_directory(const QString& path) {
    // Only already-captured physical paths enter here. Reject later ancestor
    // links instead of resolving unknown replacement path text.
    if (!QDir::isAbsolutePath(path)) refuse();
    Fd fd(::open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC));
    const auto view=QStringView(path);
    for(qsizetype start=0;start<view.size();) {
        while(start<view.size() && view[start]==u'/')++start;
        if(start==view.size())break;
        auto end=view.indexOf(u'/',start);if(end<0)end=view.size();
        const auto part=view.mid(start,end-start);start=end;
        if(part==u"." || part==u".." || part.contains(QChar(0)))refuse();
        fd=Fd(::openat(fd.n,part.toUtf8().constData(),O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC));
    }
    return fd;
}
Fd directory(const QString& path) {
    // Ordinary callers keep system-alias canonicalization (notably macOS
    // /var and /tmp). The same no-follow reader owns physical descent.
    if (!QDir::isAbsolutePath(path)) refuse();
    const auto physical = QFileInfo(path).canonicalFilePath();
    if (physical.isEmpty()) refuse();
    auto fd=physical_directory(physical);
    Fd original(::open(path.toUtf8().constData(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
    if (!Identity(fd.n).object(original.n)) refuse();
    return fd;
}
Fd below(int parent, const QString& name, bool dir) {
    const auto parts = name.split('/');
    Fd fd(::dup(parent));
    for (qsizetype i = 0; i < parts.size(); ++i) {
        validate_assistant_result_leaf(parts[i]);
        const bool directoryPart = i + 1 != parts.size() || dir;
        if (!directoryPart) {
            struct stat admitted{};
            if (::fstatat(fd.n, parts[i].toUtf8().constData(), &admitted, AT_SYMLINK_NOFOLLOW) || !S_ISREG(admitted.st_mode)) refuse();
        }
        fd = Fd(::openat(fd.n, parts[i].toUtf8().constData(), O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC | (directoryPart ? O_DIRECTORY : 0)));
    }
    return fd;
}
int atomic_publish(int sp, const char* sn, int p, const char* leaf, bool exchange) noexcept {
#if defined(__linux__) && defined(SYS_renameat2)
    return static_cast<int>(::syscall(SYS_renameat2,sp,sn,p,leaf,exchange?RENAME_EXCHANGE:RENAME_NOREPLACE));
#elif defined(__APPLE__)
    return ::renameatx_np(sp,sn,p,leaf,exchange?RENAME_SWAP:RENAME_EXCL);
#else
    return -1;
#endif
}
} // namespace edi_app::assistant_files
#endif
