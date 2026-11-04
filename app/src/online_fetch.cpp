// SPDX-License-Identifier: BSD-3-Clause
#include "online_fetch.hpp"

#include <QCoreApplication>
#include <QCryptographicHash>
#include <QFile>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QTimer>

namespace edi_app {
namespace {

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

void fetch_url(QObject* owner, QNetworkAccessManager*& manager, const QUrl& url, FetchDone done) {
    if (url.isLocalFile() || url.scheme().isEmpty()) {
        const QString path = url.isLocalFile() ? url.toLocalFile() : url.toString();
        QTimer::singleShot(0, owner, [path, done] {
            QFile file(path);
            if (!file.exists()) {
                done({}, QCoreApplication::translate("OnlineSearch", "%1 does not exist").arg(path), true);
                return;
            }
            if (!file.open(QIODevice::ReadOnly)) {
                done({}, QCoreApplication::translate("OnlineSearch", "%1 cannot be read").arg(path), false);
                return;
            }
            done(file.readAll(), {}, false);
        });
        return;
    }
    if (manager == nullptr) manager = new QNetworkAccessManager(owner);
    QNetworkRequest request(url);
    request.setAttribute(QNetworkRequest::RedirectPolicyAttribute, QNetworkRequest::NoLessSafeRedirectPolicy);
    request.setTransferTimeout(30000);
    QNetworkReply* reply = manager->get(request);
    QObject::connect(reply, &QNetworkReply::finished, owner, [reply, done, url] {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
            const QString what = status > 0 ? QCoreApplication::translate("OnlineSearch", "%1 answered %2").arg(url.toString()).arg(status)
                                            : reply->errorString();
            done({}, what, unreachable_error(reply->error(), status));
            return;
        }
        done(reply->readAll(), {}, false);
    });
}

}  // namespace edi_app
