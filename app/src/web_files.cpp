// SPDX-License-Identifier: BSD-3-Clause
#include "web_files.hpp"

#include <QBuffer>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QStandardPaths>
#include <QtCore/private/qzipreader_p.h>
#include <QtCore/private/qzipwriter_p.h>
#include <memory>
#include <vector>

#if defined(Q_OS_WASM)
#include <QPointer>
#include <QtGui/private/qwasmlocalfileaccess_p.h>
#include <emscripten.h>

// The browser's folder upload (an `<input type="file" webkitdirectory>`, which every current browser offers):
// each chosen file is read and written into the page's memory under `root`, by its path relative to the chosen
// folder's parent, then edi_web_folder_copied(request, count) runs; a dismissed chooser calls
// edi_web_folder_cancelled(request). The input stays in the page, hidden, as `#edi-open-folder` until the choice
// ends, so a page driver can hand it a folder too.
EM_JS_DEPS(edi_web_files, "$FS");
EM_JS(void, edi_web_pick_folder, (int request, const char* root_utf8), {
    const root = UTF8ToString(root_utf8);
    document.getElementById("edi-open-folder")?.remove();
    const input = document.createElement("input");
    input.type = "file";
    input.id = "edi-open-folder";
    input.webkitdirectory = true;
    input.multiple = true;
    input.style.display = "none";
    input.addEventListener("cancel", () => {
        input.remove();
        Module._edi_web_folder_cancelled(request);
    });
    input.addEventListener("change", async () => {
        const files = Array.from(input.files);
        input.remove();
        let copied = 0;
        for (const file of files) {
            const path = root + "/" + (file.webkitRelativePath || file.name);
            const dir = path.substring(0, path.lastIndexOf("/"));
            try {
                FS.mkdirTree(dir);
                FS.writeFile(path, new Uint8Array(await file.arrayBuffer()));
                copied += 1;
            } catch (e) {
                console.error("edi: cannot copy " + path, e);
            }
        }
        Module._edi_web_folder_copied(request, copied);
    });
    document.body.appendChild(input);
    input.click();
});

namespace {
// The WebFiles instance whose folder requests the page's script answers.
QPointer<edi_app::WebFiles>& folder_owner() {
    static QPointer<edi_app::WebFiles> owner;
    return owner;
}
}  // namespace

extern "C" EMSCRIPTEN_KEEPALIVE void edi_web_folder_copied(int request, int count) {
    edi_app::WebFiles::folderCopied(request, count);
}
extern "C" EMSCRIPTEN_KEEPALIVE void edi_web_folder_cancelled(int request) {
    edi_app::WebFiles::folderCancelled(request);
}
#endif

