// SPDX-License-Identifier: BSD-3-Clause
#include <QtQml/qqml.h>

#include <QCoreApplication>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QObject>
#include <QTemporaryDir>
#include <QUrl>

#include "web_files.hpp"

class WebArchivePermissionProof : public QObject {
    Q_OBJECT
   public:
    using QObject::QObject;
    Q_INVOKABLE bool writeReference(const QUrl& input) {
        const QString root = qEnvironmentVariable("EDI_ACCEPTANCE_REFERENCE", temporary_.path());
        return !root.isEmpty() &&
               write(input, QUrl::fromLocalFile(QDir(root).filePath(QStringLiteral("archives"))));
    }
    Q_INVOKABLE bool write(const QUrl& input, const QUrl& output) {
        const QDir root(input.toLocalFile());
        const QString destination = output.toLocalFile();
        if (!QDir().mkpath(destination)) return false;
        QList<QPair<QString, QByteArray>> files;
        QStringList paths;
        QDirIterator iterator(root.path(), QDir::Files | QDir::Hidden,
                              QDirIterator::Subdirectories);
        while (iterator.hasNext()) paths.append(iterator.next());
        paths.sort();
        for (const QString& path : paths) {
            QFile file(path);
            if (!file.open(QIODevice::ReadOnly)) return false;
            files.append({root.relativeFilePath(path), file.readAll()});
        }
        const auto store = [&](const QString& name, const QByteArray& bytes) {
            QFile file(QDir(destination).filePath(name));
            return !bytes.isEmpty() && file.open(QIODevice::WriteOnly) &&
                   file.write(bytes) == bytes.size();
        };
        return store(QStringLiteral("pack.zip"), edi_app::WebFiles::pack(root.path())) &&
               store(QStringLiteral("packFiles.zip"), edi_app::WebFiles::packFiles(files));
    }

   private:
    QTemporaryDir temporary_;
};

#ifdef EDI_WEB_ARCHIVE_PROBE_MAIN
int main(int argc, char** argv) {
    QCoreApplication application(argc, argv);
    if (argc != 3) return 2;
    WebArchivePermissionProof proof;
    return proof.write(QUrl::fromLocalFile(QString::fromLocal8Bit(argv[1])),
                       QUrl::fromLocalFile(QString::fromLocal8Bit(argv[2])))
               ? 0
               : 1;
}
#else
static void register_web_archive_permissions() {
    qmlRegisterType<WebArchivePermissionProof>("WebArchivePermissionTests", 1, 0,
                                               "WebArchivePermissionProof");
}
Q_COREAPP_STARTUP_FUNCTION(register_web_archive_permissions)
#endif
#include "test_web_archive_permissions.moc"
