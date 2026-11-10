// SPDX-License-Identifier: BSD-3-Clause
#include <QCoreApplication>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QTimer>
#include <iostream>
#include <thread>
int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);
    const auto args = app.arguments();
    const auto role = args.contains("--grandchild") ? "grandchild" : args.contains("--child") ? "child" : "server";
    QFile pids(qEnvironmentVariable("EDI_LIFETIME_PID_FILE"));
    if (!pids.open(QIODevice::Append)) return 2;
    pids.write(QByteArray(role) + " " + QByteArray::number(app.applicationPid()) + "\n");
    pids.close();
    QProcess child;
    if (QByteArray(role) != "grandchild")
        child.start(app.applicationFilePath(), {QByteArray(role) == "server" ? "--child" : "--grandchild"});
    if (QByteArray(role) == "server") std::thread([] {
        for (std::string line; std::getline(std::cin, line);) {
            const auto request = QJsonDocument::fromJson(QByteArray::fromStdString(line)).object();
            if (!request.contains("id")) continue;
            const QJsonObject response{{"id", request.value("id")}, {"result", QJsonObject{{"userAgent", "recorded"}}}};
            std::cout << QJsonDocument(response).toJson(QJsonDocument::Compact).toStdString() << std::endl;
        }
    }).detach();
    QTimer stream;
    if (QByteArray(role) == "server" && qEnvironmentVariableIsSet("EDI_LIFETIME_STREAM")) {
        QObject::connect(&stream, &QTimer::timeout, &app, [] {
            std::cout << "{\"method\":\"recorded/heartbeat\",\"params\":{}}" << std::endl;
        });
        stream.start(1);
    }
    return app.exec();
}
