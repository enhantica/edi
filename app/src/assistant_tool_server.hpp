// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QByteArray>
#include <QJsonArray>
#include <QJsonObject>
#include <QJsonValue>
#include <QList>
#include <QObject>
#include <QPointer>
#include <QSet>
#include <QString>
#include "edi/assistant_limits.hpp"

class QLocalServer;
class QLocalSocket;

namespace edi_app {
/// edi's tools as an MCP server (ADR-0108 §3) for runtimes other than Codex. The runtime starts
/// `edi_assistant_guard mcp`, which connects here and copies newline-delimited JSON-RPC both ways.
/// The server holds no tool logic: a call is emitted as toolCall() and answered with reply().
class AssistantToolServer final : public QObject {
    Q_OBJECT
public:
    explicit AssistantToolServer(QObject* parent = nullptr);
    ~AssistantToolServer() override;

    /// Listens on a new random, owner-only local name with a new random key.
    bool listen();
    /// The local server name the bridge connects to; empty before listen().
    QString name() const;
    /// The key the bridge sends as its first line; empty before listen().
    QByteArray key() const;
    /// The stdio server entry for a runtime's MCP config:
    /// `{"command": guard, "args": ["mcp"], "env": {"EDI_ASSISTANT_TOOLS": …, "EDI_ASSISTANT_TOOLS_KEY": …}}`.
    QJsonObject mcpServerEntry(const QString& guardExecutable) const;

    /// The MCP tool list `tools/list` answers with (see assistant_native_mcp_tools()).
    void setTools(const QJsonArray& mcpTools);
    /// Accepts one connection, the first that sends the key, for this runtime process generation.
    /// Any earlier connection is closed.
    void bindGeneration(quint64 generation);
    /// The bound generation; meaningful while bound() is true.
    quint64 generation() const noexcept { return generation_; }
    bool bound() const noexcept { return bound_; }
    /// True while the bound generation's connection is open.
    bool isConnected() const noexcept;
    /// Closes the connection and drops any later input until the next bindGeneration().
    void retire();

    /// Answers a pending `tools/call` with the tool's outgoing JSON as text. False when the id is not pending.
    bool reply(const QJsonValue& requestId, bool success, const QByteArray& outgoingJson);
    /// Answers a pending `tools/call` as a tool error carrying the message. False when the id is not pending.
    bool refuse(const QJsonValue& requestId, const QString& message);

    /// The longest line read or written; a longer one closes the connection.
    static constexpr qsizetype lineBytes = static_cast<qsizetype>(edi::assistant::Limits::request_bytes);

signals:
    /// The bound generation's bridge sent the right key.
    void connected();
    /// The bound connection closed for a reason other than retire() or bindGeneration().
    void disconnected();
    /// The runtime called `tools/list` and was answered.
    void toolsListed();
    /// The runtime called a tool; answer with reply() or refuse().
    void toolCall(const QJsonValue& requestId, const QString& tool, const QJsonObject& arguments);
    /// The runtime cancelled a pending call; it must not be answered.
    void cancelled(const QJsonValue& requestId);

private:
    struct Pending {
        QPointer<QLocalSocket> socket;
        QByteArray buffer;
    };
    void accept();
    void readPending(QLocalSocket* socket);
    void readConnection();
    void dropPending(QLocalSocket* socket);
    void closeConnection(bool notify);
    void handle(const QJsonObject& message);
    bool send(const QJsonObject& message);
    bool sendResult(const QJsonValue& id, const QJsonObject& result);
    bool sendError(const QJsonValue& id, int code, const QString& message);
    bool answerCall(const QJsonValue& requestId, bool isError, const QString& text);

    QLocalServer* server_ = nullptr;
    QList<Pending> pending_;
    QPointer<QLocalSocket> connection_;
    QByteArray buffer_;
    QString name_;
    QByteArray key_;
    QJsonArray tools_;
    QSet<QString> toolNames_;
    QSet<QString> calls_;
    quint64 generation_ = 0;
    bool bound_ = false;
    bool used_ = false;
};
} // namespace edi_app