namespace edi_app {

namespace {
// Holds a chosen file's bytes while the browser reads them in.
struct Incoming {
    QString name;
    QByteArray data;
};

// A relative archive path that stays inside its target: no absolute path, no drive, no `..` component.
bool inside(const QString& path) {
    if (path.isEmpty() || path.startsWith(QLatin1Char('/')) || path.startsWith(QLatin1Char('\\'))
        || path.contains(QLatin1Char(':'))) {
        return false;
    }
    const QStringList parts = QString(path).replace(QLatin1Char('\\'), QLatin1Char('/')).split(QLatin1Char('/'));
    return !parts.contains(QStringLiteral(".."));
}
}  // namespace

bool WebFiles::available() {
#if defined(Q_OS_WASM)
    return true;
#else
    return false;
#endif
}

QString WebFiles::freshDirectory(const QString& kind) {
    static int counter = 0;
    const QString root = QDir(QStandardPaths::writableLocation(QStandardPaths::TempLocation)).filePath(QStringLiteral("edi-web"));
    QString path;
    do {
        path = QDir(root).filePath(kind + QLatin1Char('-') + QString::number(++counter));
    } while (QFileInfo::exists(path));
    QDir().mkpath(path);
    return path;
}

QByteArray WebFiles::pack(const QString& directory) {
    const QDir dir(directory);
    const QString top = dir.dirName();
    QByteArray archive;
    QBuffer buffer(&archive);
    buffer.open(QIODevice::WriteOnly);
    QZipWriter writer(&buffer);
    writer.setCompressionPolicy(QZipWriter::AutoCompress);
    writer.addDirectory(top);
    QStringList files;
    QDirIterator it(directory, QDir::Files | QDir::Hidden, QDirIterator::Subdirectories);
    while (it.hasNext()) {
        files.append(it.next());
    }
    files.sort();  // the same project packs into the same archive layout
    for (const QString& path : files) {
        QFile file(path);
        if (!file.open(QIODevice::ReadOnly)) {
            return {};
        }
        writer.addFile(top + QLatin1Char('/') + dir.relativeFilePath(path), file.readAll());
    }
    writer.close();
    return writer.status() == QZipWriter::NoError ? archive : QByteArray();
}

QString WebFiles::unpack(const QByteArray& archive, const QString& target, QString& error) {
    QByteArray bytes = archive;
    QBuffer buffer(&bytes);
    buffer.open(QIODevice::ReadOnly);
    QZipReader reader(&buffer);
    if (!reader.isReadable() || reader.status() != QZipReader::NoError) {
        error = QStringLiteral("the file is not a .zip archive");
        return {};
    }
    const QList<QZipReader::FileInfo> entries = reader.fileInfoList();
    if (entries.isEmpty()) {
        error = QStringLiteral("the file is not a .zip archive, or an empty one");
        return {};
    }
    for (const QZipReader::FileInfo& entry : entries) {
        if (!inside(entry.filePath)) {
            error = QStringLiteral("the archive names a path outside its folder: %1").arg(entry.filePath);
            return {};
        }
    }
    const QDir root(target);
    for (const QZipReader::FileInfo& entry : entries) {
        const QString path = root.filePath(entry.filePath);
        if (entry.isDir) {
            root.mkpath(entry.filePath);
            continue;
        }
        if (!entry.isFile) {
            continue;  // a link is not unpacked
        }
        QDir().mkpath(QFileInfo(path).absolutePath());
        QFile file(path);
        if (!file.open(QIODevice::WriteOnly) || file.write(reader.fileData(entry.filePath)) < 0) {
            error = QStringLiteral("cannot unpack %1").arg(entry.filePath);
            return {};
        }
    }
    const QString project = projectIn(target, error);
    if (project.isEmpty()) {
        error = QStringLiteral("the archive holds no project: no project.edi at its top or in its one folder");
    }
    return project;
}

QString WebFiles::projectIn(const QString& path, QString& error) {
    const QDir root(path);
    if (QFileInfo(root.filePath(QStringLiteral("project.edi"))).isFile()) {
        return root.absolutePath();
    }
    const QStringList folders = root.entryList(QDir::Dirs | QDir::NoDotAndDotDot);
    if (folders.size() == 1 && QFileInfo(root.filePath(folders.constFirst() + QStringLiteral("/project.edi"))).isFile()) {
        return root.absoluteFilePath(folders.constFirst());
    }
    error = QStringLiteral("the folder holds no project: no project.edi in it");
    return {};
}

int WebFiles::begin() {
    if (m_active != 0) {
        const int superseded = m_active;
        m_active = 0;
        emit cancelled(superseded);
    }
    m_active = ++m_last;
    return m_active;
}

bool WebFiles::finish(int request) {
    if (request == 0 || request != m_active) {
        return false;
    }
    m_active = 0;
    return true;
}

QUrl WebFiles::saveLocation(const QString& name) {
    QString folder = name.trimmed();
    folder.replace(QLatin1Char('/'), QLatin1Char('_')).replace(QLatin1Char('\\'), QLatin1Char('_'));
    if (folder.isEmpty() || folder == QStringLiteral(".") || folder == QStringLiteral("..")) {
        folder = QStringLiteral("project");
    }
    return QUrl::fromLocalFile(QDir(freshDirectory(QStringLiteral("save"))).filePath(folder));
}

#if defined(Q_OS_WASM)

int WebFiles::openProject() {
    const int request = begin();
    const QString root = freshDirectory(QStringLiteral("open"));
    m_folders.insert(request, root);
    folder_owner() = this;
    edi_web_pick_folder(request, root.toUtf8().constData());
    return request;
}

void WebFiles::folderCopied(int request, int count) {
    const QPointer<WebFiles> owner = folder_owner();
    if (owner.isNull()) {
        return;
    }
    // Answered on the app's own turn, never inside the browser's event handler.
    QMetaObject::invokeMethod(
        owner.data(),
        [owner, request, count] {
            if (!owner.isNull()) {
                owner->answerFolder(request, count);
            }
        },
        Qt::QueuedConnection);
}

void WebFiles::folderCancelled(int request) { folderCopied(request, -1); }

void WebFiles::answerFolder(int request, int count) {
    const QString root = m_folders.take(request);
    if (!finish(request)) {
        // A superseded request's copy: nobody waits for it.
        if (!root.isEmpty()) {
            QDir(root).removeRecursively();
        }
        return;
    }
    if (count < 0) {
        QDir(root).removeRecursively();
        emit cancelled(request);
        return;
    }
    QString error;
    const QString project = count > 0 ? projectIn(root, error) : QString();
    if (project.isEmpty()) {
        emit failed(request, QStringLiteral("cannot open the chosen folder: %1")
                                 .arg(count > 0 ? error : QStringLiteral("no file could be read")));
        return;
    }
    emit projectOpened(request, QUrl::fromLocalFile(project));
}

int WebFiles::openFiles(const QString& accept, bool multiple) {
    struct Batch {
        int expected = 0;
        QString directory;
        std::vector<Incoming> files;
        QList<QUrl> written;
    };
    const int request = begin();
    auto batch = std::make_shared<Batch>();
    batch->directory = freshDirectory(QStringLiteral("files"));
    const QPointer<WebFiles> self(this);
    QWasmLocalFileAccess::openFiles(
        accept.toStdString(),
        multiple ? QWasmLocalFileAccess::FileSelectMode::MultipleFiles : QWasmLocalFileAccess::FileSelectMode::SingleFile,
        [self, request, batch](int count) {
            batch->expected = count;
            if (count == 0 && !self.isNull() && self->finish(request)) {
                emit self->cancelled(request);
            }
        },
        [batch](uint64_t size, const std::string& name) -> char* {
            batch->files.push_back(Incoming{QString::fromStdString(name), QByteArray()});
            batch->files.back().data.resize(static_cast<qsizetype>(size));
            return batch->files.back().data.data();
        },
        [self, request, batch] {
            if (self.isNull() || self->m_active != request) {
                return;  // superseded, failed or cancelled: the rest of the batch is not kept
            }
            const Incoming& file = batch->files.back();
            const QString path = QDir(batch->directory).filePath(QFileInfo(file.name).fileName());
            // Closed before the file is handed on: an open QFile can still hold the end of its data in its buffer.
            QFile out(path);
            const bool kept = out.open(QIODevice::WriteOnly) && out.write(file.data) == file.data.size() && out.flush();
            out.close();
            if (!kept) {
                self->finish(request);
                emit self->failed(request, QStringLiteral("cannot keep %1 in memory").arg(file.name));
                return;
            }
            batch->written.append(QUrl::fromLocalFile(path));
            if (batch->written.size() == batch->expected && self->finish(request)) {
                emit self->filesOpened(request, batch->written);
            }
        });
    return request;
}

bool WebFiles::downloadProject(const QString& path) {
    const QByteArray archive = QFileInfo(path).isDir() ? pack(path) : QByteArray();
    if (archive.isEmpty()) {
        emit failed(0, QStringLiteral("cannot pack the project in %1").arg(path));
        return false;
    }
    QWasmLocalFileAccess::saveFile(archive, (QDir(path).dirName() + QStringLiteral(".zip")).toStdString());
    return true;
}

#else

int WebFiles::openProject() {
    const int request = begin();
    finish(request);
    emit failed(request, QStringLiteral("opening a project folder upload is the browser build's"));
    return request;
}

void WebFiles::folderCopied(int /*request*/, int /*count*/) {}

void WebFiles::folderCancelled(int /*request*/) {}

void WebFiles::answerFolder(int /*request*/, int /*count*/) {}

int WebFiles::openFiles(const QString& /*accept*/, bool /*multiple*/) {
    const int request = begin();
    finish(request);
    emit failed(request, QStringLiteral("opening files through the browser is the browser build's"));
    return request;
}

bool WebFiles::downloadProject(const QString& /*directory*/) {
    emit failed(0, QStringLiteral("downloading a project is the browser build's"));
    return false;
}

#endif

}  // namespace edi_app
