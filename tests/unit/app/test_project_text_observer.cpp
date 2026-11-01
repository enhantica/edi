#include <QtQml/qqml.h>

#include <QCoreApplication>
#include <QDataStream>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QProcess>
#include <QQuickTextDocument>
#include <QStandardPaths>
#include <QTemporaryDir>
#include <QTextBlock>
#include <QTextDocument>
#include <QTextLayout>
#include <QUrl>
#include <QVariantList>

class ProjectTextProof : public QObject {
    Q_OBJECT
   public:
    using QObject::QObject;
    ~ProjectTextProof() override {
        QFile::setPermissions(directory_.path() + "/classic.zip", QFile::ReadOwner | QFile::WriteOwner);
    }
    Q_INVOKABLE QVariantMap dictionary() const {
        const QDir root(QDir(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath())
                            .absoluteFilePath("../../.."));
        const QString source = qEnvironmentVariable("CRYSTA_CONSUMER_SRC", root.filePath("build/crysta-src"));
        QString python = QStandardPaths::findExecutable("python3");
        if (python.isEmpty()) python = QStandardPaths::findExecutable("python");
        if (python.isEmpty()) return {};
        QProcess process;
        process.start(python, {root.filePath("tests/fixtures/project_text/dictionary_reference.py"),
                              source + "/data/dictionary/parameters.yaml"});
        if (!process.waitForFinished(5000) || process.exitCode() != 0) return {};
        return QJsonDocument::fromJson(process.readAllStandardOutput()).toVariant().toMap();
    }
    Q_INVOKABLE QUrl project() {
        const QDir source(QDir(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath())
                              .absoluteFilePath("../../fixtures/project_text/project"));
        const QString destination = directory_.path() + "/project";
        if (!QDir(destination).exists()) {
            QDirIterator files(source.absolutePath(), QDir::Files, QDirIterator::Subdirectories);
            while (files.hasNext()) {
                const QString from = files.next();
                const QString to = destination + "/" + source.relativeFilePath(from);
                if (!QDir().mkpath(QFileInfo(to).absolutePath()) || !QFile::copy(from, to)) return {};
            }
        }
        return QUrl::fromLocalFile(destination);
    }
    Q_INVOKABLE QString structureText() {
        QFile file(project().toLocalFile() + "/structures/structure.edi");
        return file.open(QIODevice::ReadOnly) ? QString::fromUtf8(file.readAll()) : QString();
    }
    Q_INVOKABLE QVariantList formats(QObject* editor) const {
        const auto document = qvariant_cast<QQuickTextDocument*>(editor->property("textDocument"));
        if (!document || !document->textDocument()) return {};
        QVariantList result;
        for (auto block = document->textDocument()->begin(); block.isValid(); block = block.next()) {
            if (!block.layout()) continue;
            for (const auto& format : block.layout()->formats()) {
                result.push_back(QVariantMap{{"start", block.position() + format.start},
                                             {"length", format.length},
                                             {"color", format.format.foreground().color()}});
            }
        }
        return result;
    }
    Q_INVOKABLE QUrl classicArchive(int count = 65535) {
        struct Member { QByteArray name; QByteArray data; quint32 crc; quint32 offset; };
        QList<Member> members;
        const QDir root(project().toLocalFile());
        QDirIterator files(root.path(), QDir::Files, QDirIterator::Subdirectories);
        while (files.hasNext()) {
            QFile file(files.next());
            if (!file.open(QIODevice::ReadOnly)) return {};
            members.push_back({root.relativeFilePath(file.fileName()).toUtf8(), file.readAll(), 0, 0});
        }
        for (int index = static_cast<int>(members.size()); index < count; ++index)
            members.push_back({QByteArray("attachments/") + QByteArray::number(index) + ".txt", "x", 0, 0});
        QByteArray bytes;
        QDataStream out(&bytes, QIODevice::WriteOnly);
        out.setByteOrder(QDataStream::LittleEndian);
        for (auto& member : members) {
            member.crc = crc32(member.data);
            member.offset = static_cast<quint32>(bytes.size());
            out << quint32(0x04034b50) << quint16(20) << quint16(0x800) << quint16(0)
                << quint16(0) << quint16(0) << member.crc << quint32(member.data.size())
                << quint32(member.data.size()) << quint16(member.name.size()) << quint16(0);
            out.writeRawData(member.name.constData(), member.name.size());
            out.writeRawData(member.data.constData(), member.data.size());
        }
        const quint32 start = static_cast<quint32>(bytes.size());
        for (const auto& member : members) {
            out << quint32(0x02014b50) << quint16(0x0314) << quint16(20) << quint16(0x800)
                << quint16(0) << quint16(0) << quint16(0) << member.crc
                << quint32(member.data.size()) << quint32(member.data.size())
                << quint16(member.name.size()) << quint16(0) << quint16(0) << quint16(0)
                << quint16(0) << quint32(0100600U << 16) << member.offset;
            out.writeRawData(member.name.constData(), member.name.size());
        }
        const quint32 size = static_cast<quint32>(bytes.size()) - start;
        out << quint32(0x06054b50) << quint16(0) << quint16(0) << quint16(members.size())
            << quint16(members.size()) << size << start << quint16(0);
        const QString path = directory_.path() + "/classic.zip";
        QFile::setPermissions(path, QFile::ReadOwner | QFile::WriteOwner);
        QFile file(path);
        if (!file.open(QIODevice::WriteOnly) || file.write(bytes) != bytes.size()) return {};
        return QUrl::fromLocalFile(path);
    }
    Q_INVOKABLE QStringList archiveMembers(const QUrl& archive) const {
        QFile file(archive.toLocalFile());
        if (!file.open(QIODevice::ReadOnly)) return {};
        QByteArray bytes = file.readAll();
        const qsizetype end = bytes.lastIndexOf(QByteArray("PK\x05\x06", 4));
        if (end < 0 || end + 22 > bytes.size()) return {};
        QDataStream in(bytes);
        in.setByteOrder(QDataStream::LittleEndian);
        in.skipRawData(end + 10);
        quint16 count;
        quint32 size, offset;
        in >> count >> size >> offset;
        if (offset + size > static_cast<quint64>(bytes.size())) return {};
        in.device()->seek(offset);
        QStringList result;
        for (int index = 0; index < count; ++index) {
            quint32 signature;
            in >> signature;
            if (signature != 0x02014b50) return {};
            in.skipRawData(24);
            quint16 name, extra, comment;
            in >> name >> extra >> comment;
            in.skipRawData(12);
            QByteArray path(name, '\0');
            if (in.readRawData(path.data(), path.size()) != path.size()) return {};
            result.push_back(QString::fromUtf8(path));
            in.skipRawData(extra + comment);
        }
        return result;
    }
    Q_INVOKABLE bool readOnlyArchive(const QUrl& archive) const {
        return QFile::setPermissions(archive.toLocalFile(), QFile::ReadOwner | QFile::ReadUser |
                                     QFile::ReadGroup | QFile::ReadOther);
    }

   private:
    static quint32 crc32(const QByteArray& bytes) {
        quint32 crc = 0xffffffff;
        for (unsigned char byte : bytes) {
            crc ^= byte;
            for (int bit = 0; bit < 8; ++bit) crc = (crc >> 1) ^ (0xedb88320U & (0U - (crc & 1U)));
        }
        return ~crc;
    }
    QTemporaryDir directory_;
};
static void register_project_text_proof() {
    qmlRegisterType<ProjectTextProof>("ProjectTextAcceptance", 1, 0, "ProjectTextProof");
}
Q_COREAPP_STARTUP_FUNCTION(register_project_text_proof)
#include "test_project_text_observer.moc"
