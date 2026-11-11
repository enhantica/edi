// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QString>
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
#include <sys/stat.h>
namespace edi_app::assistant_files {
struct Fd {
    int n = -1;
    Fd() = default;
    explicit Fd(int);
    ~Fd();
    Fd(Fd&&) noexcept;
    Fd& operator=(Fd&&) noexcept;
    Fd(const Fd&) = delete;
};
// The same file with the same bytes as far as its status shows: device, inode, type, size and modification time.
// Not the change time or the permissions, which move with metadata alone: macOS writes extended attributes (the
// last-used date after a file dialog) to files it opens. Content is proven apart, by its digest.
bool same_file_bytes(const struct stat& a, const struct stat& b) noexcept;
struct Identity {
    struct stat value{};
    explicit Identity(int);
    bool object(int) const;
    bool unchanged(int) const;
};
Fd physical_directory(const QString&);
Fd directory(const QString&);
Fd below(int, const QString&, bool dir = false);
// Same original no-replace/exchange operation; returns the actual syscall
// result. Callers latch namespace change before any later verification.
int atomic_publish(int stageParent, const char* stage, int parent, const char* leaf, bool exchange) noexcept;
}
#endif
