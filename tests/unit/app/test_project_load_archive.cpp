// SPDX-License-Identifier: BSD-3-Clause
#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QTemporaryDir>
#include <QUrl>
#include <QtQml/qqml.h>
#include "web_files.hpp"

class LoadArchiveProof : public QObject {
    Q_OBJECT
public:
    using QObject::QObject;
    Q_INVOKABLE QUrl unpack(const QString& fixture) {
        const QString root = QDir(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath())
                                 .absoluteFilePath("../../..");
        const QByteArray archive = edi_app::WebFiles::pack(root + "/" + fixture);
        QString error;
        const QString path = edi_app::WebFiles::unpack(archive, target(), error);
        return path.isEmpty() ? QUrl() : QUrl::fromLocalFile(path);
    }
    Q_INVOKABLE QString malformedArchiveError() {
        QString error;
        edi_app::WebFiles::unpack(QByteArray("invalid minimal archive"), target(), error);
        return error;
    }
private:
    QString target() {
        const QString path = directory_.path() + "/attempt-" + QString::number(++attempt_);
        QDir().mkpath(path);
        return path;
    }
    QTemporaryDir directory_;
    int attempt_ = 0;
};
static void register_load_archive() {
    qmlRegisterType<LoadArchiveProof>("LoadArchiveTests", 1, 0, "LoadArchiveProof");
}
Q_COREAPP_STARTUP_FUNCTION(register_load_archive)
#include "test_project_load_archive.moc"
