// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QByteArray>
#include <QHash>
#include <QList>
#include <QObject>
#include <QPointer>
#include <QStringList>
#include <QTemporaryDir>
#include <QUrl>

#include <functional>
#include <memory>

#include "online_fetch.hpp"

class QNetworkAccessManager;

namespace edi_app {

class OnlineSourcesModel;

/// The files the app takes from the data collections (ADR-0068): every enabled source's index is read once, and
/// each entry is known under its own id, served by the first source that holds it. The `project` entries serve the
/// examples the bundled catalogue lists; a project the catalogue does not list is not an example (owner record
/// 2026-11-09: the Examples list shows exactly the tutorial cases). A download is checked against the size and digest the index records before it is used.
/// When no source holding projects could be read, `notice` says so and names the failures.
class CollectionExamples : public QObject {
    Q_OBJECT

public:
    using BytesDone = std::function<void(const QByteArray& bytes, const QString& error)>;
    using ProjectDone = std::function<void(const QUrl& archive, const QString& error)>;

    CollectionExamples(OnlineSourcesModel* sources, QObject* parent = nullptr);
    ~CollectionExamples() override;

    /// Read the sources again.
    void refresh();
    /// Whether a source that answered holds this entry.
    bool knows(const QString& id) const { return known_.contains(id); }
    /// Whether a source is still being read.
    bool loading() const { return pending_ > 0; }
    /// Why no example can be opened, or empty while a source holding projects answered or is still being read.
    QString notice() const { return notice_; }
    /// Calls `then` once the sources have been read: at once when the entry is known, after the current read when
    /// one is under way, else after a fresh read, so an outage at start-up is retried by the next request.
    void whenRead(const QString& id, std::function<void()> then);
    /// Download (or copy) the entry's file, checked against the index; `done` gets the bytes or an error.
    void fetchBytes(const QString& id, BytesDone done, FetchProgress progress = {});
    /// The entry's zip in a temporary folder; `done` gets the archive or an error.
    void fetchProject(const QString& id, ProjectDone done, FetchProgress progress = {});
    /// The file name the entry's path ends with; empty for an unknown entry.
    QString fileName(const QString& id) const;

signals:
    void noticeChanged();

private:
    struct Known {
        QStringList sources;  ///< the entry's source's locations, in order
        QString path, kind;
        long long bytes = -1;
        QString sha256;
    };
    void updateNotice();
    void settle();

    QPointer<OnlineSourcesModel> sources_;
    QNetworkAccessManager* network_ = nullptr;
    QHash<QString, Known> known_;
    QStringList failed_;
    int projects_ = 0;
    int pending_ = 0;
    QString notice_;
    QList<std::function<void()>> waiting_;
    std::unique_ptr<QTemporaryDir> downloads_;
    int generation_ = 0;
};

}  // namespace edi_app
