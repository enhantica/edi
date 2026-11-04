// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QAbstractListModel>
#include <QHash>
#include <QPointer>
#include <QTemporaryDir>
#include <QUrl>
#include <QVariant>
#include <QtQml/qqmlregistration.h>

#include <functional>
#include <memory>

#include "edi/online_index.hpp"

class QNetworkAccessManager;
class QNetworkReply;

namespace edi_app {

class OnlineSourcesModel;

/// The rows of one search: the entries found, for the popup's results table.
class OnlineResultsModel : public QAbstractListModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to the search")
    Q_PROPERTY(int count READ rowCount NOTIFY countChanged)

public:
    enum Role { IdRole = Qt::UserRole + 1, KindRole, NameRole, FormulaRole, SpaceGroupRole, CellRole, RadiationRole, TechniqueRole, InstrumentRole, SourceRole };
    Q_ENUM(Role)

    using QAbstractListModel::QAbstractListModel;
    int rowCount(const QModelIndex& parent = {}) const override;
    QVariant data(const QModelIndex& index, int role) const override;
    QHash<int, QByteArray> roleNames() const override;

    void assign(std::vector<edi::online::Entry> entries);
    const edi::online::Entry* at(int row) const;

signals:
    void countChanged();

private:
    std::vector<edi::online::Entry> entries_;
};

/// One From web… popup's state (ADR-0068): the source chosen among those offering the page's kind, that source's
/// fields, the search and its results, and the download of a chosen entry's file. A collection source answers from
/// its `index.json`; COD from its query service, unless its URL is a local folder, which is read as a collection
/// (the test seam, OnlineSourcesModel). A download lands in a temporary file that the project's ordinary file
/// loaders then read, so online loading has no reader of its own.
class OnlineSearch : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to the session")
    Q_PROPERTY(QString kind READ kind WRITE setKind NOTIFY kindChanged)
    Q_PROPERTY(QVariantList sources READ sources NOTIFY sourcesChanged)
    Q_PROPERTY(QString sourceId READ sourceId WRITE setSourceId NOTIFY sourceIdChanged)
    Q_PROPERTY(QString sourceName READ sourceName NOTIFY sourceNameChanged)
    Q_PROPERTY(QVariantList fields READ fields NOTIFY fieldsChanged)
    Q_PROPERTY(edi_app::OnlineResultsModel* results READ results CONSTANT)
    Q_PROPERTY(bool busy READ busy NOTIFY busyChanged)
    Q_PROPERTY(QString message READ message NOTIFY messageChanged)
    Q_PROPERTY(QString detail READ detail NOTIFY detailChanged)
    Q_PROPERTY(bool unreachable READ unreachable NOTIFY unreachableChanged)
    Q_PROPERTY(QString alternativeId READ alternativeId NOTIFY alternativeIdChanged)
    Q_PROPERTY(QString alternativeName READ alternativeName NOTIFY alternativeNameChanged)
    Q_PROPERTY(bool searched READ searched NOTIFY searchedChanged)

public:
    OnlineSearch(OnlineSourcesModel* sources, QObject* parent = nullptr);
    ~OnlineSearch() override;

    QString kind() const { return kind_; }
    void setKind(const QString& kind);
    QVariantList sources() const;
    QString sourceId() const { return source_id_; }
    void setSourceId(const QString& id);
    QString sourceName() const;
    /// The search fields of the current source, ID first: a list of {key, label}.
    QVariantList fields() const;
    OnlineResultsModel* results() const { return results_; }
    bool busy() const { return busy_; }
    QString message() const { return message_; }
    /// What exactly failed behind `message`: a path or the server's answer.
    QString detail() const { return detail_; }
    bool unreachable() const { return unreachable_; }
    QString alternativeId() const { return alternative_id_; }
    QString alternativeName() const;
    bool searched() const { return searched_; }

    /// Search the current source with the field values (keys as in `fields`); the results follow asynchronously.
    Q_INVOKABLE void search(const QVariantMap& values);
    /// Switch to the alternative source offered after an unreachable one, keeping the results empty.
    Q_INVOKABLE void useAlternative();
    /// Download the first file of a result into a temporary file; `fileReady` then carries it to the loaders.
    Q_INVOKABLE void load(int row);
    /// Forget everything shown: results, message, the chosen source stays.
    Q_INVOKABLE void reset();

signals:
    void kindChanged();
    void sourcesChanged();
    void sourceIdChanged();
    void sourceNameChanged();
    void fieldsChanged();
    void busyChanged();
    void messageChanged();
    void detailChanged();
    void unreachableChanged();
    void alternativeIdChanged();
    void alternativeNameChanged();
    void searchedChanged();
    /// A downloaded entry: its kind, the local file and the entry's fields (id, name, radiation, technique, …).
    void fileReady(const QString& kind, const QUrl& file, const QVariantMap& entry);

private:
    using Bytes = std::function<void(const QByteArray& bytes, const QString& error, bool unreachable)>;
    void fetch(const QUrl& url, Bytes done);
    void withIndex(const QString& url, const std::function<void(const edi::online::Index*, const QString& error, bool unreachable)>& done);
    void finish(std::vector<edi::online::Entry> entries);
    void fail(const QString& message, bool unreachable);
    void setBusy(bool busy);
    QUrl fileUrl(const QString& base, const QString& path) const;
    bool codService(const QString& url) const;

    QPointer<OnlineSourcesModel> sources_;
    OnlineResultsModel* results_;
    QNetworkAccessManager* network_ = nullptr;
    QString kind_ = QStringLiteral("structure");
    QString source_id_, message_, detail_, alternative_id_;
    bool busy_ = false, unreachable_ = false, searched_ = false;
    int generation_ = 0;
    QHash<QString, std::shared_ptr<edi::online::Index>> indexes_;
    std::unique_ptr<QTemporaryDir> downloads_;
};

}  // namespace edi_app
