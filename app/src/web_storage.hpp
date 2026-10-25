// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_WEB_STORAGE_HPP
#define EDI_APP_WEB_STORAGE_HPP

#include <QHash>
#include <QJsonObject>
#include <QObject>
#include <QString>
#include <QVariantList>
#include <QtQml/qqmlregistration.h>
#include <functional>

class QQmlEngine;
class QJSEngine;

namespace edi_app {

// Where the web app keeps a project (edi ADR-0052 §9). The page's own files live in memory; a project's place is one
// of: the browser's private storage (its origin private file system, kept across reloads), or, in Chrome and Edge, a
// folder or a .zip on the user's disk reached through the File System Access API. Every place has a record in the
// browser's IndexedDB (its kind, name and, for the disk, the handle), which is what Recent projects lists; the latest
// unsaved state of a project is kept beside it, so a reload or a closed tab can continue where it left off.
//
// Each call starts a job whose one answer arrives later, on the app's own turn, as a JSON object: `ok`, or
// `cancelled`, or a `message` saying why not. On the desktop every job answers that it is the browser's.
class WebStorage : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON
    // Whether the browser can open and write folders and files on the disk (Chrome and Edge on the desktop).
    Q_PROPERTY(bool diskAccess READ diskAccess CONSTANT)
    // The stored places, most recent first: each a map of key, kind ("browser", "folder" or "zip"), name, time and
    // whether unsaved changes are kept for it (`recovery`).
    Q_PROPERTY(QVariantList places READ places NOTIFY placesChanged)
    // Whether the browser lets the page keep projects: false until a small write proves it, and for good in a
    // window that refuses it (a private window may). Without it a project lives only in the tab.
    Q_PROPERTY(bool usable READ usable NOTIFY usableChanged)

   public:
    using Answer = std::function<void(const QJsonObject&)>;

    static WebStorage* instance();
    static WebStorage* create(QQmlEngine*, QJSEngine*);

    static bool diskAccess();
    QVariantList places() const { return places_; }
    bool usable() const { return usable_; }
    // A write to the browser's storage failed: it is not used again in this tab.
    void markUnusable();
    QVariantMap place(const QString& key) const;

    // Asks the user for a project to open, a "folder" or a "file" (a .zip), and copies it into `root` in memory: a folder's files
    // under root/<its name>, an archive as root/<its name>. With disk access the answer's `key` names the new place on
    // the disk; without it the copy is the browser's (kind "browser", no key yet).
    void pickOpen(const QString& kind, const QString& root, Answer answer);
    // Asks the user where on the disk to save, a "folder" or a "zip" named `suggested`, starting where the place
    // `startKey` is. The answer's `key` names the new place, recorded once it is first written.
    void pickSave(const QString& kind, const QString& suggested, const QString& startKey, Answer answer);
    // Writes the project folder `folder` (in memory) into the place `key` of `kind`, named `name`: every file, then
    // the files the place had from it before and no longer has are removed. A "zip" place gets the folder's archive.
    // With `recovery` the folder is the project's unsaved state, kept beside the place until it is dropped.
    void write(const QString& key, const QString& kind, const QString& name, const QString& folder, bool recovery,
               Answer answer);
    // Copies the place `key` (or its kept unsaved state) into `root` in memory; the answer's `path` is the project
    // folder or, for a "zip" place, the archive.
    void load(const QString& key, bool recovery, const QString& root, Answer answer);
    // Drops the unsaved state kept for `key`.
    Q_INVOKABLE void dropRecovery(const QString& key);
    // Removes the place `key` from the list; a project kept in the browser is deleted with it.
    Q_INVOKABLE void forget(const QString& key);
    // Reads the places again.
    Q_INVOKABLE void refresh();

    // A job's answer, from the page's script.
    static void answered(int job, const QString& json);

   signals:
    void placesChanged();
    void usableChanged();

   private:
    explicit WebStorage(QObject* parent = nullptr);
    int begin(Answer answer);
    void finish(int job, const QJsonObject& answer);

    QHash<int, Answer> jobs_;
    int last_ = 0;
    QVariantList places_;
    bool usable_ = false;
};

}  // namespace edi_app

#endif  // EDI_APP_WEB_STORAGE_HPP
