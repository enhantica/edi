// SPDX-License-Identifier: BSD-3-Clause
#include "desktop_updates.hpp"

#include <QCoreApplication>
#include <QDate>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkReply>
#include <QRegularExpression>
#include <QSet>
#include <QTimer>
#ifndef __EMSCRIPTEN__
#include <QProcess>
#endif
#if !defined(__EMSCRIPTEN__) && !defined(Q_OS_WIN)
#define EDI_TOOL_LOCK 1
#include <cerrno>
#include <fcntl.h>
#include <sys/file.h>
#include <unistd.h>
#endif
#include <algorithm>
#include <array>
#include <optional>
#include <memory>

#include "build_version.hpp"

namespace edi_app {
std::optional<ReleaseKey> release_version_key(const QString& value) {
    static const QRegularExpression year(QStringLiteral(R"(\A([1-9][0-9])\.([1-9][0-9]*)\z)"));
    static const QRegularExpression old(QStringLiteral(R"(\A([0-9]{4})\.(0[1-9]|1[0-2])\.(0|[1-9][0-9]*)\z)"));
    const auto number = [](const QString& text) {
        bool ok = false;
        const auto result = text.toULongLong(&ok);
        return ok ? std::optional<quint64>(result) : std::nullopt;
    };
    if (const auto match = year.match(value); match.hasMatch()) {
        const auto yy = number(match.captured(1)), n = number(match.captured(2));
        if (!yy || !n) return {};
        return ReleaseKey{2000 + *yy, 1, *n, 0};
    }
    const auto match = old.match(value);
    if (!match.hasMatch()) return {};
    const auto y = number(match.captured(1)), m = number(match.captured(2)), n = number(match.captured(3));
    if (!y || !m || !n || *y < 2000) return {};
    return ReleaseKey{*y, 0, *m, *n};
}
namespace {
// The lock every writer of the Maintenance Tool's files takes (ADR-0108). The kernel drops it when its holder exits, so
// an update stopped by a crash or a power cut never leaves it taken. The app never waits for it: busy means an update
// is changing the files right now. Windows has no swap and so no lock: there it is never held.
class ToolLock {
public:
    explicit ToolLock(const QString& target) {
#ifdef EDI_TOOL_LOCK
        const QByteArray path = QFile::encodeName(target + QStringLiteral("/.MaintenanceTool.lock"));
        fd_ = ::open(path.constData(), O_RDWR | O_CREAT | O_CLOEXEC, 0644);
        if (fd_ < 0) return;
        int result = 0;
        do result = ::flock(fd_, LOCK_EX | LOCK_NB);
        while (result != 0 && errno == EINTR);
        if (result != 0) {
            ::close(fd_);
            fd_ = -1;
        }
#else
        Q_UNUSED(target);
#endif
    }
    ~ToolLock() {
#ifdef EDI_TOOL_LOCK
        if (fd_ >= 0) ::close(fd_);
#endif
    }
    ToolLock(const ToolLock&) = delete;
    ToolLock& operator=(const ToolLock&) = delete;
    bool held() const { return fd_ >= 0; }

private:
    int fd_ = -1;
};
// The folder an update swaps in for the installed one (ADR-0108), or an empty string: the bundle holding `executable`
// on macOS, the Qt runtime beside the tool on Linux. Windows has none, the Framework writes the tool itself.
QString swapped_item(const QString& executable) {
    if (executable.isEmpty() || executable.endsWith(QStringLiteral(".exe"), Qt::CaseInsensitive)) return {};
    QString bundle = QDir::cleanPath(executable + QStringLiteral("/../../.."));
    if (bundle.endsWith(QStringLiteral(".app"))) return bundle;
    return QFileInfo(executable).absolutePath() + QStringLiteral("/installer-runtime");
}
// Whether `folder`, the item or its kept copy, has the file that makes the item usable, as the scripts test it.
bool usable_item(const QString& folder, const QString& item, const QString& executable) {
    const QString probe = item.endsWith(QStringLiteral(".app"))
                              ? QStringLiteral("/Contents/MacOS/") + QFileInfo(executable).fileName()
                              : QStringLiteral("/dependencies.json");
    return QFileInfo(folder + probe).isFile();
}
bool present(const QString& path) {
    const QFileInfo info(path);
    return info.exists() || info.isSymLink();
}
bool remove_path(const QString& path) {
    const QFileInfo info(path);
    return info.isDir() && !info.isSymLink() ? QDir(path).removeRecursively() : QFile::remove(path);
}
// Compared byte by byte: equal files mean the Framework has already written the staged tool in place.
bool same_bytes(const QString& a, const QString& b) {
    QFile first(a), second(b);
    if (!first.open(QIODevice::ReadOnly) || !second.open(QIODevice::ReadOnly) || first.size() != second.size())
        return false;
    while (!first.atEnd()) {
        const QByteArray chunk = first.read(qint64{1} << 16);
        if (chunk.isEmpty() || chunk != second.read(chunk.size())) return false;
    }
    return true;
}
// Whether the tool named in a kept item's mark, "<token> <pid> <start>", still runs: the same process number with the
// same start time, read as the scripts read it (ADR-0108). Only the cleanup asks, so a wrong yes merely leaves the
// backup to the next start; when it cannot tell, it says yes.
bool marked_tool_running(const QString& mark_file) {
#ifdef EDI_TOOL_LOCK
    QFile file(mark_file);
    if (!file.open(QIODevice::ReadOnly)) return false;
    const QStringList fields = QString::fromUtf8(file.read(4096)).simplified().split(QLatin1Char(' '));
    bool number = false;
    const qint64 pid = fields.value(1).toLongLong(&number);
    if (!number || pid <= 0) return false;
    QProcess ps;
    QProcessEnvironment environment = QProcessEnvironment::systemEnvironment();
    environment.insert(QStringLiteral("TZ"), QStringLiteral("UTC0"));
    environment.insert(QStringLiteral("LC_ALL"), QStringLiteral("C"));
    ps.setProcessEnvironment(environment);
    ps.start(QStringLiteral("/bin/ps"),
             {QStringLiteral("-o"), QStringLiteral("lstart="), QStringLiteral("-p"), QString::number(pid)});
    if (!ps.waitForFinished(3000)) {
        ps.kill();
        ps.waitForFinished(1000);
        return true;
    }
    if (ps.exitStatus() != QProcess::NormalExit) return true;
    if (ps.exitCode() != 0) return false;  // no such process
    return QString::fromUtf8(ps.readAllStandardOutput()).simplified() == fields.mid(2).join(QLatin1Char(' '));
#else
    Q_UNUSED(mark_file);
    return false;
#endif
}
}  // namespace
// A kept tool beside the one holding `executable`: a swap is running or stopped, and the installation is managed.
static bool kept_maintenance_tool(const QString& executable) {
    const QString item = swapped_item(executable);
    return !item.isEmpty() && usable_item(item + QStringLiteral(".old"), item, executable);
}
bool restore_kept_maintenance_tool(const QString& executable) {
    const QString item = swapped_item(executable);
    if (item.isEmpty()) return false;
    const QString kept = item + QStringLiteral(".old");
    const QString drop = item + QStringLiteral(".drop");
    const auto needed = [&] { return !usable_item(item, item, executable) && usable_item(kept, item, executable); };
    if (!needed()) return false;
    // Busy, an update is between its renames and finishes or undoes them itself; the launch actions try again later.
    // Held, the state is read again: the update may have ended just before.
    const ToolLock lock(QFileInfo(item).absolutePath());
    if (!lock.held() || !needed()) return false;
    // Part of an item in its place leaves it in one rename first, as in the swap. The staged item stays: the retried
    // update finishes the swap with it.
    if (present(item)) {
        QDir(drop).removeRecursively();
        if (!QDir().rename(item, drop)) return false;
    }
    if (!QDir().rename(kept, item)) {
        if (!present(item)) QDir().rename(drop, item);
        return false;
    }
    QFile::remove(item + QStringLiteral(".old-token"));
    QDir(drop).removeRecursively();
    return true;
}
bool remove_maintenance_tool_leftovers(const QString& executable) {
    if (executable.endsWith(QStringLiteral(".exe"), Qt::CaseInsensitive)) {
        // The staged copy is what the Framework writes the tool from (ADR-0091), so it goes only once it is in place.
        const QString staging = QFileInfo(executable).absolutePath() + QStringLiteral("/maintenancetool");
        return same_bytes(executable, staging + QStringLiteral("/MaintenanceTool.exe")) &&
               QDir(staging).removeRecursively();
    }
    const QString item = swapped_item(executable);
    if (item.isEmpty()) return false;
    const QString target = QFileInfo(item).absolutePath();
    const QString staging = target + QStringLiteral("/maintenancetool");
    const QString mark = item + QStringLiteral(".old-token");
    QStringList leftovers{item + QStringLiteral(".old"), mark, staging};
    if (!usable_item(item, item, executable) || std::none_of(leftovers.cbegin(), leftovers.cend(), present))
        return false;
    const ToolLock lock(target);
    if (!lock.held() || !usable_item(item, item, executable)) return false;
    // A usable staged item is a swap still to come in a running update, and the backup is its undo's until the tool
    // that kept it has exited. Anything else is left over from an update that has ended.
    if (usable_item(staging + QLatin1Char('/') + QFileInfo(item).fileName(), item, executable)) leftovers.removeLast();
    if (marked_tool_running(mark)) leftovers.remove(0, 2);
    bool removed = false;
    for (const QString& path : leftovers) {
        if (present(path) && remove_path(path)) removed = true;
    }
    return removed;
}
namespace {
QString maintenance_path() {
#ifdef __EMSCRIPTEN__
    return {};
#else
    const QDir binary(QCoreApplication::applicationDirPath());
#ifdef Q_OS_MACOS
    return binary.absoluteFilePath(QStringLiteral("../../../MaintenanceTool.app/Contents/MacOS/MaintenanceTool"));
#elif defined(Q_OS_WIN)
    return binary.absoluteFilePath(QStringLiteral("../MaintenanceTool.exe"));
#else
    return binary.absoluteFilePath(QStringLiteral("../MaintenanceTool"));
#endif
#endif
}
QList<QUrl> feed_urls() {
    const QDir installation(QFileInfo(maintenance_path()).absoluteDir());
#ifdef Q_OS_MACOS
    const auto channelPath = installation.absoluteFilePath(QStringLiteral("../../../update-channel.txt"));
#else
    const auto channelPath = installation.absoluteFilePath(QStringLiteral("update-channel.txt"));
#endif
    QFile channelFile(channelPath);
    const bool testing = channelFile.open(QIODevice::ReadOnly) && channelFile.read(32).trimmed() == "testing";
    QFile policy(QStringLiteral(":/edi/distribution.json"));
    if (!policy.open(QIODevice::ReadOnly)) return {};
    const auto object = QJsonDocument::fromJson(policy.readAll()).object();
    QList<QUrl> result;
    QStringList bases{object.value(QStringLiteral("primary_base")).toString()};
    for (const auto& mirror : object.value(QStringLiteral("mirror_bases")).toArray()) bases.append(mirror.toString());
    for (const auto& base : bases) {
        const QUrl url = QUrl(base).resolved(QUrl(testing ? QStringLiteral("releases/testing.json") : QStringLiteral("releases/stable.json")));
        if (url.scheme() == QLatin1String("https") && !url.host().isEmpty()) result.append(url);
    }
    return result;
}
QString markdown_title(QString text) {
    text = text.toHtmlEscaped();
    for (const QChar character : QStringLiteral("\\`*_[]!#")) text.replace(character, QStringLiteral("\\") + character);
    return text;
}
}  // namespace

QVariantList release_changes(const QByteArray& content, const QString& current, bool* valid, bool allow_preview) {
    if (valid) *valid = false;
    const auto upper = release_version_key(current);
    if ((!current.isEmpty() && !upper) || content.size() > qsizetype{1024} * 1024) return {};
    const auto document = QJsonDocument::fromJson(content);
    const auto object = document.object();
    const auto schema = object.value(QStringLiteral("schema")).toString();
    const bool preview = allow_preview && schema == QLatin1String("edi.preview-releases/1");
    if ((!preview && schema != QLatin1String("edi.releases/1")) ||
        !object.value(QStringLiteral("releases")).isArray()) return {};
    QVariantList result;
    QSet<QString> seen;
    for (const auto& value : object.value(QStringLiteral("releases")).toArray()) {
        const auto release = value.toObject();
        const QString version = release.value(QStringLiteral("version")).toString();
        const auto key = release_version_key(version);
        const auto date = release.value(QStringLiteral("date")).toString();
        static const QRegularExpression commit(QStringLiteral("\\A[0-9a-f]{40}\\z"));
        const auto notes = release.value(QStringLiteral("notes")).toObject();
        if (!key || seen.contains(version) || (!QDate::fromString(date, Qt::ISODate).isValid() || QDate::fromString(date, Qt::ISODate).toString(Qt::ISODate) != date) ||
            !commit.match(release.value(QStringLiteral("commit")).toString()).hasMatch() || notes.isEmpty()) return {};
        seen.insert(version);
        QString text;
        for (const auto& group : {QStringLiteral("Added"), QStringLiteral("Fixed"), QStringLiteral("Changed")}) {
            if (!notes.value(group).isArray()) return {};
            const auto entries = notes.value(group).toArray();
            if (entries.isEmpty()) continue;
            text += QStringLiteral("### ") + group + QStringLiteral("\n\n");
            for (const auto& entry : entries) {
                const auto item = entry.toObject();
                const auto title = item.value(QStringLiteral("title")).toString();
                const auto number = item.value(QStringLiteral("pull_request")).toInteger();
                if (title.trimmed().isEmpty() || title.size() > 512 || title.contains('\n') || title.contains('\r') || (!preview && number <= 0)) return {};
                text += QStringLiteral("- ") + markdown_title(title) + QStringLiteral("\n");
            }
            text += QLatin1Char('\n');
        }
        if (text.isEmpty()) return {};
        if (!upper || *key <= *upper) {
            QVariantMap entry{{QStringLiteral("version"), version},
                              {QStringLiteral("date"), date},
                              {QStringLiteral("text"), text.trimmed()}};
            if (preview) entry.insert(QStringLiteral("preview"), true);
            result.append(entry);
        }
    }
    std::sort(result.begin(), result.end(), [](const QVariant& a, const QVariant& b) {
        return release_version_key(a.toMap().value(QStringLiteral("version")).toString()) >
               release_version_key(b.toMap().value(QStringLiteral("version")).toString());
    });
    if (valid) *valid = true;
    return result;
}

DesktopUpdates::DesktopUpdates(QObject* parent)
    : DesktopUpdates(QString::fromUtf8(app_version()), maintenance_path(), feed_urls(), true, parent) {}
DesktopUpdates::DesktopUpdates(QString version, QString maintenance, QList<QUrl> feeds, bool automatic, QObject* parent)
    : QObject(parent), version_(std::move(version)), maintenance_(std::move(maintenance)), feeds_(std::move(feeds)) {
#ifndef __EMSCRIPTEN__
    const bool release = release_version_key(version_).has_value();
    if (release) {
        restore_kept_maintenance_tool(maintenance_);
        remove_maintenance_tool_leftovers(maintenance_);
    }
    // While an update still runs, the tool may be aside: the launch actions put it back once that update has ended.
    managed_ = release && (QFileInfo(maintenance_).isExecutable() || kept_maintenance_tool(maintenance_));
#endif
    status_ = managed_ ? tr("Updates have not been checked yet.") : tr("Updates are available for installed desktop releases.");
    if (managed_ && automatic && !QCoreApplication::arguments().contains(QStringLiteral("--testmode")) &&
        !QCoreApplication::arguments().contains(QStringLiteral("--test-observer"))) {
        QTimer::singleShot(2000, this, [this] { checkNow(); });
        auto* timer = new QTimer(this);
        timer->setInterval(60 * 60 * 1000);
        connect(timer, &QTimer::timeout, this, [this] { checkNow(); });
        timer->start();
    }
}
bool DesktopUpdates::newerVersion(const QString& candidate, const QString& previous) const {
    const auto a = release_version_key(candidate), b = release_version_key(previous);
    return a && b && *a > *b;
}
namespace {
// One release's entry as the What's new dialog shows it, the same type the app's own history gives.
ChangeDay change_day(const QVariant& release) {
    const auto item = release.toMap();
    return ChangeDay{item.value(QStringLiteral("date")).toString(), item.value(QStringLiteral("text")).toString(),
                     item.value(QStringLiteral("version")).toString()};
}
}  // namespace

QList<ChangeDay> DesktopUpdates::releaseChanges() const {
    QFile history(QStringLiteral(":/edi/releases.json"));
    QList<ChangeDay> days;
    if (history.open(QIODevice::ReadOnly)) {
        for (const auto& release : release_changes(history.readAll(), version_, nullptr, true)) days.append(change_day(release));
    }
    return days;
}
void DesktopUpdates::checkNow(bool manual) {
    if (!managed_ || checking_) return;
    checking_ = true;
    manual_ = manual;
    next_feed_ = 0;
    status_ = tr("Checking for updates…");
    emit checkingChanged();
    emit statusChanged();
    emit changed();
    fetchNext();
}
void DesktopUpdates::fetchNext() {
    if (next_feed_ >= feeds_.size()) {
        checking_ = false;
        status_ = tr("Unable to check for updates.");
        emit checkingChanged();
        emit statusChanged();
        emit changed();
        return;
    }
    QNetworkRequest request(feeds_.at(next_feed_++));
    request.setTransferTimeout(15000);
    request.setMaximumRedirectsAllowed(4);
    auto* reply = network_.get(request);
    reply->setReadBufferSize(qint64{64} * 1024);
    auto bytes = std::make_shared<QByteArray>();
    const auto read = [reply, bytes] {
        bytes->append(reply->read(1024 * 1024 + 1 - bytes->size()));
        if (bytes->size() > qsizetype{1024} * 1024) reply->abort();
    };
    connect(reply, &QIODevice::readyRead, this, read);
    connect(reply, &QNetworkReply::finished, this, [this, reply, bytes, read] {
        read();
        bool valid = false;
        const bool preview = reply->request().url().path().endsWith(QStringLiteral("/releases/testing.json"));
        const auto history = release_changes(*bytes, QString{}, &valid, preview);
        const bool success = reply->error() == QNetworkReply::NoError && valid;
        reply->deleteLater();
        if (!success) { fetchNext(); return; }
        available_version_.clear();
        available_changes_.clear();
        const auto latest = history.isEmpty() ? QString{} :
            history.first().toMap().value(QStringLiteral("version")).toString();
        if (!latest.isEmpty()) {
            if (newerVersion(latest, version_)) {
                available_version_ = latest;
                for (const auto& change : history) {
                    if (newerVersion(change.toMap().value(QStringLiteral("version")).toString(), version_))
                        available_changes_.append(change_day(change));
                }
            }
        }
        checking_ = false;
        status_ = history.isEmpty() ? tr("No published releases are available.") :
                  available() ? tr("EasyDiffraction %1 is available.").arg(available_version_) :
                                latest == version_ ? tr("You are using the latest release, %1.").arg(version_) :
                                       tr("You are using release %1.").arg(version_);
        const bool manual = manual_;
        emit checkingChanged();
        emit availableChanged();
        emit availableVersionChanged();
        emit availableChangesChanged();
        emit statusChanged();
        emit changed();
        emit checkFinished(manual);
    });
}
bool DesktopUpdates::startMaintenance() {
#ifndef __EMSCRIPTEN__
    // The tool may have been left aside since the app started (see restore_kept_maintenance_tool).
    if (managed_) restore_kept_maintenance_tool(maintenance_);
    if (managed_ && QProcess::startDetached(maintenance_, {}, QFileInfo(maintenance_).absolutePath())) return true;
#endif
    status_ = tr("The Maintenance Tool could not be opened.");
    emit statusChanged();
    emit changed();
    return false;
}

bool DesktopUpdates::startUpdate() {
#ifndef __EMSCRIPTEN__
    // The tool may have been left aside since the app started (see restore_kept_maintenance_tool).
    if (managed_) restore_kept_maintenance_tool(maintenance_);
    if (managed_ && available() && QProcess::startDetached(maintenance_, {QStringLiteral("--start-updater")}, QFileInfo(maintenance_).absolutePath())) return true;
#endif
    status_ = tr("The updater could not be opened. Your project is still open.");
    emit statusChanged();
    emit changed();
    return false;
}
}  // namespace edi_app
