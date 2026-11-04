// SPDX-License-Identifier: BSD-3-Clause
#pragma once

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

/// The example projects from the data collections (ADR-0068): every enabled source that holds projects is read
/// for its `project` entries, under the entry's own id. An entry the bundled catalogue lists serves that row's
/// project; any other entry joins the Examples list as a row of its own. The first source holding an id serves it.
/// Opening downloads the zipped project and opens it as any archive. When no source could be read, `notice`
/// says so and names the failures; it is empty once one source answered.
class CollectionExamples : public QObject {
    Q_OBJECT

public:
    using ProjectDone = std::function<void(const QUrl& archive, const QString& error)>;

    CollectionExamples(OnlineSourcesModel* sources, QObject* parent = nullptr);
    ~CollectionExamples() override;

    /// Read the sources again; `itemsChanged` follows for each source answered.
    void refresh();
    /// The rows to add to the Examples list: the entries no bundled catalogue row stands for.
    QList<ExampleListModel::Item> items() const { return items_; }
    /// Whether a source that answered holds this example's project.
    bool knows(const QString& id) const { return known_.contains(id); }
    /// Whether a source is still being read.
    bool loading() const { return pending_ > 0; }
    /// Why no example can be opened, or empty while a source answered or is still being read.
    QString notice() const { return notice_; }
    /// Download (or copy) the entry's zip into a temporary folder; `done` gets the archive or an error.
    void fetchProject(const QString& id, ProjectDone done);

signals:
    void itemsChanged();
    void noticeChanged();

private:
    struct Known {
        QString source, path, title;
    };
    void updateNotice();

    QPointer<OnlineSourcesModel> sources_;
    QNetworkAccessManager* network_ = nullptr;
    QList<ExampleListModel::Item> items_;
    QHash<QString, Known> known_;
    QStringList failed_;
    bool answered_ = false;
    int pending_ = 0;
    QString notice_;
    std::unique_ptr<QTemporaryDir> downloads_;
    int generation_ = 0;
};

}  // namespace edi_app
