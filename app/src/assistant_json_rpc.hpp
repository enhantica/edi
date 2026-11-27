// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QHash>
#include <QJsonObject>
#include <QJsonValue>
#include <QObject>
#include <QPointer>
#include <QString>
#include "assistant_process.hpp"

namespace edi_app {

/// JSON-RPC 2.0 over one AssistantProcess (ADR-0108 §2), for runtimes such as Copilot's ACP. Requests carry numeric
/// ids; every incoming message must name `"jsonrpc": "2.0"`. A reply to no outstanding request, a duplicated server
/// request id or a malformed message fails the process. Outstanding ids belong to one process generation and are
/// dropped when it fails, retires or restarts. Construct and call on the owner thread.
class AssistantJsonRpc final : public QObject {
    Q_OBJECT
public:
    /// Speak over `process`; it outlives this object or this object stops sending.
    explicit AssistantJsonRpc(AssistantProcess& process, QObject* parent = nullptr);

    /// Send a request; returns its id (decimal), or empty when nothing was sent.
    QString request(const QString& method, const QJsonObject& params = {});
    /// Send a notification; false when nothing was sent.
    bool notify(const QString& method, const QJsonObject& params = {});
    /// Answer the server request `id` once. False, keeping the request open, when nothing was sent.
    bool respond(const QJsonValue& id, const QJsonValue& result);
    /// Answer the server request `id` once with an error.
    bool respondError(const QJsonValue& id, int code, const QString& message);
    /// True while the request `id` waits for its response.
    bool outstanding(const QString& id) const;

signals:
    /// The reply to `request`: `error` is empty on success, else {code, message[, data]} and `result` is undefined.
    void response(const QString& id, const QJsonValue& result, const QJsonObject& error);
    void notification(const QString& method, const QJsonObject& params);
    /// A request from the runtime; answer it with `respond` or `respondError`.
    void serverRequest(const QJsonValue& id, const QString& method, const QJsonObject& params);

private:
    void receive(const QJsonObject& message);
    void sync();
    void clear();
    bool answer(const QJsonValue& id, const QJsonObject& envelope);
    void refuse(const char* explanation);

    QPointer<AssistantProcess> process_;
    quint64 generation_ = 0, next_id_ = 0;
    QHash<QString, QString> pending_;  // id -> method
    QHash<QString, QJsonValue> server_requests_;  // id key -> the id as sent
};

}  // namespace edi_app
