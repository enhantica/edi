// SPDX-License-Identifier: BSD-3-Clause
#include "untitled_operation.hpp"

#include "project_view_model.hpp"

#include <QDir>
#include <QFile>

#include <utility>

#if defined(_WIN32)
#include "../../core/src/windows_sdk.hpp"
#else
#include <sys/stat.h>
#endif

namespace edi_app {

UntitledOperation::UntitledOperation(std::uint64_t id, ProjectViewModel* owner, std::uint64_t replacement,
                                     Origin origin, std::function<void()> continuation)
    : id_(id), owner_(owner), replacement_(replacement), origin_(origin), continuation_(std::move(continuation)) {}

bool UntitledOperation::advance(State next) {
    if (settled() || next >= State::Saved) return false;
    state_ = next;
    return true;
}

bool UntitledOperation::settle(State terminal) {
    if (settled() || terminal < State::Saved) return false;
    state_ = terminal;
    // Only a saved operation runs what waited for it.
    if (terminal != State::Saved) continuation_ = nullptr;
    return true;
}

std::optional<UntitledOperation::FileIdentity> UntitledOperation::identity(const QString& path) {
#if defined(_WIN32)
    const QString native = QDir::toNativeSeparators(path);
    const HANDLE handle = ::CreateFileW(reinterpret_cast<const wchar_t*>(native.utf16()), 0,
                                        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING,
                                        FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr);
    if (handle == INVALID_HANDLE_VALUE) return std::nullopt;
    BY_HANDLE_FILE_INFORMATION info{};
    const bool read = ::GetFileInformationByHandle(handle, &info) != 0;
    ::CloseHandle(handle);
    if (!read) return std::nullopt;
    return FileIdentity{static_cast<std::uint64_t>(info.dwVolumeSerialNumber),
                        (static_cast<std::uint64_t>(info.nFileIndexHigh) << 32) |
                            static_cast<std::uint64_t>(info.nFileIndexLow)};
#else
    struct stat status {};
    if (::lstat(QFile::encodeName(path).constData(), &status) != 0) return std::nullopt;
    return FileIdentity{static_cast<std::uint64_t>(status.st_dev), static_cast<std::uint64_t>(status.st_ino)};
#endif
}

std::function<void()> UntitledOperation::takeContinuation() { return std::exchange(continuation_, nullptr); }

QString UntitledOperation::name(State state) {
    switch (state) {
        case State::Asking: return QStringLiteral("asking");
        case State::Replanning: return QStringLiteral("replanning");
        case State::Writing: return QStringLiteral("writing");
        case State::Saved: return QStringLiteral("saved");
        case State::Refused: return QStringLiteral("refused");
        case State::Rejected: return QStringLiteral("rejected");
        case State::Superseded: return QStringLiteral("superseded");
    }
    return {};
}

QString UntitledOperation::name(Origin origin) {
    switch (origin) {
        case Origin::ManualCreate: return QStringLiteral("manual-create");
        case Origin::Save: return QStringLiteral("save");
        case Origin::GuardSave: return QStringLiteral("guard-save");
        case Origin::AssistantCreate: return QStringLiteral("assistant-create");
    }
    return {};
}

}  // namespace edi_app
