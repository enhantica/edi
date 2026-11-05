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
#include <algorithm>
#include <array>
#include <optional>
#include <memory>

#include "build_version.hpp"

namespace edi_app {
namespace {
using Version = std::array<quint64, 3>;
std::optional<Version> calendar_version(const QString& value) {
    static const QRegularExpression syntax(QStringLiteral(R"(\A([0-9]{4})\.(0[1-9]|1[0-2])\.(0|[1-9][0-9]*)\z)"));
    const auto match = syntax.match(value);
    if (!match.hasMatch()) return {};
    Version result{};
    for (qsizetype i = 0; i < 3; ++i) {
        bool ok = false;
        result[i] = match.captured(i + 1).toULongLong(&ok);
        if (!ok) return {};
    }
    if (result[0] < 2000) return {};
    return result;
}
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
    const auto upper = calendar_version(current);
    if ((!current.isEmpty() && !upper) || content.size() > 1024 * 1024) return {};
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
        const auto key = calendar_version(version);
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
        if (!upper || *key <= *upper) result.append(QVariantMap{{QStringLiteral("version"), version}, {QStringLiteral("date"), date}, {QStringLiteral("text"), text.trimmed()}});
    }
    std::sort(result.begin(), result.end(), [](const QVariant& a, const QVariant& b) {
        return calendar_version(a.toMap().value(QStringLiteral("version")).toString()) >
               calendar_version(b.toMap().value(QStringLiteral("version")).toString());
    });
    if (valid) *valid = true;
    return result;
}

DesktopUpdates::DesktopUpdates(QObject* parent)
    : DesktopUpdates(QString::fromUtf8(app_version()), maintenance_path(), feed_urls(), true, parent) {}
DesktopUpdates::DesktopUpdates(QString version, QString maintenance, QList<QUrl> feeds, bool automatic, QObject* parent)
    : QObject(parent), version_(std::move(version)), maintenance_(std::move(maintenance)), feeds_(std::move(feeds)) {
#ifndef __EMSCRIPTEN__
    managed_ = calendar_version(version_).has_value() && QFileInfo(maintenance_).isExecutable();
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
    const auto a = calendar_version(candidate), b = calendar_version(previous);
    return a && b && *a > *b;
}
QVariantList DesktopUpdates::releaseChanges() const {
    QFile history(QStringLiteral(":/edi/releases.json"));
    return history.open(QIODevice::ReadOnly) ? release_changes(history.readAll(), version_, nullptr, true) : QVariantList{};
}
void DesktopUpdates::checkNow(bool manual) {
    if (!managed_ || checking_) return;
    checking_ = true;
    manual_ = manual;
    next_feed_ = 0;
    status_ = tr("Checking for updates…");
    emit changed();
    fetchNext();
}
void DesktopUpdates::fetchNext() {
    if (next_feed_ >= feeds_.size()) {
        checking_ = false;
        status_ = tr("Unable to check for updates.");
        emit changed();
        return;
    }
    QNetworkRequest request(feeds_.at(next_feed_++));
    request.setTransferTimeout(15000);
    request.setMaximumRedirectsAllowed(4);
    auto* reply = network_.get(request);
    reply->setReadBufferSize(64 * 1024);
    auto bytes = std::make_shared<QByteArray>();
    const auto read = [reply, bytes] {
        bytes->append(reply->read(1024 * 1024 + 1 - bytes->size()));
        if (bytes->size() > 1024 * 1024) reply->abort();
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
        if (!history.isEmpty()) {
            const auto latest = history.first().toMap().value(QStringLiteral("version")).toString();
            if (newerVersion(latest, version_)) {
                available_version_ = latest;
                for (const auto& change : history) {
                    if (newerVersion(change.toMap().value(QStringLiteral("version")).toString(), version_))
                        available_changes_.append(change);
                }
            }
        }
        checking_ = false;
        status_ = history.isEmpty() ? tr("No published releases are available.") :
                  available() ? tr("EasyDiffraction %1 is available.").arg(available_version_) :
                                tr("You are using the latest release.");
        const bool manual = manual_;
        emit changed();
        emit checkFinished(manual);
    });
}
bool DesktopUpdates::startUpdate() {
#ifndef __EMSCRIPTEN__
    if (managed_ && available() && QProcess::startDetached(maintenance_, {QStringLiteral("--start-updater")}, QFileInfo(maintenance_).absolutePath())) return true;
#endif
    status_ = tr("The updater could not be opened. Your project is still open.");
    emit changed();
    return false;
}
}  // namespace edi_app
