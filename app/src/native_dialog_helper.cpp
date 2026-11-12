// SPDX-License-Identifier: BSD-3-Clause
#include "native_dialog_helper.hpp"
#include <QApplication>
#include <QFileDialog>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTimer>
#include <cstdio>
#include <cstdlib>
#include <thread>
#ifdef Q_OS_WIN
#include <fcntl.h>
#include <io.h>
#endif

namespace edi_app {
namespace {
void send(const QJsonObject& object) {
    const auto bytes = QJsonDocument(object).toJson(QJsonDocument::Compact) + '\n';
    if (std::fwrite(bytes.constData(), 1, static_cast<std::size_t>(bytes.size()), stdout) != static_cast<std::size_t>(bytes.size()) || std::fflush(stdout) != 0)
        std::_Exit(2);
}
}
int native_dialog_helper_main(int argc, char** argv) {
#ifdef Q_OS_WIN
    _setmode(_fileno(stdin), _O_BINARY);
    _setmode(_fileno(stdout), _O_BINARY);
#endif
    char input[65536];
    if (!std::fgets(input, sizeof input, stdin)) return 2;
    const QByteArray bytes(input);
    if (!bytes.endsWith('\n')) return 2;
    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(bytes, &error);
    const auto request = document.object();
    const auto mode = request.value("mode").toInt(-1);
    if (error.error != QJsonParseError::NoError || !document.isObject() || request.value("schema").toInt() != 1 ||
        !request.value("directory").isBool() || mode < 0 || mode > 2 ||
        !request.value("nameFilters").isArray()) return 2;
    for (const auto& key : {"title", "acceptLabel", "defaultSuffix", "currentFolder", "selectedFile"})
        if (!request.value(key).isString()) return 2;
    QStringList filters;
    for (const auto& filter : request.value("nameFilters").toArray()) {
        if (!filter.isString()) return 2;
        filters.append(filter.toString());
    }
    for (const auto& key : {"currentFolder", "selectedFile"}) {
        const auto text = request.value(key).toString();
        if (!text.isEmpty() && !QUrl(text, QUrl::StrictMode).isLocalFile()) return 2;
    }
    // EOF also exits when the parent dies while AppKit is stuck constructing its panel.
    std::thread([] { while (std::getc(stdin) != EOF) {} std::_Exit(0); }).detach();
    QApplication app(argc, argv);
    app.setApplicationName(QStringLiteral("EasyDiffraction"));
    app.setOrganizationName(QStringLiteral("EasyScience"));
    app.setQuitOnLastWindowClosed(false);
    QFileDialog dialog;
    const bool directory = request.value("directory").toBool();
    dialog.setWindowTitle(request.value("title").toString());
    dialog.setAcceptMode(mode == 2 && !directory ? QFileDialog::AcceptSave : QFileDialog::AcceptOpen);
    dialog.setFileMode(directory ? QFileDialog::Directory : mode == 2 ? QFileDialog::AnyFile : mode == 1 ? QFileDialog::ExistingFiles : QFileDialog::ExistingFile);
    if (directory) dialog.setOption(QFileDialog::ShowDirsOnly);
    dialog.setSupportedSchemes({QStringLiteral("file")});
    dialog.setNameFilters(filters);
    dialog.setDefaultSuffix(request.value("defaultSuffix").toString());
    const auto folder = QUrl(request.value("currentFolder").toString());
    if (!folder.isEmpty()) dialog.setDirectoryUrl(folder);
    const auto selected = QUrl(request.value("selectedFile").toString());
    if (!selected.isEmpty()) {
        if (directory) dialog.setDirectoryUrl(selected); else dialog.selectUrl(selected);
    }
    const auto label = request.value("acceptLabel").toString();
    if (!label.isEmpty()) dialog.setLabelText(QFileDialog::Accept, label);
    QObject::connect(&dialog, &QDialog::accepted, &app, [&] {
        QJsonArray files;
        for (const auto& url : dialog.selectedUrls()) files.append(url.toString(QUrl::FullyEncoded));
        send({{"schema", 1}, {"event", "accepted"}, {"files", files}, {"currentFolder", dialog.directoryUrl().toString(QUrl::FullyEncoded)}});
        app.quit();
    });
    QObject::connect(&dialog, &QDialog::rejected, &app, [&] {
        send({{"schema", 1}, {"event", "rejected"}});
        app.quit();
    });
    QTimer::singleShot(0, &dialog, [&] {
        dialog.open();
        send({{"schema", 1}, {"event", "ready"}});
    });
    return app.exec();
}
} // namespace edi_app
