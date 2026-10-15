// SPDX-License-Identifier: BSD-3-Clause
#include "connection_services.hpp"
#include "assistant_json.hpp"

#include <QDateTime>
#include <QDesktopServices>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QLockFile>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QPointer>
#include <QSaveFile>
#include <QStandardPaths>
#include <QThread>
#include <algorithm>
#include <chrono>
#include <stdexcept>
#ifdef Q_OS_UNIX
#include <unistd.h>
#endif

namespace edi::assistant::native {
void validate_dependencies(const NativeDependencies& d) {
    if (!d.request || !d.open_browser || !d.read_record || !d.write_record || !d.erase_record ||
        !d.list_registrations || !d.unix_seconds || !d.monotonic_ms)
        throw std::invalid_argument("Incomplete assistant native dependencies");
}
namespace {
class NetworkOperation final : public HttpOperation {
    QPointer<QNetworkReply> reply_;
    std::vector<QMetaObject::Connection> bindings_;
public:
    explicit NetworkOperation(QNetworkReply* reply) : reply_(reply) {}
    void bind(QMetaObject::Connection connection) { bindings_.push_back(connection); }
    void cancel() noexcept override { if (reply_ && reply_->isRunning()) reply_->abort(); }
    ~NetworkOperation() override {
        for (const auto& connection : bindings_) QObject::disconnect(connection);
        cancel();
        if (reply_) reply_->deleteLater();
    }
};
struct Services : QObject {
    QNetworkAccessManager network{this};
    QString root = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation) + "/assistant/connections";
    std::unique_ptr<QLockFile> record_lock;
    std::string locked_id;

