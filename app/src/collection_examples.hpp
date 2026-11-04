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

#include "example_list_model.hpp"

class QNetworkAccessManager;

namespace edi_app {

class OnlineSourcesModel;

/// The files the app takes from the data collections (ADR-0068): every enabled source's index is read once, and
/// each entry is known under its own id, served by the first source that holds it. The `project` entries are the
/// examples: an entry the bundled catalogue lists serves that row's project, any other joins the Examples list as
/// a row of its own. A download is checked against the size and digest the index records before it is used.
/// When no source holding projects could be read, `notice` says so and names the failures.
class CollectionExamples : public QObject {
    Q_OBJECT

public:
    using BytesDone = std::function<void(const QByteArray& bytes, const QString& error)>;
    using ProjectDone = std::function<void(const QUrl& archive, const QString& error)>;

    CollectionExamples(OnlineSourcesModel* sources, QObject* parent = nullptr);
    ~CollectionExamples() override;

    /// Read the sources again; `itemsChanged` follows for each source answered.
    void refresh();
    /// The rows to add to the Examples list: the project entries no bundled catalogue row stands for.
    QList<ExampleListModel::Item> items() const { return items_; }
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
    void fetchBytes(const QString& id, BytesDone done);
    /// The entry's zip in a temporary folder; `done` gets the archive or an error.
    void fetchProject(const QString& id, ProjectDone done);
    /// The file name the entry's path ends with; empty for an unknown entry.
    QString fileName(const QString& id) const;

signals:
    void itemsChanged();
    void noticeChanged();

private:
    struct Known {
        QString source, path, kind;
        long long bytes = -1;
        QString sha256;
    };
    void updateNotice();
    void settle();

    QPointer<OnlineSourcesModel> sources_;
    QNetworkAccessManager* network_ = nullptr;
    QList<ExampleListModel::Item> items_;
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
