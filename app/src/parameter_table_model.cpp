// SPDX-License-Identifier: BSD-3-Clause
#include "parameter_table_model.hpp"

#include "category_list_model.hpp"
#include "parameter_item.hpp"
#include "parameter_registry.hpp"

namespace edi_app {

namespace {
const QStringList kRoles{"parameter", "path",  "blockKind", "blockName", "category", "rowLabel", "name",
                         "displayName", "value", "uncertainty", "hasUncertainty", "free", "minimum",
                         "maximum", "units", "refinable"};
// One predicate serves menu counts and filtering, so parent groups include all their children.
bool matches_group(const QString& group, const QString& kind, const QString& category, const QString& name) {
    if (group.isEmpty()) return true;
    if (group == QLatin1String("@structure")) return kind == QLatin1String("structure");
    if (group == QLatin1String("@experiment")) return kind == QLatin1String("experiment");
    if (group == QLatin1String("@atoms")) return category == QLatin1String("atom_site") || category == QLatin1String("atom_site_aniso");
    if (group == QLatin1String("@coordinates")) return category == QLatin1String("atom_site") && name.startsWith(QLatin1String("fract_"));
    if (group == QLatin1String("@occupancies")) return category == QLatin1String("atom_site") && name == QLatin1String("occupancy");
    if (group == QLatin1String("@displacement")) return category == QLatin1String("atom_site_aniso") || (category == QLatin1String("atom_site") && name.startsWith(QLatin1String("adp_")));
    if (group == QLatin1String("@peakBroadening")) return category == QLatin1String("peak") && name.startsWith(QLatin1String("broad_"));
    if (group == QLatin1String("@peakMixing")) return category == QLatin1String("peak") && name.startsWith(QLatin1String("mixing_"));
    if (group == QLatin1String("@peakAsymmetry")) return category == QLatin1String("peak") &&
        (name.startsWith(QLatin1String("asym_")) || name.startsWith(QLatin1String("rise_alpha_")) || name.startsWith(QLatin1String("decay_beta_")));
    return category == group;
}
}  // namespace

ParameterTableModel::ParameterTableModel(ParameterRegistry& registry, QObject* parent)
    : RowTableModel(kRoles, parent), registry_(registry) {
    sync();
}

void ParameterTableModel::setExperimentScope(const QString& experiment) {
    experiment_scope_ = experiment;
}

void ParameterTableModel::sync() {
    QList<Row> rows;
    int free_count = 0;
    for (ParameterItem* item : registry_.items()) {
        if (!item->isRefinable() || !item->isFittable()) {
            continue;  // symmetry fixes or ties it, or a fixed setting: shown on its page, never fitted
        }
        if (!experiment_scope_.isEmpty() && item->blockKind() == QLatin1String("experiment") &&
            item->blockName() != experiment_scope_) {
            continue;  // a scan mode fits one experiment at a time: another experiment's parameter
        }
        free_count += item->isFree() ? 1 : 0;
        rows.append({item,
                     {QVariant::fromValue<QObject*>(item), item->path(), item->blockKind(), item->blockName(),
                      item->category(), item->rowLabel(), item->name(), item->displayName(), item->value(),
                      item->uncertainty(), item->hasUncertainty(), item->isFree(), item->minimum(), item->maximum(),
                      item->displayUnits(), item->isRefinable()}});
    }
    setTableRows(rows);
    const int fixed_count = count() - free_count;
    if (free_count != free_count_) {
        free_count_ = free_count;
        emit freeCountChanged();
    }
    if (fixed_count != fixed_count_) {
        fixed_count_ = fixed_count;
        emit fixedCountChanged();
    }
}

bool ParameterTableModel::setRole(int row, const QString& role, const QVariant& value) {
    auto* item = const_cast<ParameterItem*>(static_cast<const ParameterItem*>(keyAt(row)));
    if (item == nullptr) {
        return false;
    }
    if (role == QLatin1String("value")) {
        item->setValue(value.toDouble());
    } else if (role == QLatin1String("free")) {
        item->setFree(value.toBool());
    } else {
        return false;
    }
    return item->lastError().isEmpty();
}

ParameterFilterModel::ParameterFilterModel(QObject* parent) : QSortFilterProxyModel(parent) {}

void ParameterFilterModel::setSourceModel(QAbstractItemModel* source) {
    for (const auto& connection : source_connections_) {
        disconnect(connection);
    }
    source_connections_.clear();
    QSortFilterProxyModel::setSourceModel(source);
    if (source != nullptr) {
        source_connections_.append(connect(source, &QAbstractItemModel::modelReset, this, &ParameterFilterModel::refreshCategories));
        source_connections_.append(connect(source, &QAbstractItemModel::rowsInserted, this, &ParameterFilterModel::refreshCategories));
        source_connections_.append(connect(source, &QAbstractItemModel::rowsRemoved, this, &ParameterFilterModel::refreshCategories));
        source_connections_.append(connect(source, &QAbstractItemModel::dataChanged, this, &ParameterFilterModel::refreshCategories));
    }
    refreshCategories();
}

void ParameterFilterModel::refreshCategories() {
    struct Row { QString kind, category, name; };
    QList<Row> rows;
    if (sourceModel() != nullptr) {
        const auto roles = sourceModel()->roleNames();
        const auto value = [&](int row, const char* role) {
            return sourceModel()->data(sourceModel()->index(row, 0), roles.key(role)).toString();
        };
        for (int row = 0; row < sourceModel()->rowCount(); ++row) {
            rows.append({value(row, "blockKind"), value(row, "category"), value(row, "name")});
        }
    }
    QStringList categories;
    QVariantList groups;
    const auto countGroup = [&](const QString& key) {
        int count = 0;
        for (const Row& row : rows) {
            count += matches_group(key, row.kind, row.category, row.name) ? 1 : 0;
        }
        return count;
    };
    const auto add = [&](const QString& key, const QString& title, const QString& icon, bool datablock = false) {
        const int count = countGroup(key);
        if (count == 0 && !key.isEmpty()) return;
        categories.append(key);
        groups.append(QVariantMap{{"key", key}, {"title", title + QStringLiteral(" (%1)").arg(count)},
                                  {"icon", icon}, {"datablock", datablock}, {"count", count}});
    };
    // A subset must narrow its category; otherwise its second menu entry adds no choice.
    const auto addSubset = [&](const QString& parent, const QString& key, const QString& title, const QString& icon) {
        if (countGroup(key) < countGroup(parent)) add(key, title, icon);
    };
    add({}, tr("All categories"), {});
    for (const QString& kind : {QStringLiteral("structure"), QStringLiteral("experiment")}) {
        add(QLatin1Char('@') + kind, kind == QLatin1String("structure") ? tr("Structure") : tr("Experiment"),
            kind == QLatin1String("structure") ? QStringLiteral("layer-group") : QStringLiteral("microscope"), true);
        QStringList seen;
        for (const Row& row : rows) {
            if (row.kind != kind || seen.contains(row.category)) continue;
            seen.append(row.category);
            if (row.category == QLatin1String("atom_site") || row.category == QLatin1String("atom_site_aniso")) {
                if (seen.contains(QStringLiteral("@atoms"))) continue;
                seen.append(QStringLiteral("@atoms"));
                add(QStringLiteral("@atoms"), tr("Atom sites"), QStringLiteral("atom"));
                addSubset(QStringLiteral("@atoms"), QStringLiteral("@coordinates"), tr("Atomic coordinates"), QStringLiteral("map-marker-alt"));
                addSubset(QStringLiteral("@atoms"), QStringLiteral("@occupancies"), tr("Atomic occupancies"), QStringLiteral("fill"));
                addSubset(QStringLiteral("@atoms"), QStringLiteral("@displacement"), tr("Atomic displacement"), QStringLiteral("arrows-alt"));
                continue;
            }
            const auto presentation = category_presentation(row.category);
            QString title = QString::fromUtf8(presentation.title);
            if (row.category == QLatin1String("cell")) title = tr("Unit cell");
            if (title.isEmpty()) { title = row.category; title.replace(QLatin1Char('_'), QLatin1Char(' ')); }
            add(row.category, title, QString::fromUtf8(presentation.icon));
            if (row.category == QLatin1String("peak")) {
                addSubset(row.category, QStringLiteral("@peakBroadening"), tr("Peak broadening"), QStringLiteral("arrows-alt-h"));
                addSubset(row.category, QStringLiteral("@peakMixing"), tr("Peak mixing"), QStringLiteral("shapes"));
                addSubset(row.category, QStringLiteral("@peakAsymmetry"), tr("Peak asymmetry"), QStringLiteral("balance-scale-left"));
            }
        }
    }
    // Any additional block kind remains selectable when the parameter walk grows.
    for (const Row& row : rows) {
        if (row.kind == QLatin1String("structure") || row.kind == QLatin1String("experiment") || categories.contains(row.category)) continue;
        const auto presentation = category_presentation(row.category);
        QString title = QString::fromUtf8(presentation.title);
        if (title.isEmpty()) { title = row.category; title.replace(QLatin1Char('_'), QLatin1Char(' ')); }
        add(row.category, title, QString::fromUtf8(presentation.icon));
    }
    if (categories != categories_ || groups != category_groups_) {
        categories_ = categories;
        category_groups_ = groups;
        emit categoriesChanged();
    }
    if (!categories_.contains(category_filter_)) {
        setCategoryFilter({});
    }
}

void ParameterFilterModel::setCategoryFilter(const QString& category) {
    if (category != category_filter_) {
        beginFilterChange();
        category_filter_ = category;
        endFilterChange(Direction::Rows);
        emit categoryFilterChanged();
    }
}

QString ParameterFilterModel::text(int row, const QString& role) const {
    if (sourceModel() == nullptr || row < 0 || row >= rowCount()) {
        return {};
    }
    return data(index(row, 0), sourceModel()->roleNames().key(role.toUtf8())).toString();
}

void ParameterFilterModel::setNameFilter(const QString& filter) {
    if (filter != name_filter_) {
        beginFilterChange();
        name_filter_ = filter;
        endFilterChange(Direction::Rows);
        emit nameFilterChanged();
    }
}

ParameterItem* ParameterFilterModel::parameterAt(int row) const {
    if (sourceModel() == nullptr || row < 0 || row >= rowCount()) {
        return nullptr;
    }
    const int role = sourceModel()->roleNames().key("parameter");
    return qobject_cast<ParameterItem*>(data(index(row, 0), role).value<QObject*>());
}

bool ParameterFilterModel::shows(ParameterItem* parameter) const {
    if (parameter == nullptr) {
        return false;
    }
    for (int row = 0; row < rowCount(); ++row) {
        if (parameterAt(row) == parameter) {
            return true;
        }
    }
    return false;
}

void ParameterFilterModel::setVariability(Variability variability) {
    if (variability != variability_) {
        beginFilterChange();
        variability_ = variability;
        endFilterChange(Direction::Rows);
        emit variabilityChanged();
    }
}

bool ParameterFilterModel::filterAcceptsRow(int source_row, const QModelIndex& source_parent) const {
    const QModelIndex index = sourceModel()->index(source_row, 0, source_parent);
    const QHash<int, QByteArray> roles = sourceModel()->roleNames();
    const auto value = [&](const char* name) { return sourceModel()->data(index, roles.key(name)); };
    if (!matches_group(category_filter_, value("blockKind").toString(), value("category").toString(), value("name").toString())) {
        return false;
    }
    const bool free = value("free").toBool();
    if ((variability_ == Free && !free) || (variability_ == Fixed && free)) {
        return false;
    }
    return name_filter_.isEmpty() || value("path").toString().contains(name_filter_, Qt::CaseInsensitive) ||
           value("displayName").toString().contains(name_filter_, Qt::CaseInsensitive);
}

}  // namespace edi_app
