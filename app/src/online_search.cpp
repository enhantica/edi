// SPDX-License-Identifier: BSD-3-Clause
#include "online_search.hpp"

#include <QCoreApplication>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLoggingCategory>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QTimer>

#include <algorithm>
#include <functional>
#include <memory>
#include <stdexcept>

#include "online_fetch.hpp"
#include "online_sources.hpp"

namespace edi_app {
namespace {

QString field_hint(const QString& key) {
    static const QHash<QString, QString> hints{
        {QStringLiteral("formula"), QCoreApplication::translate("OnlineSearch", "any order: LaCoO3, La Co O3")},
        {QStringLiteral("elements"), QCoreApplication::translate("OnlineSearch", "all of them: La Co O")},
        {QStringLiteral("space_group"), QCoreApplication::translate("OnlineSearch", "Hermann-Mauguin: P m -3 m")},
        {QStringLiteral("radiation"), QCoreApplication::translate("OnlineSearch", "neutron or xray")},
        {QStringLiteral("technique"), QCoreApplication::translate("OnlineSearch", "powder, single crystal, time-of-flight…")},
    };
    return hints.value(key);
}

Q_LOGGING_CATEGORY(lcSearch, "edi.online.search")

constexpr int kChunk = 100;  // COD entries loaded at once (the owner, 2026-11-04)

// A journal name as the abbreviation table is keyed: letters and digits only, in lower case, so punctuation and
// spacing differences between COD's spelling and the list's do not matter.
QString journal_key(const QString& name) {
    QString key;
    for (const QChar c : name)
        if (c.isLetterOrNumber()) key += c.toLower();
    return key;
}

edi::online::Query query_from(const QHash<QString, QString>& values) {
    edi::online::Query q;
    const auto s = [&values](const char* key) { return values.value(QLatin1String(key)).toStdString(); };
    q.id = s("id");
    q.name = s("name");
    q.formula = s("formula");
    q.elements = s("elements");
    q.space_group = s("space_group");
    q.radiation = s("radiation");
    q.technique = s("technique");
    q.instrument = s("instrument");
    return q;
}

OnlineEntry entry_value(const edi::online::Entry& e) {
    OnlineEntry out;
    out.id = QString::fromStdString(e.id);
    out.kind = QString::fromStdString(e.kind);
    out.name = QString::fromStdString(e.name);
    out.formula = QString::fromStdString(e.formula);
    out.spaceGroup = QString::fromStdString(e.space_group);
    out.radiation = QString::fromStdString(e.radiation);
    out.technique = QString::fromStdString(e.technique);
    out.instrument = QString::fromStdString(e.instrument);
    out.source = QString::fromStdString(e.source);
    out.format = e.files.empty() ? QString() : QString::fromStdString(e.files.front().format);
    out.description = QString::fromStdString(e.description);
    for (const std::string& id : e.structures) out.structureIds.append(QString::fromStdString(id));
    return out;
}


}  // namespace

int OnlineResultsModel::rowCount(const QModelIndex& parent) const { return parent.isValid() ? 0 : static_cast<int>(entries_.size()); }

QVariant OnlineResultsModel::data(const QModelIndex& index, int role) const {
    if (!index.isValid() || index.row() < 0 || static_cast<std::size_t>(index.row()) >= entries_.size()) return {};
    const edi::online::Entry& e = entries_[static_cast<std::size_t>(index.row())];
    switch (role) {
        case IdRole: return QString::fromStdString(e.id);
        case KindRole: return QString::fromStdString(e.kind);
        case NameRole: return QString::fromStdString(e.name);
        case DescriptionRole: return QString::fromStdString(e.description);
        case FormulaRole: return QString::fromStdString(e.formula);
        case SpaceGroupRole: return QString::fromStdString(e.space_group);
        case HasCellRole: return e.cell.size() == 6;
        case CellARole: return e.cell.size() == 6 ? e.cell[0] : 0.0;
        case CellBRole: return e.cell.size() == 6 ? e.cell[1] : 0.0;
        case CellCRole: return e.cell.size() == 6 ? e.cell[2] : 0.0;
        case CellAlphaRole: return e.cell.size() == 6 ? e.cell[3] : 0.0;
        case CellBetaRole: return e.cell.size() == 6 ? e.cell[4] : 0.0;
        case CellGammaRole: return e.cell.size() == 6 ? e.cell[5] : 0.0;
        case RadiationRole: return QString::fromStdString(e.radiation);
        case TechniqueRole: return QString::fromStdString(e.technique);
        case InstrumentRole: return QString::fromStdString(e.instrument);
        case SourceRole: return QString::fromStdString(e.source);
        case ReferenceRole:
        case ReferenceStyledRole: {
            const edi::online::Reference parts = edi::online::reference_parts(e, journalShown(e.journal).toStdString());
            const QString authors = QString::fromStdString(parts.authors), where = QString::fromStdString(parts.where);
            if (role == ReferenceRole) return authors.isEmpty() ? where : where.isEmpty() ? authors : authors + QStringLiteral(", ") + where;
            // Styled text for the table's cell: the authors in italic.
            const QString italic = authors.isEmpty() ? QString() : QStringLiteral("<i>%1</i>").arg(authors.toHtmlEscaped());
            return italic.isEmpty() ? where.toHtmlEscaped() : where.isEmpty() ? italic : italic + QStringLiteral(", ") + where.toHtmlEscaped();
        }
        case ReferenceUrlRole: return QString::fromStdString(edi::online::reference_url(e));
        default: return {};
    }
}

QHash<int, QByteArray> OnlineResultsModel::roleNames() const {
    return {{IdRole, "id"},           {KindRole, "kind"},           {NameRole, "name"},           {FormulaRole, "formula"},
            {SpaceGroupRole, "spaceGroup"}, {HasCellRole, "hasCell"},   {CellARole, "cellA"},         {CellBRole, "cellB"},
            {CellCRole, "cellC"},         {CellAlphaRole, "cellAlpha"}, {CellBetaRole, "cellBeta"},   {CellGammaRole, "cellGamma"},
            {RadiationRole, "radiation"}, {TechniqueRole, "technique"}, {InstrumentRole, "instrument"}, {SourceRole, "source"},
            {ReferenceRole, "reference"},   {ReferenceUrlRole, "referenceUrl"}, {ReferenceStyledRole, "referenceStyled"},
            {DescriptionRole, "description"}};
}

void OnlineResultsModel::setJournalAbbreviations(QHash<QString, QString> byName) {
    journals_ = std::move(byName);
    if (!entries_.empty())
        emit dataChanged(index(0), index(static_cast<int>(entries_.size()) - 1), {ReferenceRole, ReferenceStyledRole});
}

QString OnlineResultsModel::journalShown(const std::string& journal) const {
    const QString name = QString::fromStdString(journal);
    return journals_.value(journal_key(name), name);
}

void OnlineResultsModel::append(std::vector<edi::online::Entry> entries) {
    if (entries.empty()) return;
    const int first = static_cast<int>(entries_.size());
    beginInsertRows({}, first, first + static_cast<int>(entries.size()) - 1);
    entries_.insert(entries_.end(), std::make_move_iterator(entries.begin()), std::make_move_iterator(entries.end()));
    endInsertRows();
    emit countChanged();
}

void OnlineResultsModel::assign(std::vector<edi::online::Entry> entries) {
    beginResetModel();
    entries_ = std::move(entries);
    endResetModel();
    emit countChanged();
}

const edi::online::Entry* OnlineResultsModel::at(int row) const {
    return row >= 0 && static_cast<std::size_t>(row) < entries_.size() ? &entries_[static_cast<std::size_t>(row)] : nullptr;
}

int OnlineChoiceModel::rowCount(const QModelIndex& parent) const { return parent.isValid() ? 0 : static_cast<int>(choices_.size()); }

QVariant OnlineChoiceModel::data(const QModelIndex& index, int role) const {
    if (!index.isValid() || index.row() < 0 || index.row() >= choices_.size()) return {};
    const Choice& c = choices_[index.row()];
    switch (role) {
        case KeyRole: return c.key;
        case NameRole: return c.name;
        case HintRole: return c.hint;
        case OptionsRole: return c.options;
        default: return {};
    }
}

QHash<int, QByteArray> OnlineChoiceModel::roleNames() const {
    return {{KeyRole, "key"}, {NameRole, "name"}, {HintRole, "hint"}, {OptionsRole, "options"}};
}

QStringList OnlineChoiceModel::optionsAt(int row) const { return row >= 0 && row < choices_.size() ? choices_[row].options : QStringList(); }

QString OnlineChoiceModel::hintAt(int row) const { return row >= 0 && row < choices_.size() ? choices_[row].hint : QString(); }

int OnlineChoiceModel::indexOfKey(const QString& key) const {
    for (int i = 0; i < choices_.size(); ++i)
        if (choices_[i].key == key) return i;
    return -1;
}

QString OnlineChoiceModel::keyAt(int row) const { return row >= 0 && row < choices_.size() ? choices_[row].key : QString(); }

void OnlineChoiceModel::assign(QList<Choice> choices) {
    beginResetModel();
    choices_ = std::move(choices);
    endResetModel();
    emit countChanged();
}

OnlineSearch::OnlineSearch(OnlineSourcesModel* sources, QObject* parent)
    : QObject(parent), sources_(sources), results_(new OnlineResultsModel(this)), sources_model_(new OnlineChoiceModel(this)),
      fields_model_(new OnlineChoiceModel(this)) {
    if (sources_) connect(sources_, &OnlineSourcesModel::sourcesChanged, this, [this] {
        refreshSources();
        // A source disabled or removed in Preferences leaves the selection: the first still offered, or none.
        if (!source_id_.isEmpty() && !eligible(source_id_)) setSourceId(sources_model_->keyAt(0));
    });
    refreshSources();
    refreshFields();
}

void OnlineSearch::refreshSources() {
    QList<OnlineChoiceModel::Choice> choices;
    if (sources_)
        for (const OnlineSourcesModel::Source& s : sources_->sourcesFor(kind_)) choices.append({s.id, s.name, {}});
    sources_model_->assign(std::move(choices));
    emit sourcesChanged();
}

void OnlineSearch::refreshFields() {
    field_values_.clear();
    const QStringList bases = sources_ ? sources_->urlsOf(source_id_) : QStringList();
    const auto cached = indexes_.value(bases.join(u'\n'));
    buildFields(sources_ && !codService(sources_->urlOf(source_id_)) ? cached.get() : nullptr);
}

void OnlineSearch::buildFields(const edi::online::Index* index) {
    QStringList keys;
    // Structures take the same fields from every source (the owner, 2026-11-04); for COD, Name is its free-text search.
    if (kind_ == QStringLiteral("structure")) keys = {QStringLiteral("id"), QStringLiteral("name"), QStringLiteral("formula"), QStringLiteral("elements"), QStringLiteral("space_group")};
    else keys = {QStringLiteral("id"), QStringLiteral("name"), QStringLiteral("formula"), QStringLiteral("elements"), QStringLiteral("radiation"), QStringLiteral("technique"), QStringLiteral("instrument")};
    QList<OnlineChoiceModel::Choice> choices;
    for (const QString& key : keys) {
        OnlineChoiceModel::Choice choice{key, {}, field_hint(key), {}};
        // Radiation and technique are selectors over the collection's own values (the owner, 2026-11-04).
        if (index != nullptr && (key == QStringLiteral("radiation") || key == QStringLiteral("technique"))) {
            const std::string kind = kind_.toStdString();
            for (const edi::online::Entry& e : index->entries) {
                if (e.kind != kind) continue;
                const QString value = QString::fromStdString(key == QStringLiteral("radiation") ? e.radiation : e.technique);
                if (!value.isEmpty() && !choice.options.contains(value)) choice.options.append(value);
            }
            choice.options.sort(Qt::CaseInsensitive);
        }
        choices.append(std::move(choice));
    }
    fields_model_->assign(std::move(choices));
    emit fieldsChanged();
}

void OnlineSearch::prepare() {
    if (!sources_) return;
    const QString base = sources_->urlOf(source_id_);
    if (base.isEmpty() || codService(base)) return;
    const QString source = source_id_;
    const QString kind = kind_;
    withIndex(sources_->urlsOf(source_id_), [this, source, kind](const edi::online::Index* index, const QString&, bool) {
        if (index == nullptr || source != source_id_ || kind != kind_) return;
        buildFields(index);
    });
}

void OnlineSearch::setField(const QString& key, const QString& value) { field_values_.insert(key, value); }

OnlineSearch::~OnlineSearch() = default;

void OnlineSearch::setKind(const QString& kind) {
    if (kind_ == kind) return;
    kind_ = kind;
    emit kindChanged();
    refreshSources();
    reset();
    if (sources_model_->indexOfKey(source_id_) < 0) setSourceId(sources_model_->keyAt(0));
    else refreshFields();
}

void OnlineSearch::setSourceId(const QString& id) {
    if (source_id_ == id) return;
    source_id_ = id;
    reset();
    refreshFields();
    emit sourceIdChanged();
    emit sourceNameChanged();
}

QString OnlineSearch::sourceName() const { return sources_ ? sources_->nameOf(source_id_) : QString(); }


QString OnlineSearch::alternativeName() const { return sources_ ? sources_->nameOf(alternative_id_) : QString(); }

bool OnlineSearch::eligible(const QString& id) const {
    if (!sources_ || id.isEmpty()) return false;
    for (const OnlineSourcesModel::Source& s : sources_->sourcesFor(kind_))
        if (s.id == id) return true;
    return false;
}

bool OnlineSearch::codService(const QString& url) const {
    return sources_ && sources_->isCod(source_id_) && !QUrl(url).isLocalFile() && QUrl(url).scheme() != QStringLiteral("file");
}

void OnlineSearch::search() {
    const QHash<QString, QString> values = field_values_;
    if (!sources_) return;
    const QString base = sources_->urlOf(source_id_);
    if (base.isEmpty() || !eligible(source_id_)) {
        fail(tr("Choose a source first"), false);
        return;
    }
    loadJournals();
    const int generation = ++generation_;
    message_.clear();
    detail_.clear();
    unreachable_ = false;
    alternative_id_.clear();
    emit messageChanged();
    emit detailChanged();
    emit unreachableChanged();
    emit alternativeIdChanged();
    emit alternativeNameChanged();
    results_->assign({});
    searched_ = false;
    emit searchedChanged();
    setBusy(true);
    edi::online::Query query;
    try {
        query = query_from(values);
        if (!query.formula.empty()) edi::online::hill_formula(query.formula);
        if (!query.elements.empty()) edi::online::element_list(query.elements);
    } catch (const std::exception& error) {
        fail(QString::fromUtf8(error.what()), false);
        return;
    }
    if (codService(base)) {
        // COD searched its metadata for the Name already (`text`); the other fields are checked here on each answer.
        // The service holds eight element slots and no result filter of its own: the whole query is applied to the
        // mapped answer, so nothing typed is silently dropped.
        chunk_rest_ = query;
        chunk_rest_.name.clear();
        chunk_rest_.formula_exact = true;  // COD's own formula search is exact; the collection's is amount-free
        chunk_base_ = base;
        const std::string root = base.toStdString();
        // The count first; up to 100 matches load at once, a longer answer by its id list, 100 at a time (the owner,
        // 2026-11-04).
        fetch(QUrl(QString::fromStdString(edi::online::cod_search_url(root, query, "count"))),
              [this, generation, query, root](const QByteArray& bytes, const QString& error, bool unreachable) {
                  if (generation != generation_) return;
                  if (!error.isEmpty()) {
                      fail(error, unreachable);
                      return;
                  }
                  bool numeric = false;
                  const int count = QString::fromUtf8(bytes).trimmed().toInt(&numeric);
                  if (!numeric || count < 0) {
                      fail(tr("%1 answered with no count").arg(sourceName()), false);
                      return;
                  }
                  total_ = count;
                  pagingChanged();
                  if (count <= kChunk) {
                      fetch(QUrl(QString::fromStdString(edi::online::cod_search_url(root, query))),
                            [this, generation](const QByteArray& bytes, const QString& error, bool unreachable) {
                                if (generation != generation_) return;
                                if (!error.isEmpty()) {
                                    fail(error, unreachable);
                                    return;
                                }
                                try {
                                    std::vector<edi::online::Entry> found = codAnswer(bytes);
                                    total_ = static_cast<int>(found.size());
                                    finish(std::move(found));
                                } catch (const std::exception& problem) {
                                    fail(QString::fromUtf8(problem.what()), false);
                                }
                            });
                      return;
                  }
                  fetch(QUrl(QString::fromStdString(edi::online::cod_search_url(root, query, "lst"))),
                        [this, generation](const QByteArray& bytes, const QString& error, bool unreachable) {
                            if (generation != generation_) return;
                            if (!error.isEmpty()) {
                                fail(error, unreachable);
                                return;
                            }
                            pending_ids_.clear();
                            for (const QByteArray& line : bytes.split('\n')) {
                                const QByteArray id = line.trimmed();
                                if (!id.isEmpty()) pending_ids_.push_back(id.toStdString());
                            }
                            total_ = static_cast<int>(pending_ids_.size());
                            pagingChanged();
                            loadChunk(generation, true);
                        });
              });
        return;
    }
    withIndex(sources_->urlsOf(source_id_), [this, generation, query](const edi::online::Index* index, const QString& error, bool unreachable) {
        if (generation != generation_) return;
        if (index == nullptr) {
            fail(error, unreachable);
            return;
        }
        std::vector<edi::online::Entry> found;
        for (const edi::online::Entry* entry : edi::online::search(*index, kind_.toStdString(), query)) found.push_back(*entry);
        finish(std::move(found));
    });
}

std::vector<edi::online::Entry> OnlineSearch::codAnswer(const QByteArray& bytes) const {
    edi::online::Index answered;
    answered.schema = "edi-data-index/1";
    answered.entries = edi::online::cod_entries(bytes.toStdString());
    std::vector<edi::online::Entry> found;
    for (const edi::online::Entry* e : edi::online::search(answered, kind_.toStdString(), chunk_rest_)) found.push_back(*e);
    return found;
}

void OnlineSearch::loadChunk(int generation, bool first) {
    if (pending_ids_.empty() || loading_more_) return;
    loading_more_ = true;
    chunk_error_.clear();
    pagingChanged();
    const std::size_t n = std::min<std::size_t>(kChunk, pending_ids_.size());
    const std::vector<std::string> ids(pending_ids_.begin(), pending_ids_.begin() + static_cast<std::ptrdiff_t>(n));
    fetch(QUrl(QString::fromStdString(edi::online::cod_details_url(chunk_base_.toStdString(), ids))),
          [this, generation, n, first](const QByteArray& bytes, const QString& error, bool) {
              if (generation != generation_) return;
              loading_more_ = false;
              std::vector<edi::online::Entry> found;
              try {
                  if (!error.isEmpty()) throw std::runtime_error(error.toStdString());
                  found = codAnswer(bytes);
              } catch (const std::exception& problem) {
                  // The rows shown stay; the line under them offers the chunk again.
                  chunk_error_ = QString::fromUtf8(problem.what());
                  if (first) setBusy(false);
                  pagingChanged();
                  return;
              }
              pending_ids_.erase(pending_ids_.begin(), pending_ids_.begin() + static_cast<std::ptrdiff_t>(n));
              if (first) {
                  finish(std::move(found));
              } else {
                  results_->append(std::move(found));
                  if (const auto it = memory_.find(memoryKey()); it != memory_.end()) it->entries = results_->entries();
              }
              if (const auto it = memory_.find(memoryKey()); it != memory_.end()) it->pending = pending_ids_;
              pagingChanged();
          });
}

void OnlineSearch::pagingChanged() {
    emit totalChanged();
    emit moreAvailableChanged();
    emit loadingMoreChanged();
    emit chunkErrorChanged();
}

void OnlineSearch::loadMore() {
    if (busy_ || loading_more_ || pending_ids_.empty()) return;
    loadChunk(generation_, results_->rowCount() == 0);
}

void OnlineSearch::useAlternative() {
    if (alternative_id_.isEmpty()) return;
    setSourceId(alternative_id_);
}

namespace {
// One downloaded file in its own folder under `downloads`, so two entries with one file name never overwrite each
// other; empty with the reason when it could not be written.
QString write_download(QTemporaryDir& downloads, const QString& name, const QByteArray& bytes, QString& error) {
    QDir folder(downloads.path());
    QString sub = QString::number(QDateTime::currentMSecsSinceEpoch(), 36);
    int n = 0;
    while (folder.exists(sub)) sub += QString::number(++n);
    folder.mkdir(sub);
    const QString path = folder.filePath(sub + u'/' + name);
    QFile out(path);
    if (!out.open(QIODevice::WriteOnly) || out.write(bytes) != bytes.size()) {
        error = QCoreApplication::translate("OnlineSearch", "The download could not be written to %1").arg(path);
        return {};
    }
    out.close();
    return path;
}
}  // namespace

void OnlineSearch::load(int row, QObject* project, QObject* target) {
    const edi::online::Entry* entry = results_->at(row);
    if (entry == nullptr || entry->files.empty() || !sources_) return;
    if (!eligible(source_id_)) {
        fail(tr("Choose a source first"), false);
        return;
    }
    const QPointer<QObject> requestProject(project), requestTarget(target);
    const bool newTarget = target == nullptr;
    const QStringList bases = sources_->urlsOf(source_id_);
    const OnlineEntry fields = entry_value(*entry);
    const QString kind = QString::fromStdString(entry->kind);
    const int generation = generation_;
    // The files to download, the experiment's linked structures first (their entries are in the same index), then
    // the entry's own; each checked against the index's size and digest before it reaches a loader.
    struct Wanted {
        QString path, name, digest, structure;
        long long bytes = -1;
    };
    auto wanted = std::make_shared<QList<Wanted>>();
    const auto plan = [wanted](const edi::online::Entry& e, const QString& structure) {
        const edi::online::File& f = e.files.front();
        const QString path = QString::fromStdString(f.path);
        wanted->append({path, QFileInfo(path).fileName(), QString::fromStdString(f.sha256), structure, f.bytes});
    };
    const auto start = [this, generation, fields, kind, bases, requestProject, requestTarget, newTarget, wanted] {
        setBusy(true);
        auto files = std::make_shared<QList<QUrl>>();
        auto step = std::make_shared<std::function<void()>>();
        *step = [this, generation, fields, kind, bases, requestProject, requestTarget, newTarget, wanted, files, step] {
            if (generation != generation_) return;
            if (wanted->isEmpty()) {
                setBusy(false);
                OnlineEntry delivered = fields;
                delivered.structureFiles = *files;
                delivered.structureFiles.removeLast();
                const QUrl own = files->last();
                emit fileReady(kind, own, delivered, requestProject.data(), requestTarget.data(), newTarget);
                return;
            }
            const Wanted next = wanted->takeFirst();
            fetchFrom(bases, next.path, [this, generation, fields, next, files, step](const QByteArray& bytes, const QString& error, bool unreachable) {
                if (generation != generation_) return;
                QString problem = error;
                if (problem.isEmpty()) problem = content_problem(bytes, next.bytes, next.digest, next.name);
                QString written;
                if (problem.isEmpty()) {
                    if (!downloads_) downloads_ = std::make_unique<QTemporaryDir>();
                    if (!downloads_->isValid()) problem = tr("No temporary folder for the download");
                    else written = write_download(*downloads_, next.name, bytes, problem);
                }
                if (!problem.isEmpty()) {
                    if (!next.structure.isEmpty())
                        fail(tr("%1 needs the structure %2, which could not be loaded: %3").arg(fields.name.isEmpty() ? fields.id : fields.name, next.structure, problem), false);
                    else
                        fail(problem, unreachable && error == problem);
                    return;
                }
                files->append(QUrl::fromLocalFile(written));
                (*step)();
            });
        };
        (*step)();
    };
    if (entry->structures.empty()) {
        plan(*entry, {});
        start();
        return;
    }
    // A full experiment brings the structures it links (the owner, 2026-11-04): their entries come from the index.
    const QStringList ids = fields.structureIds;
    const edi::online::Entry own = *entry;
    withIndex(bases, [this, generation, ids, own, plan, start](const edi::online::Index* index, const QString& error, bool unreachable) {
        if (generation != generation_) return;
        if (index == nullptr) {
            fail(error, unreachable);
            return;
        }
        for (const QString& id : ids) {
            const std::string wantedId = id.toStdString();
            const auto found = std::find_if(index->entries.begin(), index->entries.end(), [&wantedId](const edi::online::Entry& e) { return e.id == wantedId; });
            if (found == index->entries.end() || found->files.empty()) {
                fail(tr("%1 needs the structure %2, which the collection does not list").arg(QString::fromStdString(own.name.empty() ? own.id : own.name), id), false);
                return;
            }
            plan(*found, id);
        }
        plan(own, {});
        start();
    });
}

void OnlineSearch::reset() {
    ++generation_;
    pending_ids_.clear();
    total_ = -1;
    loading_more_ = false;
    chunk_error_.clear();
    pagingChanged();
    results_->assign({});
    message_.clear();
    unreachable_ = false;
    alternative_id_.clear();
    searched_ = false;
    setBusy(false);
    emit messageChanged();
    emit detailChanged();
    emit unreachableChanged();
    emit alternativeIdChanged();
    emit alternativeNameChanged();
    emit searchedChanged();
}

void OnlineSearch::finish(std::vector<edi::online::Entry> entries) {
    if (pending_ids_.empty()) total_ = static_cast<int>(entries.size());
    // This kind and source's last search, for the session: recall brings it back when the popup opens again.
    memory_.insert(memoryKey(), Remembered{field_values_, entries, -1, pending_ids_, total_, chunk_base_, chunk_rest_});
    results_->assign(std::move(entries));
    searched_ = true;
    setBusy(false);
    emit searchedChanged();
    pagingChanged();
}

bool OnlineSearch::recall() {
    const auto it = memory_.constFind(memoryKey());
    if (it == memory_.constEnd()) {
        reset();
        return false;
    }
    reset();
    field_values_ = it->fields;
    pending_ids_ = it->pending;
    total_ = it->total;
    chunk_base_ = it->base;
    chunk_rest_ = it->rest;
    results_->assign(it->entries);
    searched_ = true;
    emit searchedChanged();
    pagingChanged();
    return true;
}

void OnlineSearch::clear() {
    memory_.remove(memoryKey());
    field_values_.clear();
    reset();
}

QVariantMap OnlineSearch::fieldValues() const {
    QVariantMap out;
    for (auto it = field_values_.cbegin(); it != field_values_.cend(); ++it) out.insert(it.key(), it.value());
    return out;
}

void OnlineSearch::rememberSelection(int row) {
    const auto it = memory_.find(memoryKey());
    if (it != memory_.end()) it->selected = row;
}

int OnlineSearch::rememberedSelection() const {
    const auto it = memory_.constFind(memoryKey());
    return it == memory_.constEnd() ? -1 : it->selected;
}

void OnlineSearch::loadJournals() {
    if (journals_requested_ || !sources_) return;
    // The table lives in the EasyDiffraction collection (generated from JabRef's lists); with that source disabled
    // the references show the journals' full names.
    const QString collection = QStringLiteral("easydiffraction");
    bool enabled = false;
    for (const OnlineSourcesModel::Source& s : sources_->sourcesFor(QStringLiteral("structure"))) enabled = enabled || s.id == collection;
    const QStringList bases = enabled ? sources_->urlsOf(collection) : QStringList();
    if (bases.isEmpty()) return;
    journals_requested_ = true;
    fetchFrom(bases, QStringLiteral("journal-abbreviations.json"), [this](const QByteArray& bytes, const QString& error, bool) {
        if (!error.isEmpty()) {
            qCInfo(lcSearch, "journal abbreviations not read: %s", qPrintable(error));
            return;
        }
        const QJsonObject table = QJsonDocument::fromJson(bytes).object().value(QStringLiteral("abbreviations")).toObject();
        QHash<QString, QString> byName;
        for (auto it = table.constBegin(); it != table.constEnd(); ++it)
            if (it.value().isString() && !it.value().toString().isEmpty()) byName.insert(journal_key(it.key()), it.value().toString());
        qCInfo(lcSearch, "journal abbreviations: %lld", static_cast<long long>(byName.size()));
        results_->setJournalAbbreviations(std::move(byName));
    });
}

void OnlineSearch::fail(const QString& message, bool unreachable) {
    // A plain sentence in the popup; what exactly failed stays in `detail`, a tool tip.
    message_ = unreachable ? tr("%1 cannot be reached").arg(sourceName()) : message;
    detail_ = unreachable ? message : QString();
    unreachable_ = unreachable;
    alternative_id_.clear();
    if (unreachable && sources_) {
        // Another enabled source for this kind, the first that is not the one that failed.
        for (const OnlineSourcesModel::Source& s : sources_->sourcesFor(kind_)) {
            if (s.id != source_id_) {
                alternative_id_ = s.id;
                break;
            }
        }
    }
    setBusy(false);
    emit messageChanged();
    emit detailChanged();
    emit unreachableChanged();
    emit alternativeIdChanged();
    emit alternativeNameChanged();
}

void OnlineSearch::setBusy(bool busy) {
    if (busy_ == busy) return;
    busy_ = busy;
    emit busyChanged();
}

QUrl OnlineSearch::fileUrl(const QString& base, const QString& path) const { return joined_url(base, path); }

void OnlineSearch::withIndex(const QStringList& bases, const std::function<void(const edi::online::Index*, const QString&, bool)>& done) {
    const QString key = bases.join(u'\n');
    if (const auto cached = indexes_.value(key)) {
        done(cached.get(), {}, false);
        return;
    }
    fetchFrom(bases, QStringLiteral("index.json"), [this, key, done](const QByteArray& bytes, const QString& error, bool unreachable) {
        if (!error.isEmpty()) {
            done(nullptr, error, unreachable);
            return;
        }
        try {
            auto index = std::make_shared<edi::online::Index>(edi::online::parse_index(bytes.toStdString()));
            indexes_.insert(key, index);
            done(index.get(), {}, false);
        } catch (const std::exception& problem) {
            done(nullptr, QString::fromUtf8(problem.what()), false);
        }
    });
}

void OnlineSearch::fetch(const QUrl& url, Bytes done) { fetch_url(this, network_, url, std::move(done)); }
void OnlineSearch::fetchFrom(const QStringList& bases, const QString& path, Bytes done) { fetch_from(this, network_, bases, path, std::move(done)); }

}  // namespace edi_app
