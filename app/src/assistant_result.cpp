// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_result.hpp"
#include "edi/assistant.hpp"
#include "edi/io.hpp"
// Reuse the existing strict parser, preserving member order for duplicate checks below.
#include "../../core/src/assistant_json.hpp"
#include "../../core/src/assistant_project_io.hpp"
#include <QCryptographicHash>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QSaveFile>
#include <QJsonObject>
#include <QStandardPaths>
#include <QUuid>
#include <algorithm>
#include <cmath>
#include <map>
#include <set>
#include <stdexcept>
#include <utility>
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
#include <cerrno>
#include <cstring>
#include <dirent.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#if defined(__linux__)
#include <sys/syscall.h>
#include <linux/fs.h>
#elif defined(__APPLE__)
#include <stdio.h>
#endif
#endif

namespace edi_app {
namespace {
using Bounds = edi::assistant::SelectedFileLimits;
using Limits = edi::assistant::Limits;
[[noreturn]] void refuse() { throw std::runtime_error("Saved assistant result is unavailable, changed, or outside the supported self-contained project limits"); }
void leaf_name(const QString& name) {
    if (name.isEmpty() || name == "." || name == ".." || name.contains('/') || name.contains('\\') || name.contains(QChar(0)) ||
        name.toUtf8().size() > static_cast<qsizetype>(Bounds::name_bytes) || name.endsWith('.') || name.endsWith(' ')) refuse();
}
QString relative_name(const std::string& bytes) {
    if (bytes.empty() || bytes.size() > Bounds::name_bytes) refuse();
    const auto name = QString::fromUtf8(bytes.data(), static_cast<qsizetype>(bytes.size()));
    if (name.toUtf8() != QByteArray(bytes.data(), static_cast<qsizetype>(bytes.size())) || name.startsWith('/')) refuse();
    const auto parts = name.split('/');
    if (parts.size() > static_cast<qsizetype>(Limits::json_depth)) refuse();
    for (const auto& part : parts) leaf_name(part);
    // This first route accepts only the actual fixed native project layout.
    if (name == "project.edi") return name;
    if (parts.size() != 2 || !parts[1].endsWith(".edi") || parts[1].size() <= 4 ||
        !(parts[0] == "structures" || parts[0] == "experiments" ||
          (parts[0] == "analysis" && parts[1] == "analysis.edi") ||
          (parts[0] == "reports" && parts[1] == "report.edi"))) refuse();
    return name;
}
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
struct Fd {
    int n = -1;
    Fd() = default;
    explicit Fd(int fd) : n(fd) { if (n < 0) refuse(); }
    ~Fd() { if (n >= 0) ::close(n); }
    Fd(Fd&& other) noexcept : n(std::exchange(other.n, -1)) {}
    Fd& operator=(Fd&& other) noexcept { if (n >= 0) ::close(n); n = std::exchange(other.n, -1); return *this; }
    Fd(const Fd&) = delete;
};
struct Identity {
    struct stat value{};
    explicit Identity(int fd) { if (::fstat(fd, &value)) refuse(); }
    bool object(int fd) const { struct stat now{}; return !::fstat(fd, &now) && value.st_dev == now.st_dev && value.st_ino == now.st_ino && value.st_mode == now.st_mode; }
    bool unchanged(int fd) const {
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
};
Fd directory(const QString& path) {
    // Open each component, including the selected parent's ancestry, without following links.
    if (!QDir::isAbsolutePath(path)) refuse();
    // macOS /var and /tmp are system aliases. Pin their physical directory, then
    // verify the caller's final object too; never follow a runtime-owned child.
    const auto physical = QFileInfo(path).canonicalFilePath();
    if (physical.isEmpty()) refuse();
    Fd fd(::open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC));
    for (const auto& part : physical.split('/', Qt::SkipEmptyParts)) {
        fd = Fd(::openat(fd.n, part.toUtf8().constData(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
    }
    Fd original(::open(path.toUtf8().constData(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
    if (!Identity(fd.n).object(original.n)) refuse();
    return fd;
}
Fd below(int parent, const QString& name, bool dir = false) {
    const auto parts = name.split('/');
    Fd fd(::dup(parent));
    for (qsizetype i = 0; i < parts.size(); ++i) {
        leaf_name(parts[i]);
        const bool directoryPart = i + 1 != parts.size() || dir;
        if (!directoryPart) {
            struct stat admitted{};
            if (::fstatat(fd.n, parts[i].toUtf8().constData(), &admitted, AT_SYMLINK_NOFOLLOW) || !S_ISREG(admitted.st_mode)) refuse();
        }
        fd = Fd(::openat(fd.n, parts[i].toUtf8().constData(), O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC | (directoryPart ? O_DIRECTORY : 0)));
    }
    return fd;
}
QByteArray read_file(int fd, quint64 cap) {
    const Identity original(fd);
    if (!S_ISREG(original.value.st_mode) || original.value.st_nlink != 1 || original.value.st_size < 0 || static_cast<quint64>(original.value.st_size) > cap) refuse();
    QByteArray bytes;
    bytes.reserve(static_cast<qsizetype>(original.value.st_size));
    char chunk[65536];
    for (;;) {
        const auto count = ::read(fd, chunk, sizeof chunk);
        if (count < 0) { if (errno == EINTR) continue; refuse(); }
        if (!count) break;
        if (static_cast<quint64>(count) > cap - static_cast<quint64>(bytes.size())) refuse();
        bytes.append(chunk, static_cast<qsizetype>(count));
    }
    if (bytes.size() != original.value.st_size || !original.unchanged(fd)) refuse();
    return bytes;
}
struct Entry { QString path; quint64 bytes; QByteArray hash; };
void enumerate(int parent, const QString& prefix, std::set<QString>& files, std::set<QString>& aliases, std::size_t& entries, std::size_t depth = 0) {
    if (depth > Limits::json_depth) refuse();
    Fd owned(::openat(parent, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
    DIR* raw = ::fdopendir(owned.n);
    if (!raw) refuse();
    owned.n = -1;
    std::unique_ptr<DIR, decltype(&::closedir)> stream(raw, ::closedir);
    for (;;) {
        errno = 0;
        auto* entry = ::readdir(raw);
        if (!entry) { if (errno) refuse(); break; }
        const QByteArray rawName(entry->d_name);
        if (rawName == "." || rawName == "..") continue;
        if (++entries > Bounds::files) refuse(); // Includes directories and empty directories.
        const auto name = QString::fromUtf8(rawName);
        if (name.toUtf8() != rawName) refuse();
        leaf_name(name);
        const auto path = prefix.isEmpty() ? name : prefix + '/' + name;
        if (path.toUtf8().size() > static_cast<qsizetype>(Bounds::name_bytes) || !aliases.insert(path.normalized(QString::NormalizationForm_C).toCaseFolded()).second) refuse();
        struct stat st{};
        if (::fstatat(parent, rawName.constData(), &st, AT_SYMLINK_NOFOLLOW)) refuse();
        if (S_ISDIR(st.st_mode)) {
            if (!prefix.isEmpty() || !(name == "structures" || name == "experiments" || name == "analysis" || name == "reports")) refuse();
            auto child = below(parent, name, true);
            enumerate(child.n, path, files, aliases, entries, depth + 1);
        } else if (S_ISREG(st.st_mode)) { relative_name(path.toStdString()); files.insert(path); }
        else refuse();
    }
}
std::set<QString> closure(int fd) {
    std::set<QString> files, aliases;
    std::size_t entries = 0;
    enumerate(fd, {}, files, aliases, entries);
    if (!files.count("project.edi")) refuse();
    return files;
}
void keys(const edi::json::Object& object, std::initializer_list<const char*> allowed) {
    if (object.size() != allowed.size()) refuse();
    for (const auto* key : allowed) if (std::count_if(object.begin(), object.end(), [key](const auto& member) { return member.first == key; }) != 1) refuse();
}
std::vector<Entry> manifest(const QByteArray& bytes, const QString& intent) {
    const auto parsed = edi::assistant::detail::parse(bytes.toStdString(), Limits::context_bytes);
    const auto& root = parsed.object("result receipt"); keys(root, {"schema", "intent", "project", "files"});
    if (parsed.at("schema").string("schema") != "edi.assistant.result/1" || parsed.at("intent").string("intent") != intent.toStdString() ||
        parsed.at("project").string("project") != "project") refuse();
    const auto& items = parsed.at("files").array("files");
    if (items.empty() || items.size() > Bounds::files) refuse();
    std::vector<Entry> result; std::set<QString> names; quint64 total = 0;
    for (const auto& item : items) {
        keys(item.object("file"), {"path", "bytes", "sha256"});
        const auto name = relative_name(item.at("path").string("path"));
        if (!names.insert(name.normalized(QString::NormalizationForm_C).toCaseFolded()).second) refuse();
        const auto size = item.at("bytes").number("bytes");
        if (!std::isfinite(size) || size < 0 || std::floor(size) != size || size > Bounds::file_bytes || size > Bounds::collection_bytes - total) refuse();
        const auto& hash = item.at("sha256").string("sha256");
        if (hash.size() != 64 || !std::all_of(hash.begin(), hash.end(), [](char c) { return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'); })) refuse();
        total += static_cast<quint64>(size);
        result.push_back({name, static_cast<quint64>(size), QByteArray::fromStdString(hash)});
    }
    return result;
}
void write_staged(int root, const QString& path, const std::string& bytes) {
    const auto parts = path.split('/');
    Fd directoryFd(::dup(root));
    if (parts.size() == 2) {
        const auto name = parts[0].toUtf8();
        if (::mkdirat(root, name.constData(), 0700) && errno != EEXIST) refuse();
        directoryFd = below(root, parts[0], true);
    }
    Fd file(::openat(directoryFd.n, parts.back().toUtf8().constData(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600));
    std::size_t written = 0;
    while (written < bytes.size()) {
        const auto count = ::write(file.n, bytes.data() + written, bytes.size() - written);
        if (count < 0) { if (errno == EINTR) continue; refuse(); }
        if (!count) refuse();
        written += static_cast<std::size_t>(count);
    }
}
QJsonArray receipt_files(const std::vector<Entry>& entries) {
    QJsonArray result;
    for (const auto& entry : entries) result.append(QJsonObject{{"path", entry.path}, {"bytes", static_cast<qint64>(entry.bytes)}, {"sha256", QString::fromLatin1(entry.hash)}});
    return result;
}
void verify(int fd, const std::vector<Entry>& entries, int copy = -1) {
    const auto before = closure(fd);
    std::set<QString> expected;
    for (const auto& entry : entries) {
        expected.insert(entry.path);
        auto source = below(fd, entry.path);
        const auto bytes = read_file(source.n, Bounds::file_bytes);
        if (static_cast<quint64>(bytes.size()) != entry.bytes || QCryptographicHash::hash(bytes, QCryptographicHash::Sha256).toHex() != entry.hash) refuse();
        if (copy >= 0) write_staged(copy, entry.path, bytes.toStdString());
    }
    if (before != expected || closure(fd) != expected) refuse();
}
edi::Project load_owned_project(int fd, const QString& ownedPath, const std::vector<Entry>& entries) {
    const Identity pinned(fd);
    verify(fd, entries);
    QString access;
#if defined(__linux__)
    access = QStringLiteral("/proc/self/fd/%1").arg(fd);
#elif defined(__APPLE__)
    // Darwin fdescfs duplicates a descriptor; it does not implement child
    // lookup. Use the actual private host-owned copy's physical directory.
    // This directory is outside the admitted runtime write root, not its source.
    access = QFileInfo(ownedPath).canonicalFilePath();
    if (access.isEmpty()) refuse();
#else
    Q_UNUSED(ownedPath); refuse();
#endif
    // Bond the named copy to the pinned descriptor both before and after the
    // real loader. Directory ancestors may have trusted system aliases; every
    // untrusted copied descendant was no-follow admitted and hash verified.
    auto named = directory(ownedPath);
    if (!pinned.object(named.n)) refuse();
    auto project = edi::detail::load_assistant_project(access.toStdString());
    auto again = directory(ownedPath);
    if (!pinned.object(again.n)) refuse();
    verify(fd, entries);
    return project;
}

#endif
} // namespace
struct AssistantResultDirectory {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    Fd descriptor;
    explicit AssistantResultDirectory(Fd fd) : descriptor(std::move(fd)) {}
#endif
};

void check_assistant_result_mode(const edi::Project& project) {
    if (project.sequential_fit.declared() || edi::is_scan_fitting_mode(project.fitting_mode) || !project.report_files.empty())
        throw std::runtime_error("This result requires external scan/report files; automatic opening currently supports self-contained native projects only");
}
std::shared_ptr<ImmutableAssistantResult> capture_assistant_result(const QString& workspace, const QString& intent) {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    leaf_name(intent);
    auto root = directory(workspace);
    const auto receiptName = ".edi-result/" + intent + "/result.json";
    auto receipt = below(root.n, receiptName);
    const Identity receiptIdentity(receipt.n);
    const auto original = read_file(receipt.n, Limits::context_bytes);
    const auto entries = manifest(original, intent);
    auto project = below(root.n, ".edi-result/" + intent + "/project", true);
    const Identity projectIdentity(project.n);
    auto result = std::make_shared<ImmutableAssistantResult>();
    const auto cache = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation) + "/assistant/results";
    if (!QDir().mkpath(cache)) refuse();
    result->lease = std::make_shared<QTemporaryDir>(cache + "/result-XXXXXX");
    if (!result->lease->isValid()) refuse();
    result->lease->setAutoRemove(false);
    result->recovery_directory = result->lease->path();
    const auto physicalAgentRoot = QFileInfo(QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation) + "/assistant/agent").canonicalFilePath();
    const auto physicalWorkspace = QFileInfo(workspace).canonicalFilePath();
    const auto physicalCopy = QFileInfo(result->recovery_directory).canonicalFilePath();
    if (physicalWorkspace.isEmpty() || physicalCopy.isEmpty() || physicalCopy == physicalWorkspace || physicalCopy.startsWith(physicalWorkspace + '/') ||
        (!physicalAgentRoot.isEmpty() && (physicalCopy == physicalAgentRoot || physicalCopy.startsWith(physicalAgentRoot + '/')))) refuse();
    auto copy = std::make_shared<AssistantResultDirectory>(directory(result->recovery_directory));
    result->handle = copy;
    result->directory = physicalCopy;
    verify(project.n, entries, copy->descriptor.n);
    // Reopen source paths as well: a rename/replacement cannot substitute a different receipt/tree.
    auto receiptAgain = below(root.n, receiptName);
    auto projectAgain = below(root.n, ".edi-result/" + intent + "/project", true);
    if (!receiptIdentity.unchanged(receipt.n) || !receiptIdentity.unchanged(receiptAgain.n) || !projectIdentity.object(projectAgain.n)) refuse();
    verify(copy->descriptor.n, entries);
    verify(project.n, entries); // Later companions cannot conceal a changed earlier source file.
    if (!receiptIdentity.unchanged(receipt.n)) refuse();
    auto loaded = load_owned_project(copy->descriptor.n, result->directory, entries);
    check_assistant_result_mode(loaded);
    result->files = receipt_files(entries); result->receipt = original; result->intent = intent;
    return result;
#else
    Q_UNUSED(workspace); Q_UNUSED(intent); refuse();
#endif
}

edi::Project load_captured_assistant_result(const ImmutableAssistantResult& result) {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    if (!result.handle || !result.lease || !result.lease->isValid()) refuse();
    const auto entries = manifest(result.receipt, result.intent);
    auto loaded = load_owned_project(result.handle->descriptor.n, result.directory, entries);
    check_assistant_result_mode(loaded);
    return loaded;
#else
    Q_UNUSED(result); refuse();
#endif
}

struct AssistantResultExport::State {
    QString parent, stage, leaf, destination;
    QJsonArray files;
    bool committed = false;
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    std::vector<Entry> entries;
#endif
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    Fd parentFd, stageFd;
    Identity parentIdentity, stageIdentity;
    static Fd selectedParent(const QString& path) {
        const auto physical = QFileInfo(path).canonicalFilePath();
        if (physical.isEmpty()) refuse();
        return directory(physical);
    }
    State(const QString& parentPath, const QString& leafName)
        : parent(parentPath), stage(".edi-export-" + QUuid::createUuid().toString(QUuid::WithoutBraces)), leaf(leafName),
          destination(QDir(parentPath).filePath(leafName)), parentFd(selectedParent(parentPath)), parentIdentity(parentFd.n),
          stageIdentity(parentFd.n) {
        leaf_name(leaf);
        if (leaf.toCaseFolded() == stage.toCaseFolded()) refuse();
        if (::mkdirat(parentFd.n, stage.toUtf8().constData(), 0700)) refuse();
        stageFd = below(parentFd.n, stage, true); stageIdentity = Identity(stageFd.n);
    }
#endif
};
AssistantResultExport::AssistantResultExport(const ImmutableAssistantResult& source, const QString& parent, const QString& leaf) {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    if (!source.handle) refuse();
    const auto physicalParent = QFileInfo(parent).canonicalFilePath();
    const auto appData = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
    for (const auto& reserved : {appData + "/assistant/agent", appData + "/assistant/results"}) {
        const auto physical = QFileInfo(reserved).canonicalFilePath();
        if (!physical.isEmpty() && (physicalParent == physical || physicalParent.startsWith(physical + '/'))) refuse();
    }
    // First export preserves the exact already-admitted saved native bytes.
    // Session refuses any intervening model edit; no unbounded serializer is invoked.
    const auto entries = manifest(source.receipt, source.intent);
    verify(source.handle->descriptor.n, entries);
    auto state = std::make_unique<State>(parent, leaf);
    try {
        // Pinning both objects prevents a substituted parent path from redirecting writes.
        verify(source.handle->descriptor.n, entries, state->stageFd.n);
        verify(state->stageFd.n, entries);
        auto loaded = load_owned_project(state->stageFd.n, QDir(state->parent).filePath(state->stage), entries);
        check_assistant_result_mode(loaded);
        state->files = receipt_files(entries); state->entries = entries;
    } catch (...) {
        // Deliberately leave the bounded unpublished directory for recovery.
        // There is no portable inode-conditional recursive unlink; a pathname
        // cleanup must never delete a substituted foreign object.
        throw;
    }
    state_ = std::move(state);
#else
    Q_UNUSED(source); Q_UNUSED(parent); Q_UNUSED(leaf); refuse();
#endif
}
AssistantResultExport::~AssistantResultExport() = default; // Descriptor cleanup only; never delete by a mutable path.
void AssistantResultExport::publish(const std::function<bool()>& current) {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    auto& s = *state_;
    // Allocate syscall arguments before the final namespace/currentness bond.
    const auto stageName = s.stage.toUtf8();
    const auto leafName = s.leaf.toUtf8();
    verify(s.stageFd.n, s.entries);
    if (!current()) refuse();
    // Hashing and host-currentness can be lengthy. Only now revalidate the
    // actual selected parent and named source that rename will consume.
    auto parent = State::selectedParent(s.parent);
    if (!s.parentIdentity.object(parent.n)) refuse();
    auto stage = below(parent.n, s.stage, true);
    if (!s.stageIdentity.object(stage.n)) refuse();
    int outcome = -1;
#if defined(__linux__) && defined(SYS_renameat2)
    outcome = static_cast<int>(::syscall(SYS_renameat2, s.parentFd.n, stageName.constData(), s.parentFd.n, leafName.constData(), RENAME_NOREPLACE));
#elif defined(__APPLE__)
    outcome = ::renameatx_np(s.parentFd.n, stageName.constData(), s.parentFd.n, leafName.constData(), RENAME_EXCL);
#endif
    if (outcome != 0) throw std::runtime_error("Fresh project export was refused: the destination exists, changed, or non-overwriting publication is unavailable");
    s.committed = true; // Nonallocating commit latch before every fallible postcommit operation.
#else
    Q_UNUSED(current); refuse();
#endif
}
edi::Project AssistantResultExport::reopen() const {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    const auto& s = *state_;
    if (!s.committed) refuse();
    auto parent = State::selectedParent(s.parent); auto final = below(parent.n, s.leaf, true);
    if (!s.parentIdentity.object(parent.n) || !s.stageIdentity.object(final.n)) refuse();
    verify(s.stageFd.n, s.entries);
    auto result = load_owned_project(s.stageFd.n, s.destination, s.entries);
    verify(s.stageFd.n, s.entries);
    check_assistant_result_mode(result);
    auto again = below(parent.n, s.leaf, true);
    if (!s.stageIdentity.object(again.n)) refuse();
    result.path = s.destination.toStdString(); result.metadata.path = result.path;
    return result;
#else
    refuse();
#endif
}
std::shared_ptr<ImmutableAssistantReport> capture_assistant_report(const QString& workspace, const QString& relative, quint64 remaining) {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    if (relative.isEmpty() || QDir::isAbsolutePath(relative) || relative.toUtf8().size() > static_cast<qsizetype>(Bounds::name_bytes)) refuse();
    const auto suffix = QFileInfo(relative).suffix().toLower();
    if (suffix != "html" && suffix != "htm" && suffix != "pdf") refuse();
    auto root = directory(workspace);
    const Identity rootIdentity(root.n);
    const auto parentName = QFileInfo(relative).path();
    const auto leaf = QFileInfo(relative).fileName(); leaf_name(leaf);
    auto sourceRoot = parentName == "." ? Fd(::openat(root.n, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)) : below(root.n, parentName, true);
    const Identity sourceRootIdentity(sourceRoot.n);
    auto result = std::make_shared<ImmutableAssistantReport>();
    const auto cache = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation) + "/assistant/report-views";
    if (!QDir().mkpath(cache)) refuse();
    result->lease = std::make_shared<QTemporaryDir>(cache + "/report-XXXXXX");
    if (!result->lease->isValid()) refuse();
    const auto physicalCopy = QFileInfo(result->lease->path()).canonicalFilePath();
    const auto agentRoot = QFileInfo(QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation) + "/assistant/agent").canonicalFilePath();
    if (physicalCopy.isEmpty() || agentRoot.isEmpty() || physicalCopy == agentRoot || physicalCopy.startsWith(agentRoot + '/')) refuse();
    auto destination = directory(physicalCopy);
    struct Source { QString path; Identity identity; bool directory; };
    std::vector<Source> admitted; std::set<QString> aliases;
    std::size_t entries = 0;
    const auto copyTree = [&](auto&& self, int from, int to, const QString& prefix, std::size_t depth) -> void {
        if (depth > Limits::json_depth) refuse();
        Fd scan(::openat(from, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
        DIR* raw = ::fdopendir(scan.n); if (!raw) refuse(); scan.n = -1;
        std::unique_ptr<DIR, decltype(&::closedir)> stream(raw, ::closedir);
        for (;;) {
            errno = 0; auto* entry = ::readdir(raw);
            if (!entry) { if (errno) refuse(); break; }
            const QByteArray rawName(entry->d_name); if (rawName == "." || rawName == "..") continue;
            if (++entries > Bounds::files) refuse();
            const auto name = QString::fromUtf8(rawName); if (name.toUtf8() != rawName) refuse(); leaf_name(name);
            const auto path = prefix.isEmpty() ? name : prefix + '/' + name;
            if (path.toUtf8().size() > static_cast<qsizetype>(Bounds::name_bytes) || !aliases.insert(path.normalized(QString::NormalizationForm_C).toCaseFolded()).second) refuse();
            struct stat st{}; if (::fstatat(from, rawName.constData(), &st, AT_SYMLINK_NOFOLLOW)) refuse();
            const bool isDirectory = S_ISDIR(st.st_mode);
            if (!isDirectory && !S_ISREG(st.st_mode)) refuse();
            auto input = below(from, name, isDirectory);
            const Identity identity(input.n);
            admitted.push_back({path, identity, isDirectory});
            if (isDirectory) {
                if (::mkdirat(to, rawName.constData(), 0700)) refuse();
                auto child = below(to, name, true); self(self, input.n, child.n, path, depth + 1);
            } else {
                const auto bytes = read_file(input.n, std::min<quint64>(Bounds::file_bytes, remaining - result->bytes));
                Fd output(::openat(to, rawName.constData(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600));
                qsizetype written = 0;
                while (written < bytes.size()) {
                    const auto n = ::write(output.n, bytes.constData() + written, static_cast<std::size_t>(bytes.size() - written));
                    if (n < 0) { if (errno == EINTR) continue; refuse(); }
                    if (!n) refuse(); written += n;
                }
                if (::fchmod(output.n, 0400)) refuse();
                result->bytes += static_cast<quint64>(bytes.size());
            }
        }
    };
    // Preserve the entry point and its local relative assets, not a renamed
    // text-only HTML file. No HTML is parsed/re-written and no URI is fetched.
    if (suffix == "pdf") {
        auto input = below(sourceRoot.n, leaf);
        const auto bytes = read_file(input.n, std::min<quint64>(Bounds::file_bytes, remaining));
        admitted.push_back({leaf, Identity(input.n), false});
        Fd output(::openat(destination.n, leaf.toUtf8().constData(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600));
        qsizetype written = 0;
        while (written < bytes.size()) { const auto n = ::write(output.n, bytes.constData() + written, static_cast<std::size_t>(bytes.size() - written)); if (n < 0) { if (errno == EINTR) continue; refuse(); } if (!n) refuse(); written += n; }
        if (::fchmod(output.n, 0400)) refuse(); result->bytes = static_cast<quint64>(bytes.size());
    } else copyTree(copyTree, sourceRoot.n, destination.n, {}, 0);
    for (const auto& source : admitted) { auto check = below(sourceRoot.n, source.path, source.directory); if (!source.identity.unchanged(check.n)) refuse(); }
    auto rootAgain = directory(workspace);
    auto sourceAgain = parentName == "." ? Fd(::openat(rootAgain.n, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)) : below(rootAgain.n, parentName, true);
    if (!rootIdentity.object(rootAgain.n) || !sourceRootIdentity.unchanged(sourceAgain.n)) refuse();
    auto entryPoint = below(destination.n, leaf); // The actual linked report must exist in the copy.
    result->file = physicalCopy + '/' + leaf;
    return result;
#else
    Q_UNUSED(workspace); Q_UNUSED(relative); Q_UNUSED(remaining); refuse();
#endif
}
bool AssistantResultExport::committed() const noexcept { return state_ && state_->committed; }
const QString& AssistantResultExport::destination() const noexcept { return state_->destination; }
const QJsonArray& AssistantResultExport::files() const noexcept { return state_->files; }
} // namespace edi_app

