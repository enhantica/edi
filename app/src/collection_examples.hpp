// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QHash>
#include <QList>
#include <QObject>
#include <QPointer>
#include <QTemporaryDir>
#include <QUrl>

#include <functional>
#include <memory>

#include "example_list_model.hpp"

class QNetworkAccessManager;

namespace edi_app {

class OnlineSourcesModel;

/// The Examples list's rows from the data collections (ADR-0068): every enabled source that holds projects is
/// read for its `project` entries, each becoming an example `collection/<source>/<entry>`; opening one downloads
/// its zipped project and opens it as any archive. A source that cannot be read adds nothing and says so in the log.
class CollectionExamples : public QObject {
    Q_OBJECT

public:
    using ProjectDone = std::function<void(const QUrl& archive, const QString& error)>;

    CollectionExamples(OnlineSourcesModel* sources, QObject* parent = nullptr);
    ~CollectionExamples() override;

    /// Read the sources again; `itemsChanged` follows for each source answered.
    void refresh();
    QList<ExampleListModel::Item> items() const { return items_; }
    static bool isCollectionId(const QString& id) { return id.startsWith(QStringLiteral("collection/")); }
    /// Download (or copy) the entry's zip into a temporary folder; `done` gets the archive or an error.
    void fetchProject(const QString& id, ProjectDone done);

signals:
    void itemsChanged();

private:
    struct Known {
        QString source, path, title;
    };
    QPointer<OnlineSourcesModel> sources_;
    QNetworkAccessManager* network_ = nullptr;
    QList<ExampleListModel::Item> items_;
    QHash<QString, Known> known_;
    std::unique_ptr<QTemporaryDir> downloads_;
    int generation_ = 0;
};

}  // namespace edi_app
