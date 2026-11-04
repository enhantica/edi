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
#include "online_values.hpp"

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
    enum Role {
        IdRole = Qt::UserRole + 1, KindRole, NameRole, FormulaRole, SpaceGroupRole, HasCellRole,
        CellARole, CellBRole, CellCRole, CellAlphaRole, CellBetaRole, CellGammaRole,
        RadiationRole, TechniqueRole, InstrumentRole, SourceRole, ReferenceRole, ReferenceUrlRole, ReferenceStyledRole,
        DescriptionRole
    };
    Q_ENUM(Role)

    using QAbstractListModel::QAbstractListModel;
    int rowCount(const QModelIndex& parent = {}) const override;
    QVariant data(const QModelIndex& index, int role) const override;
    QHash<int, QByteArray> roleNames() const override;

    void assign(std::vector<edi::online::Entry> entries);
    /// More rows of the same search (a later chunk of a long COD answer).
    void append(std::vector<edi::online::Entry> entries);
    const edi::online::Entry* at(int row) const;
    const std::vector<edi::online::Entry>& entries() const { return entries_; }
    /// The journals' ISO 4 abbreviations by their normalised full name (journal_key); a journal not in the table
    /// shows its full name. Every row's reference is re-read.
    void setJournalAbbreviations(QHash<QString, QString> byName);
    /// The journal as the reference shows it: its abbreviation when the table holds it, else the name itself.
    QString journalShown(const std::string& journal) const;

signals:
    void countChanged();

private:
    std::vector<edi::online::Entry> entries_;
    QHash<QString, QString> journals_;
};

/// A short list of choices for the popup: the sources offering a kind (key = id, name), or a source's search fields
/// (key, hint). A model, as every list the pages bind (ADR-0015 §2).
class OnlineChoiceModel : public QAbstractListModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to the search")
    Q_PROPERTY(int count READ rowCount NOTIFY countChanged)

public:
    enum Role { KeyRole = Qt::UserRole + 1, NameRole, HintRole, OptionsRole };
    Q_ENUM(Role)
    struct Choice {
        QString key, name, hint;
        QStringList options;  // a selector's values (radiation, technique); empty for a text field
    };

    using QAbstractListModel::QAbstractListModel;
    int rowCount(const QModelIndex& parent = {}) const override;
    QVariant data(const QModelIndex& index, int role) const override;
    QHash<int, QByteArray> roleNames() const override;

    Q_INVOKABLE int indexOfKey(const QString& key) const;
    Q_INVOKABLE QString keyAt(int row) const;
    Q_INVOKABLE QString hintAt(int row) const;
    Q_INVOKABLE QStringList optionsAt(int row) const;
    void assign(QList<Choice> choices);

signals:
    void countChanged();

private:
    QList<Choice> choices_;
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
    Q_PROPERTY(edi_app::OnlineChoiceModel* sources READ sources CONSTANT)
    Q_PROPERTY(QString sourceId READ sourceId WRITE setSourceId NOTIFY sourceIdChanged)
    Q_PROPERTY(QString sourceName READ sourceName NOTIFY sourceNameChanged)
    Q_PROPERTY(edi_app::OnlineChoiceModel* fields READ fields CONSTANT)
    Q_PROPERTY(edi_app::OnlineResultsModel* results READ results CONSTANT)
    Q_PROPERTY(bool busy READ busy NOTIFY busyChanged)
    Q_PROPERTY(QString message READ message NOTIFY messageChanged)
    Q_PROPERTY(QString detail READ detail NOTIFY detailChanged)
    Q_PROPERTY(bool unreachable READ unreachable NOTIFY unreachableChanged)
    Q_PROPERTY(QString alternativeId READ alternativeId NOTIFY alternativeIdChanged)
    Q_PROPERTY(QString alternativeName READ alternativeName NOTIFY alternativeNameChanged)
    Q_PROPERTY(bool searched READ searched NOTIFY searchedChanged)
    /// How many entries the search matched (-1 before an answer); the table may hold fewer while a long COD answer
    /// loads 100 at a time (moreAvailable, loadingMore, chunkError).
    Q_PROPERTY(int total READ total NOTIFY totalChanged)
    Q_PROPERTY(bool moreAvailable READ moreAvailable NOTIFY moreAvailableChanged)
    Q_PROPERTY(bool loadingMore READ loadingMore NOTIFY loadingMoreChanged)
    Q_PROPERTY(QString chunkError READ chunkError NOTIFY chunkErrorChanged)

