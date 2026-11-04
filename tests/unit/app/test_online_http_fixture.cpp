// SPDX-License-Identifier: BSD-3-Clause
// Replace only the per-search transport in the Qt test binary. All requests,
// callbacks and model updates still use the shipped OnlineSearch implementation.
#include "online_search.hpp"

#include <QCoreApplication>
#include <QEvent>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QQueue>
#include <QUrlQuery>
#include <QVariantMap>
#include <QTimer>
#include <QtQml/qqml.h>

#include <algorithm>
#include <cstring>

namespace {
struct NetworkSlot {
    using Member = QNetworkAccessManager* edi_app::OnlineSearch::*;
    friend Member onlineNetwork(NetworkSlot);
};

// Explicit instantiations are exempt from access checking. Keep this adapter
// limited to the transport slot so the app API need not expose test injection.
template<class Slot, typename Slot::Member member>
struct TestAccess {
    friend typename Slot::Member onlineNetwork(Slot) { return member; }
};
template struct TestAccess<NetworkSlot, &edi_app::OnlineSearch::network_>;

struct Response {
    int status;
    QByteArray body;
    int error = 0;
};

class ScriptedReply final : public QNetworkReply {
public:
    ScriptedReply(const QNetworkRequest& request, Response response, QObject* parent)
        : QNetworkReply(parent), body_(std::move(response.body)) {
        setRequest(request);
        setUrl(request.url());
        setAttribute(QNetworkRequest::HttpStatusCodeAttribute, response.status);
        open(QIODevice::ReadOnly);
        QTimer::singleShot(0, this, [this, status = response.status, error = response.error] {
            if (error)
                setError(static_cast<NetworkError>(error), QStringLiteral("fixture transport unavailable"));
            else if (status == 503)
                setError(ServiceUnavailableError, QStringLiteral("fixture service unavailable"));
            else if (status == 404)
                setError(ContentNotFoundError, QStringLiteral("fixture file absent"));
            else if (status != 200)
                setError(ProtocolFailure, QStringLiteral("unexpected fixture request"));
            setFinished(true);
            if (!body_.isEmpty()) emit readyRead();
            emit finished();
        });
    }

    void abort() override {}
    qint64 bytesAvailable() const override { return body_.size() + QNetworkReply::bytesAvailable(); }

private:
    qint64 readData(char* destination, qint64 capacity) override {
        if (body_.isEmpty()) return -1;
        const auto size = std::min(capacity, static_cast<qint64>(body_.size()));
        std::memcpy(destination, body_.constData(), static_cast<std::size_t>(size));
        body_.remove(0, size);
        return size;
    }
    QByteArray body_;
};

class ScriptedNetwork final : public QNetworkAccessManager {
public:
    using QNetworkAccessManager::QNetworkAccessManager;
    QQueue<Response> responses;
    QStringList requests;

protected:
    QNetworkReply* createRequest(Operation operation, const QNetworkRequest& request,
                                 QIODevice*) override {
        requests.append(request.url().toString());
        const auto response = operation == GetOperation && !responses.isEmpty()
            ? responses.dequeue() : Response{500, {}};
        return new ScriptedReply(request, response, this);
    }
};

class OnlineHttpFixture final : public QObject {
    Q_OBJECT
public:
    using QObject::QObject;

    Q_INVOKABLE bool attach(edi_app::OnlineSearch* search) {
        if (!search || search->busy()) return false;
        auto*& transport = search->*onlineNetwork(NetworkSlot{});
        if (transport) return transport == network_;
        network_ = new ScriptedNetwork(search);
        transport = network_;
        return true;
    }

    Q_INVOKABLE bool finishRemoval(QObject* removed) {
        const QPointer<QObject> original(removed);
        QCoreApplication::sendPostedEvents(nullptr, QEvent::DeferredDelete);
        return original.isNull();
    }

    Q_INVOKABLE void clear() {
        network_->requests.clear();
        network_->responses.clear();
    }

    Q_INVOKABLE void enqueue(int status, const QString& body) {
        network_->responses.enqueue({status, body.toUtf8()});
    }

    Q_INVOKABLE void enqueueError(int status, int error) {
        network_->responses.enqueue({status, {}, error});
    }

    Q_INVOKABLE QStringList requests() const { return network_->requests; }

    Q_INVOKABLE QVariantMap query(const QString& url) const {
        QVariantMap values;
        for (const auto& pair : QUrlQuery(QUrl(url)).queryItems(QUrl::FullyDecoded))
            values.insert(pair.first, pair.second);
        return values;
    }

private:
    QPointer<ScriptedNetwork> network_;
};
}

static void registerOnlineHttpFixture() {
    qmlRegisterSingletonType<OnlineHttpFixture>("EdiOnlineHttpFixture", 1, 0, "OnlineHttpFixture",
        [](QQmlEngine*, QJSEngine*) -> QObject* { return new OnlineHttpFixture; });
}
Q_COREAPP_STARTUP_FUNCTION(registerOnlineHttpFixture)

#include "test_online_http_fixture.moc"
