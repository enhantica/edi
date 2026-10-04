// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_WEB_FILES_HPP
#define EDI_APP_WEB_FILES_HPP

#include <QByteArray>
#include <QHash>
#include <QList>
#include <QObject>
#include <QString>
#include <QUrl>
#include <QtQml/qqmlregistration.h>

namespace edi_app {

// ADR-0023: the browser's file access. In the browser the app's files live in memory. Opening a project asks
// the browser for a folder (a directory upload) and copies its files into memory, then the app opens it as
// the desktop opens a folder; saving writes the project into memory and hands its .zip archive to the browser
// as a download, since a page cannot write a folder on the user's disk. Data files are asked for the same
// way. On the desktop `available` is false and the app keeps its folder and file dialogs.
class WebFiles : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON
    Q_PROPERTY(bool available READ available CONSTANT)

   public:
    explicit WebFiles(QObject* parent = nullptr) : QObject(parent) {}

    static bool available();

    // A request (openProject, openFiles) returns its id, and its one answer carries it: projectOpened or
    // filesOpened, failed, or cancelled. One request is active at a time, as the browser shows one file chooser:
    // a new request cancels the active one, and an answer that arrives for a request no longer active is dropped.
    // Callers act only on their own id.

    // Asks the browser for a project folder and copies it into memory; answers with projectOpened (the project
    // directory in it).
    Q_INVOKABLE int openProject();
    // The browser has copied `count` files of request `request`'s folder, or the choice was cancelled (called from
    // the page's script).
    static void folderCopied(int request, int count);
    static void folderCancelled(int request);
    // Asks the browser for data files (`accept`: the input's filter, e.g. ".edi"), one or `multiple`; answers with
    // filesOpened (the files, copied into memory).
    Q_INVOKABLE int openFiles(const QString& accept, bool multiple);
    // A new, empty directory in memory to save a project named `name` into.
    Q_INVOKABLE QUrl saveLocation(const QString& name);
    // Packs the project directory into `<directory name>.zip` and hands it to the browser to download.
    Q_INVOKABLE bool downloadProject(const QString& directory);

    // The archive format, on every platform (the unit tier proves it natively). `pack` stores every file
    // under `directory`, with paths relative to its parent: one top-level folder named as the directory.
    static QByteArray pack(const QString& directory);
    // Unpacks `archive` into the empty directory `target` and returns the project directory in it — the one
    // holding project.edi, at the top or in the one top-level folder — or an empty string with `error` set.
    // An entry whose path climbs out of `target` (a `..` component) refuses the whole archive; Qt's reader itself
    // drops a leading `/` or `../`.
    static QString unpack(const QByteArray& archive, const QString& target, QString& error);
    // The project directory in `root`: `root` itself when it holds project.edi, else its one folder that does;
    // otherwise an empty string with `error` set.
    static QString projectIn(const QString& root, QString& error);

   signals:
    void projectOpened(int request, const QUrl& directory);
    void filesOpened(int request, const QList<QUrl>& files);
    // `request` is 0 for a failure outside a request (a download).
    void failed(int request, const QString& message);
    void cancelled(int request);

   private:
    // A new directory under the app's temporary space in memory.
    static QString freshDirectory(const QString& kind);
    // Starts a request, cancelling the active one, and returns its id.
    int begin();
    // Ends `request` if it is the active one; false when it is not (superseded or already answered).
    bool finish(int request);
    void answerFolder(int request, int count);

    int m_active = 0;
    int m_last = 0;
    QHash<int, QString> m_folders;  // each folder request's directory in memory, until it is answered
};

}  // namespace edi_app

#endif  // EDI_APP_WEB_FILES_HPP
