// SPDX-License-Identifier: BSD-3-Clause
#include <QCoreApplication>
#include <QFile>
#include <QTimer>
#include "codex_agent.hpp"
int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);
    const auto args = app.arguments();
    if (args.size() < 4) return 2;
    edi_app::CodexAgent agent;
    QObject::connect(&agent, &edi_app::CodexAgent::started, &app, [&] { agent.request("initialize", {}); });
    QObject::connect(&agent, &edi_app::CodexAgent::response, &app, [&](const QString&, const QString& method, const QJsonObject&) {
        if (method != "initialize") return;
        auto* process = agent.findChild<QProcess*>();
        if (!process || process->processId() <= 0) { app.exit(5); return; }
        QFile pids(qEnvironmentVariable("EDI_LIFETIME_PID_FILE"));
        if (!pids.open(QIODevice::Append)) { app.exit(6); return; }
        pids.write("guard " + QByteArray::number(process->processId()) + "\n");
        pids.close();
        QFile ready(args.at(3));
        if (!ready.open(QIODevice::WriteOnly) || ready.write("connected") != 9) { app.exit(3); return; }
        ready.close();
        if (args.contains("--retire")) QTimer::singleShot(100, &app, [&] { agent.retire(); QTimer::singleShot(500, &app, &QCoreApplication::quit); });
    });
    if (!agent.start(args.at(1), args.at(2))) return 4;
    return app.exec();
}