    bool directory(const QString& name) {
#ifdef Q_OS_UNIX
        const QFileInfo before(name);
        if (before.isSymLink() || (before.exists() && (!before.isDir() || before.ownerId() != getuid()))) return false;
        return QDir().mkpath(name) && QFile::setPermissions(name, QFile::ReadOwner | QFile::WriteOwner | QFile::ExeOwner);
#else
        (void)name;
        return false;
#endif
    }
    bool protect() {
        return directory(QFileInfo(root).absolutePath()) && directory(root) &&
               directory(root + "/registrations") && directory(root + "/credentials");
    }
    QString path(const RecordKey& key) {
        if (key.kind == RecordKind::host) {
            if (key.id != "host") throw std::invalid_argument("Invalid own host key");
            return root + "/host.json";
        }
        if (key.id.size() != 64 || !std::all_of(key.id.begin(), key.id.end(), [](char c) {
            return (c >= 'a' && c <= 'f') || (c >= '0' && c <= '9');
        })) throw std::invalid_argument("Invalid own registration key");
        return root + (key.kind == RecordKind::registration ? "/registrations/" : "/credentials/") + QString::fromStdString(key.id) + ".json";
    }
    void release() { record_lock.reset(); locked_id.clear(); }
    bool acquire(const std::string& id) {
        if (record_lock) return locked_id == id;
        auto next = std::make_unique<QLockFile>(root + "/credentials/" + QString::fromStdString(id) + ".lock");
        if (!next->tryLock(0)) return false;
        record_lock = std::move(next); locked_id = id; return true;
    }
    RecordRead read(const RecordKey& key) {
        if (!protect()) return {StoreStatus::failed, {}};
        const auto name = path(key); const QFileInfo info(name);
        if (info.isSymLink() || (info.exists() && !info.isFile())) return {StoreStatus::failed, {}};
        if (!info.exists()) return {StoreStatus::absent, {}};
#ifdef Q_OS_UNIX
        if (info.ownerId() != getuid() || (info.permissions() & (QFile::ReadGroup | QFile::WriteGroup | QFile::ExeGroup | QFile::ReadOther | QFile::WriteOther | QFile::ExeOther)))
            return {StoreStatus::failed, {}};
#endif
        if (key.kind == RecordKind::credentials && !acquire(key.id)) return {StoreStatus::failed, {}};
        QFile file(name);
        if (info.size() > static_cast<qint64>(Limits::record_bytes))
            detail::refuse("resource_exhausted", "Own record exceeds the assistant limit");
        if (!file.open(QIODevice::ReadOnly)) return {StoreStatus::failed, {}};
        const auto bytes = file.read(static_cast<qint64>(Limits::record_bytes) + 1);
        if (file.error() != QFile::NoError) return {StoreStatus::failed, {}};
        if (!file.atEnd() || bytes.size() > static_cast<qint64>(Limits::record_bytes))
            detail::refuse("resource_exhausted", "Own record exceeds the assistant limit");
        return {StoreStatus::ok, bytes};
    }
    StoreStatus write(const RecordKey& key, const QByteArray& bytes) {
        if (bytes.size() > static_cast<qint64>(Limits::record_bytes))
            detail::refuse("resource_exhausted", "Own record exceeds the assistant limit");
        if (!protect()) return StoreStatus::failed;
        const auto name = path(key); const QFileInfo info(name);
        if (info.isSymLink() || (info.exists() && !info.isFile())) return StoreStatus::failed;
#ifdef Q_OS_UNIX
        if (info.exists() && (info.ownerId() != getuid() || (info.permissions() & (QFile::ReadGroup | QFile::WriteGroup | QFile::ExeGroup | QFile::ReadOther | QFile::WriteOther | QFile::ExeOther)))) return StoreStatus::failed;
#endif
        if (key.kind == RecordKind::credentials && !acquire(key.id)) return StoreStatus::failed;
        QSaveFile file(name);
        if (!file.open(QIODevice::WriteOnly) || !file.setPermissions(QFile::ReadOwner | QFile::WriteOwner) ||
            file.write(bytes) != bytes.size() || !file.commit()) return StoreStatus::failed;
        if (key.kind == RecordKind::credentials) release();
        return StoreStatus::ok;
    }
    StoreStatus erase(const RecordKey& key) {
        if (!protect()) return StoreStatus::failed;
        const auto name = path(key); const QFileInfo info(name);
        if (info.isSymLink() || (info.exists() && !info.isFile())) return StoreStatus::failed;
#ifdef Q_OS_UNIX
        if (info.exists() && info.ownerId() != getuid()) return StoreStatus::failed;
#endif
        if (key.kind == RecordKind::credentials && !acquire(key.id)) return StoreStatus::failed;
        const bool absent = !info.exists();
        if (!absent && !QFile::remove(name)) return StoreStatus::failed;
        if (key.kind == RecordKind::credentials) release();
        return absent ? StoreStatus::absent : StoreStatus::ok;
    }
    RegistrationList list() {
        if (!protect()) return {StoreStatus::failed, {}};
        RegistrationList result{StoreStatus::ok, {}};
        const auto files = QDir(root + "/registrations").entryInfoList(QDir::AllEntries | QDir::NoDotAndDotDot);
        if (files.size() > static_cast<qsizetype>(Limits::registrations))
            detail::refuse("resource_exhausted", "Own registration count exceeds the assistant limit");
        for (const auto& info : files) {
            if (!info.isFile() || info.isSymLink() || !info.fileName().endsWith(".json")) return {StoreStatus::failed, {}};
            const auto id = info.fileName().chopped(5).toStdString();
            (void)path({RecordKind::registration, id});
            result.ids.push_back(id);
        }
        return result;
    }
    std::unique_ptr<HttpOperation> request(HttpRequest source, HttpCallbacks callbacks) {
        QNetworkRequest request(source.url);
        request.setAttribute(QNetworkRequest::RedirectPolicyAttribute, QNetworkRequest::ManualRedirectPolicy);
        request.setTransferTimeout(static_cast<int>(source.timeout_ms));
        for (const auto& [name, value] : source.headers) request.setRawHeader(name, value);
        auto* reply = source.method == HttpMethod::get ? network.get(request) : network.post(request, source.body);
        reply->setReadBufferSize(static_cast<qint64>(Limits::http_chunk_bytes));
        auto owned = std::make_unique<NetworkOperation>(reply);
        auto headers_sent = std::make_shared<bool>(false);
        auto headers = [reply, headers_sent, callbacks] {
            if (*headers_sent || !reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).isValid()) return;
            *headers_sent = true;
            HttpHeaders list;
            for (const auto& pair : reply->rawHeaderPairs()) list.emplace_back(pair.first, pair.second);
            if (callbacks.headers) callbacks.headers(reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt(), std::move(list));
        };
        auto read = [reply, headers, callbacks] {
            headers();
            while (reply->bytesAvailable() > 0) {
                auto bytes = reply->read(static_cast<qint64>(Limits::http_chunk_bytes));
                if (bytes.isEmpty()) break;
                if (callbacks.data) callbacks.data(std::move(bytes));
            }
        };
        owned->bind(QObject::connect(reply, &QNetworkReply::metaDataChanged, this, headers));
        owned->bind(QObject::connect(reply, &QNetworkReply::readyRead, this, read));
        owned->bind(QObject::connect(reply, &QNetworkReply::finished, this, [reply, read, callbacks] {
            read();
            HttpFailure failure = HttpFailure::network;
            switch (reply->error()) {
                case QNetworkReply::NoError: failure = HttpFailure::none; break;
                case QNetworkReply::OperationCanceledError: failure = HttpFailure::cancelled; break;
                case QNetworkReply::TimeoutError: failure = HttpFailure::timeout; break;
                case QNetworkReply::SslHandshakeFailedError: failure = HttpFailure::tls; break;
                case QNetworkReply::ContentAccessDenied:
                case QNetworkReply::ContentOperationNotPermittedError:
                case QNetworkReply::ContentNotFoundError:
                case QNetworkReply::AuthenticationRequiredError:
                case QNetworkReply::ContentConflictError:
                case QNetworkReply::ContentGoneError:
                case QNetworkReply::UnknownContentError:
                case QNetworkReply::InternalServerError:
                case QNetworkReply::OperationNotImplementedError:
                case QNetworkReply::ServiceUnavailableError:
                case QNetworkReply::UnknownServerError: {
                    const auto status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
                    if (status >= 400 && status <= 599) failure = HttpFailure::none;
                    break;
                }
                // In particular ContentReSendError is not an ordinary HTTP rejection.
                // Having headers never erases a genuine network/proxy/TLS/protocol failure.
                default: break;
            }
            if (callbacks.finished) callbacks.finished(failure);
        }));
        return owned;
    }
};
}
ProductionServices production_services() {
    auto services = std::make_shared<Services>();
    NativeDependencies d;
    d.request = [services](HttpRequest request, HttpCallbacks callbacks) { return services->request(std::move(request), std::move(callbacks)); };
    d.open_browser = [](const QUrl& url) { return QDesktopServices::openUrl(url); };
    d.read_record = [services](const RecordKey& key) { return services->read(key); };
    d.write_record = [services](const RecordKey& key, const QByteArray& bytes) { return services->write(key, bytes); };
    d.erase_record = [services](const RecordKey& key) { return services->erase(key); };
    d.list_registrations = [services] { return services->list(); };
    d.unix_seconds = [] { return QDateTime::currentSecsSinceEpoch(); };
    d.monotonic_ms = [] { return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now().time_since_epoch()).count()); };
    return {std::move(d), [services] { services->release(); }};
}
}