public:
    OnlineSearch(OnlineSourcesModel* sources, QObject* parent = nullptr);
    ~OnlineSearch() override;

    QString kind() const { return kind_; }
    void setKind(const QString& kind);
    OnlineChoiceModel* sources() const { return sources_model_; }
    QString sourceId() const { return source_id_; }
    void setSourceId(const QString& id);
    QString sourceName() const;
    /// The search fields of the current source, ID first; the popup names each key.
    OnlineChoiceModel* fields() const { return fields_model_; }
    OnlineResultsModel* results() const { return results_; }
    bool busy() const { return busy_; }
    QString message() const { return message_; }
    /// What exactly failed behind `message`: a path or the server's answer.
    QString detail() const { return detail_; }
    bool unreachable() const { return unreachable_; }
    QString alternativeId() const { return alternative_id_; }
    QString alternativeName() const;
    bool searched() const { return searched_; }
    int total() const { return total_; }
    bool moreAvailable() const { return !pending_ids_.empty(); }
    bool loadingMore() const { return loading_more_; }
    QString chunkError() const { return chunk_error_; }

    /// A field's value for the next search; the fields are cleared when the source changes.
    Q_INVOKABLE void setField(const QString& key, const QString& value);
    Q_INVOKABLE QString field(const QString& key) const { return field_values_.value(key); }
    /// Search the current source with the field values; the results follow asynchronously.
    Q_INVOKABLE void search();
    /// Switch to the alternative source offered after an unreachable one, keeping the results empty.
    Q_INVOKABLE void useAlternative();
    /// Download the first file of a result into a temporary file; `fileReady` then carries it to the loaders
    /// with the project and the measured-data target the request was made for (null target: a new one).
    Q_INVOKABLE void load(int row, QObject* project, QObject* target);
    /// Forget everything shown: results, message, the chosen source stays.
    Q_INVOKABLE void reset();
    /// The next chunk of a long answer (also the retry after a failed one); nothing while one is loading.
    Q_INVOKABLE void loadMore();
    /// Reads the chosen collection's index ahead of a search, so the selectors (radiation, technique) offer its values.
    Q_INVOKABLE void prepare();
    /// The last search of this kind and source, for the app session: its fields and results come back, and
    /// rememberedSelection says which row was selected. False, with the popup empty, when there was none.
    Q_INVOKABLE bool recall();
    /// Forgets this kind and source's last search and empties the popup.
    Q_INVOKABLE void clear();
    /// The fields' values, by key, as the last search or recall left them.
    Q_INVOKABLE QVariantMap fieldValues() const;
    Q_INVOKABLE void rememberSelection(int row);
    Q_INVOKABLE int rememberedSelection() const;

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
    void totalChanged();
    void moreAvailableChanged();
    void loadingMoreChanged();
    void chunkErrorChanged();
    /// A downloaded entry: its kind, the local file, the entry, and the request's authority: the project it was
    /// made for and its measured-data target (null when it was made for a new experiment, `newTarget` true; null
    /// with `newTarget` false when the target has gone since).
    void fileReady(const QString& kind, const QUrl& file, const edi_app::OnlineEntry& entry, QObject* project,
                   QObject* target, bool newTarget);

private:
    using Bytes = std::function<void(const QByteArray& bytes, const QString& error, bool unreachable)>;
    void fetch(const QUrl& url, Bytes done);
    void withIndex(const QStringList& bases, const std::function<void(const edi::online::Index*, const QString& error, bool unreachable)>& done);
    void fetchFrom(const QStringList& bases, const QString& path, Bytes done);
    void finish(std::vector<edi::online::Entry> entries);
    void refreshSources();
    void refreshFields();
    /// The fields of the kind and source, with the selectors' values from `index` when it is a collection's.
    void buildFields(const edi::online::Index* index);
    /// The next up-to-100 ids of a long COD answer; `first` when the table is still empty.
    void loadChunk(int generation, bool first);
    std::vector<edi::online::Entry> codAnswer(const QByteArray& bytes) const;
    /// The paging properties, told together after any of them moved.
    void pagingChanged();
    void fail(const QString& message, bool unreachable);
    void setBusy(bool busy);
    /// The journal abbreviations, once per session, from the EasyDiffraction source when it is enabled.
    void loadJournals();
    QString memoryKey() const { return kind_ + u'\n' + source_id_; }
    QUrl fileUrl(const QString& base, const QString& path) const;
    bool codService(const QString& url) const;
    /// Whether `id` is an enabled source offering the current kind.
    bool eligible(const QString& id) const;

    QPointer<OnlineSourcesModel> sources_;
    OnlineResultsModel* results_;
    OnlineChoiceModel* sources_model_;
    OnlineChoiceModel* fields_model_;
    QHash<QString, QString> field_values_;
    QNetworkAccessManager* network_ = nullptr;
    QString kind_ = QStringLiteral("structure");
    QString source_id_, message_, detail_, alternative_id_;
    bool busy_ = false, unreachable_ = false, searched_ = false;
    int generation_ = 0;
    QHash<QString, std::shared_ptr<edi::online::Index>> indexes_;
    struct Remembered {
        QHash<QString, QString> fields;
        std::vector<edi::online::Entry> entries;
        int selected = -1;
        std::vector<std::string> pending;  // a long COD answer's ids not loaded yet
        int total = -1;
        QString base;
        edi::online::Query rest;
    };
    std::vector<std::string> pending_ids_;
    int total_ = -1;
    bool loading_more_ = false;
    QString chunk_error_, chunk_base_;
    edi::online::Query chunk_rest_;
    QHash<QString, Remembered> memory_;  // per kind and source, the app session only
    bool journals_requested_ = false;
    std::unique_ptr<QTemporaryDir> downloads_;
};

}  // namespace edi_app
