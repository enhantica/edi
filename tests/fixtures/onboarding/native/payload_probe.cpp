// SPDX-License-Identifier: BSD-3-Clause
#include <QCoreApplication>
#include <QFile>
#include <QJSEngine>
#include <QJSValue>
#include <QJsonDocument>
#include <QJsonObject>
#include <cstdio>

int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);
    if (argc != 2) return 2;
    QFile request_file(QString::fromLocal8Bit(argv[1]));
    if (!request_file.open(QIODevice::ReadOnly)) return 3;
    const auto input = QJsonDocument::fromJson(request_file.readAll()).object();
    QFile module(input["module"].toString());
    if (!module.open(QIODevice::ReadOnly)) return 4;
    QString source = QString::fromUtf8(module.readAll());
    if (source.startsWith(".pragma library")) source = source.mid(source.indexOf('\n') + 1);
    QJSEngine engine;
    auto evaluated = engine.evaluate(source, module.fileName());
    if (evaluated.isError()) { std::fprintf(stderr, "%s", qPrintable(evaluated.toString())); return 5; }
    const auto make = engine.globalObject().property("buildPayload");
    if (!make.isCallable()) return 6;
    // A feedback app object is JavaScript JSON, not Qt's wrapped QVariant sequences.
    // Parse the serialized JSON so nested arrays have their actual production shape.
    const auto arguments = engine.evaluate("(" + QString::fromUtf8(QJsonDocument(input).toJson(QJsonDocument::Compact)) + ")");
    const auto argument = [&](const char* name) { return arguments.property(name); };
    auto payload = make.call({argument("kind"), argument("text"), argument("include"), argument("app"),
                              argument("log"), argument("home"), argument("user")});
    if (payload.isError()) {
        QJsonObject result{{"error", payload.toString()}};
        const auto bytes = QJsonDocument(result).toJson(QJsonDocument::Compact);
        std::fwrite(bytes.constData(), 1, bytes.size(), stdout); return 0;
    }
    engine.globalObject().setProperty("responseStatus", input["status"].toInt(201));
    engine.evaluate("var requests = []; var completedStatus = null; "
                    "function transport(url, body, done) { requests.push({url:url, payload:body}); done(responseStatus); } "
                    "function completed(status) { completedStatus = status; }");
    const auto submit = engine.globalObject().property("submit");
    if (!submit.isCallable()) return 7;
    auto sent = submit.call({argument("endpoint"), payload, engine.globalObject().property("transport"),
                             engine.globalObject().property("completed")});
    QJsonObject result{{"payload", QJsonValue::fromVariant(payload.toVariant())},
                       {"requests", QJsonValue::fromVariant(engine.globalObject().property("requests").toVariant())},
                       {"status", QJsonValue::fromVariant(engine.globalObject().property("completedStatus").toVariant())}};
    if (sent.isError()) result["error"] = sent.toString();
    const auto bytes = QJsonDocument(result).toJson(QJsonDocument::Compact);
    std::fwrite(bytes.constData(), 1, bytes.size(), stdout);
    return 0;
}
