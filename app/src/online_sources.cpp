// SPDX-License-Identifier: BSD-3-Clause
#include "online_sources.hpp"

#include <QCoreApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSettings>

#include "engine_setup.hpp"

namespace edi_app {
namespace {

const QString kStoreKey = QStringLiteral("Online/sources");
const QStringList kAllKinds{QStringLiteral("structure"), QStringLiteral("experiment"), QStringLiteral("data"), QStringLiteral("project")};

QList<OnlineSourcesModel::Source> builtin_sources() {
    return {
        {QStringLiteral("cod"), QStringLiteral("COD"), QStringLiteral("https://www.crystallography.net/cod"),
         {QStringLiteral("structure")}, true, true, {}},
        // One EasyDiffraction source, two locations in order: GitHub, then the mirror (the owner, 2026-11-04).
        {QStringLiteral("easydiffraction"), QStringLiteral("EasyDiffraction"),
         QStringLiteral("https://raw.githubusercontent.com/enhantica/edi-data/main"), kAllKinds, true, true, {},
         {QStringLiteral("https://data.easydiffraction.org")}},
    };
}

QString slug(const QString& name) {
    QString out;
    for (const QChar c : name.toLower())
        out += c.isLetterOrNumber() ? c : u'-';
    while (out.contains(QStringLiteral("--"))) out.replace(QStringLiteral("--"), QStringLiteral("-"));
    while (out.startsWith(u'-')) out.remove(0, 1);
    while (out.endsWith(u'-')) out.chop(1);
    return out.isEmpty() ? QStringLiteral("source") : out;
}

// `id=url` pairs from the command line and the environment, the command line last so it wins.
QList<QPair<QString, QString>> overrides() {
    QList<QPair<QString, QString>> pairs;
    const auto take = [&pairs](const QString& text) {
        const int eq = text.indexOf(u'=');
        if (eq <= 0) return;
        pairs.append({text.left(eq).trimmed(), text.mid(eq + 1).trimmed()});
    };
    for (const QString& item : qEnvironmentVariable("EDI_ONLINE_SOURCES").split(u';', Qt::SkipEmptyParts)) take(item);
    const QStringList arguments = QCoreApplication::arguments();
    for (int i = 0; i < arguments.size(); ++i) {
        if (arguments[i] == QStringLiteral("--online-source") && i + 1 < arguments.size()) take(arguments[++i]);
        else if (arguments[i].startsWith(QStringLiteral("--online-source="))) take(arguments[i].mid(16));
    }
    return pairs;
}

}  // namespace

OnlineSourcesModel::OnlineSourcesModel(QObject* parent) : QAbstractListModel(parent) {
    load();
    applyOverrides();
}

int OnlineSourcesModel::rowCount(const QModelIndex& parent) const { return parent.isValid() ? 0 : static_cast<int>(sources_.size()); }

QVariant OnlineSourcesModel::data(const QModelIndex& index, int role) const {
    if (!index.isValid() || index.row() >= sources_.size()) return {};
    const Source& s = sources_[index.row()];
    switch (role) {
        case IdRole: return s.id;
        case NameRole: return s.name;
        case UrlRole: return locations(s).join(QStringLiteral(", "));
        case KindsRole: return s.kinds;
        case BuiltinRole: return s.builtin;
        case EnabledRole: return s.enabled;
        case OverriddenRole: return !s.override.isEmpty();
        default: return {};
    }
}

QHash<int, QByteArray> OnlineSourcesModel::roleNames() const {
    return {{IdRole, "id"},         {NameRole, "name"},       {UrlRole, "url"},           {KindsRole, "kinds"},
            {BuiltinRole, "builtin"}, {EnabledRole, "enabled"}, {OverriddenRole, "overridden"}};
}

QList<OnlineSourcesModel::Source> OnlineSourcesModel::sourcesFor(const QString& kind) const {
    QList<Source> out;
    for (const Source& s : sources_)
        if (s.enabled && s.kinds.contains(kind)) out.append(s);
    return out;
}

QStringList OnlineSourcesModel::locations(const Source& s) {
    if (!s.override.isEmpty()) return {s.override};
    QStringList out{s.url};
    out.append(s.mirrors);
    return out;
}

QString OnlineSourcesModel::urlOf(const QString& id) const {
    const int row = indexOf(id);
    return row < 0 ? QString() : locations(sources_[row]).constFirst();
}

QStringList OnlineSourcesModel::urlsOf(const QString& id) const {
    const int row = indexOf(id);
    return row < 0 ? QStringList() : locations(sources_[row]);
}

QString OnlineSourcesModel::nameOf(const QString& id) const {
    const int row = indexOf(id);
    return row < 0 ? QString() : sources_[row].name;
}

QStringList OnlineSourcesModel::kindsOf(const QString& id) const {
    const int row = indexOf(id);
    return row < 0 ? QStringList() : sources_[row].kinds;
}

bool OnlineSourcesModel::isCod(const QString& id) const { return id == QStringLiteral("cod"); }

void OnlineSourcesModel::add() {
    Source s;
    s.name = tr("New source");
    s.id = slug(s.name);
    int n = 1;
    while (indexOf(s.id) >= 0) s.id = slug(s.name) + QStringLiteral("-") + QString::number(++n);
    s.kinds = kAllKinds;
    beginInsertRows({}, static_cast<int>(sources_.size()), static_cast<int>(sources_.size()));
    sources_.append(s);
    endInsertRows();
    store();
    emit countChanged();
    emit sourcesChanged();
}

void OnlineSourcesModel::remove(const QString& id) {
    const int row = indexOf(id);
    if (row < 0 || sources_[row].builtin) return;
    beginRemoveRows({}, row, row);
    sources_.removeAt(row);
    endRemoveRows();
    store();
    emit countChanged();
    emit sourcesChanged();
}

void OnlineSourcesModel::setEnabled(const QString& id, bool enabled) {
    const int row = indexOf(id);
    if (row < 0 || sources_[row].enabled == enabled) return;
    sources_[row].enabled = enabled;
    changed(row);
}

void OnlineSourcesModel::setName(const QString& id, const QString& name) {
    const int row = indexOf(id);
    if (row < 0 || sources_[row].builtin || name.trimmed().isEmpty() || sources_[row].name == name.trimmed()) return;
    sources_[row].name = name.trimmed();
    changed(row);
}

void OnlineSourcesModel::setUrl(const QString& id, const QString& url) {
    const int row = indexOf(id);
    if (row < 0 || sources_[row].builtin || sources_[row].url == url.trimmed()) return;
    sources_[row].url = url.trimmed();
    changed(row);
}

void OnlineSourcesModel::setKinds(const QString& id, const QStringList& kinds) {
    const int row = indexOf(id);
    if (row < 0 || sources_[row].builtin) return;
    QStringList known;
    for (const QString& k : kAllKinds)
        if (kinds.contains(k)) known.append(k);
    if (sources_[row].kinds == known) return;
    sources_[row].kinds = known;
    changed(row);
}

int OnlineSourcesModel::indexOf(const QString& id) const {
    for (int i = 0; i < sources_.size(); ++i)
        if (sources_[i].id == id) return i;
    return -1;
}

void OnlineSourcesModel::changed(int row) {
    emit dataChanged(index(row), index(row));
    store();
    emit sourcesChanged();
}

// The stored table is the built-in rows' enabled flags plus every user row; a built-in row's name, URL and kinds
// always come from the program, so an update can move them.
void OnlineSourcesModel::load() {
    sources_ = builtin_sources();
    const QSettings store(settings_file_path(), QSettings::IniFormat);
    const QJsonArray rows = QJsonDocument::fromJson(store.value(kStoreKey).toString().toUtf8()).array();
    for (const QJsonValue& value : rows) {
        const QJsonObject row = value.toObject();
        const QString id = row.value(QStringLiteral("id")).toString();
        const int at = indexOf(id);
        if (at >= 0) {
            sources_[at].enabled = row.value(QStringLiteral("enabled")).toBool(true);
            continue;
        }
        // A row an earlier build stored for a built-in that no longer exists (the mirror is a location now) is dropped.
        if (id.isEmpty() || id == QStringLiteral("easydiffraction-mirror")) continue;
        Source s;
        s.id = id;
        s.name = row.value(QStringLiteral("name")).toString();
        s.url = row.value(QStringLiteral("url")).toString();
        for (const QJsonValue& k : row.value(QStringLiteral("kinds")).toArray())
            if (kAllKinds.contains(k.toString())) s.kinds.append(k.toString());
        s.enabled = row.value(QStringLiteral("enabled")).toBool(true);
        sources_.append(s);
    }
}

void OnlineSourcesModel::store() const {
    QJsonArray rows;
    for (const Source& s : sources_) {
        QJsonObject row{{QStringLiteral("id"), s.id}, {QStringLiteral("enabled"), s.enabled}};
        if (!s.builtin) {
            row.insert(QStringLiteral("name"), s.name);
            row.insert(QStringLiteral("url"), s.url);
            row.insert(QStringLiteral("kinds"), QJsonArray::fromStringList(s.kinds));
        }
        rows.append(row);
    }
    QSettings store(settings_file_path(), QSettings::IniFormat);
    store.setValue(kStoreKey, QString::fromUtf8(QJsonDocument(rows).toJson(QJsonDocument::Compact)));
}

void OnlineSourcesModel::applyOverrides() {
    for (const auto& [id, url] : overrides()) {
        int row = indexOf(id);
        if (row < 0) {
            Source s;
            s.id = id;
            s.name = id;
            s.kinds = kAllKinds;
            sources_.append(s);
            row = static_cast<int>(sources_.size()) - 1;
        }
        sources_[row].override = url;
        sources_[row].enabled = true;
    }
}

}  // namespace edi_app
