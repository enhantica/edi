// SPDX-License-Identifier: BSD-3-Clause
#include "online_fetch.hpp"

#include <QPointer>

#include <QCoreApplication>
#include <QCryptographicHash>
#include <QFile>
#include <QLoggingCategory>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkProxyFactory>
#include <QNetworkRequest>
#include <QTimer>

namespace edi_app {
namespace {
Q_LOGGING_CATEGORY(lcOnline, "edi.online")

// Whether a failed reply means the source could not be reached, as opposed to answering with a refusal: by error
// class, not by a list. Qt numbers transport errors 1 to 99, proxy errors 101 to 199, server errors 401 to 499;
// content and protocol errors (a 404, a bad redirect) are answers. Any 5xx status is an outage too.
bool unreachable_error(QNetworkReply::NetworkError error, int status) {
    const int code = static_cast<int>(error);
    if (status >= 500) return true;
    return (code >= 1 && code <= 199) || (code >= 401 && code <= 499);
}

}  // namespace

QString content_problem(const QByteArray& bytes, long long expected_bytes, const QString& sha256, const QString& name) {
    if (expected_bytes >= 0 && bytes.size() != expected_bytes)
        return QCoreApplication::translate("OnlineSearch", "%1 has %2 bytes, not the %3 the index records")
            .arg(name).arg(bytes.size()).arg(expected_bytes);
    if (!sha256.isEmpty() &&
        QString::fromLatin1(QCryptographicHash::hash(bytes, QCryptographicHash::Sha256).toHex()).compare(sha256, Qt::CaseInsensitive) != 0)
        return QCoreApplication::translate("OnlineSearch", "%1 does not match the digest the index records").arg(name);
    return {};
}

QUrl joined_url(const QString& base, const QString& path) {
    QString root = base;
    while (root.endsWith(u'/')) root.chop(1);
    const QUrl url(root + u'/' + path);
    if (url.scheme().isEmpty()) return QUrl::fromLocalFile(root + u'/' + path);
    return url;
}

void fetch_from(QObject* owner, QNetworkAccessManager*& manager, const QStringList& bases, const QString& path, FetchDone done, FetchProgress progress) {
    if (bases.isEmpty()) {
        done({}, QCoreApplication::translate("OnlineSearch", "No location to read %1 from").arg(path), true);
        return;
    }
    const QStringList rest = bases.mid(1);
    fetch_url(owner, manager, joined_url(bases.constFirst(), path),
              [owner, &manager, rest, path, done, progress](const QByteArray& bytes, const QString& error, bool unreachable) {
                  if (!error.isEmpty() && unreachable && !rest.isEmpty()) {
                      fetch_from(owner, manager, rest, path, done, progress);
                      return;
                  }
                  done(bytes, error, unreachable);
              }, progress);
}

void fetch_url(QObject* owner, QNetworkAccessManager*& manager, const QUrl& url, FetchDone done, FetchProgress progress) {
    if (url.isLocalFile() || url.scheme().isEmpty()) {
        const QString path = url.isLocalFile() ? url.toLocalFile() : url.toString();
        QTimer::singleShot(0, owner, [path, done, progress, receiver = QPointer<QObject>(owner)] {
            QFile file(path);
            if (!file.exists()) {
                done({}, QCoreApplication::translate("OnlineSearch", "%1 does not exist").arg(path), true);
                return;
            }
            if (!file.open(QIODevice::ReadOnly)) {
                done({}, QCoreApplication::translate("OnlineSearch", "%1 cannot be read").arg(path), false);
                return;
            }
            const auto bytes = file.readAll();
            if (progress) progress(bytes.size(), bytes.size());
            if (receiver) done(bytes, {}, false);
        });
        return;
    }
    if (manager == nullptr) {
        // The system's proxy (on Linux the http_proxy environment) and a transfer timeout, so a request behind a proxy
        // neither bypasses it nor hangs without a word.
        QNetworkProxyFactory::setUseSystemConfiguration(true);
        manager = new QNetworkAccessManager(owner);
        manager->setTransferTimeout(30000);
    }
    QNetworkRequest request(url);
    request.setAttribute(QNetworkRequest::RedirectPolicyAttribute, QNetworkRequest::NoLessSafeRedirectPolicy);
    request.setTransferTimeout(30000);
    QNetworkReply* reply = manager->get(request);
    if (progress) QObject::connect(reply, &QNetworkReply::downloadProgress, owner, progress);
    QObject::connect(reply, &QNetworkReply::finished, owner, [reply, done, url, progress, receiver = QPointer<QObject>(owner)] {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
            const QString what = status > 0 ? QCoreApplication::translate("OnlineSearch", "%1 answered %2").arg(url.toString()).arg(status)
                                            : QCoreApplication::translate("OnlineSearch", "%1: %2").arg(url.toString(), reply->errorString());
            qCWarning(lcOnline, "%s", qPrintable(what));
            done({}, what, unreachable_error(reply->error(), status));
            return;
        }
        const auto bytes = reply->readAll();
        if (progress) progress(bytes.size(), bytes.size());
        if (receiver) done(bytes, {}, false);
    });
}

}  // namespace edi_app
