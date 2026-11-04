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

#include "online_sources.hpp"

namespace edi_app {
namespace {

QString cell_text(const std::vector<double>& cell) {
    if (cell.size() != 6) return {};
    QStringList parts;
    for (double v : cell) parts.append(QString::number(v, 'g', 6));
    return parts.join(u' ');
}

QString field_label(const QString& key) {
    static const QHash<QString, QString> labels{
        {QStringLiteral("id"), QCoreApplication::translate("OnlineSearch", "ID")},
        {QStringLiteral("name"), QCoreApplication::translate("OnlineSearch", "Name")},
        {QStringLiteral("formula"), QCoreApplication::translate("OnlineSearch", "Formula")},
        {QStringLiteral("elements"), QCoreApplication::translate("OnlineSearch", "Elements")},
        {QStringLiteral("space_group"), QCoreApplication::translate("OnlineSearch", "Space group")},
        {QStringLiteral("radiation"), QCoreApplication::translate("OnlineSearch", "Radiation")},
        {QStringLiteral("technique"), QCoreApplication::translate("OnlineSearch", "Technique")},
        {QStringLiteral("instrument"), QCoreApplication::translate("OnlineSearch", "Instrument")},
    };
    return labels.value(key, key);
}

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

edi::online::Query query_from(const QVariantMap& values) {
    edi::online::Query q;
    const auto s = [&values](const char* key) { return values.value(QLatin1String(key)).toString().toStdString(); };
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

QVariantMap entry_map(const edi::online::Entry& e) {
    return {{QStringLiteral("id"), QString::fromStdString(e.id)},
            {QStringLiteral("kind"), QString::fromStdString(e.kind)},
            {QStringLiteral("name"), QString::fromStdString(e.name)},
            {QStringLiteral("formula"), QString::fromStdString(e.formula)},
            {QStringLiteral("spaceGroup"), QString::fromStdString(e.space_group)},
            {QStringLiteral("radiation"), QString::fromStdString(e.radiation)},
            {QStringLiteral("technique"), QString::fromStdString(e.technique)},
            {QStringLiteral("instrument"), QString::fromStdString(e.instrument)},
            {QStringLiteral("source"), QString::fromStdString(e.source)},
            {QStringLiteral("format"), e.files.empty() ? QString() : QString::fromStdString(e.files.front().format)}};
}

bool unreachable_error(QNetworkReply::NetworkError error) {
    switch (error) {
        case QNetworkReply::ConnectionRefusedError:
        case QNetworkReply::RemoteHostClosedError:
        case QNetworkReply::HostNotFoundError:
        case QNetworkReply::TimeoutError:
        case QNetworkReply::NetworkSessionFailedError:
        case QNetworkReply::TemporaryNetworkFailureError:
        case QNetworkReply::UnknownNetworkError:
        case QNetworkReply::ProxyConnectionRefusedError:
        case QNetworkReply::ProxyNotFoundError:
        case QNetworkReply::ProxyTimeoutError:
        case QNetworkReply::ServiceUnavailableError:
        case QNetworkReply::OperationCanceledError:
        case QNetworkReply::SslHandshakeFailedError:
            return true;
        default:
            return false;
    }
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
        case CellRole: return cell_text(e.cell);
        case RadiationRole: return QString::fromStdString(e.radiation);
        case TechniqueRole: return QString::fromStdString(e.technique);
        case InstrumentRole: return QString::fromStdString(e.instrument);
        case SourceRole: return QString::fromStdString(e.source);
        default: return {};
    }
}

QHash<int, QByteArray> OnlineResultsModel::roleNames() const {
    return {{IdRole, "id"},           {KindRole, "kind"},           {NameRole, "name"},         {FormulaRole, "formula"},
            {SpaceGroupRole, "spaceGroup"}, {CellRole, "cell"},       {RadiationRole, "radiation"}, {TechniqueRole, "technique"},
            {InstrumentRole, "instrument"}, {SourceRole, "source"}};
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

OnlineSearch::OnlineSearch(OnlineSourcesModel* sources, QObject* parent)
    : QObject(parent), sources_(sources), results_(new OnlineResultsModel(this)) {
    if (sources_) connect(sources_, &OnlineSourcesModel::sourcesChanged, this, [this] {
        emit sourcesChanged();
        if (!source_id_.isEmpty() && sources_->urlOf(source_id_).isEmpty()) setSourceId({});
    });
}

OnlineSearch::~OnlineSearch() = default;

void OnlineSearch::setKind(const QString& kind) {
    if (kind_ == kind) return;
    kind_ = kind;
    emit kindChanged();
    emit fieldsChanged();
    emit sourcesChanged();
    reset();
    const QVariantList offered = sources();
    const bool keep = std::any_of(offered.begin(), offered.end(), [this](const QVariant& v) { return v.toMap().value(QStringLiteral("id")).toString() == source_id_; });
    if (!keep) setSourceId(offered.isEmpty() ? QString() : offered.first().toMap().value(QStringLiteral("id")).toString());
}

QVariantList OnlineSearch::sources() const { return sources_ ? sources_->sourcesFor(kind_) : QVariantList(); }

void OnlineSearch::setSourceId(const QString& id) {
    if (source_id_ == id) return;
    source_id_ = id;
    reset();
    emit sourceIdChanged();
    emit sourceNameChanged();
    emit fieldsChanged();
}

QString OnlineSearch::sourceName() const { return sources_ ? sources_->nameOf(source_id_) : QString(); }

QVariantList OnlineSearch::fields() const {
    QStringList keys;
    if (sources_ && sources_->isCod(source_id_)) keys = {QStringLiteral("id"), QStringLiteral("formula"), QStringLiteral("elements"), QStringLiteral("space_group")};
    else if (kind_ == QStringLiteral("structure")) keys = {QStringLiteral("id"), QStringLiteral("name"), QStringLiteral("formula"), QStringLiteral("space_group")};
    else keys = {QStringLiteral("id"), QStringLiteral("name"), QStringLiteral("radiation"), QStringLiteral("technique"), QStringLiteral("instrument")};
    QVariantList out;
    for (const QString& key : keys)
        out.append(QVariantMap{{QStringLiteral("key"), key}, {QStringLiteral("label"), field_label(key)}, {QStringLiteral("hint"), field_hint(key)}});
    return out;
}

QString OnlineSearch::alternativeName() const { return sources_ ? sources_->nameOf(alternative_id_) : QString(); }

bool OnlineSearch::codService(const QString& url) const {
    return sources_ && sources_->isCod(source_id_) && !QUrl(url).isLocalFile() && QUrl(url).scheme() != QStringLiteral("file");
}

void OnlineSearch::search(const QVariantMap& values) {
    if (!sources_) return;
    const QString base = sources_->urlOf(source_id_);
    if (base.isEmpty()) {
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
        if (!query.elements.empty()) edi::online::formula_elements(query.elements);
    } catch (const std::exception& error) {
        fail(QString::fromUtf8(error.what()), false);
        return;
    }
    if (codService(base)) {
        fetch(QUrl(QString::fromStdString(edi::online::cod_search_url(base.toStdString(), query))),
              [this, generation](const QByteArray& bytes, const QString& error, bool unreachable) {
                  if (generation != generation_) return;
                  if (!error.isEmpty()) {
                      fail(error, unreachable);
                      return;
                  }
                  try {
                      finish(edi::online::cod_entries(bytes.toStdString()));
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

void OnlineSearch::load(int row) {
    const edi::online::Entry* entry = results_->at(row);
    if (entry == nullptr || entry->files.empty() || !sources_) return;
    const QString base = sources_->urlOf(source_id_);
    const QUrl url = fileUrl(base, QString::fromStdString(entry->files.front().path));
    const QVariantMap fields = entry_map(*entry);
    const QString kind = QString::fromStdString(entry->kind);
    const QString name = QFileInfo(url.path()).fileName();
    const int generation = generation_;
    setBusy(true);
    fetch(url, [this, generation, fields, kind, name](const QByteArray& bytes, const QString& error, bool unreachable) {
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
        emit fileReady(kind, QUrl::fromLocalFile(path), fields);
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
        for (const QVariant& v : sources_->sourcesFor(kind_)) {
            const QString id = v.toMap().value(QStringLiteral("id")).toString();
            if (id != source_id_) {
                alternative_id_ = id;
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

QUrl OnlineSearch::fileUrl(const QString& base, const QString& path) const {
    QString root = base;
    while (root.endsWith(u'/')) root.chop(1);
    const QUrl url(root + u'/' + path);
    if (url.scheme().isEmpty()) return QUrl::fromLocalFile(root + u'/' + path);
    return url;
}

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

// Local files answer on the next event-loop turn, so callers see one asynchronous shape for every source.
void OnlineSearch::fetch(const QUrl& url, Bytes done) {
    if (url.isLocalFile() || url.scheme().isEmpty()) {
        const QString path = url.isLocalFile() ? url.toLocalFile() : url.toString();
        QTimer::singleShot(0, this, [path, done] {
            QFile file(path);
            // A folder that is not there is the offline stand-in for a host that does not answer.
            if (!file.exists()) {
                done({}, tr("%1 does not exist").arg(path), true);
                return;
            }
            if (!file.open(QIODevice::ReadOnly)) {
                done({}, tr("%1 cannot be read").arg(path), false);
                return;
            }
            done(file.readAll(), {}, false);
        });
        return;
    }
    if (network_ == nullptr) network_ = new QNetworkAccessManager(this);
    QNetworkRequest request(url);
    request.setAttribute(QNetworkRequest::RedirectPolicyAttribute, QNetworkRequest::NoLessSafeRedirectPolicy);
    request.setTransferTimeout(30000);
    QNetworkReply* reply = network_->get(request);
    connect(reply, &QNetworkReply::finished, this, [reply, done, url] {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
            const QString what = status > 0 ? tr("%1 answered %2").arg(url.toString()).arg(status) : reply->errorString();
            done({}, what, status == 0 && unreachable_error(reply->error()));
            return;
        }
        done(reply->readAll(), {}, false);
    });
}

}  // namespace edi_app
