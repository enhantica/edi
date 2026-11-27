// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_json_rpc.hpp"
#include <cmath>

namespace edi_app {
namespace {
constexpr double kSafeInteger = 9007199254740991.0;

// The same id rule as the Codex transport: a short nonempty string or a safe integer.
QString idKey(const QJsonValue& value) {
    using Limits = edi::assistant::Limits;
    if (value.isString() && !value.toString().isEmpty() &&
        value.toString().toUtf8().size() <= static_cast<qsizetype>(Limits::id_bytes))
        return QStringLiteral("s:") + value.toString();
    if (value.isDouble()) {
        const auto number = value.toDouble();
        if (std::isfinite(number) && std::floor(number) == number && std::abs(number) <= kSafeInteger)
            return QStringLiteral("n:") + QString::number(number, 'f', 0);
    }
    return {};
}

// Our own request ids are positive safe integers; a reply naming anything else matches none of them.
QString requestId(const QJsonValue& value) {
    if (!value.isDouble()) return {};
    const auto number = value.toDouble();
    if (!std::isfinite(number) || std::floor(number) != number || number < 1 || number > kSafeInteger) return {};
    return QString::number(number, 'f', 0);
}
}  // namespace

AssistantJsonRpc::AssistantJsonRpc(AssistantProcess& process, QObject* parent)
    : QObject(parent), process_(&process), generation_(process.generation()) {
    connect(&process, &AssistantProcess::record, this, &AssistantJsonRpc::receive);
    connect(&process, &AssistantProcess::failed, this, &AssistantJsonRpc::clear);
}

void AssistantJsonRpc::clear() {
    pending_.clear();
    server_requests_.clear();
}

void AssistantJsonRpc::sync() {
    if (!process_ || process_->generation() == generation_) return;
    generation_ = process_->generation();
    clear();
}

bool AssistantJsonRpc::outstanding(const QString& id) const {
    return process_ && process_->generation() == generation_ && pending_.contains(id);
}

QString AssistantJsonRpc::request(const QString& method, const QJsonObject& params) {
    sync();
    if (!process_ || method.isEmpty() || static_cast<double>(next_id_) >= kSafeInteger) return {};
    const auto number = ++next_id_;
    const auto id = QString::number(number);
    pending_.insert(id, method);
    const QJsonObject envelope{{QStringLiteral("jsonrpc"), QStringLiteral("2.0")},
                               {QStringLiteral("id"), static_cast<qint64>(number)},
                               {QStringLiteral("method"), method},
                               {QStringLiteral("params"), params}};
    // A write cannot read, so no reply can arrive before the id is recorded.
    if (!process_ || !process_->write(envelope)) {
        pending_.remove(id);
        return {};
    }
    return id;
}

bool AssistantJsonRpc::notify(const QString& method, const QJsonObject& params) {
    sync();
    if (!process_ || method.isEmpty()) return false;
    return process_->write({{QStringLiteral("jsonrpc"), QStringLiteral("2.0")},
                            {QStringLiteral("method"), method},
                            {QStringLiteral("params"), params}});
}

bool AssistantJsonRpc::answer(const QJsonValue& id, const QJsonObject& envelope) {
    sync();
    const auto key = idKey(id);
    const auto found = server_requests_.constFind(key);
    if (!process_ || key.isEmpty() || found == server_requests_.cend()) return false;
    auto message = envelope;
    message.insert(QStringLiteral("jsonrpc"), QStringLiteral("2.0"));
    message.insert(QStringLiteral("id"), found.value());
    if (!process_ || !process_->write(message)) return false;
    server_requests_.remove(key);
    return true;
}

bool AssistantJsonRpc::respond(const QJsonValue& id, const QJsonValue& result) {
    return answer(id, {{QStringLiteral("result"), result}});
}

bool AssistantJsonRpc::respondError(const QJsonValue& id, int code, const QString& message) {
    return answer(id, {{QStringLiteral("error"),
                        QJsonObject{{QStringLiteral("code"), code}, {QStringLiteral("message"), message}}}});
}

void AssistantJsonRpc::refuse(const char* explanation) {
    clear();
    if (process_) process_->fail(tr(explanation));
}

void AssistantJsonRpc::receive(const QJsonObject& message) {
    sync();
    if (message.value(QStringLiteral("jsonrpc")) != QStringLiteral("2.0")) {
        refuse("The assistant sent a message that is not JSON-RPC 2.0.");
        return;
    }
    if (message.contains(QStringLiteral("method"))) {
        const auto method = message.value(QStringLiteral("method"));
        const auto params = message.value(QStringLiteral("params"));
        if (!method.isString() || method.toString().isEmpty() ||
            (message.contains(QStringLiteral("params")) && !params.isObject())) {
            refuse("The assistant sent a request or notification with an invalid shape.");
            return;
        }
        if (!message.contains(QStringLiteral("id"))) {
            emit notification(method.toString(), params.toObject());
            return;
        }
        const auto id = message.value(QStringLiteral("id"));
        const auto key = idKey(id);
        if (key.isEmpty() || server_requests_.contains(key)) {
            refuse("The assistant request identity is invalid or duplicated.");
            return;
        }
        server_requests_.insert(key, id);
        emit serverRequest(id, method.toString(), params.toObject());
        return;
    }
    const auto id = requestId(message.value(QStringLiteral("id")));
    const bool hasResult = message.contains(QStringLiteral("result"));
    const bool hasError = message.contains(QStringLiteral("error"));
    if (id.isEmpty() || !pending_.contains(id) || hasResult == hasError) {
        refuse("The assistant reply does not match an outstanding request.");
        return;
    }
    QJsonObject error;
    if (hasError) {
        const auto value = message.value(QStringLiteral("error"));
        const auto code = value.toObject().value(QStringLiteral("code"));
        if (!value.isObject() || !code.isDouble() || std::floor(code.toDouble()) != code.toDouble() ||
            !value.toObject().value(QStringLiteral("message")).isString()) {
            refuse("The assistant reply has an invalid error.");
            return;
        }
        error = value.toObject();
    }
    pending_.remove(id);
    emit response(id, hasResult ? message.value(QStringLiteral("result")) : QJsonValue(QJsonValue::Undefined),
                  error);
}

}  // namespace edi_app
