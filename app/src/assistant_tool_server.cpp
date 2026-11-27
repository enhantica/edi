// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_tool_server.hpp"
#include <QCoreApplication>
#include <QJsonDocument>
#include <QLocalServer>
#include <QLocalSocket>
#include <QRandomGenerator>
#include <QTimer>
#include <algorithm>
#include <array>
#include <utility>

namespace edi_app {
namespace {
constexpr qsizetype keyLineBytes = 256;
constexpr qsizetype maxPending = 4;
constexpr int keyWaitMs = 10000;

// The MCP revisions edi answers in; anything else gets the newest.
QString negotiatedVersion(const QString& requested) {
    for (const char* version : {"2025-03-26", "2025-06-18"})
        if (requested == QLatin1StringView(version)) return requested;
    return QStringLiteral("2025-11-25");
}

template <std::size_t Words>
QByteArray randomHex() {
    std::array<quint32, Words> buffer{};
    QRandomGenerator::system()->generate(buffer.begin(), buffer.end());
    return QByteArray(reinterpret_cast<const char*>(buffer.data()), static_cast<qsizetype>(sizeof(buffer))).toHex();
}

// Pending calls are keyed by id type and value, so the string "1" and the number 1 stay apart.
QString idKey(const QJsonValue& id) {
    if (id.isString()) return QLatin1Char('s') + id.toString();
    if (id.isDouble()) return QLatin1Char('n') + QString::number(id.toDouble(), 'g', 17);
    return {};
}

bool sameKey(const QByteArray& given, const QByteArray& expected) {
    if (given.size() != expected.size() || expected.isEmpty()) return false;
    unsigned char difference = 0;
    for (qsizetype i = 0; i < given.size(); ++i) difference |= static_cast<unsigned char>(given[i] ^ expected[i]);
    return difference == 0;
}

void discard(QLocalSocket* socket, QObject* receiver) {
    if (!socket) return;
    socket->disconnect(receiver);
    socket->abort();
    socket->deleteLater();
}
} // namespace

AssistantToolServer::AssistantToolServer(QObject* parent) : QObject(parent) {}

AssistantToolServer::~AssistantToolServer() {
    retire();
    if (server_) server_->disconnect(this);
}

bool AssistantToolServer::listen() {
    retire();
    if (server_) {
        server_->disconnect(this);
        server_->close();
        delete server_;
    }
    server_ = new QLocalServer(this);
    server_->setSocketOptions(QLocalServer::UserAccessOption);
    connect(server_, &QLocalServer::newConnection, this, &AssistantToolServer::accept);
    name_ = QStringLiteral("edi-tools-") + QString::fromLatin1(randomHex<4>());
    key_ = randomHex<8>();
    if (server_->listen(name_)) return true;
    name_.clear();
    key_.clear();
    return false;
}

QString AssistantToolServer::name() const { return name_; }

QByteArray AssistantToolServer::key() const { return key_; }

QJsonObject AssistantToolServer::mcpServerEntry(const QString& guardExecutable) const {
    return {{"command", guardExecutable},
            {"args", QJsonArray{"mcp"}},
            {"env", QJsonObject{{"EDI_ASSISTANT_TOOLS", name_}, {"EDI_ASSISTANT_TOOLS_KEY", QString::fromLatin1(key_)}}}};
}

void AssistantToolServer::setTools(const QJsonArray& mcpTools) {
    tools_ = mcpTools;
    toolNames_.clear();
    for (const auto& tool : mcpTools) toolNames_.insert(tool.toObject().value("name").toString());
}

void AssistantToolServer::bindGeneration(quint64 generation) {
    retire();
    generation_ = generation;
    bound_ = true;
    used_ = false;
}

bool AssistantToolServer::isConnected() const noexcept { return connection_ && connection_->state() == QLocalSocket::ConnectedState; }

void AssistantToolServer::retire() {
    closeConnection(false);
    for (const auto& pending : std::as_const(pending_)) discard(pending.socket, this);
    pending_.clear();
    bound_ = false;
}

bool AssistantToolServer::reply(const QJsonValue& requestId, bool success, const QByteArray& outgoingJson) {
    return answerCall(requestId, !success, QString::fromUtf8(outgoingJson));
}

bool AssistantToolServer::refuse(const QJsonValue& requestId, const QString& message) {
    return answerCall(requestId, true, message);
}

void AssistantToolServer::accept() {
    while (QLocalSocket* socket = server_->nextPendingConnection()) {
        if (!bound_ || used_ || pending_.size() >= maxPending) {
            discard(socket, this);
            continue;
        }
        pending_.append({socket, {}});
        connect(socket, &QLocalSocket::readyRead, this, [this, socket] { readPending(socket); });
        connect(socket, &QLocalSocket::disconnected, this, [this, socket] { dropPending(socket); });
        QTimer::singleShot(keyWaitMs, socket, [this, socket] { dropPending(socket); });
        readPending(socket);
    }
}

void AssistantToolServer::readPending(QLocalSocket* socket) {
    const auto found = std::find_if(pending_.begin(), pending_.end(), [socket](const Pending& p) { return p.socket == socket; });
    if (found == pending_.end()) return;
    found->buffer.append(socket->readAll());
    const auto end = found->buffer.indexOf('\n');
    if (end < 0) {
        if (found->buffer.size() > keyLineBytes) dropPending(socket);
        return;
    }
    QByteArray line = found->buffer.left(end);
    if (line.endsWith('\r')) line.chop(1);
    const QByteArray rest = found->buffer.mid(end + 1);
    pending_.erase(found);
    if (!bound_ || used_ || !sameKey(line, key_)) {
        discard(socket, this);
        return;
    }
    used_ = true;
    for (const auto& other : std::as_const(pending_)) discard(other.socket, this);
    pending_.clear();
    socket->disconnect(this);
    connection_ = socket;
    buffer_ = rest;
    connect(socket, &QLocalSocket::readyRead, this, &AssistantToolServer::readConnection);
    connect(socket, &QLocalSocket::disconnected, this, [this, socket] {
        if (connection_ == socket) closeConnection(true);
    });
    emit connected();
    if (connection_ == socket) readConnection();
}

void AssistantToolServer::dropPending(QLocalSocket* socket) {
    const auto found = std::find_if(pending_.begin(), pending_.end(), [socket](const Pending& p) { return p.socket == socket; });
    if (found == pending_.end()) return;
    pending_.erase(found);
    discard(socket, this);
}

void AssistantToolServer::readConnection() {
    const QPointer<QLocalSocket> socket = connection_;
    if (!socket) return;
    buffer_.append(socket->readAll());
    qsizetype start = 0;
    for (;;) {
        const auto end = buffer_.indexOf('\n', start);
        if (end < 0) break;
        QByteArray line = buffer_.mid(start, end - start);
        start = end + 1;
        if (line.endsWith('\r')) line.chop(1);
        if (line.size() > lineBytes) {
            closeConnection(true);
            return;
        }
        if (line.trimmed().isEmpty()) continue;
        QJsonParseError error{};
        const auto document = QJsonDocument::fromJson(line, &error);
        if (error.error != QJsonParseError::NoError || !document.isObject()) {
            closeConnection(true);
            return;
        }
        handle(document.object());
        // A handler may have retired or rebound the server.
        if (!socket || connection_ != socket) return;
    }
    buffer_.remove(0, start);
    if (buffer_.size() > lineBytes) closeConnection(true);
}

void AssistantToolServer::closeConnection(bool notify) {
    calls_.clear();
    buffer_.clear();
    QLocalSocket* socket = connection_.data();
    connection_ = nullptr;
    if (!socket) return;
    discard(socket, this);
    if (notify) emit disconnected();
}

void AssistantToolServer::handle(const QJsonObject& message) {
    const auto method = message.value("method");
    // Responses would answer requests this server never sends.
    if (!method.isString()) return;
    const auto name = method.toString();
    const auto params = message.value("params").toObject();
    if (!message.contains("id")) {
        if (name == QLatin1StringView("notifications/cancelled")) {
            const auto requestId = params.value("requestId");
            if (calls_.remove(idKey(requestId))) emit cancelled(requestId);
        }
        return;
    }
    const auto id = message.value("id");
    if (idKey(id).isEmpty()) {
        sendError(QJsonValue::Null, -32600, QStringLiteral("Invalid request id"));
        return;
    }
    if (name == QLatin1StringView("initialize")) {
        const auto requested = params.value("protocolVersion").toString();
        auto version = QCoreApplication::applicationVersion();
        if (version.isEmpty()) version = QStringLiteral("0");
        sendResult(id, {{"protocolVersion", negotiatedVersion(requested)},
                        {"capabilities", QJsonObject{{"tools", QJsonObject{{"listChanged", false}}}}},
                        {"serverInfo", QJsonObject{{"name", "edi"}, {"version", version}}}});
    } else if (name == QLatin1StringView("ping")) {
        sendResult(id, {});
    } else if (name == QLatin1StringView("tools/list")) {
        if (sendResult(id, {{"tools", tools_}})) emit toolsListed();
    } else if (name == QLatin1StringView("tools/call")) {
        const auto tool = params.value("name").toString();
        const auto arguments = params.value("arguments");
        if (!toolNames_.contains(tool)) {
            sendError(id, -32602, QStringLiteral("Unknown tool: %1").arg(tool));
        } else if (!arguments.isUndefined() && !arguments.isNull() && !arguments.isObject()) {
            sendError(id, -32602, QStringLiteral("Tool arguments must be an object"));
        } else if (calls_.contains(idKey(id))) {
            sendError(id, -32600, QStringLiteral("Request id is already in use"));
        } else {
            calls_.insert(idKey(id));
            emit toolCall(id, tool, arguments.toObject());
        }
    } else {
        sendError(id, -32601, QStringLiteral("Method not found"));
    }
}

bool AssistantToolServer::send(const QJsonObject& message) {
    if (!connection_) return false;
    QByteArray bytes = QJsonDocument(message).toJson(QJsonDocument::Compact);
    if (bytes.size() > lineBytes) return false;
    bytes.append('\n');
    return connection_->write(bytes) == bytes.size();
}

bool AssistantToolServer::sendResult(const QJsonValue& id, const QJsonObject& result) {
    return send({{"jsonrpc", "2.0"}, {"id", id}, {"result", result}});
}

bool AssistantToolServer::sendError(const QJsonValue& id, int code, const QString& message) {
    return send({{"jsonrpc", "2.0"}, {"id", id}, {"error", QJsonObject{{"code", code}, {"message", message}}}});
}

bool AssistantToolServer::answerCall(const QJsonValue& requestId, bool isError, const QString& text) {
    if (!connection_ || !calls_.remove(idKey(requestId))) return false;
    const auto result = [](bool error, const QString& content) {
        return QJsonObject{{"content", QJsonArray{QJsonObject{{"type", "text"}, {"text", content}}}}, {"isError", error}};
    };
    if (sendResult(requestId, result(isError, text))) return true;
    // A reply too long for one line still ends the call, as an error.
    return sendResult(requestId, result(true, QStringLiteral("The reply was too large to send.")));
}
} // namespace edi_app
