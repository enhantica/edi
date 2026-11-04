// SPDX-License-Identifier: BSD-3-Clause
#include "online_search.hpp"

#include <QCoreApplication>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QTimer>

#include <algorithm>
#include <stdexcept>

#include "online_fetch.hpp"
#include "online_sources.hpp"

namespace edi_app {
namespace {

QString field_hint(const QString& key) {
    static const QHash<QString, QString> hints{
        {QStringLiteral("formula"), QCoreApplication::translate("OnlineSearch", "Hill notation, for example B6 La")},
        {QStringLiteral("elements"), QCoreApplication::translate("OnlineSearch", "all of these, for example La Co")},
        {QStringLiteral("space_group"), QCoreApplication::translate("OnlineSearch", "Hermann-Mauguin, for example P m -3 m")},
        {QStringLiteral("radiation"), QCoreApplication::translate("OnlineSearch", "neutron or xray")},
        {QStringLiteral("technique"), QCoreApplication::translate("OnlineSearch", "powder, single crystal, time-of-flight…")},
    };
    return hints.value(key);
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
        default: return {};
    }
}

QHash<int, QByteArray> OnlineResultsModel::roleNames() const {
    return {{IdRole, "id"},           {KindRole, "kind"},           {NameRole, "name"},           {FormulaRole, "formula"},
            {SpaceGroupRole, "spaceGroup"}, {HasCellRole, "hasCell"},   {CellARole, "cellA"},         {CellBRole, "cellB"},
            {CellCRole, "cellC"},         {CellAlphaRole, "cellAlpha"}, {CellBetaRole, "cellBeta"},   {CellGammaRole, "cellGamma"},
            {RadiationRole, "radiation"}, {TechniqueRole, "technique"}, {InstrumentRole, "instrument"}, {SourceRole, "source"}};
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
        default: return {};
    }
}

QHash<int, QByteArray> OnlineChoiceModel::roleNames() const { return {{KeyRole, "key"}, {NameRole, "name"}, {HintRole, "hint"}}; }

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
    QStringList keys;
    if (sources_ && sources_->isCod(source_id_)) keys = {QStringLiteral("id"), QStringLiteral("formula"), QStringLiteral("elements"), QStringLiteral("space_group")};
    else if (kind_ == QStringLiteral("structure")) keys = {QStringLiteral("id"), QStringLiteral("name"), QStringLiteral("formula"), QStringLiteral("space_group")};
    else keys = {QStringLiteral("id"), QStringLiteral("name"), QStringLiteral("radiation"), QStringLiteral("technique"), QStringLiteral("instrument")};
    QList<OnlineChoiceModel::Choice> choices;
    for (const QString& key : keys) choices.append({key, {}, field_hint(key)});
    fields_model_->assign(std::move(choices));
    field_values_.clear();
    emit fieldsChanged();
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
        fetch(QUrl(QString::fromStdString(edi::online::cod_search_url(base.toStdString(), query))),
              [this, generation, query](const QByteArray& bytes, const QString& error, bool unreachable) {
                  if (generation != generation_) return;
                  if (!error.isEmpty()) {
                      fail(error, unreachable);
                      return;
                  }
                  try {
                      // The service holds eight element slots and no result filter of its own: the whole query
                      // is applied to the mapped answer, so nothing typed is silently dropped.
                      edi::online::Index answered;
                      answered.schema = "edi-data-index/1";
                      answered.entries = edi::online::cod_entries(bytes.toStdString());
                      std::vector<edi::online::Entry> found;
                      for (const edi::online::Entry* e : edi::online::search(answered, kind_.toStdString(), query)) found.push_back(*e);
                      finish(std::move(found));
                  } catch (const std::exception& problem) {
                      fail(QString::fromUtf8(problem.what()), false);
                  }
              });
        return;
    }
    withIndex(base, [this, generation, query](const edi::online::Index* index, const QString& error, bool unreachable) {
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

void OnlineSearch::useAlternative() {
    if (alternative_id_.isEmpty()) return;
    setSourceId(alternative_id_);
}

void OnlineSearch::load(int row, QObject* project, QObject* target) {
    const edi::online::Entry* entry = results_->at(row);
    if (entry == nullptr || entry->files.empty() || !sources_) return;
    if (!eligible(source_id_)) {
        fail(tr("Choose a source first"), false);
        return;
    }
    // The request keeps the project and target it was made for; a QPointer goes null when either is destroyed.
    const QPointer<QObject> requestProject(project);
    const QPointer<QObject> requestTarget(target);
    const bool newTarget = target == nullptr;
    const QString base = sources_->urlOf(source_id_);
    const QUrl url = fileUrl(base, QString::fromStdString(entry->files.front().path));
    const OnlineEntry fields = entry_value(*entry);
    const QString kind = QString::fromStdString(entry->kind);
    const QString name = QFileInfo(url.path()).fileName();
    const int generation = generation_;
    setBusy(true);
    fetch(url, [this, generation, fields, kind, name, requestProject, requestTarget, newTarget](const QByteArray& bytes, const QString& error, bool unreachable) {
        if (generation != generation_) return;
        if (!error.isEmpty()) {
            fail(error, unreachable);
            return;
        }
        if (!downloads_) downloads_ = std::make_unique<QTemporaryDir>();
        if (!downloads_->isValid()) {
            fail(tr("No temporary folder for the download"), false);
            return;
        }
        // Each download gets its own folder, so two entries with one file name never overwrite each other.
        QDir folder(downloads_->path());
        QString sub = QString::number(QDateTime::currentMSecsSinceEpoch(), 36);
        int n = 0;
        while (folder.exists(sub)) sub += QString::number(++n);
        folder.mkdir(sub);
        const QString path = folder.filePath(sub + u'/' + name);
        QFile out(path);
        if (!out.open(QIODevice::WriteOnly) || out.write(bytes) != bytes.size()) {
            fail(tr("The download could not be written to %1").arg(path), false);
            return;
        }
        out.close();
        setBusy(false);
        emit fileReady(kind, QUrl::fromLocalFile(path), fields, requestProject.data(), requestTarget.data(), newTarget);
    });
}

void OnlineSearch::reset() {
    ++generation_;
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
    results_->assign(std::move(entries));
    searched_ = true;
    setBusy(false);
    emit searchedChanged();
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

void OnlineSearch::withIndex(const QString& url, const std::function<void(const edi::online::Index*, const QString&, bool)>& done) {
    if (const auto cached = indexes_.value(url)) {
        done(cached.get(), {}, false);
        return;
    }
    fetch(fileUrl(url, QStringLiteral("index.json")), [this, url, done](const QByteArray& bytes, const QString& error, bool unreachable) {
        if (!error.isEmpty()) {
            done(nullptr, error, unreachable);
            return;
        }
        try {
            auto index = std::make_shared<edi::online::Index>(edi::online::parse_index(bytes.toStdString()));
            indexes_.insert(url, index);
            done(index.get(), {}, false);
        } catch (const std::exception& problem) {
            done(nullptr, QString::fromUtf8(problem.what()), false);
        }
    });
}

void OnlineSearch::fetch(const QUrl& url, Bytes done) { fetch_url(this, network_, url, std::move(done)); }

}  // namespace edi_app
