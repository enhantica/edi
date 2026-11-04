// SPDX-License-Identifier: BSD-3-Clause
#include "web_files.hpp"
#include <limits>

#include "edi/project_archive.hpp"

#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QPointer>
#include <QStandardPaths>
#include <cstdlib>
#include <memory>
#include <vector>

#if defined(Q_OS_WASM)
#include <QtGui/private/qwasmlocalfileaccess_p.h>
#include <emscripten.h>

// The browser's folder upload (an `<input type="file" webkitdirectory>`, which every current browser offers):
// each chosen file is read and written into the page's memory under `root`, by its path relative to the chosen
// folder's parent, then edi_web_folder_copied(request, count) runs; a dismissed chooser calls
// edi_web_folder_cancelled(request). The input stays in the page, hidden, as `#edi-open-folder` until the choice
// ends, so a page driver can hand it a folder too.
EM_JS_DEPS(edi_web_files, "$FS,$stringToNewUTF8");

// A file of the site, read with a same-origin request that waits for its answer: a few megabytes at most, once per
// saved report. Its text in new memory the caller frees, or null.
EM_JS(char*, edi_web_site_file, (const char* path_utf8), {
    try {
        const request = new XMLHttpRequest();
        request.open("GET", UTF8ToString(path_utf8), false);
        request.overrideMimeType("text/plain; charset=utf-8");
        request.send(null);
        return request.status === 200 ? stringToNewUTF8(request.responseText) : 0;
    } catch (error) {
        return 0;
    }
});
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

// The archives are the core's (edi ADR-0052), the same bytes every surface writes and reads.
QByteArray WebFiles::pack(const QString& directory) {
    try {
        const std::string bytes = edi::project_archive_bytes(directory.toStdString());
        return QByteArray(bytes.data(), static_cast<qsizetype>(bytes.size()));
    } catch (const std::exception&) {
        return {};
    }
}

QByteArray WebFiles::packFiles(const QList<QPair<QString, QByteArray>>& files) {
    std::vector<std::pair<std::string, std::string>> members;
    for (const auto& [path, data] : files) {
        members.emplace_back(path.toStdString(), data.toStdString());
    }
    try {
        const std::string bytes = edi::archive_bytes(members);
        return QByteArray(bytes.data(), static_cast<qsizetype>(bytes.size()));
    } catch (const std::exception&) {
        return {};
    }
}

QString WebFiles::unpack(const QByteArray& archive, const QString& target, QString& error) {
    try {
        return QString::fromStdString(edi::unpack_project_archive(
            std::string_view(archive.constData(), static_cast<std::size_t>(archive.size())), target.toStdString()));
    } catch (const std::exception& refusal) {
        error = QString::fromUtf8(refusal.what());
        return {};
    }
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
    if (m_last == std::numeric_limits<int>::max()) return 0;
    const QPointer<WebFiles> self(this);
    const auto original_serial = m_last;
    if (m_active != 0) {
        const int superseded = m_active;
        m_active = 0;
        emit cancelled(superseded);
        if (!self || m_last != original_serial || m_active != 0) return 0;
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
    if (request == 0) return 0; // Receiver retirement/reentry admitted no request.
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
    if (request == 0) return 0; // Receiver retirement/reentry admitted no request.
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
    return download(archive, QDir(path).dirName() + QStringLiteral(".zip"));
}

bool WebFiles::download(const QByteArray& data, const QString& name) {
    QWasmLocalFileAccess::saveFile(data, name.toStdString());
    return true;
}

QByteArray WebFiles::siteFile(const QString& path) {
    char* text = edi_web_site_file(path.toUtf8().constData());
    if (text == nullptr) {
        return {};
    }
    QByteArray out(text);
    std::free(text);
    return out;
}

#else

int WebFiles::openProject() {
    const int request = begin();
    if (request == 0) return 0; // Receiver retirement/reentry admitted no request.
    finish(request);
    emit failed(request, QStringLiteral("opening a project folder upload is the browser build's"));
    return request;
}

void WebFiles::folderCopied(int /*request*/, int /*count*/) {}

void WebFiles::folderCancelled(int /*request*/) {}

void WebFiles::answerFolder(int /*request*/, int /*count*/) {}

int WebFiles::openFiles(const QString& /*accept*/, bool /*multiple*/) {
    const int request = begin();
    if (request == 0) return 0; // Receiver retirement/reentry admitted no request.
    finish(request);
    emit failed(request, QStringLiteral("opening files through the browser is the browser build's"));
    return request;
}

bool WebFiles::downloadProject(const QString& /*directory*/) {
    emit failed(0, QStringLiteral("downloading a project is the browser build's"));
    return false;
}

bool WebFiles::download(const QByteArray& /*data*/, const QString& /*name*/) { return false; }

QByteArray WebFiles::siteFile(const QString& /*path*/) { return {}; }

#endif

}  // namespace edi_app
