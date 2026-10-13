// SPDX-License-Identifier: BSD-3-Clause
#include <QtQml/qqml.h>

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QTemporaryDir>
#include <QUrl>

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
    Q_INVOKABLE QUrl olderProject(const QString& fixture) {
        const QUrl copy = unpack(fixture);
        QFile analysis(copy.toLocalFile() + "/analysis/analysis.edi");
        if (!analysis.open(QIODevice::ReadOnly)) return {};
        QByteArray text = analysis.readAll();
        analysis.close();
        const auto header = text.indexOf("_fit_parameter.start_tied\n");
        if (header < 0) return {};
        const auto first = text.indexOf('\n', header) + 1;
        const auto end = text.indexOf(' ', first);
        if (end < first) return {};
        text.replace(first, end - first, "bank.background[0]");
        if (!analysis.open(QIODevice::WriteOnly | QIODevice::Truncate)) return {};
        if (analysis.write(text) != text.size()) return {};
        return copy;
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
