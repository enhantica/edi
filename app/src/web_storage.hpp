// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_WEB_STORAGE_HPP
#define EDI_APP_WEB_STORAGE_HPP

#include <QAbstractListModel>
#include <QHash>
#include <QList>
#include <QObject>
#include <QString>
#include <QStringList>
#include <QtQml/qqmlregistration.h>
#include <functional>

class QQmlEngine;
class QJSEngine;

#if defined(Q_OS_WASM)
namespace emscripten { class val; }
#endif

namespace edi_app {

// Where the web app keeps a project (edi ADR-0052 §9). The page's own files live in memory; a project's place is one
// of: the browser's private storage (its origin private file system, kept across reloads), or, in Chrome and Edge, a
// folder or a .zip on the user's disk reached through the File System Access API. Every place has a record in the
// browser's IndexedDB (its kind, name and, for the disk, the handle), which is what Recent projects lists; the latest
// unsaved state of a project is kept beside it, so a reload or a closed tab can continue where it left off.
//
// Each call starts a job whose one answer arrives later, on the app's own turn: done, or cancelled, or a message
// saying why not. On the desktop every job answers that it is the browser's.
// A job's answer, and the place and the copy in memory it made, where it made one.
struct WebStorageAnswer {
    bool ok = false;
    bool cancelled = false;
    QString message;
    QString key;
    QString kind;
    QString name;
    // The project folder in memory or, for a "zip" place, the archive.
    QString path;
};

// The stored places, most recent first: each its key, kind ("browser", "folder" or "zip") and name, whether it has
// been saved and whether unsaved changes are kept for it.
class WebPlaceListModel : public QAbstractListModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to WebStorage")
    Q_PROPERTY(int count READ count NOTIFY countChanged)

   public:
    enum Role { KeyRole = Qt::UserRole + 1, KindRole, NameRole, SavedRole, RecoveryRole };
    struct Place {
        QString key;
        QString kind;
        QString name;
        bool saved = false;
        bool recovery = false;
    };

    using QAbstractListModel::QAbstractListModel;

    int rowCount(const QModelIndex& parent = QModelIndex()) const override;
    QVariant data(const QModelIndex& index, int role) const override;
    QHash<int, QByteArray> roleNames() const override;
    int count() const { return static_cast<int>(places_.size()); }
    Q_INVOKABLE QString key(int row) const;
    Q_INVOKABLE QString kind(int row) const;
    Q_INVOKABLE QString name(int row) const;
    Q_INVOKABLE bool saved(int row) const;
    Q_INVOKABLE bool recovery(int row) const;
    void setPlaces(QList<Place> places);

   signals:
    void countChanged();

   private:
    const Place* at(int row) const;
    QList<Place> places_;
};

class WebStorage : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON
    // Whether the browser can open and write folders and files on the disk (Chrome and Edge on the desktop).
    Q_PROPERTY(bool diskAccess READ diskAccess CONSTANT)
    // The stored places, most recent first.
    Q_PROPERTY(edi_app::WebPlaceListModel* places READ places CONSTANT)
    // Whether the browser lets the page keep projects: false until a small write proves it, and for good in a
    // window that refuses it (a private window may). Without it a project lives only in the tab.
    Q_PROPERTY(bool usable READ usable NOTIFY usableChanged)

   public:
    using Answer = std::function<void(const WebStorageAnswer&)>;

    static WebStorage* instance();
    static WebStorage* create(QQmlEngine*, QJSEngine*);

    static bool diskAccess();
    WebPlaceListModel* places() const { return places_; }
    bool usable() const { return usable_; }
    // A write to the browser's storage failed: it is not used again in this tab.
    void markUnusable();

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

    // A job's answer, from the page's script, as its JSON text.
    static void answered(int job, const QString& json);
#if defined(Q_OS_WASM)
    // Native persistence policy over the browser's actual values; not a QML API.
    static emscripten::val policy(int operation, const emscripten::val& arguments);
    static void serialFinished(int job);
#endif

   signals:
    void placesChanged();
    void usableChanged();

   private:
    // A job's own handler reads the script's answer as it was sent.
    using Reply = std::function<void(const QString&)>;

    explicit WebStorage(QObject* parent = nullptr);
    int begin(Reply reply);
    int begin(Answer answer);
    void finish(int job, const QString& json);

#if defined(Q_OS_WASM)
    void queueSerial(int job, const QString& key);
    QHash<QString, QList<int>> serial_jobs_;
    QHash<QString, QStringList> loaded_files_;
#endif
    QHash<int, Reply> jobs_;
    int last_ = 0;
    WebPlaceListModel* places_;
    bool usable_ = false;
};

}  // namespace edi_app

#endif  // EDI_APP_WEB_STORAGE_HPP
