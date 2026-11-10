// SPDX-License-Identifier: BSD-3-Clause
#include "run_log.hpp"
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QLockFile>
#include <QQmlComponent>
#include <QQmlEngine>
#include <cstdio>
#include <cstdlib>

int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);
    if (argc != 2) return 2;
    QFile request_file(QString::fromLocal8Bit(argv[1]));
    if (!request_file.open(QIODevice::ReadOnly)) return 3;
    const auto request = QJsonDocument::fromJson(request_file.readAll()).object();
    QDateTime now = QDateTime::fromString(request["time"].toString(), Qt::ISODateWithMs);
    if (!now.isValid()) return 4;
    edi_app::RunLog::Options options;
    options.directory = request["directory"].toString();
    options.clock = [&] { return now; };
    options.terminal = request["operation"].toString() == "thresholds";
    if (request.contains("max_bytes")) options.maxBytes = request["max_bytes"].toInteger();
    const QString operation = request["operation"].toString();
    const auto emitLine = [](const QJsonObject& value) {
        const auto bytes = QJsonDocument(value).toJson(QJsonDocument::Compact);
        std::fwrite(bytes.constData(), 1, bytes.size(), stdout);
        std::fputc('\n', stdout);
        std::fflush(stdout);
    };
    if (operation == "reserve-slot") {
        QDir().mkpath(options.directory);
        const auto path = QDir(options.directory).filePath("session-20260718-094126.log");
        QLockFile owner(path.left(path.size() - 4) + ".running");
        owner.setStaleLockTime(0);
        if (!owner.tryLock(0)) return 7;
        emitLine({{"reserved", path}, {"pid", QCoreApplication::applicationPid()}});
        if (std::getchar() == EOF) return 8;
        QFile file(path);
        if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate)) return 9;
        file.write("first-run-owned-bytes\n");
        file.flush();
        emitLine({{"written", true}});
        std::getchar();
        return 0;
    }
    if (operation == "coordinated") {
        emitLine({{"ready", true}, {"pid", QCoreApplication::applicationPid()}});
        if (std::getchar() == EOF) return 8;
    }
    edi_app::RunLog log(options);
    const QString default_level = log.level();
    // Source/clock/privacy/growth witnesses request Info explicitly; they do not pin the default.
    if (request.contains("level")) log.setLevel(request["level"].toString());
    else if (operation == "records" || operation == "bounded" || operation == "hold" || operation == "coordinated")
        log.setLevel("Info");
    edi_app::RunLog::Header header;
    const auto supplied = request["header"].toObject();
    for (auto it = supplied.begin(); it != supplied.end(); ++it)
        header.append({it.key(), it.value().toString()});
    if (!log.start(header)) return 5;
    QJsonObject result{{"path", log.path()}, {"crashed", log.crashedLog()},
                       {"crash_text", log.crashedLogText()}, {"level", log.level()}, {"default_level", default_level}};
    if (operation == "thresholds") {
        edi_app::RunLog::install(&log);
        QMessageLogger("/fixture/core.cpp", 21, "probe", "crysta").debug("level-debug-sentinel");
        QMessageLogger("/fixture/core.cpp", 22, "probe", "crysta").info("crysta.fit.su_undefined: level-info-sentinel");
        QMessageLogger("/fixture/core.cpp", 23, "probe", "crysta").warning("level-warning-sentinel");
        QMessageLogger("/fixture/core.cpp", 24, "probe", "crysta").critical("level-error-sentinel");
        edi_app::RunLog::install(nullptr);
    }
    if (request["operation"].toString() == "records") {
        edi_app::RunLog::install(&log);
        now = now.addMSecs(137);
        QMessageLogger("/fixture/native.cpp", 41, "probe", "acceptance").info("cpp-sentinel");
        now = now.addMSecs(2100);
        QQmlEngine engine;
        QQmlComponent component(&engine);
        component.setData("import QtQml\nQtObject { Component.onCompleted: console.info('qml-sentinel') }", QUrl("qrc:/onboarding.qml"));
        QObject* object = component.create();
        if (!object) return 6;
        delete object;
        now = now.addMSecs(71);
        QMessageLogger("/fixture/engine.cpp", 53, "probe", "crysta").warning("engine-sentinel");
        QMessageLogger("/fixture/native.cpp", 54, "probe", "acceptance").debug("hidden-debug-sentinel");
        now = now.addMSecs(29);
        QMessageLogger("/fixture/native.cpp", 55, "probe", "acceptance").info("first-line\nsecond-line");
        edi_app::RunLog::install(nullptr);
    }
    if (operation == "columns") {
        log.setLevel("Debug");
        edi_app::RunLog::install(&log);
        const auto advance = [&] { now = now.addMSecs(request["milliseconds"].toInteger()); };
        advance();
        QMessageLogger("/fixture/native.cpp", 41, "probe", "acceptance").debug("column-debug");
        advance();
        QMessageLogger("qrc:/ColumnWitness.qml", 19, "probe", "qml").info("column-info");
        advance();
        QMessageLogger("/fixture/engine.cpp", 53, "probe", "crysta").warning("column-warning");
        advance();
        QMessageLogger("/fixture/native.cpp", 55, "probe", "acceptance").critical("column-critical");
        edi_app::RunLog::install(nullptr);
    }
    if (request["operation"].toString() == "bounded") {
        for (int i = 0; i < 100; ++i)
            log.write(QtInfoMsg, QMessageLogContext("/fixture/native.cpp", 90, "probe", "acceptance"), QString(request["message_size"].toInt(200), QChar(0x03bb)));
    }
    QJsonArray markers;
    for (const auto& name : QDir(options.directory).entryList({"session-*.running"}, QDir::Files))
        markers.append(name);
    result["running_markers"] = markers;
    if (operation == "hold" || operation == "coordinated") {
        log.write(QtInfoMsg, QMessageLogContext("owner.cpp", 17, "probe", "acceptance"), request["sentinel"].toString());
        QLockFile marker(log.path().left(log.path().size() - 4) + ".running");
        qint64 ownerPid = -1;
        QString host, application;
        result["owned_marker"] = marker.getLockInfo(&ownerPid, &host, &application);
        result["owner_pid"] = ownerPid;
        result["pid"] = QCoreApplication::applicationPid();
        emitLine(result);
        std::getchar();
        log.finish();
        return 0;
    }
    if (request["operation"].toString() == "crash") {
        log.write(QtWarningMsg, QMessageLogContext("/fixture/crash.cpp", 11, "probe", "acceptance"), "retained-crash-sentinel");
        const auto bytes = QJsonDocument(result).toJson(QJsonDocument::Compact);
        std::fwrite(bytes.constData(), 1, bytes.size(), stdout);
        std::fflush(stdout);
        std::_Exit(0);
    }
    log.finish();
    const auto bytes = QJsonDocument(result).toJson(QJsonDocument::Compact);
    std::fwrite(bytes.constData(), 1, bytes.size(), stdout);
    return 0;
}
